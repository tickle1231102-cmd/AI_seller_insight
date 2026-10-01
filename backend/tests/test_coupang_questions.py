"""쿠팡 판매 분석(옵션별 지표) 질문: 질문 사전 검사 → run_plan → 근거 문장."""

from pathlib import Path

import pytest

from app.ai.facts import EvidenceCatalogue
from app.ai.models import AnalysisPlan
from app.ai.question_policy import inspect_question
from app.analysis import compare, kpi, normalize
from app.core.errors import AppError

FIXTURES = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
SAMPLE = (FIXTURES / "exports" / "SELLER_INSIGHTS_VENDOR_ITEM_METRICS_SAMPLE_coupang.xlsx").read_bytes()


@pytest.fixture(scope="module")
def data():
    # 같은 샘플을 8월·9월로 올리고, 9월은 첫 옵션의 취소 수량만 늘린다.
    df, sales = normalize.normalize_with_coupang_sales([("cs_2026-08.xlsx", SAMPLE), ("cs_2026-09.xlsx", SAMPLE)])
    first = sales.index[sales["period"] == "2026-09"][0]
    sales.loc[first, "cancel_units"] += 10
    return df, sales


def plan(**kwargs):
    return {"metric": "coupang_conversion_rate", "group_by": None, "sort": None, "limit": 5, "period": None, **kwargs}


@pytest.mark.parametrize(("question", "expected"), [
    ("쿠팡 전환율 가장 낮은 상품 3개", {"metric": "coupang_conversion_rate", "group_by": "product", "sort": "asc", "limit": 3}),
    ("장바구니율 높은 상품", {"metric": "coupang_cart_rate", "group_by": "product", "sort": "desc"}),
    ("9월 취소율", {"metric": "coupang_cancel_rate", "group_by": None, "period": "2026-09"}),
    ("쿠팡 방문자 전월 대비 증감", {"metric": "coupang_visits_change", "group_by": None}),
    ("쿠팡 취소율 늘어난 상품", {"metric": "coupang_cancel_rate_change_pp", "group_by": "product"}),
    ("쿠팡 객단가", {"metric": "coupang_aov", "group_by": None}),
])
def test_policy_maps_coupang_questions(question, expected):
    r = inspect_question(question, periods=["2026-08", "2026-09"])
    assert r.reason is None
    assert {k: r.expected.get(k) for k in expected} == expected


@pytest.mark.parametrize("question", ["쿠팡 매출", "쿠팡 ROAS"])
def test_policy_still_blocks_single_platform_filter(question):
    assert inspect_question(question, periods=["2026-09"]).reason


def test_policy_keeps_smartstore_metric_without_coupang():
    assert inspect_question("전환율 상품별", periods=["2026-09"]).expected["metric"] == "conversion_rate"


def test_totals_match_coupang_section(data):
    df, sales = data
    section = kpi.compute_coupang_kpis(sales)
    for metric in ("coupang_visits", "coupang_aov", "coupang_conversion_rate", "coupang_cart_rate", "coupang_cancel_rate"):
        assert compare.run_plan(df, plan(metric=metric), sales) == [{metric: section["current"][metric.removeprefix("coupang_")]}]


def test_change_by_product_finds_cancel_spike(data):
    df, sales = data
    (row,) = compare.run_plan(df, plan(metric="coupang_cancel_rate_change_pp", group_by="product", limit=1), sales)
    first = sales[sales["period"] == "2026-09"].iloc[0]
    assert row["product_id"] == first["product_id"] and row["coupang_cancel_rate_change_pp"] > 0
    assert row["coupang_cancel_rate"] > row["coupang_cancel_rate_previous"]


def test_platform_group_is_coupang_only(data):
    df, sales = data
    rows = compare.run_plan(df, plan(group_by="platform"), sales)
    assert [r["platform"] for r in rows] == ["coupang"]


def test_missing_coupang_sales_is_explained(data):
    df, _ = data
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(), None)
    assert exc.value.code == "COUPANG_SALES_DATA_NOT_FOUND"


def test_evidence_is_labeled_as_coupang(data):
    df, sales = data
    core = normalize.core_rows(df)
    p = AnalysisPlan(metric="coupang_cart_rate", group_by="product", limit=1)
    answer = compare.run_plan(df, p, sales)
    catalogue = EvidenceCatalogue.build(kpi.compute_kpis(core), compare.build_comparison(core), [], p, answer)
    fact = catalogue.facts["answer.0.coupang_cart_rate"]
    assert fact.text.startswith("쿠팡 판매 분석 최신 업로드 월 / 쿠팡 / ") and "쿠팡 장바구니율" in fact.text
    assert not catalogue.conflicts


def test_analyze_route_answers_coupang_question(monkeypatch):
    import json
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from app.ai.models import PlannerResult
    from app.main import app
    from app.routers import analyze as analyze_router

    p = AnalysisPlan(metric="coupang_cart_rate", group_by="product", limit=2)
    stub = SimpleNamespace(
        create_analysis_plan=lambda question, periods: PlannerResult(status="ok", plan=p),
        create_insight=lambda *a, **k: {"status": "ok", "summary": "요약"},
    )
    monkeypatch.setattr(analyze_router, "_load_ai", lambda: stub)
    res = TestClient(app).post("/api/analyze", files=[("files", ("cs.xlsx", SAMPLE))],
                               data={"question": "장바구니율 높은 상품 2개", "periods": json.dumps({"cs.xlsx": "2026-09"})})
    insight = res.json()["insight"]
    assert insight["status"] == "ok" and len(insight["answer"]) == 2
    assert insight["answer"][0]["coupang_cart_rate"] >= insight["answer"][1]["coupang_cart_rate"]


def test_store_metric_with_only_coupang_sales_hints_coupang_prefix(data):
    df, sales = data
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(metric="conversion_rate"), sales)
    assert exc.value.code == "STORE_DATA_NOT_FOUND" and "쿠팡 전환율" in exc.value.message
