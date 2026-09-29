"""Optional real-OpenAI planner quality test.

Run explicitly after setting an API key:
    RUN_LLM_INTEGRATION=1 OPENAI_API_KEY=... LLM_MODEL=... pytest backend/tests/test_ai_live.py -q

This test intentionally does not run in the normal unit-test suite because it
uses a paid external API.
"""

from __future__ import annotations

import os

import pytest

from backend.app.ai.planner import create_analysis_plan


CASES = [
    ("광고 효율이 가장 안 좋은 플랫폼 어디야?", {"status": "ok", "metric": "roas", "group_by": "platform", "sort": "asc"}),
    ("매출이 가장 높은 플랫폼 알려줘", {"status": "ok", "metric": "revenue", "group_by": "platform", "sort": "desc"}),
    ("주문이 많은 상품 5개 보여줘", {"status": "ok", "metric": "orders", "group_by": "product", "sort": "desc", "limit": 5}),
    ("판매량이 적은 상품은?", {"status": "ok", "metric": "units", "group_by": "product", "sort": "asc"}),
    ("2026-09 광고비가 높은 플랫폼", {"status": "ok", "metric": "ad_spend", "group_by": "platform", "sort": "desc", "period": "2026-09"}),
    ("광고매출이 높은 플랫폼", {"status": "ok", "metric": "ad_revenue", "group_by": "platform", "sort": "desc"}),
    ("월별 매출 추이 보여줘", {"status": "ok", "metric": "revenue", "group_by": "period"}),
    ("ROAS 높은 플랫폼 3개", {"status": "ok", "metric": "roas", "group_by": "platform", "sort": "desc", "limit": 3}),
    ("2026-08 매출 보여줘", {"status": "ok", "metric": "revenue", "period": "2026-08"}),
    ("오늘 서울 날씨 알려줘", {"status": "unsupported_question"}),
]


def _matches(result, expected: dict) -> bool:
    if result.status != expected["status"]:
        return False
    if result.status != "ok":
        return True
    if result.plan is None:
        return False

    for field in ("metric", "group_by", "sort", "limit", "period"):
        if field in expected and getattr(result.plan, field) != expected[field]:
            return False
    return True


@pytest.mark.integration
def test_real_openai_planner_accuracy_at_least_90_percent():
    if os.getenv("RUN_LLM_INTEGRATION") != "1":
        pytest.skip("Set RUN_LLM_INTEGRATION=1 to run paid OpenAI integration tests.")
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")):
        pytest.skip("OPENAI_API_KEY or LLM_API_KEY is required.")

    correct = 0
    failures: list[str] = []

    for question, expected in CASES:
        result = create_analysis_plan(question)
        if _matches(result, expected):
            correct += 1
        else:
            failures.append(
                f"{question!r}: expected={expected}, actual={result.model_dump()}"
            )

    accuracy = correct / len(CASES)
    assert accuracy >= 0.9, "\n".join(failures)
