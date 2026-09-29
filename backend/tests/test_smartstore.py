"""스마트스토어 판매 분석(SALES) 파일 정규화 · store KPI · /api/analyze 응답."""

import io
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analysis import kpi, normalize
from app.core.errors import AppError
from app.main import app

SMARTSTORE = Path(__file__).resolve().parents[2] / "shared" / "fixtures" / "smartstore"
FIXTURES = SMARTSTORE.parent
SALES = sorted(SMARTSTORE.glob("sales_*_sample.xlsx"))
client = TestClient(app, raise_server_exceptions=False)


def files(paths):
    return [(p.name, p.read_bytes()) for p in paths]


def xlsx(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def sales_row(**overrides):
    row = {c: 0 for c in normalize.SMARTSTORE_SALES_MAP.values()}
    row.update({"날짜": "2026-09-01~2026-09-30", "채널상품명": "이어폰", "채널상품번호": "P1", "상품결제건수": 10,
                "판매금액(총)": 1000, "판매금액(순)": 900, "방문수": 200})
    row.update(overrides)
    return row


def test_sample_fixtures_exist():
    assert [p.name for p in SALES] == ["sales_20260801-20260831_sample.xlsx", "sales_20260901-20260930_sample.xlsx"]


def test_sales_file_is_naver_store_with_period_from_date_column():
    result = normalize.preview_file(SALES[1].name, SALES[1].read_bytes())
    assert result["platform"] == "naver_store"
    assert result["periods"] == ["2026-09"]
    assert result["row_count"] == 10
    assert result["columns"][0] == "product_name" and "방문수" in result["columns"]


def test_normalize_adds_store_fields_and_zero_ad_metrics():
    df = normalize.normalize_files(files(SALES))
    assert list(df.columns) == normalize.NORMALIZED_COLUMNS + normalize.STORE_FIELDS
    assert set(df["period"]) == {"2026-08", "2026-09"}
    assert (df["ad_spend"] == 0).all() and (df["ad_revenue"] == 0).all()
    assert df["visits"].notna().all()


def test_legacy_rows_get_none_store_fields_when_mixed():
    df = normalize.normalize_files(files([*SALES, FIXTURES / "coupang_2026-09.csv"]))
    coupang = df[df["platform"] == "coupang"]
    assert coupang["visits"].isna().all() and not coupang.empty


def test_legacy_only_upload_keeps_9_columns():
    df = normalize.normalize_files(files([FIXTURES / "coupang_2026-09.csv"]))
    assert list(df.columns) == normalize.NORMALIZED_COLUMNS


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("sales_20260830-20260928_x.xlsx", "2026-09"), ("sales_20260801-20260831.xlsx", "2026-08"), ("sales_2026-07.xlsx", "2026-07")],
)
def test_period_from_filename_when_date_column_is_missing(filename, expected):
    row = sales_row()
    del row["날짜"]
    assert normalize.preview_file(filename, xlsx(pd.DataFrame([row])))["periods"] == [expected]


def test_dash_is_zero_and_daily_rows_are_merged():
    rows = [sales_row(날짜="2026-09-01", 환불건수="-"), sales_row(날짜="2026-09-02", 환불건수=2)]
    df = normalize.normalize_files([("sales.xlsx", xlsx(pd.DataFrame(rows)))])
    assert len(df) == 1
    assert (df.loc[0, "orders"], df.loc[0, "visits"], df.loc[0, "refund_count"]) == (20, 400, 2)


def test_dash_is_invalid_number_outside_smartstore_sales():
    with pytest.raises(AppError) as exc:
        normalize.normalize_files([("coupang_2026-09.csv", "상품ID,상품명,총매출,주문,판매량,광고비,광고매출\nP1,a,-,1,1,0,0\n".encode())])
    assert exc.value.code == "INVALID_NUMBER" and exc.value.details["value"] == "-"


def test_missing_store_column_is_reported():
    row = sales_row()
    del row["방문수"]
    with pytest.raises(AppError) as exc:
        normalize.preview_file("sales_2026-09.xlsx", xlsx(pd.DataFrame([row])))
    assert exc.value.code == "MISSING_COLUMNS" and exc.value.details["missing"] == ["방문수"]


@pytest.mark.parametrize("kind", ["visit", "query", "customer"])
def test_other_smartstore_datasets_are_unsupported(kind):
    path = next(SMARTSTORE.glob(f"{kind}_*_sample.xlsx"))
    with pytest.raises(AppError) as exc:
        normalize.preview_file(path.name, path.read_bytes())
    assert exc.value.code == "UNSUPPORTED_DATASET" and exc.value.details["dataset"] == kind


def test_store_totals_ratios_are_from_sums():
    df = pd.DataFrame([
        {"visits": 100, "orders": 10, "units": 12, "gross_revenue": 1000, "revenue": 900, "refund_count": 1, "refund_amount": 100, "discount_amount": 50},
        {"visits": 300, "orders": 10, "units": 10, "gross_revenue": 3000, "revenue": 3000, "refund_count": 0, "refund_amount": 0, "discount_amount": 350},
    ])
    t = kpi.store_totals(df)
    assert t["conversion_rate"] == 5.0  # 20/400, 행 평균(6.67) 아님
    assert (t["refund_rate"], t["discount_rate"], t["net_ratio"], t["aov"]) == (5.0, 10.0, 97.5, 200)


def test_store_totals_zero_denominators_are_none():
    df = pd.DataFrame([{f: 0 for f in kpi.STORE_SUM_FIELDS}])
    t = kpi.store_totals(df)
    assert t["conversion_rate"] is None and t["aov"] is None and t["discount_rate"] is None


def test_store_kpis_reflect_fixture_patterns():
    store = kpi.compute_store_kpis(normalize.normalize_files(files(SALES)))
    assert (store["period"], store["previous_period"]) == ("2026-09", "2026-08")
    change = store["change"]
    assert change["visits_change"] > 10 and change["conversion_rate_change_pp"] < 0  # 방문↑ 전환↓
    assert change["discount_rate_change_pp"] > 3  # 할인 의존 증가
    speaker = next(p for p in store["products"] if p["product_id"] == "P1003")
    assert speaker["refund_rate_change_pp"] > 10  # 환불률 급증 상품
    assert [t["period"] for t in store["trend"]] == ["2026-08", "2026-09"]
    revenues = [p["gross_revenue"] for p in store["products"]]
    assert revenues == sorted(revenues, reverse=True)


def test_store_kpis_none_without_smartstore():
    assert kpi.compute_store_kpis(normalize.normalize_files(files([FIXTURES / "naver_2026-09.csv"]))) is None


def test_single_month_has_no_previous():
    store = kpi.compute_store_kpis(normalize.normalize_files(files(SALES[1:])))
    assert store["previous"] is None and store["change"]["visits_change"] is None
    assert store["products"][0]["refund_rate_change_pp"] is None


def _post(paths):
    upload = [("files", (p.name, p.read_bytes(), "application/octet-stream")) for p in paths]
    return client.post("/api/analyze", files=upload)


def test_api_analyze_returns_store(monkeypatch):
    monkeypatch.setattr("app.routers.analyze._load_ai", lambda: (_ for _ in ()).throw(RuntimeError("no ai")))
    res = _post([*SALES, FIXTURES / "coupang_2026-09.csv"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["store"]["period"] == "2026-09"
    coupang_row = next(r for r in body["rows"] if r["platform"] == "coupang")
    assert "visits" not in coupang_row and body["rows"][-1]["visits"] is not None


def test_store_file_does_not_inflate_kpis_or_comparison(monkeypatch):
    """스토어 파일과 광고 CSV 의 네이버 판매액이 겹쳐도 kpis·comparison 은 광고 리포트만으로 계산한다."""
    monkeypatch.setattr("app.routers.analyze._load_ai", lambda: (_ for _ in ()).throw(RuntimeError("no ai")))
    legacy = sorted(FIXTURES.glob("*_2026-0[89].csv"))
    base = _post(legacy).json()
    body = _post([*legacy, *SALES]).json()
    assert body["kpis"] == base["kpis"] and body["comparison"] == base["comparison"]
    assert body["signals"] == base["signals"]
    assert {r["platform"] for r in body["rows"]} == {"coupang", "naver", "naver_store"}
    assert body["store"]["period"] == "2026-09"


def test_store_only_upload_still_analyzes(monkeypatch):
    monkeypatch.setattr("app.routers.analyze._load_ai", lambda: (_ for _ in ()).throw(RuntimeError("no ai")))
    res = _post(SALES)
    assert res.status_code == 200, res.text
    assert res.json()["comparison"]["by_platform"][0]["platform"] == "naver_store"


def test_api_analyze_store_null_for_legacy(monkeypatch):
    monkeypatch.setattr("app.routers.analyze._load_ai", lambda: (_ for _ in ()).throw(RuntimeError("no ai")))
    res = _post([FIXTURES / "coupang_2026-09.csv"])
    assert res.status_code == 200 and res.json()["store"] is None
