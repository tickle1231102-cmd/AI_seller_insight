"""담당: C — TECH_SPEC 5장 참고.

아래 함수 이름·시그니처는 B 의 routers/analyze.py 가 호출하는 계약이다.
"""

from typing import Any

from app.analysis.kpi import STORE_SUM_FIELDS, _pct_change, _ratio, previous_calendar_month, raw_roas, store_totals, totals
from app.analysis.normalize import STORE_PLATFORM, core_rows
from app.core.errors import AppError

DEFAULT_LIMIT = 5
GROUP_KEYS = {"platform": ["platform"], "period": ["period"], "product": ["product_id", "product_name"]}
# 전월 대비 증감 지표 → 원 지표. 금액·건수는 증감률(%), ROAS 는 증감(%p).
CHANGE_METRICS = {
    "revenue_change": "revenue",
    "orders_change": "orders",
    "units_change": "units",
    "ad_spend_change": "ad_spend",
    "ad_revenue_change": "ad_revenue",
    "roas_change_pp": "roas",
    "visits_change": "visits",
    "gross_revenue_change": "gross_revenue",
    "aov_change": "aov",
    "conversion_rate_change_pp": "conversion_rate",
    "refund_rate_change_pp": "refund_rate",
    "discount_rate_change_pp": "discount_rate",
}
# 스마트스토어 판매 분석 파일에만 있는 지표. 스마트스토어 행만 골라 store_totals 로 계산한다.
STORE_METRICS = {"visits", "gross_revenue", "aov", "conversion_rate", "refund_rate", "discount_rate"}
# 비율 지표의 반올림 전 원값. 증감은 이 값끼리 뺀 %p 다.
_RAW_RATES = {
    "roas": lambda t: raw_roas(t["ad_revenue"], t["ad_spend"]),
    "conversion_rate": lambda t: _ratio(t["orders"], t["visits"]),
    "refund_rate": lambda t: _ratio(t["refund_count"], t["orders"]),
    "discount_rate": lambda t: _ratio(t["discount_amount"], t["gross_revenue"]),
}


def _scope(df, base: str):
    """지표에 맞는 행만 남긴다.

    스마트스토어 지표면 스마트스토어 행만 (없으면 AppError). 그 외 지표는 routers/analyze.py 의 kpis 와 같은 규칙
    (normalize.core_rows) 으로 판매액이 겹치는 스마트스토어 행을 빼거나 naver 로 합친다.
    """
    if base not in STORE_METRICS:
        return core_rows(df)
    store = df[df["platform"] == STORE_PLATFORM]
    if store.empty:
        raise AppError(
            "STORE_DATA_NOT_FOUND",
            "방문수·전환율·환불률·할인율·결제단가는 스마트스토어 판매 분석(SALES) 파일이 있어야 답할 수 있어요.",
            422,
            {"metric": base},
        )
    return store.astype({f: "int64" for f in STORE_SUM_FIELDS})


def _totals(group, base: str) -> dict:
    return store_totals(group) if base in STORE_METRICS else totals(group)


def build_comparison(df) -> dict:
    """정규화 DataFrame → TECH_SPEC 7-4 의 comparison (by_platform, trend).

    by_platform 은 최신 월 기준, trend 는 전체 기간(오래된 월부터).
    """
    latest = df[df["period"] == df["period"].max()]
    by_platform = []
    for platform, group in latest.groupby("platform", sort=True):
        t = totals(group)
        by_platform.append({"platform": platform, **{k: t[k] for k in ("revenue", "orders", "ad_spend", "ad_revenue", "roas")}})
    trend = []
    for period, group in df.groupby("period", sort=True):
        t = totals(group)
        trend.append({"period": period, "revenue": t["revenue"], "roas": t["roas"]})
    return {"by_platform": by_platform, "trend": trend}


def _get(plan: Any, key: str, default: Any = None) -> Any:
    """D 의 AnalysisPlan(pydantic)과 dict 를 모두 받고, 값이 None 이면 default 로 본다."""
    value = plan.get(key) if isinstance(plan, dict) else getattr(plan, key, None)
    return default if value is None else value


def run_plan(df, plan) -> list[dict]:
    """D 의 AnalysisPlan (metric, group_by, sort, limit, period) 을 실행 → insight.answer 행 목록.

    sort=None → desc, limit=None → 5, period=None → 최신 월, group_by=None → 전체 1행.
    단, group_by="period" 이면서 period=None 이면 월별 비교가 목적이므로 전체 기간을 쓴다.
    그룹별 ROAS 는 행 평균이 아니라 그룹 합계로 다시 계산한다. 데이터에 없는 월이면 AppError.
    """
    metric = _get(plan, "metric")
    if metric in CHANGE_METRICS:
        return _run_change_plan(df, plan, metric)
    df = _scope(df, metric)
    group_by = _get(plan, "group_by")
    descending = _get(plan, "sort", "desc") != "asc"
    limit = _get(plan, "limit", DEFAULT_LIMIT)
    period = _get(plan, "period")

    if period is None and group_by != "period":
        period = df["period"].max()
    if period is not None:
        available = sorted(df["period"].unique())
        if period not in available:
            raise AppError(
                "PERIOD_NOT_FOUND",
                f"{period} 데이터가 업로드한 파일에 없어요. 업로드된 기간은 {', '.join(available)}입니다. "
                "이 기간 안에서 다시 질문해 주세요.",
                422,
                {"period": period, "available": available},
            )
        df = df[df["period"] == period]

    if group_by is None:
        return [{metric: _totals(df, metric)[metric]}]

    keys = GROUP_KEYS[group_by]
    rows = []
    for key, group in df.groupby(keys, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip(keys, key)), metric: _totals(group, metric)[metric]})
    # 값이 None(ROAS 분모 0)인 그룹은 방향과 상관없이 맨 뒤로 보낸다. 동률은 그룹 키 순으로 안정 정렬.
    known = sorted((r for r in rows if r[metric] is not None), key=lambda r: r[metric], reverse=descending)
    unknown = [r for r in rows if r[metric] is None]
    return (known + unknown)[:limit]


def _change(base: str, current: dict, previous: dict) -> float | None:
    if base in _RAW_RATES:  # 비율 증감(%p)은 반올림 전 원값끼리 뺀다
        cur, prev = _RAW_RATES[base](current), _RAW_RATES[base](previous)
        return None if cur is None or prev is None else round(cur - prev, 1)
    cur, prev = current[base], previous[base]
    return None if cur is None or prev is None else _pct_change(cur, prev)


def _run_change_plan(df, plan, metric: str) -> list[dict]:
    """증감 지표 (예: ad_spend_change) — 기준 월(period, 없으면 최신 월)과 달력상 전월을 그룹별로 비교한다.

    각 행: 그룹 키, {원 지표}_previous, {원 지표}, {증감 지표}. 전월 자료가 없거나 월별로 묶으면 AppError.
    """
    base = CHANGE_METRICS[metric]
    df = _scope(df, base)
    group_by = _get(plan, "group_by")
    descending = _get(plan, "sort", "desc") != "asc"
    limit = _get(plan, "limit", DEFAULT_LIMIT)
    available = sorted(df["period"].unique())
    period = _get(plan, "period", available[-1])

    if group_by == "period":
        raise AppError(
            "UNSUPPORTED_PLAN",
            "전월 대비 증감은 월별로 묶을 수 없어요. 플랫폼별·상품별로 물어보거나 월별 추이를 물어봐 주세요.",
            422,
            {"metric": metric, "group_by": group_by},
        )
    if period not in available:
        raise AppError(
            "PERIOD_NOT_FOUND",
            f"{period} 데이터가 업로드한 파일에 없어요. 업로드된 기간은 {', '.join(available)}입니다. "
            "이 기간 안에서 다시 질문해 주세요.",
            422,
            {"period": period, "available": available},
        )
    # '전월' 은 직전 업로드 월이 아니라 달력상 바로 앞 달이다 (2026-09 → 2026-08, 2026-01 → 2025-12).
    previous_period = previous_calendar_month(period)
    if previous_period not in available:
        raise AppError(
            "PREVIOUS_PERIOD_NOT_FOUND",
            f"{period} 의 전월({previous_period}) 데이터가 없어 증감을 계산할 수 없어요. "
            f"업로드된 기간은 {', '.join(available)}입니다. {previous_period} 파일도 함께 올려 주세요.",
            422,
            {"period": period, "previous_period": previous_period, "available": available},
        )
    cur_df = df[df["period"] == period]
    prev_df = df[df["period"] == previous_period]

    def row(cur, prev) -> dict:
        c, p = _totals(cur, base), _totals(prev, base)
        return {f"{base}_previous": p[base], base: c[base], metric: _change(base, c, p)}

    if group_by is None:
        return [row(cur_df, prev_df)]

    keys = GROUP_KEYS[group_by]
    rows = []
    for key, group in cur_df.groupby(keys, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        mask = (prev_df[keys] == list(key)).all(axis=1)
        rows.append({**dict(zip(keys, key)), **row(group, prev_df[mask])})
    # 전월 값이 0이라 증감을 못 구한 그룹은 맨 뒤로 보낸다.
    known = sorted((r for r in rows if r[metric] is not None), key=lambda r: r[metric], reverse=descending)
    unknown = [r for r in rows if r[metric] is None]
    return (known + unknown)[:limit]
