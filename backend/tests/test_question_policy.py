import json
from pathlib import Path
import pytest
from backend.app.ai.models import AnalysisPlan, PlannerDecision
from backend.app.ai.planner import create_analysis_plan
from backend.app.ai.question_policy import inspect_question
from backend.tests.test_ai import FakeStructuredLLM

CASES = json.loads(Path(__file__).with_name("ai_quality_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_question_requirements_accept_supported_and_reject_unrepresentable(case):
    expected = case["expected"]
    if expected["status"] != "ok":
        assert inspect_question(case["question"]).reason
        return
    values = {k: v for k, v in expected.items() if k != "status"}
    result = create_analysis_plan(case["question"],
        llm=FakeStructuredLLM(PlannerDecision(status="ok", plan=AnalysisPlan(**values))))
    assert result.status == "ok"
    for key, value in values.items():
        assert getattr(result.plan, key) == value


@pytest.mark.parametrize("question, plan", [
    ("2026-09 매출", {"metric": "revenue", "period": None}),
    ("매출", {"metric": "revenue", "period": "2026-09"}),
    ("매출 높은 상품 3개", {"metric": "revenue", "group_by": "product", "sort": "desc", "limit": 5}),
    ("주문이 낮은 플랫폼", {"metric": "orders", "group_by": "platform", "sort": "desc"}),
    ("광고비가 높은 플랫폼", {"metric": "revenue", "group_by": "platform", "sort": "desc"}),
    ("상품별 매출", {"metric": "revenue", "group_by": "platform"}),
])
def test_model_cannot_silently_change_explicit_conditions(question, plan):
    result = create_analysis_plan(question,
        llm=FakeStructuredLLM(PlannerDecision(status="ok", plan=AnalysisPlan(**plan))))
    assert result.status == "unsupported_question" and result.plan is None
    assert "일치하지 않아" in result.reason


def test_model_audit_can_reject_conditions_lexical_checks_do_not_recognize():
    result = create_analysis_plan("운동화 매출",
        llm=FakeStructuredLLM(PlannerDecision(status="ok", plan=AnalysisPlan(metric="revenue"),
                                             unrepresented_constraints=["특정 상품명 필터"])))
    assert result.status == "unsupported_question" and result.plan is None


def test_invalid_injected_provider_is_normalized():
    result = create_analysis_plan("매출", llm=FakeStructuredLLM(decision={"plan": "invalid"}))
    assert result.status == "llm_error" and result.reason == "invalid_structured_output"
