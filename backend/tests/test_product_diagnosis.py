"""Independent known-answer cases for C's composite product diagnosis."""
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from app.analysis import compare, normalize
from app.analysis.product_diagnosis import run_product_diagnosis
from app.core.errors import AppError

HEADER = "상품ID,상품명,총매출,주문,판매량,광고비,광고매출"


def csv_bytes(header, rows):
    return (header + "\n" + "\n".join(rows) + "\n").encode("utf-8")


def uploads():
    return [
        ("coupang_2026-08.csv", csv_bytes(HEADER, ["P1,A,1000,10,10,100,300", "P2,B,1000,10,10,100,300", "P3,C,1000,10,10,100,300"])),
        ("coupang_2026-09.csv", csv_bytes(HEADER, ["P1,A,1400,12,13,110,440", "P2,B,800,8,8,120,240", "P3,C,1100,11,11,150,450"])),
    ]


@pytest.fixture
def df():
    return normalize.normalize_files(uploads())


def test_opportunity_known_answers(df):
    rows = run_product_diagnosis(df, "opportunity")
    assert [(r["product_id"], r["score"]) for r in rows] == [("P1", 4), ("P3", 3)]
    first = rows[0]
    assert (first["period"], first["previous_period"], first["rank"]) == ("2026-09", "2026-08", 1)
    assert (first["revenue_change"], first["orders_change"], first["units_change"], first["ad_spend_change"], first["ad_revenue_change"]) == (40, 20, 30, 10, 46.7)
    assert (first["roas"], first["roas_change_pp"], first["benchmark_roas"], first["benchmark_count"]) == (400, 100, 300, 3)
    assert first["reason_codes"] == ["REVENUE_GROWTH", "SALES_VOLUME_GROWTH", "GOOD_ROAS", "REVENUE_GROWTH_GT_AD_SPEND"]


def test_attention_known_answers(df):
    (row,) = run_product_diagnosis(df, "attention")
    assert (row["product_id"], row["score"], row["score_max"], row["evaluated_rules"]) == ("P2", 4, 5, 4)
    assert (row["revenue_change"], row["ad_spend_change"], row["ad_revenue_change"], row["roas_change_pp"]) == (-20, 20, -20, -100)
    assert row["reason_codes"] == ["REVENUE_DECLINE", "SALES_VOLUME_DECLINE", "ROAS_DECLINE", "AD_SPEND_UP_WITH_WEAK_RETURN"]


def test_three_months_uses_latest_calendar_pair(df):
    old = ("coupang_2026-07.csv", csv_bytes(HEADER, ["P1,A,900000,500,500,100,300"]))
    assert run_product_diagnosis(normalize.normalize_files([old, *uploads()]), "opportunity") == run_product_diagnosis(df, "opportunity")


@pytest.mark.parametrize("months", [["2026-09"], ["2026-07", "2026-09"]])
def test_missing_calendar_previous_is_explicit(months):
    files = [(f"coupang_{m}.csv", csv_bytes(HEADER, ["P1,A,100,1,1,10,20"])) for m in months]
    with pytest.raises(AppError) as error:
        run_product_diagnosis(normalize.normalize_files(files), "attention")
    assert error.value.code == "DIAGNOSIS_INSUFFICIENT_PERIODS"
    assert "2026-08" in error.value.message and "기간" in error.value.message


def test_year_boundary():
    files = [("coupang_2025-12.csv", uploads()[0][1]), ("coupang_2026-01.csv", uploads()[1][1])]
    assert run_product_diagnosis(normalize.normalize_files(files), "opportunity")[0]["previous_period"] == "2025-12"


def test_new_and_disappeared_products_are_not_zero_filled():
    files = [
        ("coupang_2026-08.csv", csv_bytes(HEADER, ["OLD,이전상품,9000,90,90,100,400", "P1,A,100,1,1,10,20"])),
        ("coupang_2026-09.csv", csv_bytes(HEADER, ["NEW,새상품,99999,999,999,100,900", "P1,A,200,2,2,10,30"])),
    ]
    data = normalize.normalize_files(files)
    assert [r["product_id"] for r in run_product_diagnosis(data, "opportunity")] == ["P1"]
    assert all(r["product_id"] not in {"OLD", "NEW"} for r in run_product_diagnosis(data, "attention"))


def test_no_shared_product_ids_has_specific_message():
    files = [("coupang_2026-08.csv", csv_bytes(HEADER, ["OLD,A,100,1,1,10,20"])),
             ("coupang_2026-09.csv", csv_bytes(HEADER, ["NEW,A,200,2,2,10,30"]))]
    with pytest.raises(AppError) as e:
        run_product_diagnosis(normalize.normalize_files(files), "opportunity")
    assert e.value.code == "DIAGNOSIS_NO_COMPARABLE_PRODUCTS"


@pytest.mark.parametrize("spend", ["0", ""])
def test_actual_zero_and_missing_spend_remain_distinct(spend):
    files = [(f"coupang_{m}.csv", csv_bytes(HEADER, [f"P1,A,{rev},{orders},{orders},{spend},0"]))
             for m, rev, orders in [("2026-08", 100, 1), ("2026-09", 200, 2)]]
    (row,) = run_product_diagnosis(normalize.normalize_files(files), "opportunity")
    assert row["ad_spend"] == (0 if spend == "0" else None)
    assert row["roas"] is None and row["roas_change_pp"] is None and row["ad_spend_change"] is None
    assert row["score"] == 2 and row["evaluated_rules"] == 2


def test_same_id_different_platforms_are_not_joined():
    records = []
    for platform, current in [("coupang", 200), ("naver", 50)]:
        for period, revenue in [("2026-08", 100), ("2026-09", current)]:
            records.append(dict(period=period, platform=platform, product_id="P1", product_name="같은 이름",
                                revenue=revenue, orders=revenue, units=revenue, ad_spend=10, ad_revenue=20))
    data = pd.DataFrame(records)
    assert run_product_diagnosis(data, "opportunity")[0]["platform"] == "coupang"
    assert run_product_diagnosis(data, "attention")[0]["platform"] == "naver"


def test_name_change_does_not_break_id_matching():
    files = uploads()
    files[1] = (files[1][0], files[1][1].replace(b"P1,A,", "P1,새 이름,".encode()))
    assert run_product_diagnosis(normalize.normalize_files(files), "opportunity")[0]["product_name"] == "새 이름"


def test_repeat_reverse_and_shuffled_rows_have_identical_rankings(df):
    before = deepcopy(df)
    expected = run_product_diagnosis(df, "opportunity")
    for _ in range(4):
        assert run_product_diagnosis(df, "opportunity") == expected
    assert run_product_diagnosis(normalize.normalize_files(list(reversed(uploads()))), "opportunity") == expected
    assert run_product_diagnosis(df.sample(frac=1, random_state=4).reset_index(drop=True), "opportunity") == expected
    pd.testing.assert_frame_equal(df, before)
    assert df.attrs == before.attrs


def test_ties_use_stable_product_identity():
    files = [(f"coupang_{month}.csv", csv_bytes(HEADER, [f"{pid},이름,{rev},{rev},{rev},10,20" for pid in ["P3", "P1", "P2"]]))
             for month, rev in [("2026-08", 100), ("2026-09", 200)]]
    assert [r["product_id"] for r in run_product_diagnosis(normalize.normalize_files(files), "opportunity", 2)] == ["P1", "P2"]


def test_conditions_are_hard_filters_not_just_scores(df):
    assert run_product_diagnosis(df, "opportunity", required_conditions=["ad_spend_down"]) == []
    assert [r["product_id"] for r in run_product_diagnosis(df, "attention", required_conditions=["ad_spend_up", "ad_revenue_down"])] == ["P2"]


@pytest.mark.parametrize("kwargs", [{"intent": "invented"}, {"limit": 0}, {"limit": 51}, {"limit": True}, {"required_conditions": ["margin_up"]}])
def test_invalid_diagnosis_plan(df, kwargs):
    with pytest.raises(AppError) as e:
        run_product_diagnosis(df, **{"intent": "opportunity", **kwargs})
    assert e.value.code == "UNSUPPORTED_PLAN"


def test_unknown_period(df):
    with pytest.raises(AppError) as e:
        run_product_diagnosis(df, "opportunity", period="2027-01")
    assert e.value.code == "PERIOD_NOT_FOUND"


def test_stale_provenance_is_rejected(df):
    df.loc[0, "revenue"] = 999
    with pytest.raises(AppError) as e:
        run_product_diagnosis(df, "opportunity")
    assert e.value.code == "DIAGNOSIS_SOURCE_MISMATCH"


def export_files(ad_id="P1", missing_sales=False):
    files = []
    for month, revenue, orders, spend, ad_rev in [("2026-08", 100, 10, 10, 30), ("2026-09", 200, 20, 12, 48)]:
        if not missing_sales:
            files.append((f"sales_{month}.csv", csv_bytes("옵션 ID,등록상품ID,옵션명,매출(원),주문,판매량", [f"P1,등록,상품,{revenue},{orders},{orders}"])))
        files.append((f"ads_{month}.csv", csv_bytes("캠페인 ID,광고집행 옵션ID,광고집행 상품명,광고비,총 전환매출액(14일)", [f"campaign,{ad_id},상품,{spend},{ad_rev}"])))
    return files


def test_identical_coupang_option_ids_can_join_sales_and_ads():
    (row,) = run_product_diagnosis(normalize.normalize_files(export_files()), "opportunity")
    assert (row["revenue"], row["ad_spend"], row["roas"], row["score"]) == (200, 12, 400, 4)


def test_unmatched_coupang_ids_do_not_gain_ad_efficiency():
    (row,) = run_product_diagnosis(normalize.normalize_files(export_files(ad_id="different")), "opportunity")
    assert row["product_id"] == "P1" and row["score"] == 2
    assert row["ad_spend"] is None and row["roas"] is None


def test_ads_only_does_not_create_zero_sales():
    files = export_files(missing_sales=True)
    files[1] = (files[1][0], files[1][1].replace(b",12,48", b",20,20"))
    data = normalize.normalize_files(files)
    (row,) = run_product_diagnosis(data, "attention")
    assert row["revenue"] is None and row["revenue_change"] is None
    assert row["score"] == 2 and "REVENUE_DECLINE" not in row["reason_codes"]
    with pytest.raises(AppError) as e:
        run_product_diagnosis(data, "opportunity")
    assert e.value.code == "DIAGNOSIS_INSUFFICIENT_METRICS"


def test_missing_required_ad_data_is_not_reported_as_no_candidates():
    files = [f for f in export_files() if f[0].startswith("sales_")]
    with pytest.raises(AppError) as e:
        run_product_diagnosis(normalize.normalize_files(files), "opportunity", required_conditions=["ad_spend_down"])
    assert e.value.code == "DIAGNOSIS_INSUFFICIENT_METRICS"


def test_all_blank_metrics_are_not_observed_zero():
    files = [(f"coupang_{month}.csv", csv_bytes(HEADER, ["P1,A,,,,,"])) for month in ("2026-08", "2026-09")]
    with pytest.raises(AppError) as e:
        run_product_diagnosis(normalize.normalize_files(files), "attention")
    assert e.value.code == "DIAGNOSIS_INSUFFICIENT_METRICS"


def test_store_quality_and_naver_ad_ids_remain_separate():
    records = []
    for period, orders, refunds, revenue in [("2026-08", 20, 1, 1000), ("2026-09", 10, 3, 800)]:
        records.append(dict(period=period, platform="naver_store", product_id="P1", product_name="상품", revenue=revenue,
                            orders=orders, units=orders, ad_spend=0, ad_revenue=0, visits=100, gross_revenue=1000,
                            refund_count=refunds, refund_amount=0, discount_amount=0))
        records.append(dict(period=period, platform="naver", product_id="P1", product_name="동일문자열 광고ID", revenue=0,
                            orders=0, units=0, ad_spend=10, ad_revenue=1000))
    rows = run_product_diagnosis(pd.DataFrame(records), "attention")
    (row,) = [r for r in rows if r["platform"] == "naver_store"]
    assert row["roas"] is None and row["ad_spend"] is None
    assert (row["conversion_rate_change_pp"], row["refund_rate_change_pp"], row["score"]) == (-10, 25, 3)
    assert "STORE_QUALITY_DECLINE" in row["reason_codes"]


def test_real_store_fixtures_are_supported():
    root = Path(__file__).resolve().parents[2] / "shared" / "fixtures" / "smartstore"
    data = normalize.normalize_files([(p.name, p.read_bytes()) for p in sorted(root.glob("sales_*_sample.xlsx"))])
    rows = run_product_diagnosis(data, "attention")
    assert rows and all(r["roas"] is None for r in rows)
    assert any("STORE_QUALITY_DECLINE" in r["reason_codes"] for r in rows)


def test_public_rows_and_existing_plan_stay_unchanged(df):
    assert list(df.columns) == normalize.NORMALIZED_COLUMNS
    assert compare.run_plan(df, {"metric": "revenue", "group_by": "product", "limit": 1}) == [{"product_id": "P1", "product_name": "A", "revenue": 1400}]
    assert compare.run_plan(df, {"analysis_type": "product_diagnosis", "diagnosis_intent": "opportunity", "limit": 1}) == run_product_diagnosis(df, "opportunity", 1)
