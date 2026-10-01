from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .client import LLMClientError, OpenAIStructuredClient
from .models import AnalysisPlan, ProductDiagnosisPlan, Insight, InsightSelection
from .diagnosis_insight import create_diagnosis_insight
from .facts import EvidenceCatalogue
from .prompts import INSIGHT_INSTRUCTIONS

TModel = TypeVar("TModel", bound=BaseModel)


class StructuredGenerator(Protocol):
    def generate_structured(
        self, *, schema: type[TModel], instructions: str, input_text: str,
        max_output_tokens: int = 600,
    ) -> TModel: ...


def create_insight(
    kpis: Mapping[str, Any], comparison: Mapping[str, Any],
    signals: Sequence[Mapping[str, Any]], *,
    plan: AnalysisPlan | ProductDiagnosisPlan | None = None,
    answer: Sequence[Mapping[str, Any]] | None = None,
    llm: StructuredGenerator | None = None,
) -> Insight:
    """Let AI prioritize verified facts; only the server renders public text."""
    if getattr(plan, "analysis_type", None) == "product_diagnosis":
        return create_diagnosis_insight(plan, answer)
    caller_fields = {"plan": plan, "answer": list(answer) if answer is not None else []}
    catalogue = EvidenceCatalogue.build(kpis, comparison, signals, plan, answer)
    if catalogue.conflicts:
        return Insight(status="unsupported_question", **caller_fields,
                       reason="inconsistent_analysis_results",
                       summary="같은 기간·대상·지표의 계산 결과가 서로 달라 AI 설명을 생성하지 않았습니다. 원자료와 계산 결과를 확인하세요.",
                       limitations=["같은 기간·대상·지표의 계산 결과가 서로 달라 AI 설명을 생성하지 않았습니다. 원자료와 계산 결과를 확인하세요."])
    if plan is not None and not catalogue.answer_ids:
        return Insight(status="unsupported_question", **caller_fields,
                       summary="질문 조건에 해당하는 계산 가능한 결과가 없습니다.",
                       limitations=catalogue.limitations, reason="no_supported_answer")
    if not catalogue.facts:
        return Insight(status="ok", **caller_fields,
                       summary="현재 자료에서 설명할 수 있는 계산 결과가 없습니다.",
                       limitations=catalogue.limitations)
    payload = catalogue.payload()
    payload["plan"] = plan.model_dump() if plan else None
    generator = llm or OpenAIStructuredClient()
    try:
        generated = generator.generate_structured(
            schema=InsightSelection, instructions=INSIGHT_INSTRUCTIONS,
            input_text=json.dumps(payload, ensure_ascii=False, default=str),
            max_output_tokens=800,
        )
    except LLMClientError as exc:
        return Insight(status="llm_error", reason=exc.code, **caller_fields)
    try:
        fields = InsightSelection.model_fields
        raw = generated.model_dump() if isinstance(generated, BaseModel) else generated
        # Ignore attempted status/plan/answer/reason injection.
        selection = InsightSelection.model_validate(
            {name: raw[name] for name in fields if name in raw}
            if isinstance(raw, Mapping) else raw)
    except (ValidationError, ValueError, TypeError):
        return Insight(status="llm_error", reason="invalid_structured_output", **caller_fields)

    if (any(fid not in catalogue.facts for fid in selection.summary_fact_ids)
            or any(cid not in catalogue.checks for cid in selection.check_ids)
            or any(aid not in catalogue.actions for aid in selection.action_ids)):
        return Insight(status="llm_error", reason="ungrounded_insight_reference", **caller_fields)
    chosen = list(dict.fromkeys(catalogue.answer_ids[:3] + selection.summary_fact_ids))[:3]
    chosen = chosen or catalogue.default_ids
    # Filter unsupported evidence individually; always keep the summary's support.
    evidence_ids = list(dict.fromkeys(chosen + [
        fid for fid in selection.evidence_fact_ids if fid in catalogue.facts]))[:12]
    return Insight(
        status="ok", **caller_fields,
        summary=" ".join(dict.fromkeys(catalogue.facts[fid].text for fid in chosen)),
        evidence=list(dict.fromkeys(catalogue.facts[fid].text for fid in evidence_ids)),
        checks=[catalogue.checks[cid] for cid in dict.fromkeys(selection.check_ids or ["check_source"])],
        actions=[catalogue.actions[aid] for aid in dict.fromkeys(selection.action_ids or ["verify_before_change"])],
        limitations=catalogue.limitations,
    )
