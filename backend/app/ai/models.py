from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Metric = Literal[
    "revenue",
    "orders",
    "units",
    "ad_spend",
    "ad_revenue",
    "roas",
    # 전월 대비 증감 (금액·건수는 %, ROAS 는 %p)
    "revenue_change",
    "orders_change",
    "units_change",
    "ad_spend_change",
    "ad_revenue_change",
    "roas_change_pp",
    # 스마트스토어 판매 분석 파일 전용
    "visits",
    "gross_revenue",
    "aov",
    "conversion_rate",
    "refund_rate",
    "discount_rate",
    "visits_change",
    "gross_revenue_change",
    "aov_change",
    "conversion_rate_change_pp",
    "refund_rate_change_pp",
    "discount_rate_change_pp",
    # 쿠팡 판매 분석(옵션별 지표) 파일 전용
    "coupang_visits",
    "coupang_aov",
    "coupang_conversion_rate",
    "coupang_cart_rate",
    "coupang_cancel_rate",
    "coupang_visits_change",
    "coupang_aov_change",
    "coupang_conversion_rate_change_pp",
    "coupang_cart_rate_change_pp",
    "coupang_cancel_rate_change_pp",
]
GroupBy = Literal["platform", "period", "product"]
SortOrder = Literal["asc", "desc"]


class AnalysisPlan(BaseModel):
    """Deterministic analysis instruction executed by C's pandas module."""

    metric: Metric
    group_by: GroupBy | None = None
    sort: SortOrder | None = None
    limit: int = Field(default=5, ge=1, le=50)
    period: str | None = Field(
        default=None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Optional YYYY-MM period filter.",
    )


class ProductDiagnosisPlan(BaseModel):
    """Deterministic composite query, carried inside the existing Insight.plan."""

    model_config = ConfigDict(extra="forbid")
    analysis_type: Literal["product_diagnosis"] = "product_diagnosis"
    diagnosis_intent: Literal["opportunity", "attention"]
    limit: int = Field(default=5, ge=1, le=50, strict=True)
    period: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    required_conditions: list[Literal["revenue_up", "ad_spend_down", "ad_spend_up",
                                      "ad_revenue_down", "ad_revenue_not_up", "roas_down"]] = Field(default_factory=list)


class PlannerDecision(BaseModel):
    """Structured output requested from the LLM before exposing a plan."""

    status: Literal["ok", "unsupported_question"]
    plan: AnalysisPlan | None = None
    reason: str | None = None
    unrepresented_constraints: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan_presence(self) -> "PlannerDecision":
        if self.status == "ok" and self.plan is None:
            raise ValueError("plan is required when status='ok'")
        if self.status == "unsupported_question" and self.plan is not None:
            raise ValueError("plan must be null when question is unsupported")
        return self


class PlannerResult(BaseModel):
    """Safe result returned to the backend integration layer."""

    status: Literal["ok", "unsupported_question", "llm_error"]
    plan: AnalysisPlan | ProductDiagnosisPlan | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> "PlannerResult":
        if self.status == "ok" and self.plan is None:
            raise ValueError("plan is required when status='ok'")
        if self.status != "ok" and self.plan is not None:
            raise ValueError("plan must be null for non-ok results")
        return self


class InsightDraft(BaseModel):
    """Text-only LLM output, compatible with OpenAI's strict schema.

    Keep main's Draft name, but status/reason/plan/answer remain server-owned.
    """

    summary: str
    evidence: list[str]
    checks: list[str]
    actions: list[str]
    limitations: list[str]


# Preserve the earlier PR #10 import name without a second, divergent schema.
InsightContent = InsightDraft


class InsightSelection(BaseModel):
    """Internal model output: IDs only. Public Insight remains unchanged."""

    summary_fact_ids: list[str] = Field(max_length=3)
    evidence_fact_ids: list[str] = Field(max_length=12)
    check_ids: list[str] = Field(max_length=3)
    action_ids: list[str] = Field(max_length=3)


class Insight(BaseModel):
    """Safe, display-ready explanation of deterministic analysis results."""

    status: Literal["ok", "unsupported_question", "llm_error", "skipped"]
    plan: AnalysisPlan | ProductDiagnosisPlan | None = None
    answer: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    evidence: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reason: str | None = None
