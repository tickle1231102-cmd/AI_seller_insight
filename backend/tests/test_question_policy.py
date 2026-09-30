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
        assert inspect_question(case["question"], periods=case.get("periods")).reason
        return
    values = {k: v for k, v in expected.items() if k != "status"}
    result = create_analysis_plan(case["question"],
        periods=case.get("periods"),
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


class MustNotCall:
    def generate_structured(self, **kwargs):
        raise AssertionError("Rejected constraints must not reach the model")


@pytest.mark.parametrize("question", ["p123의 매출", "P001은 매출 얼마야?", "p123 매출"])
def test_product_id_with_korean_particle_cannot_become_total_revenue(question):
    result = create_analysis_plan(question, llm=MustNotCall())
    assert result.status == "unsupported_question" and result.plan is None
    assert "필터" in result.reason


def test_advertising_comparison_is_not_misread_as_ad_spend():
    question = "플랫폼별 광고 비교 ROAS"
    requirements = inspect_question(question)
    assert requirements.reason is None
    assert requirements.expected["metric"] == "roas"
    result = create_analysis_plan(question, llm=FakeStructuredLLM(
        PlannerDecision(status="ok", plan=AnalysisPlan(metric="roas", group_by="platform"))))
    assert result.status == "ok" and result.plan.metric == "roas"


@pytest.mark.parametrize("question", ["3개월 매출 추이", "3 개월 매출 추이"])
def test_duration_is_not_silently_replaced_with_top_n_or_all_months(question):
    requirements = inspect_question(question)
    assert requirements.reason and "기간 범위" in requirements.reason
    assert "limit" not in requirements.expected
    assert create_analysis_plan(question, llm=MustNotCall()).status == "unsupported_question"


def test_real_top_n_still_preserves_count():
    assert inspect_question("매출 높은 상품 3개").expected["limit"] == 3
    assert inspect_question("광고비 높은 플랫폼").expected["metric"] == "ad_spend"


@pytest.mark.parametrize("question, expected", [
    ("8월 매출", "2026-08"), ("이번 달 매출", "2026-09"),
    ("지난달 매출", "2026-08"), ("전월 매출", "2026-08"),
    ("2025-12 매출", "2025-12"), ("7월 매출", "2026-07"),
])
def test_month_resolution_preserves_requested_target(question, expected):
    r = inspect_question(question, periods=["2026-09", "2026-07", "2026-08"])
    assert r.reason is None and r.expected["period"] == expected


def test_gap_and_year_boundary_do_not_choose_previous_uploaded_month():
    assert inspect_question("지난달 매출", periods=["2026-07", "2026-09"]).expected["period"] == "2026-08"
    assert inspect_question("지난달 매출", periods=["2026-01"]).expected["period"] == "2025-12"
    assert inspect_question("8월 매출", periods=["2025-08", "2026-08"]).reason
    assert inspect_question("9월 매출", periods=[]).reason


@pytest.mark.parametrize("question, metric", [
    ("전월 대비 매출 증가율이 큰 플랫폼", "revenue_change"),
    ("방문수", "visits"), ("구매전환율", "conversion_rate"),
    ("환불률", "refund_rate"), ("할인율", "discount_rate"),
    ("객단가", "aov"), ("판매금액(총)", "gross_revenue"),
    ("전월 대비 ROAS", "roas_change_pp"),
    ("환불률 전월 대비", "refund_rate_change_pp"),
])
def test_new_metric_conditions_and_model_mismatch_are_checked(question, metric):
    r = inspect_question(question, periods=["2026-08", "2026-09"])
    assert r.reason is None and r.expected["metric"] == metric
    assert create_analysis_plan(question, periods=["2026-08", "2026-09"], llm=FakeStructuredLLM(
        PlannerDecision(status="ok", plan=AnalysisPlan(metric="orders")))).status == "unsupported_question"


def test_monthly_change_is_rejected_without_dropping_grouping():
    assert create_analysis_plan("월별 전월 대비 매출", llm=MustNotCall()).status == "unsupported_question"
