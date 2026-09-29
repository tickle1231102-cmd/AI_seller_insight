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
