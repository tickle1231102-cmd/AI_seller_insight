from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .client import LLMClientError, OpenAIStructuredClient
from .models import AnalysisPlan, Insight, InsightContent
from .prompts import INSIGHT_INSTRUCTIONS


TModel = TypeVar("TModel", bound=BaseModel)
_NUMBER_RE = re.compile(r"[-+−]?(?:\d[\d,]*(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def _parse_number(token: str) -> float:
    return float(token.replace(",", "").replace("−", "-"))


class StructuredGenerator(Protocol):
    def generate_structured(
        self,
        *,
        schema: type[TModel],
        instructions: str,
        input_text: str,
        max_output_tokens: int = 600,
    ) -> TModel: ...


def _numbers_from_value(value: Any) -> set[float]:
    """Collect comparable numeric values from nested contract payloads."""

    if isinstance(value, bool) or value is None:
        return set()
    if isinstance(value, (int, float)):
        return {float(value)}
    if isinstance(value, str):
        numbers: set[float] = set()
        for token in _NUMBER_RE.findall(value):
            try:
                numbers.add(_parse_number(token))
            except ValueError:
                continue
        return numbers
    if isinstance(value, Mapping):
        result: set[float] = set()
        for nested in value.values():
            result.update(_numbers_from_value(nested))
        return result
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        result = set()
        for nested in value:
            result.update(_numbers_from_value(nested))
        return result
    return set()


def _text_matches_input(text: str, allowed_numbers: set[float]) -> bool:
    """Check numeric membership, not the meaning or attribution of a claim."""

    for token in _NUMBER_RE.findall(text):
        try:
            if _parse_number(token) not in allowed_numbers:
                return False
        except ValueError:
            return False
    return True


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

    allowed_numbers: set[float] = set()
    for value in (kpis, comparison, signals, answer):
        allowed_numbers.update(_numbers_from_value(value))

    # Preserve the agreed evidence-filter policy. An unsafe number in any other
    # display field rejects the explanation entirely; deterministic data stays.
    filtered = [item for item in content.evidence if _text_matches_input(item, allowed_numbers)]
    other_text = [content.summary, *content.checks, *content.actions, *content.limitations]
    if not all(_text_matches_input(item, allowed_numbers) for item in other_text):
        return Insight(status="llm_error", reason="ungrounded_insight_number", **caller_fields)

    return Insight(
        status="ok",
        **caller_fields,
        **content.model_dump(exclude={"evidence"}),
        evidence=filtered,
    )
