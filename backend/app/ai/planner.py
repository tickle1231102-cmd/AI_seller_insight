from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from .client import LLMClientError, OpenAIStructuredClient
from .models import PlannerDecision, PlannerResult
from .prompts import PLANNER_INSTRUCTIONS


TModel = TypeVar("TModel", bound=BaseModel)


class StructuredGenerator(Protocol):
    def generate_structured(
        self,
        *,
        schema: type[TModel],
        instructions: str,
        input_text: str,
        max_output_tokens: int = 600,
    ) -> TModel: ...


def create_analysis_plan(
    question: str,
    *,
    llm: StructuredGenerator | None = None,
) -> PlannerResult:
    """Convert a user question into a validated AnalysisPlan.

    This function never executes pandas calculations. It only produces the plan
    that C's analysis.compare.run_plan(df, plan) will execute.
    """

    normalized = question.strip()
    if not normalized:
        return PlannerResult(
            status="unsupported_question",
            reason="질문이 비어 있습니다.",
        )
    if len(normalized) > 300:
        return PlannerResult(
            status="unsupported_question",
            reason="질문은 300자 이하여야 합니다.",
        )

    generator = llm or OpenAIStructuredClient()

    try:
        decision = generator.generate_structured(
            schema=PlannerDecision,
            instructions=PLANNER_INSTRUCTIONS,
            input_text=normalized,
            max_output_tokens=500,
        )
    except LLMClientError as exc:
        return PlannerResult(
            status="llm_error",
            reason=exc.code,
        )

    if decision.status == "unsupported_question":
        return PlannerResult(
            status="unsupported_question",
            reason=decision.reason or "지원하지 않는 분석 질문입니다.",
        )

    return PlannerResult(
        status="ok",
        plan=decision.plan,
    )
