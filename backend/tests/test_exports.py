"""플랫폼 실제 내보내기 파일 (쿠팡 판매·광고, 네이버 광고, 스마트스토어 판매) 정규화 · /api/analyze."""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analysis import normalize
from app.core.errors import AppError
from app.main import app

EXPORTS = Path(__file__).resolve().parents[2] / "shared" / "fixtures" / "exports"
COUPANG_SALES = EXPORTS / "SELLER_INSIGHTS_VENDOR_ITEM_METRICS_SAMPLE_coupang.xlsx"
COUPANG_ADS = EXPORTS / "coupang_ads_sample.xlsx"
NAVER_ADS = EXPORTS / "naver_shopping_ads_sample.xlsx"
NAVER_SALES = EXPORTS / "NAVER_SALES_SAMPLE_DUMMY.xlsx"
ALL = [COUPANG_SALES, COUPANG_ADS, NAVER_ADS, NAVER_SALES]
client = TestClient(app, raise_server_exceptions=False)


def files(paths):
    return [(p.name, p.read_bytes()) for p in paths]


@pytest.mark.parametrize(
    ("path", "platform", "periods"),
    [(COUPANG_SALES, "coupang", []), (COUPANG_ADS, "coupang", []), (NAVER_ADS, "naver", ["2026-09"]),
     (NAVER_SALES, "naver_store", ["2026-09"])],
)
def test_preview_detects_export(path, platform, periods):
    result = normalize.preview_file(path.name, path.read_bytes())
    assert (result["platform"], result["periods"]) == (platform, periods)


def test_sales_and_ads_fill_each_other_without_overlap():
    df = normalize.normalize_files(files(ALL))
    assert set(df["period"]) == {"2026-09"}  # 기간 없는 쿠팡 파일은 네이버 파일의 월을 쓴다
    raw_sales, raw_ads, raw_naver = (pd.read_excel(p) for p in (COUPANG_SALES, COUPANG_ADS, NAVER_ADS))
    coupang, naver = df[df["platform"] == "coupang"], df[df["platform"] == "naver"]
    assert coupang["revenue"].sum() == raw_sales["매출(원)"].sum()
    assert coupang["ad_spend"].sum() == raw_ads["광고비"].sum()
    assert coupang["ad_revenue"].sum() == raw_ads["총 전환매출액(14일)"].sum()
    assert naver["ad_spend"].sum() == raw_naver["총비용"].sum()
    assert naver["revenue"].sum() == 0
    assert not df.duplicated(["period", "platform", "product_id"]).any()  # 광고 리포트 행은 상품별로 합친다


def test_undated_export_alone_needs_period():
    with pytest.raises(AppError) as exc:
        normalize.normalize_files(files([COUPANG_ADS]))
    assert exc.value.code == "INVALID_PERIOD"
    df = normalize.normalize_files([("coupang_ads_2026-08.xlsx", COUPANG_ADS.read_bytes())])
    assert set(df["period"]) == {"2026-08"}


def test_analyze_merges_smartstore_into_naver():
    res = client.post("/api/analyze", files=[("files", f) for f in files(ALL)])
    assert res.status_code == 200
    body = res.json()
    by_platform = {r["platform"]: r for r in body["comparison"]["by_platform"]}
    assert set(by_platform) == {"coupang", "naver"}
    assert by_platform["naver"]["revenue"] == body["store"]["current"]["revenue"]
    assert by_platform["naver"]["roas"] is not None and by_platform["coupang"]["roas"] is not None


def test_undated_export_with_multiple_months_is_ambiguous():
    """리뷰 회귀: 8·9월 자료와 함께 올리면 기간 없는 쿠팡 파일의 월을 추정하지 않는다."""
    uploads = files([COUPANG_SALES, NAVER_ADS]) + [("sales_20260801-20260831.xlsx", _store_file("2026-08-01~2026-08-31"))]
    with pytest.raises(AppError) as exc:
        normalize.normalize_files(uploads)
    assert exc.value.code == "INVALID_PERIOD" and exc.value.details["file"] == COUPANG_SALES.name


def _store_file(date: str) -> bytes:
    import io

    row = {c: 0 for c in normalize.SMARTSTORE_SALES_MAP.values()}
    row.update({"날짜": date, "채널상품명": "이어폰", "채널상품번호": "P1", "판매금액(순)": 200, "판매금액(총)": 200})
    buf = io.BytesIO()
    pd.DataFrame([row]).to_excel(buf, index=False)
    return buf.getvalue()


def test_core_rows_excludes_store_only_in_overlapping_month():
    """리뷰 회귀: 8월 예전 naver 매출 100 + 9월 스마트스토어 매출 200 + 9월 naver 광고행 → 9월 매출 200 유지."""
    base = {"product_id": "P1", "product_name": "이어폰", "orders": 0, "units": 0, "ad_spend": 0, "ad_revenue": 0}
    df = pd.DataFrame([
        {**base, "period": "2026-08", "platform": "naver", "revenue": 100},
        {**base, "period": "2026-08", "platform": "naver_store", "revenue": 100},
        {**base, "period": "2026-09", "platform": "naver_store", "revenue": 200},
        {**base, "period": "2026-09", "platform": "naver", "revenue": 0, "ad_spend": 50},
    ])
    core = normalize.core_rows(df)
    assert core.groupby("period")["revenue"].sum().to_dict() == {"2026-08": 100, "2026-09": 200}
    assert set(core["platform"]) == {"naver"}
