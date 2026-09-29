from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .client import LLMClientError, OpenAIStructuredClient
from .models import AnalysisPlan, Insight, InsightContent
from .number_grounding import NumberGrounding
from .prompts import INSIGHT_INSTRUCTIONS


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


def create_insight(
    kpis: Mapping[str, Any],
    comparison: Mapping[str, Any],
    signals: Sequence[Mapping[str, Any]],
    *,
    plan: AnalysisPlan | None = None,
    answer: Sequence[Mapping[str, Any]] | None = None,
    llm: StructuredGenerator | None = None,
) -> Insight:
    """Turn C's deterministic results into a validated, safe insight."""

    payload: dict[str, Any] = {
        "kpis": kpis,
        "comparison": comparison,
        "signals": signals,
    }
    if plan is not None:
        payload["plan"] = plan.model_dump()
    if answer is not None:
        payload["answer"] = answer

    # Always rebuild caller-owned fields, including when no question was asked.
    caller_fields = {"plan": plan, "answer": list(answer) if answer is not None else []}
    generator = llm or OpenAIStructuredClient()
    try:
        generated = generator.generate_structured(
            schema=InsightContent,
            instructions=INSIGHT_INSTRUCTIONS,
            input_text=json.dumps(payload, ensure_ascii=False, default=str),
            max_output_tokens=800,
        )
    except LLMClientError as exc:
        return Insight(status="llm_error", reason=exc.code, **caller_fields)

    try:
        # Validate even an injected generator. Ignore any attempted metadata
        # injection rather than copying the provider's full response object.
        fields = InsightContent.model_fields
        raw = generated.model_dump() if isinstance(generated, BaseModel) else generated
        content = InsightContent.model_validate(
            {name: raw[name] for name in fields if name in raw}
            if isinstance(raw, Mapping)
            else raw
        )
    except (ValidationError, ValueError, TypeError):
        return Insight(status="llm_error", reason="invalid_structured_output", **caller_fields)

    grounding = NumberGrounding.from_results(
        kpis, comparison, signals, answer, answer_count=len(caller_fields["answer"])
    )

    # Preserve the agreed evidence-filter policy. An unsafe number in any other
    # display field rejects the explanation entirely; deterministic data stays.
    filtered = [item for item in content.evidence if grounding.matches(item, field_name="evidence")]
    for field_name in ("summary", "checks", "actions", "limitations"):
        value = getattr(content, field_name)
        items = [value] if field_name == "summary" else value
        if not all(grounding.matches(item, field_name=field_name) for item in items):
            return Insight(status="llm_error", reason="ungrounded_insight_number", **caller_fields)

    return Insight(
        status="ok",
        **caller_fields,
        **content.model_dump(exclude={"evidence"}),
        evidence=filtered,
    )
