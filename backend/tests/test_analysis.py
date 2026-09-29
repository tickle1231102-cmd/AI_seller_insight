"""normalize_files · kpi · compare · signals · run_plan 테스트. 정답은 shared/fixtures/expected_kpis.json."""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analysis import compare, kpi, normalize, signals
from app.core.errors import AppError
from app.main import app

FIXTURES = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
EXPECTED = {k: v for k, v in json.loads((FIXTURES / "expected_kpis.json").read_text(encoding="utf-8")).items() if k != "_note"}
NORMAL_FILES = ["naver_2026-09.csv", "coupang_2026-08.csv", "naver_2026-08.csv", "coupang_2026-09.csv"]  # 일부러 뒤섞은 순서
client = TestClient(app, raise_server_exceptions=False)

COUPANG_HEADER = "상품ID,상품명,총매출,주문,판매량,광고비,광고매출"


def csv_bytes(*rows: str, header: str = COUPANG_HEADER) -> bytes:
    return ("\n".join([header, *rows]) + "\n").encode("utf-8")


def make_df(*rows) -> pd.DataFrame:
    """(period, platform, product_id, revenue, orders, units, ad_spend, ad_revenue) → 정규화 DataFrame."""
    return pd.DataFrame(
        [
            {"period": p, "platform": pl, "product_id": pid, "product_name": f"상품{pid}", "revenue": r, "orders": o,
             "units": u, "ad_spend": s, "ad_revenue": a}
            for p, pl, pid, r, o, u, s, a in rows
        ]
    )


@pytest.fixture(scope="module")
def df():
    return normalize.normalize_files([(n, (FIXTURES / n).read_bytes()) for n in NORMAL_FILES])


def plan(**kwargs):
    return {"metric": "revenue", "group_by": None, "sort": None, "limit": 5, "period": None, **kwargs}


# ---- normalize_files ----
def test_normalize_files_matches_expected_rows(df):
    assert list(df.columns) == normalize.NORMALIZED_COLUMNS
    assert df.to_dict("records") == EXPECTED["rows"]


def test_normalize_files_uses_plain_python_types(df):
    """B 가 JSON 으로 내보내므로 numpy 타입이 섞이면 안 된다."""
    for row in df.to_dict("records"):
        assert all(type(row[f]) is int for f in ("revenue", "orders", "units", "ad_spend", "ad_revenue"))
        assert type(row["period"]) is str and type(row["product_id"]) is str


def test_normalize_files_rounds_money_to_int():
    df = normalize.normalize_files([("coupang_2026-09.csv", csv_bytes("P001,이어폰,1000.6,3,4,200.4,500.5"))])
    row = df.to_dict("records")[0]
    assert (row["revenue"], row["ad_spend"], row["ad_revenue"]) == (1001, 200, 500)
    assert all(type(row[f]) is int for f in ("revenue", "ad_spend", "ad_revenue"))


def test_normalize_files_empty_number_cell_is_zero():
    df = normalize.normalize_files([("coupang_2026-09.csv", csv_bytes("P001,이어폰,1000,3,4,,"))])
    row = df.to_dict("records")[0]
    assert (row["ad_spend"], row["ad_revenue"]) == (0, 0)


def test_normalize_files_error_names_the_failing_file():
    good = ("coupang_2026-08.csv", (FIXTURES / "coupang_2026-08.csv").read_bytes())
    bad = ("coupang_2026-09.csv", csv_bytes("P001,이어폰,abc,3,4,1,2"))
    with pytest.raises(AppError) as exc:
        normalize.normalize_files([good, bad])
    assert exc.value.code == "INVALID_NUMBER"
    assert exc.value.details["file"] == "coupang_2026-09.csv"


def test_normalize_files_no_files_gives_empty_frame():
    df = normalize.normalize_files([])
    assert df.empty and list(df.columns) == normalize.NORMALIZED_COLUMNS


# ---- kpi / comparison / signals (fixture 정답) ----
def test_compute_kpis_matches_expected(df):
    assert kpi.compute_kpis(df) == EXPECTED["kpis"]


def test_build_comparison_matches_expected(df):
    assert compare.build_comparison(df) == EXPECTED["comparison"]


def test_detect_signals_matches_expected(df):
    k = kpi.compute_kpis(df)
    assert signals.detect_signals(k, compare.build_comparison(df)) == EXPECTED["signals"]


# ---- kpi 경계 ----
def test_single_month_has_no_previous(df):
    k = kpi.compute_kpis(df[df["period"] == "2026-09"])
    assert k["previous_period"] is None and k["previous"] is None
    assert set(k["change"].values()) == {None}
    assert k["current"] == EXPECTED["kpis"]["current"]
    assert signals.detect_signals(k, compare.build_comparison(df[df["period"] == "2026-09"])) == []


def test_zero_ad_spend_gives_null_roas_not_zero_or_inf():
    d = make_df(("2026-08", "coupang", "P1", 1000, 1, 1, 0, 0), ("2026-09", "coupang", "P1", 2000, 2, 2, 0, 0))
    k = kpi.compute_kpis(d)
    assert k["current"]["roas"] is None and k["previous"]["roas"] is None
    assert k["change"]["roas_change_pp"] is None
    assert k["change"]["ad_spend_change"] is None  # 전월 0 → 증감률 null
    assert k["change"]["revenue_change"] == 100.0


def test_previous_zero_revenue_change_is_null():
    d = make_df(("2026-08", "naver", "P1", 0, 0, 0, 100, 300), ("2026-09", "naver", "P1", 500, 1, 1, 100, 300))
    assert kpi.compute_kpis(d)["change"]["revenue_change"] is None


def test_compares_latest_with_previous_available_month_even_if_gap():
    d = make_df(
        ("2026-05", "coupang", "P1", 100, 1, 1, 10, 20),
        ("2026-07", "coupang", "P1", 200, 1, 1, 10, 20),
        ("2026-09", "coupang", "P1", 300, 1, 1, 10, 20),
    )
    k = kpi.compute_kpis(d)
    assert (k["period"], k["previous_period"]) == ("2026-09", "2026-07")
    assert k["change"]["revenue_change"] == 50.0


def test_roas_change_uses_unrounded_values():
    """원값 326.66 → 312.54 는 -14.12 → -14.1. 표시값(326.7, 312.5)끼리 빼면 -14.2 가 된다."""
    d = make_df(("2026-08", "coupang", "P1", 1, 1, 1, 10000, 32666), ("2026-09", "coupang", "P1", 1, 1, 1, 10000, 31254))
    k = kpi.compute_kpis(d)
    assert (k["previous"]["roas"], k["current"]["roas"]) == (326.7, 312.5)
    assert k["change"]["roas_change_pp"] == -14.1


def test_platform_roas_is_recomputed_not_averaged():
    d = make_df(
        ("2026-09", "coupang", "P1", 0, 0, 0, 100, 500),  # 500%
        ("2026-09", "coupang", "P2", 0, 0, 0, 900, 900),  # 100% → 평균 300% 아님, 합계 1400/1000 = 140%
    )
    assert compare.build_comparison(d)["by_platform"][0]["roas"] == 140.0


def test_by_platform_is_latest_month_and_trend_is_all_months(df):
    d = df[~((df["period"] == "2026-09") & (df["platform"] == "naver"))]  # 9월엔 쿠팡만
    c = compare.build_comparison(d)
    assert [p["platform"] for p in c["by_platform"]] == ["coupang"]
    assert [t["period"] for t in c["trend"]] == ["2026-08", "2026-09"]


# ---- signals 경계 ----
def kpis_with(**change):
    base = {f"{f}_change": None for f in ("revenue", "orders", "units", "ad_spend", "ad_revenue")}
    return {"current": {"roas": 300.0}, "change": {**base, "roas_change_pp": None, **change}}


NO_PLATFORMS = {"by_platform": [], "trend": []}


def test_revenue_down_signal():
    result = signals.detect_signals(kpis_with(revenue_change=-5.0), NO_PLATFORMS)
    assert result == [{"signal": "REVENUE_DOWN", "platform": "all", "revenue_change": -5.0}]


def test_spend_growth_signal_needs_both_conditions():
    assert signals.detect_signals(kpis_with(ad_spend_change=10.0, roas_change_pp=0.0), NO_PLATFORMS) == []
    assert signals.detect_signals(kpis_with(ad_spend_change=-10.0, roas_change_pp=-5.0), NO_PLATFORMS) == []
    assert signals.detect_signals(kpis_with(ad_spend_change=None, roas_change_pp=-5.0), NO_PLATFORMS) == []


def test_low_roas_platform_threshold_is_strictly_below_80_percent():
    comparison = {
        "by_platform": [
            {"platform": "coupang", "roas": 239.9},  # 300 × 0.8 = 240 미만
            {"platform": "naver", "roas": 240.0},  # 경계는 신호 아님
        ],
        "trend": [],
    }
    result = signals.detect_signals(kpis_with(), comparison)
    assert result == [{"signal": "LOW_ROAS_PLATFORM", "platform": "coupang", "roas": 239.9, "overall_roas": 300.0}]


def test_no_signals_gives_empty_list():
    assert signals.detect_signals(kpis_with(revenue_change=3.0, ad_spend_change=1.0, roas_change_pp=1.0), NO_PLATFORMS) == []


# ---- run_plan ----
def test_run_plan_group_by_platform_default_sort_desc_latest_month(df):
    assert compare.run_plan(df, plan(group_by="platform")) == [
        {"platform": "coupang", "revenue": 8000000},
        {"platform": "naver", "revenue": 4600000},
    ]


def test_run_plan_sort_asc_and_limit(df):
    result = compare.run_plan(df, plan(metric="roas", group_by="platform", sort="asc", limit=1))
    assert result == [{"platform": "coupang", "roas": 291.7}]


def test_run_plan_specific_period(df):
    result = compare.run_plan(df, plan(group_by="platform", period="2026-08"))
    assert result == [{"platform": "coupang", "revenue": 6600000}, {"platform": "naver", "revenue": 3800000}]


def test_run_plan_no_group_by_is_single_total_row(df):
    assert compare.run_plan(df, plan(metric="orders")) == [{"orders": 830}]
    assert compare.run_plan(df, plan(metric="roas", period="2026-08")) == [{"roas": 326.7}]


def test_run_plan_group_by_period_uses_all_months_when_period_is_none(df):
    assert compare.run_plan(df, plan(group_by="period")) == [
        {"period": "2026-09", "revenue": 12600000},
        {"period": "2026-08", "revenue": 10400000},
    ]
    assert compare.run_plan(df, plan(group_by="period", sort="asc", limit=1)) == [{"period": "2026-08", "revenue": 10400000}]


def test_run_plan_group_by_period_with_period_keeps_that_month_only(df):
    assert compare.run_plan(df, plan(group_by="period", period="2026-08")) == [{"period": "2026-08", "revenue": 10400000}]


def test_run_plan_group_by_product_sums_across_platforms(df):
    result = compare.run_plan(df, plan(group_by="product", limit=2))
    assert result == [
        {"product_id": "P001", "product_name": "무선 이어폰", "revenue": 6300000},
        {"product_id": "P002", "product_name": "보조배터리", "revenue": 3780000},
    ]


def test_run_plan_product_roas_is_recomputed(df):
    """9월 P001 = 쿠팡 1,750,000 + 네이버 1,250,000 / 광고비 600,000 + 360,000 → 3,000,000 / 960,000."""
    by_id = {r["product_id"]: r["roas"] for r in compare.run_plan(df, plan(metric="roas", group_by="product", limit=10))}
    assert by_id["P001"] == 312.5


def test_run_plan_limit_none_falls_back_to_default(df):
    d = make_df(*[("2026-09", "coupang", f"P{i}", i * 100, 1, 1, 1, 1) for i in range(1, 9)])
    assert len(compare.run_plan(d, plan(group_by="product", limit=None))) == 5


def test_run_plan_ties_are_ordered_by_group_key():
    d = make_df(("2026-09", "coupang", "P2", 100, 1, 1, 1, 1), ("2026-09", "coupang", "P1", 100, 1, 1, 1, 1))
    assert [r["product_id"] for r in compare.run_plan(d, plan(group_by="product"))] == ["P1", "P2"]


def test_run_plan_null_roas_groups_sort_last_in_both_directions():
    d = make_df(("2026-09", "coupang", "P1", 1, 1, 1, 0, 0), ("2026-09", "naver", "P1", 1, 1, 1, 100, 200))
    for sort in ("asc", "desc"):
        result = compare.run_plan(d, plan(metric="roas", group_by="platform", sort=sort))
        assert result == [{"platform": "naver", "roas": 200.0}, {"platform": "coupang", "roas": None}]


def test_run_plan_missing_period_raises_app_error_with_readable_message(df):
    with pytest.raises(AppError) as exc:
        compare.run_plan(df, plan(period="2026-07"))
    assert exc.value.code == "PERIOD_NOT_FOUND"
    assert "2026-07" in exc.value.message and "2026-08" in exc.value.message and "2026-09" in exc.value.message


def test_run_plan_accepts_pydantic_like_object(df):
    obj = SimpleNamespace(metric="orders", group_by="platform", sort="asc", limit=5, period=None)
    assert compare.run_plan(df, obj) == [{"platform": "naver", "orders": 310}, {"platform": "coupang", "orders": 520}]


# ---- 실제 연결: 가짜 없이 /api/analyze ----
def test_analyze_endpoint_returns_expected_deterministic_fields():
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/csv")) for n in NORMAL_FILES]
    res = client.post("/api/analyze", files=files)
    assert res.status_code == 200
    body = res.json()
    for key in ("kpis", "comparison", "rows", "signals"):
        assert body[key] == EXPECTED[key], key


def test_analyze_endpoint_reports_invalid_number_with_file():
    files = [("files", ("coupang_2026-09.csv", csv_bytes("P001,이어폰,abc,3,4,1,2"), "text/csv"))]
    res = client.post("/api/analyze", files=files)
    assert res.status_code == 422
    error = res.json()["error"]
    assert error["code"] == "INVALID_NUMBER" and error["details"]["file"] == "coupang_2026-09.csv"
