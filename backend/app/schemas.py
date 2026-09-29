"""API 요청/응답 스키마 (TECH_SPEC 7장, shared/contracts/ 기준).

필드 변경은 전원 합의 후에만 한다. frontend/types/api.ts 와 동일한 구조를 유지한다.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Platform = Literal["coupang", "naver"]

# 금액(원)은 정수. KRW 는 소수점이 없고 12600000.0 처럼 직렬화되지 않게 한다.
Won = int


# ---- /api/preview ----
class PreviewFile(BaseModel):
    filename: str
    platform: Platform
    periods: list[str]
    row_count: int
    columns: list[str]
    preview: list[dict[str, Any]]


class PreviewResponse(BaseModel):
    files: list[PreviewFile]


# ---- /api/analyze ----
class KPIValues(BaseModel):
    revenue: Won
    orders: int
    units: int
    ad_spend: Won
    ad_revenue: Won
    roas: float | None


class KPIChange(BaseModel):
    revenue_change: float | None
    orders_change: float | None
    units_change: float | None
    ad_spend_change: float | None
    ad_revenue_change: float | None
    roas_change_pp: float | None


class KPIs(BaseModel):
    period: str
    previous_period: str | None
    current: KPIValues
    previous: KPIValues | None
    change: KPIChange


class PlatformComparison(BaseModel):
    platform: Platform
    revenue: Won
    orders: int
    ad_spend: Won
    ad_revenue: Won
    roas: float | None


class TrendPoint(BaseModel):
    period: str
    revenue: Won
    roas: float | None


class Comparison(BaseModel):
    by_platform: list[PlatformComparison]
    trend: list[TrendPoint]


class Row(BaseModel):
    period: str
    platform: Platform
    product_id: str
    product_name: str
    revenue: Won
    orders: int
    units: int
    ad_spend: Won
    ad_revenue: Won


class Signal(BaseModel):
    """신호마다 추가 필드가 다르다 (TECH_SPEC 6장). signal, platform 외 필드는 그대로 통과."""

    model_config = ConfigDict(extra="allow")

    signal: Literal["ROAS_DOWN_WITH_SPEND_GROWTH", "REVENUE_DOWN", "LOW_ROAS_PLATFORM"]
    platform: str


class Insight(BaseModel):
    status: Literal["ok", "unsupported_question", "llm_error", "skipped"]
    plan: dict[str, Any] | None = None
    answer: list[dict[str, Any]] | None = None
    summary: str = ""  # TS 타입(summary?: string)이 null 을 허용하지 않아 빈 문자열로 둔다
    evidence: list[str] = []
    checks: list[str] = []
    actions: list[str] = []
    limitations: list[str] = []


class AnalyzeResponse(BaseModel):
    kpis: KPIs
    comparison: Comparison
    rows: list[Row]
    signals: list[Signal]
    insight: Insight


# ---- 오류 ----
class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorBody
