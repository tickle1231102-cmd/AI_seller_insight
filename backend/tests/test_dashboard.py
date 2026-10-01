"""Dashboard display contract: source availability, periods, isolation, and API regression."""

import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.analysis import normalize, kpi
from app.analysis.dashboard import build_dashboard
from app.main import app
from app.routers import analyze
from app.schemas import Insight


def source(kind, month="2026-09", **overrides):
    rows = {
        "sales": {"옵션 ID": "P1", "등록상품ID": "S1", "옵션명": "상품 A", "매출(원)": 1200, "주문": 12, "판매량": 15},
        "ads": {"캠페인 ID": "C1", "광고집행 옵션ID": "P1", "광고집행 상품명": "상품 A", "광고비": 200, "총 전환매출액(14일)": 600},
        "naver_ads": {"일별": f"{month}-01", "소재": "P1", "총비용": 100, "총 전환매출액": 400},
        "store": {"채널상품번호": "P1", "채널상품명": "상품 A", "판매금액(순)": 1800, "상품결제건수": 20, "결제상품수량": 22,
                  "판매금액(총)": 2000, "방문수": 200, "환불건수": 2, "환불금액": 200, "전체 할인액": 100},
        "template": {"상품ID": "P1", "상품명": "상품 A", "판매금액(순)": 3000, "상품결제건수": 30, "결제상품수량": 30, "광고비용": 100, "전환매출": 400},
    }
    row = {**rows[kind], **overrides}
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return (f"{kind}_{month}.csv", out.getvalue().encode("utf-8-sig"))


def dashboard(files):
    df = normalize.normalize_files(files)
    result = build_dashboard(df, max(df.period))
    return {p["platform"]: p for p in result["platforms"]}, df


def test_two_platforms_two_months_known_answers():
    files = [source(k, m) for m in ("2026-08", "2026-09") for k in ("sales", "ads", "store", "naver_ads")]
    p, df = dashboard(files)
    assert list(p) == ["coupang", "naver"]
    assert p["coupang"]["current"]["values"] == dict(revenue=1200, orders=12, units=15, ad_spend=200, ad_revenue=600, roas=300)
    assert p["naver"]["current"]["values"] == dict(revenue=1800, orders=20, units=22, ad_spend=100, ad_revenue=400, roas=400)
    for field in ("revenue", "orders", "units", "ad_spend", "ad_revenue"):
        assert sum(x["current"]["values"][field] for x in p.values()) == kpi.compute_kpis(normalize.core_rows(df))["current"][field]
    assert all(p["coupang"]["change"][f] == 0 for f in p["coupang"]["change"])
    assert len(p["coupang"]["products"]) == 1
    assert p["coupang"]["products"][0]["source"] == "coupang_export"
    assert {g["source"] for g in p["naver"]["products"]} == {"smartstore_sales", "naver_ads"}
    assert p["naver"]["current"]["store_values"]["conversion_rate"] == 10


@pytest.mark.parametrize(("kind", "platform", "sales", "ads"), [("sales", "coupang", True, False), ("ads", "coupang", False, True), ("store", "naver", True, False), ("naver_ads", "naver", False, True)])
def test_single_source_presence(kind, platform, sales, ads):
    p, _ = dashboard([source(kind)])
    assert list(p) == [platform]
    current = p[platform]["current"]
    assert (current["has_sales"], current["has_ads"]) == (sales, ads)
    assert (current["values"]["revenue"] is not None) == sales
    assert (current["values"]["ad_spend"] is not None) == ads
    assert not p[platform]["previous"]["has_data"]
    assert all(v is None for v in p[platform]["change"].values())


@pytest.mark.parametrize("raw", ["", "-", 0])
def test_missing_and_real_zero(raw):
    p, _ = dashboard([source("ads", **{"광고비": raw})])
    cur = p["coupang"]["current"]
    assert cur["has_ads"]
    assert cur["values"]["ad_spend"] == (0 if raw == 0 else None)
    assert cur["values"]["roas"] is None


def test_one_missing_cell_does_not_become_partial_total():
    p, _ = dashboard([source("ads"), ("other_2026-09.csv", source("ads", **{"광고비": ""})[1])])
    assert p["coupang"]["current"]["values"]["ad_spend"] is None


def test_global_month_does_not_hide_older_platform():
    p, _ = dashboard([source("sales", "2026-08"), source("store", "2026-09")])
    assert p["coupang"]["periods"] == ["2026-08"]
    assert not p["coupang"]["current"]["has_data"]
    assert p["coupang"]["current"]["values"]["revenue"] is None
    assert p["coupang"]["previous"]["values"]["revenue"] == 1200


@pytest.mark.parametrize("month", ["2026-07", "2025-12"])
def test_calendar_previous_only(month):
    current = "2026-01" if month == "2025-12" else "2026-09"
    p, _ = dashboard([source("sales", month), source("sales", current)])
    assert p["coupang"]["previous"]["has_data"] == (month == "2025-12")


def test_zero_previous_no_infinity():
    p, _ = dashboard([source("sales", "2026-08", **{"매출(원)": 0}), source("sales")])
    assert p["coupang"]["change"]["revenue"] is None


def test_legacy_overlap_matches_existing_core():
    p, df = dashboard([source("template"), source("store")])
    assert p["naver"]["current"]["values"]["revenue"] == 3000
    assert p["naver"]["current"]["values"]["revenue"] == kpi.compute_kpis(normalize.core_rows(df))["current"]["revenue"]
    assert p["naver"]["current"]["store_values"]["revenue"] == 1800
    assert p["naver"]["overlap_excluded"]


def test_ratios_from_sums_not_row_average():
    files = [source("ads"), ("other_2026-09.csv", source("ads", **{"광고집행 옵션ID": "P2", "광고비": 800, "총 전환매출액(14일)": 800})[1])]
    p, _ = dashboard(files)
    assert p["coupang"]["current"]["values"]["roas"] == 140


def test_roas_change_uses_unrounded_ratios():
    p, _ = dashboard([source("ads", "2026-08", **{"광고비": 3, "총 전환매출액(14일)": 1}), source("ads", **{"광고비": 6, "총 전환매출액(14일)": 1})])
    assert p["coupang"]["change"]["roas"] == -16.7


def test_product_names_do_not_join_different_ids():
    p, _ = dashboard([source("sales"), source("ads", **{"광고집행 옵션ID": "P2"})])
    products = p["coupang"]["products"][0]["items"]
    assert len(products) == 2
    assert products[0]["values"]["ad_spend"] is None


def test_product_limit_explicit_and_order_deterministic():
    files = [(f"{i}_2026-09.csv", source("sales", **{"옵션 ID": f"P{i:02}", "매출(원)": i})[1]) for i in range(12)]
    p, _ = dashboard(files)
    q, _ = dashboard(list(reversed(files)))
    assert p == q
    group = p["coupang"]["products"][0]
    assert group["total"] == 12 and len(group["items"]) == 10
    assert group["items"][0]["product_id"] == "P11"


def test_store_blank_propagates_to_derived_fields():
    p, _ = dashboard([source("store", **{"방문수": "-"})])
    v = p["naver"]["current"]["store_values"]
    assert v["visits"] is None and v["conversion_rate"] is None
    assert v["revenue"] == 1800


def test_api_additive_contract_and_ai_failure_does_not_hide_dashboard(monkeypatch):
    monkeypatch.setattr(analyze, "_run_ai", lambda *args: Insight(status="llm_error"))
    files = [source("sales"), source("ads"), source("store"), source("naver_ads")]
    response = TestClient(app).post("/api/analyze", files=[("files", f) for f in files])
    assert response.status_code == 200
    body = response.json()
    assert body["insight"]["status"] == "llm_error"
    assert len(body["dashboard"]["platforms"]) == 2
    assert body["kpis"]["current"]["revenue"] == 3000
    assert "dashboard_sources" not in str(body)
    assert "source" not in body["rows"][0]
