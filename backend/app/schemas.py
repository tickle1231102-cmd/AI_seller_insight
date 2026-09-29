"""API 요청/응답 스키마 (TECH_SPEC 7장, shared/contracts/ 기준).

필드 변경은 전원 합의 후에만 한다. frontend/types/api.ts 와 동일한 구조를 유지한다.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_serializer

Platform = Literal["coupang", "naver", "naver_store"]

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


STORE_ROW_FIELDS = ("gross_revenue", "visits", "refund_count", "refund_amount", "discount_amount")


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
    # 스마트스토어 판매 분석 파일의 행만 값이 있다 (그 외 None)
    gross_revenue: Won | None = None
    visits: int | None = None
    refund_count: int | None = None
    refund_amount: Won | None = None
    discount_amount: Won | None = None

    @model_serializer(mode="wrap")
    def _drop_empty_store_fields(self, handler):
        """스마트스토어가 아닌 행은 기존 9개 필드 계약 그대로 내보낸다."""
        data = handler(self)
        return {k: v for k, v in data.items() if k not in STORE_ROW_FIELDS or v is not None}


# ---- 스마트스토어 판매 분석 (퍼널·수익 품질) ----
class StoreValues(BaseModel):
    visits: int
    orders: int
    units: int
    gross_revenue: Won
    revenue: Won  # 판매금액(순)
    refund_count: int
    refund_amount: Won
    discount_amount: Won
    conversion_rate: float | None  # 결제건수/방문수 (%)
    net_ratio: float | None  # 순매출/총매출 (%)
    refund_rate: float | None  # 환불건수/결제건수 (%)
    refund_amount_rate: float | None  # 환불금액/총매출 (%)
    discount_rate: float | None  # 전체 할인액/총매출 (%)
    aov: Won | None  # 총매출/결제건수


class StoreChange(BaseModel):
    visits_change: float | None
    orders_change: float | None
    gross_revenue_change: float | None
    revenue_change: float | None
    aov_change: float | None
    conversion_rate_change_pp: float | None
    net_ratio_change_pp: float | None
    refund_rate_change_pp: float | None
    refund_amount_rate_change_pp: float | None
    discount_rate_change_pp: float | None


class StoreProduct(BaseModel):
    product_id: str
    product_name: str
    visits: int
    orders: int
    gross_revenue: Won
    revenue: Won
    conversion_rate: float | None
    refund_rate: float | None
    discount_rate: float | None
    aov: Won | None
    refund_rate_change_pp: float | None
    conversion_rate_change_pp: float | None


class StoreTrendPoint(BaseModel):
    period: str
    visits: int
    orders: int
    revenue: Won
    conversion_rate: float | None


class StoreKPIs(BaseModel):
    period: str
    previous_period: str | None
    current: StoreValues
    previous: StoreValues | None
    change: StoreChange
    products: list[StoreProduct]
    trend: list[StoreTrendPoint]


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
    store: StoreKPIs | None = None  # 스마트스토어 판매 분석 파일이 없으면 None


# ---- 오류 ----
class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorBody
