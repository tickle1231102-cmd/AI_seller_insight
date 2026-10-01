from __future__ import annotations

import json
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .client import LLMClientError, OpenAIStructuredClient
from .models import PlannerDecision, PlannerResult
from .diagnosis_policy import diagnosis_plan
from .question_policy import inspect_question, plan_mismatch
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


def _planner_input(question: str, periods: list[str] | None, expected: dict) -> str:
    return json.dumps({"question": question, "uploaded_periods": periods or [],
                       "explicit_conditions": expected}, ensure_ascii=False)


def create_analysis_plan(
    question: str,
    *,
    periods: list[str] | None = None,
    llm: StructuredGenerator | None = None,
) -> PlannerResult:
    """Convert a user question into a validated AnalysisPlan.

    periods are the uploaded YYYY-MM months (oldest first). They let the model
    resolve relative month words such as "8월", "지난달", "이번 달".

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

    diagnosis = diagnosis_plan(normalized, periods=periods)
    if diagnosis is not None:
        return diagnosis
    requirements = inspect_question(normalized, periods=periods)
    if requirements.reason:
        return PlannerResult(status="unsupported_question", reason=requirements.reason)
    generator = llm or OpenAIStructuredClient()

    try:
        decision = generator.generate_structured(
            schema=PlannerDecision,
            instructions=PLANNER_INSTRUCTIONS,
            input_text=_planner_input(normalized, periods, requirements.expected),
            max_output_tokens=500,
        )
    except LLMClientError as exc:
        return PlannerResult(
            status="llm_error",
            reason=exc.code,
        )

    try:
        decision = PlannerDecision.model_validate(
            decision.model_dump() if isinstance(decision, BaseModel) else decision)
    except (ValidationError, TypeError, ValueError):
        return PlannerResult(status="llm_error", reason="invalid_structured_output")

    if decision.status == "unsupported_question" or decision.unrepresented_constraints:
        return PlannerResult(
            status="unsupported_question",
            reason="질문의 조건을 현재 분석 계획에 모두 반영할 수 없습니다. 지원하는 지표 하나를 플랫폼별·상품별·월별로 질문해 주세요.",
        )

    mismatch = plan_mismatch(requirements, decision.plan)
    if mismatch:
        return PlannerResult(status="unsupported_question", reason=mismatch)

    return PlannerResult(
        status="ok",
        plan=decision.plan,
    )
