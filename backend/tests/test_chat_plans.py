"""채팅 분석 계획 확장: 전월 대비 증감 지표."""

from pathlib import Path

import pytest

from app.analysis import compare, normalize
from app.core.errors import AppError

FIXTURES = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
NORMAL_FILES = ["coupang_2026-08.csv", "coupang_2026-09.csv", "naver_2026-08.csv", "naver_2026-09.csv"]


@pytest.fixture(scope="module")
def df():
    return normalize.normalize_files([(n, (FIXTURES / n).read_bytes()) for n in NORMAL_FILES])


def plan(**kwargs):
    return {"metric": "revenue", "group_by": None, "sort": None, "limit": 5, "period": None, **kwargs}


# ---- 전월 대비 증감 ----
def test_ad_spend_change_by_platform(df):
    """예시 질문 '광고비가 가장 많이 늘어난 플랫폼은?' — 쿠팡 900,000→1,200,000 (+33.3%), 네이버 600,000→720,000 (+20.0%)."""
    assert compare.run_plan(df, plan(metric="ad_spend_change", group_by="platform")) == [
        {"platform": "coupang", "ad_spend_previous": 900000, "ad_spend": 1200000, "ad_spend_change": 33.3},
        {"platform": "naver", "ad_spend_previous": 600000, "ad_spend": 720000, "ad_spend_change": 20.0},
    ]


def test_change_sort_asc_and_limit(df):
    rows = compare.run_plan(df, plan(metric="ad_spend_change", group_by="platform", sort="asc", limit=1))
    assert [r["platform"] for r in rows] == ["naver"]


def test_revenue_change_total(df):
    assert compare.run_plan(df, plan(metric="revenue_change")) == [
        {"revenue_previous": 10400000, "revenue": 12600000, "revenue_change": 21.2}
    ]


def test_roas_change_is_pp_from_raw_values(df):
    (row,) = compare.run_plan(df, plan(metric="roas_change_pp"))
    assert (row["roas_previous"], row["roas"], row["roas_change_pp"]) == (326.7, 312.5, -14.2)


def test_change_by_product_matches_product_across_months(df):
    rows = compare.run_plan(df, plan(metric="units_change", group_by="product", limit=10))
    assert {r["product_id"] for r in rows} == {"P001", "P002", "P003"}
    assert all(r["units_change"] is not None for r in rows)


def test_change_for_first_month_has_no_previous(df):
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(metric="revenue_change", period="2026-08"))
    assert exc.value.code == "PREVIOUS_PERIOD_NOT_FOUND"


def test_change_grouped_by_period_is_rejected(df):
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(metric="revenue_change", group_by="period"))
    assert exc.value.code == "UNSUPPORTED_PLAN"


def test_change_unknown_period(df):
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(metric="revenue_change", period="2026-10"))
    assert exc.value.code == "PERIOD_NOT_FOUND"


# ---- 스마트스토어 지표 ----
SMARTSTORE = FIXTURES / "smartstore"


@pytest.fixture(scope="module")
def store_df():
    """스마트스토어 판매 분석 8·9월 + 쿠팡 9월 (스마트스토어 지표는 스마트스토어 행만으로 계산돼야 한다)."""
    paths = [*sorted(SMARTSTORE.glob("sales_*_sample.xlsx")), FIXTURES / "coupang_2026-09.csv"]
    return normalize.normalize_files([(p.name, p.read_bytes()) for p in paths])


def test_store_rate_total_matches_store_kpis(store_df):
    from app.analysis import kpi

    store = kpi.compute_store_kpis(store_df)
    for metric in ("conversion_rate", "refund_rate", "discount_rate", "aov", "visits", "gross_revenue"):
        assert compare.run_plan(store_df, plan(metric=metric)) == [{metric: store["current"][metric]}]


def test_lowest_conversion_product(store_df):
    rows = compare.run_plan(store_df, plan(metric="conversion_rate", group_by="product", sort="asc", limit=1))
    assert rows[0]["product_name"] == "기계식 키보드"


def test_refund_rate_spike_product(store_df):
    """픽스처 패턴: 블루투스 스피커 환불률 급증."""
    rows = compare.run_plan(store_df, plan(metric="refund_rate_change_pp", group_by="product", limit=1))
    assert rows[0]["product_name"] == "블루투스 스피커" and rows[0]["refund_rate_change_pp"] > 10


def test_store_change_total_matches_store_kpis(store_df):
    from app.analysis import kpi

    change = kpi.compute_store_kpis(store_df)["change"]
    for metric in ("conversion_rate_change_pp", "discount_rate_change_pp", "visits_change", "aov_change"):
        (row,) = compare.run_plan(store_df, plan(metric=metric))
        assert row[metric] == change[metric], metric


def test_store_metric_platform_only_has_store(store_df):
    rows = compare.run_plan(store_df, plan(metric="visits", group_by="platform"))
    assert [r["platform"] for r in rows] == ["naver_store"]


def test_store_metric_without_store_files(df):
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(metric="conversion_rate"))
    assert exc.value.code == "STORE_DATA_NOT_FOUND"


def test_core_metrics_exclude_store_rows_when_ads_reports_exist(store_df):
    """kpis 와 같은 규칙: 광고 리포트가 있으면 매출 등 기본 지표는 스마트스토어 행을 빼고 계산한다."""
    rows = compare.run_plan(store_df, plan(metric="revenue", group_by="platform"))
    assert [r["platform"] for r in rows] == ["coupang"]


def test_core_metrics_use_store_rows_when_only_store(store_df):
    only_store = store_df[store_df["platform"] == "naver_store"]
    rows = compare.run_plan(only_store, plan(metric="revenue", group_by="platform"))
    assert [r["platform"] for r in rows] == ["naver_store"]


def test_api_mixed_upload_can_answer_store_metric(monkeypatch):
    """회귀: 광고 리포트와 스마트스토어 파일을 함께 올리면 질문에서 스마트스토어 행이 빠져 STORE_DATA_NOT_FOUND 가 났다."""
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from app.main import app

    class FakeAI:
        def create_analysis_plan(self, question, **kwargs):
            return SimpleNamespace(status="ok", plan={**plan(metric="refund_rate_change_pp", group_by="product", limit=1)}, reason=None)

        def create_insight(self, kpis, comparison, signals, *, plan=None, answer=None):
            return {"status": "ok", "summary": "s"}

    monkeypatch.setattr("app.routers.analyze._load_ai", lambda: FakeAI())
    paths = [*sorted(SMARTSTORE.glob("sales_*_sample.xlsx")), FIXTURES / "coupang_2026-08.csv", FIXTURES / "coupang_2026-09.csv"]
    res = TestClient(app).post("/api/analyze", files=[("files", (p.name, p.read_bytes())) for p in paths], data={"question": "q"})
    insight = res.json()["insight"]
    assert insight["status"] == "ok", insight
    assert insight["answer"][0]["product_name"] == "블루투스 스피커"


# ---- '전월' = 달력상 바로 앞 달 (D 리뷰 #23) ----
def _synthetic(periods_revenue):
    import pandas as pd

    return pd.DataFrame(
        [
            {"period": p, "platform": "coupang", "product_id": "P1", "product_name": "a",
             "revenue": r, "orders": 1, "units": 1, "ad_spend": 10, "ad_revenue": 20}
            for p, r in periods_revenue
        ]
    )


def test_change_requires_calendar_previous_month_not_previous_upload():
    """회귀: 7월·9월만 있으면 9월 '전월 대비'를 7월과 비교해 +100% 로 답했다."""
    df = _synthetic([("2026-07", 100), ("2026-09", 200)])
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(metric="revenue_change"))
    assert exc.value.code == "PREVIOUS_PERIOD_NOT_FOUND"
    assert exc.value.details["previous_period"] == "2026-08"
    assert "2026-08" in exc.value.message


def test_change_with_gap_still_works_for_month_that_has_previous():
    df = _synthetic([("2026-06", 50), ("2026-07", 100), ("2026-09", 200)])
    assert compare.run_plan(df, plan(metric="revenue_change", period="2026-07")) == [
        {"revenue_previous": 50, "revenue": 100, "revenue_change": 100.0}
    ]


def test_change_across_year_boundary():
    df = _synthetic([("2025-12", 100), ("2026-01", 150)])
    (row,) = compare.run_plan(df, plan(metric="revenue_change"))
    assert (row["revenue_previous"], row["revenue_change"]) == (100, 50.0)


def test_change_january_without_december():
    df = _synthetic([("2025-11", 100), ("2026-01", 150)])
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(metric="revenue_change"))
    assert exc.value.details["previous_period"] == "2025-12"


@pytest.mark.parametrize(("period", "expected"), [("2026-09", "2026-08"), ("2026-01", "2025-12"), ("2026-12", "2026-11")])
def test_previous_month(period, expected):
    assert compare._previous_month(period) == expected
