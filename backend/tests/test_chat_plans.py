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
