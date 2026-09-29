from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from .client import LLMClientError, OpenAIStructuredClient
from .models import AnalysisPlan, Insight, InsightDraft
from .prompts import INSIGHT_INSTRUCTIONS


TModel = TypeVar("TModel", bound=BaseModel)
_NUMBER_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


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
                numbers.add(float(token.replace(",", "")))
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


def _evidence_matches_input(evidence: str, allowed_numbers: set[float]) -> bool:
    """Keep only evidence whose every numeric token exists in the input."""

    for token in _NUMBER_RE.findall(evidence):
        try:
            if float(token.replace(",", "")) not in allowed_numbers:
                return False
        except ValueError:
            return False
    return True


def _filter_evidence(evidence: Sequence[str], *inputs: Any) -> list[str]:
    allowed_numbers: set[float] = set()
    for value in inputs:
        allowed_numbers.update(_numbers_from_value(value))
    return [
        item
        for item in evidence
        if isinstance(item, str) and _evidence_matches_input(item, allowed_numbers)
    ]


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

    generator = llm or OpenAIStructuredClient()
    try:
        generated = generator.generate_structured(
            schema=InsightDraft,
            instructions=INSIGHT_INSTRUCTIONS,
            input_text=json.dumps(payload, ensure_ascii=False, default=str),
            max_output_tokens=800,
        )
    except LLMClientError as exc:
        return Insight(status="llm_error", reason=exc.code)

    # Plan and answer are computed upstream; never let the explanation model
    # rewrite them while assembling the API response.
    filtered = _filter_evidence(generated.evidence, kpis, comparison, signals, answer)
    fields = generated.model_dump(include=set(InsightDraft.model_fields))
    fields["evidence"] = filtered
    return Insight(
        **fields,
        plan=plan,
        answer=list(answer) if answer is not None else [],
    )
