"""플랫폼 실제 내보내기 파일 (쿠팡 판매·광고, 네이버 광고, 스마트스토어 판매) 정규화 · /api/analyze."""

import json
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


SEPT = {COUPANG_SALES.name: "2026-09", COUPANG_ADS.name: "2026-09"}  # 기간 정보가 없는 파일의 사용자 입력


def test_sales_and_ads_fill_each_other_without_overlap():
    df = normalize.normalize_files(files(ALL), SEPT)
    assert set(df["period"]) == {"2026-09"}
    raw_sales, raw_ads, raw_naver = (pd.read_excel(p) for p in (COUPANG_SALES, COUPANG_ADS, NAVER_ADS))
    coupang, naver = df[df["platform"] == "coupang"], df[df["platform"] == "naver"]
    assert coupang["revenue"].sum() == raw_sales["매출(원)"].sum()
    assert coupang["ad_spend"].sum() == raw_ads["광고비"].sum()
    assert coupang["ad_revenue"].sum() == raw_ads["총 전환매출액(14일)"].sum()
    assert naver["ad_spend"].sum() == raw_naver["총비용"].sum()
    assert naver["revenue"].sum() == 0
    assert not df.duplicated(["period", "platform", "product_id"]).any()  # 광고 리포트 행은 상품별로 합친다


@pytest.mark.parametrize("periods", [None, {}, {COUPANG_ADS.name: "2026-9"}, {"other.xlsx": "2026-09"}])
def test_undated_export_requires_user_period(periods):
    """기간 정보가 없는 파일은 함께 올린 파일에서 추정하지 않고 사용자 입력을 요구한다."""
    with pytest.raises(AppError) as exc:
        normalize.normalize_files(files([COUPANG_ADS, NAVER_ADS]), periods)
    assert exc.value.code == "INVALID_PERIOD"
    assert exc.value.details == {"file": COUPANG_ADS.name, "needs_input": True}


def test_user_period_and_filename_period():
    df = normalize.normalize_files(files([COUPANG_ADS]), {COUPANG_ADS.name: "2026-08"})
    assert set(df["period"]) == {"2026-08"}
    df = normalize.normalize_files([("coupang_ads_2026-07.xlsx", COUPANG_ADS.read_bytes())])
    assert set(df["period"]) == {"2026-07"}


def test_user_period_ignored_when_file_has_period():
    df = normalize.normalize_files(files([NAVER_ADS]), {NAVER_ADS.name: "2026-01"})
    assert set(df["period"]) == {"2026-09"}


def test_analyze_merges_smartstore_into_naver():
    res = client.post("/api/analyze", files=[("files", f) for f in files(ALL)], data={"periods": json.dumps(SEPT)})
    assert res.status_code == 200
    body = res.json()
    by_platform = {r["platform"]: r for r in body["comparison"]["by_platform"]}
    assert set(by_platform) == {"coupang", "naver"}
    assert by_platform["naver"]["revenue"] == body["store"]["current"]["revenue"]
    assert by_platform["naver"]["roas"] is not None and by_platform["coupang"]["roas"] is not None


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


def test_analyze_without_period_input_is_rejected():
    res = client.post("/api/analyze", files=[("files", f) for f in files(ALL)])
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_PERIOD"


@pytest.mark.parametrize("raw", ["not json", "[]", '{"a.xlsx": 9}'])
def test_analyze_rejects_malformed_period_input(raw):
    res = client.post("/api/analyze", files=[("files", f) for f in files(ALL)], data={"periods": raw})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_PERIOD"
