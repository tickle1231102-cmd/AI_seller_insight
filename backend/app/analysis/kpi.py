"""담당: C — TECH_SPEC 5장 참고.

아래 함수 이름·시그니처는 B 의 routers/analyze.py 가 호출하는 계약이다.
"""

import pandas as pd

SUM_FIELDS = ["revenue", "orders", "units", "ad_spend", "ad_revenue"]


def raw_roas(ad_revenue: float, ad_spend: float) -> float | None:
    """ROAS(%) 원값. 분모가 0 이면 None."""
    return ad_revenue / ad_spend * 100 if ad_spend else None


def _round1(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def totals(df: pd.DataFrame) -> dict:
    """행 묶음 → {revenue, orders, units, ad_spend, ad_revenue, roas}. roas 는 합계로 다시 계산한다(행 평균 아님)."""
    sums = {f: int(df[f].sum()) for f in SUM_FIELDS}
    return {**sums, "roas": _round1(raw_roas(sums["ad_revenue"], sums["ad_spend"]))}


def _pct_change(current: float, previous: float) -> float | None:
    return round((current - previous) / previous * 100, 1) if previous else None


def compute_kpis(df) -> dict:
    """정규화 DataFrame → TECH_SPEC 7-4 의 kpis (period, previous_period, current, previous, change).

    비교 대상은 데이터에 있는 최신 월과 그 직전 월이다. 월이 하나뿐이면 previous 관련 값은 모두 None.
    """
    periods = sorted(df["period"].unique())
    period = periods[-1]
    current = totals(df[df["period"] == period])

    if len(periods) == 1:
        change = {f"{f}_change": None for f in SUM_FIELDS}
        return {
            "period": period,
            "previous_period": None,
            "current": current,
            "previous": None,
            "change": {**change, "roas_change_pp": None},
        }

    previous_period = periods[-2]
    previous = totals(df[df["period"] == previous_period])
    change = {f"{f}_change": _pct_change(current[f], previous[f]) for f in SUM_FIELDS}
    # ROAS 증감은 반올림 전 원값끼리 뺀다 (내부 계산은 원값 유지).
    cur_roas = raw_roas(current["ad_revenue"], current["ad_spend"])
    prev_roas = raw_roas(previous["ad_revenue"], previous["ad_spend"])
    change["roas_change_pp"] = None if cur_roas is None or prev_roas is None else round(cur_roas - prev_roas, 1)
    return {
        "period": period,
        "previous_period": previous_period,
        "current": current,
        "previous": previous,
        "change": change,
    }


# ---- 스마트스토어 판매 분석 (퍼널·수익 품질) ----
STORE_SUM_FIELDS = ["visits", "orders", "units", "gross_revenue", "revenue", "refund_count", "refund_amount", "discount_amount"]
STORE_PRODUCT_LIMIT = 10


def _ratio(numerator: float, denominator: float) -> float | None:
    """비율(%) 원값. 분모가 0 이면 None."""
    return numerator / denominator * 100 if denominator else None


def store_totals(df: pd.DataFrame) -> dict:
    """스마트스토어 행 묶음 → 합계 + 비율 지표. 비율은 합계로 다시 계산한다(행 평균 아님).

    conversion_rate = 결제건수/방문수, net_ratio = 순매출/총매출, refund_rate = 환불건수/결제건수,
    refund_amount_rate = 환불금액/총매출, discount_rate = 전체 할인액/총매출, aov = 총매출/결제건수 (상품결제단가).
    """
    s = {f: int(df[f].sum()) for f in STORE_SUM_FIELDS}
    return {
        **s,
        "conversion_rate": _round1(_ratio(s["orders"], s["visits"])),
        "net_ratio": _round1(_ratio(s["revenue"], s["gross_revenue"])),
        "refund_rate": _round1(_ratio(s["refund_count"], s["orders"])),
        "refund_amount_rate": _round1(_ratio(s["refund_amount"], s["gross_revenue"])),
        "discount_rate": _round1(_ratio(s["discount_amount"], s["gross_revenue"])),
        "aov": round(s["gross_revenue"] / s["orders"]) if s["orders"] else None,
    }


STORE_RATE_FIELDS = ["conversion_rate", "net_ratio", "refund_rate", "refund_amount_rate", "discount_rate"]
STORE_CHANGE_FIELDS = ["visits", "orders", "gross_revenue", "revenue", "aov"]


def _store_change(current: dict, previous: dict | None) -> dict:
    """금액·건수는 증감률(%), 비율은 증감(%p). 비율 차이는 반올림 전 원값끼리 뺀다."""
    change: dict = {}
    for f in STORE_CHANGE_FIELDS:
        cur, prev = current[f], previous[f] if previous else None
        change[f"{f}_change"] = None if cur is None or not prev else _pct_change(cur, prev)
    raw = {"conversion_rate": ("orders", "visits"), "net_ratio": ("revenue", "gross_revenue"),
           "refund_rate": ("refund_count", "orders"), "refund_amount_rate": ("refund_amount", "gross_revenue"),
           "discount_rate": ("discount_amount", "gross_revenue")}
    for f, (num, den) in raw.items():
        cur = _ratio(current[num], current[den])
        prev = _ratio(previous[num], previous[den]) if previous else None
        change[f"{f}_change_pp"] = None if cur is None or prev is None else round(cur - prev, 1)
    return change


def compute_store_kpis(df: pd.DataFrame) -> dict | None:
    """정규화 DataFrame 중 스마트스토어 판매 분석 행 → AnalyzeResponse.store. 해당 행이 없으면 None.

    기간은 스마트스토어 데이터의 최신 월과 직전 월. products 는 최신 월 상품별 지표(총매출 내림차순, 최대 10개)이며
    각 상품의 전월 환불률·전환율 증감(%p)을 함께 준다.
    """
    if "visits" not in df.columns:
        return None
    store = df[df["visits"].notna()]
    if store.empty:
        return None
    store = store.astype({f: "int64" for f in STORE_SUM_FIELDS})
    periods = sorted(store["period"].unique())
    period = periods[-1]
    previous_period = periods[-2] if len(periods) > 1 else None
    cur_df = store[store["period"] == period]
    prev_df = store[store["period"] == previous_period] if previous_period else None
    current = store_totals(cur_df)
    previous = store_totals(prev_df) if prev_df is not None else None

    products = []
    for (pid, name), group in cur_df.groupby(["product_id", "product_name"], sort=True):
        t = store_totals(group)
        prev_group = prev_df[prev_df["product_id"] == pid] if prev_df is not None else None
        p = store_totals(prev_group) if prev_group is not None and not prev_group.empty else None
        change = _store_change(t, p)
        products.append({
            "product_id": pid,
            "product_name": name,
            **{k: t[k] for k in ("visits", "orders", "gross_revenue", "revenue", "conversion_rate", "refund_rate", "discount_rate", "aov")},
            "refund_rate_change_pp": change["refund_rate_change_pp"],
            "conversion_rate_change_pp": change["conversion_rate_change_pp"],
        })
    products.sort(key=lambda r: r["gross_revenue"], reverse=True)

    trend = [{"period": p, **{k: store_totals(g)[k] for k in ("visits", "orders", "revenue", "conversion_rate")}}
             for p, g in store.groupby("period", sort=True)]
    return {
        "period": period,
        "previous_period": previous_period,
        "current": current,
        "previous": previous,
        "change": _store_change(current, previous),
        "products": products[:STORE_PRODUCT_LIMIT],
        "trend": trend,
    }
