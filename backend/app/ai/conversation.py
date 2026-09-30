"""Conversational fallback for questions the planner cannot turn into a plan.

The planner stays strict. When it rejects a question (greeting, "why?",
advice, follow-up), this module lets the model answer naturally using the
already-computed KPI results as context. Numbers are never recalculated here:
any number in the reply must already appear in the input, otherwise the
caller falls back to the original unsupported_question response.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .client import LLMClientError, OpenAIStructuredClient
from .models import Insight
from .prompts import CONVERSATION_INSTRUCTIONS

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


class ConversationReply(BaseModel):
    reply: str
    suggested_questions: list[str] = Field(max_length=3)


def _numbers(text: str) -> set[str]:
    found = set()
    for raw in NUMBER.findall(text):
        value = raw.replace(",", "")
        found.add(value)
        found.add(value.lstrip("0") or "0")  # "2026-08" 의 08 → "8월"
        if "." in value:
            found.add(value.rstrip("0").rstrip("."))
    return found


def _grounded(text: str, context: str) -> bool:
    allowed = _numbers(context)
    return all(n in allowed for n in _numbers(text))


def create_conversation_reply(
    question: str, kpis: Mapping[str, Any], comparison: Mapping[str, Any],
    signals: Sequence[Mapping[str, Any]], *, reason: str | None = None,
    llm: Any | None = None,
) -> Insight | None:
    """Return a natural reply, or None so the caller keeps its old response."""
    context = json.dumps(
        {"kpis": kpis, "comparison": comparison, "signals": list(signals)},
        ensure_ascii=False, default=str)
    payload = json.dumps(
        {"question": question, "planner_reason": reason, "data": json.loads(context)},
        ensure_ascii=False, default=str)
    generator = llm or OpenAIStructuredClient()
    try:
        raw = generator.generate_structured(
            schema=ConversationReply, instructions=CONVERSATION_INSTRUCTIONS,
            input_text=payload, max_output_tokens=700)
        reply = ConversationReply.model_validate(
            raw.model_dump() if isinstance(raw, BaseModel) else raw)
    except (LLMClientError, ValidationError, TypeError, ValueError):
        return None

    text = reply.reply.strip()
    # 사용자가 질문에 쓴 숫자(예: "3개")는 그대로 되풀이해도 된다.
    if not text or not _grounded(text, context + " " + question):
        return None
    suggestions = [q.strip() for q in reply.suggested_questions if q.strip()]
    return Insight(
        status="ok",
        summary=text,
        actions=[f"이렇게 물어볼 수 있어요: “{q}”" for q in suggestions],
        limitations=[reason] if reason else [],
    )
