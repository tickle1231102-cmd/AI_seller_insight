from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class PlannerDecision(BaseModel):
    """Structured output requested from the LLM before exposing a plan."""

    status: Literal["ok", "unsupported_question"]
    plan: AnalysisPlan | None = None
    reason: str | None = None

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
    plan: AnalysisPlan | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> "PlannerResult":
        if self.status == "ok" and self.plan is None:
            raise ValueError("plan is required when status='ok'")
        if self.status != "ok" and self.plan is not None:
            raise ValueError("plan must be null for non-ok results")
        return self


class InsightDraft(BaseModel):
    """Structured output requested from the LLM for the insight explanation.

    plan/answer are computed upstream and attached afterwards, so they are
    kept out of this schema (free-form dicts are rejected by strict
    structured outputs).
    """

    status: Literal["ok", "unsupported_question"]
    summary: str = ""
    evidence: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reason: str | None = None


class Insight(BaseModel):
    """Safe, display-ready explanation of deterministic analysis results."""

    status: Literal["ok", "unsupported_question", "llm_error", "skipped"]
    plan: AnalysisPlan | None = None
    answer: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    evidence: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reason: str | None = None
