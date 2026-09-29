"""담당: C — TECH_SPEC 5장 참고.

아래 함수 이름·시그니처는 B 의 routers/analyze.py 가 호출하는 계약이다.
"""

from typing import Any

from app.analysis.kpi import totals
from app.core.errors import AppError

DEFAULT_LIMIT = 5
GROUP_KEYS = {"platform": ["platform"], "period": ["period"], "product": ["product_id", "product_name"]}


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
        return [{metric: totals(df)[metric]}]

    keys = GROUP_KEYS[group_by]
    rows = []
    for key, group in df.groupby(keys, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip(keys, key)), metric: totals(group)[metric]})
    # 값이 None(ROAS 분모 0)인 그룹은 방향과 상관없이 맨 뒤로 보낸다. 동률은 그룹 키 순으로 안정 정렬.
    known = sorted((r for r in rows if r[metric] is not None), key=lambda r: r[metric], reverse=descending)
    unknown = [r for r in rows if r[metric] is None]
    return (known + unknown)[:limit]
