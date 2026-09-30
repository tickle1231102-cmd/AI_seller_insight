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
