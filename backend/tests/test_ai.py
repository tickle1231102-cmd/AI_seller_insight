from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.ai.client import LLMClientError, OpenAIStructuredClient
from backend.app.ai.models import AnalysisPlan, PlannerDecision
from backend.app.ai.planner import create_analysis_plan


class FakeStructuredLLM:
    def __init__(self, decision: PlannerDecision | None = None, error: Exception | None = None):
        self.decision = decision
        self.error = error

    def generate_structured(self, **_kwargs):
        if self.error is not None:
            raise self.error
        assert self.decision is not None
        return self.decision


@pytest.mark.parametrize(
    ("question", "plan"),
    [
        ("광고 효율이 가장 안 좋은 플랫폼 어디야?", {"metric": "roas", "group_by": "platform", "sort": "asc"}),
        ("매출이 가장 높은 플랫폼 알려줘", {"metric": "revenue", "group_by": "platform", "sort": "desc"}),
        ("주문이 많은 상품 5개 보여줘", {"metric": "orders", "group_by": "product", "sort": "desc", "limit": 5}),
        ("판매량이 적은 상품은?", {"metric": "units", "group_by": "product", "sort": "asc"}),
        ("2026-09 광고비가 높은 플랫폼", {"metric": "ad_spend", "group_by": "platform", "sort": "desc", "period": "2026-09"}),
        ("광고매출이 높은 플랫폼", {"metric": "ad_revenue", "group_by": "platform", "sort": "desc"}),
        ("월별 매출 추이 보여줘", {"metric": "revenue", "group_by": "period"}),
        ("ROAS 높은 플랫폼 3개", {"metric": "roas", "group_by": "platform", "sort": "desc", "limit": 3}),
        ("2026-08 매출 보여줘", {"metric": "revenue", "period": "2026-08"}),
        ("주문 수가 낮은 플랫폼", {"metric": "orders", "group_by": "platform", "sort": "asc"}),
    ],
)
def test_planner_contract_cases(question, plan):
    decision = PlannerDecision(status="ok", plan=AnalysisPlan(**plan))
    result = create_analysis_plan(question, llm=FakeStructuredLLM(decision=decision))

    assert result.status == "ok"
    assert result.plan is not None
    for key, expected in plan.items():
        assert getattr(result.plan, key) == expected


def test_unrelated_question_is_unsupported():
    decision = PlannerDecision(
        status="unsupported_question",
        reason="판매/광고 분석 범위를 벗어난 질문입니다.",
    )
    result = create_analysis_plan("오늘 서울 날씨 알려줘", llm=FakeStructuredLLM(decision=decision))

    assert result.status == "unsupported_question"
    assert result.plan is None


def test_llm_error_is_normalized():
    result = create_analysis_plan(
        "ROAS가 낮은 플랫폼?",
        llm=FakeStructuredLLM(error=LLMClientError("provider_error", "boom")),
    )

    assert result.status == "llm_error"
    assert result.plan is None
    assert result.reason == "provider_error"


def test_blank_question_is_unsupported_without_llm_call():
    result = create_analysis_plan("   ")

    assert result.status == "unsupported_question"
    assert result.plan is None


def test_too_long_question_is_unsupported_without_llm_call():
    result = create_analysis_plan("가" * 301)

    assert result.status == "unsupported_question"
    assert result.plan is None


def test_analysis_plan_rejects_invalid_metric():
    with pytest.raises(ValidationError):
        AnalysisPlan(metric="ctr")


def test_analysis_plan_rejects_invalid_period():
    with pytest.raises(ValidationError):
        AnalysisPlan(metric="revenue", period="2026-13")


class _FakeResponse:
    def __init__(self, output_parsed):
        self.output_parsed = output_parsed


class _RetryingResponses:
    def __init__(self):
        self.calls = 0

    def parse(self, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return _FakeResponse(None)
        return _FakeResponse(
            PlannerDecision(
                status="ok",
                plan=AnalysisPlan(metric="roas", group_by="platform", sort="asc"),
            )
        )


class _FakeOpenAIClient:
    def __init__(self, responses):
        self.responses = responses


def test_structured_client_retries_invalid_output_once():
    responses = _RetryingResponses()
    client = OpenAIStructuredClient(
        client=_FakeOpenAIClient(responses),
        model="test-model",
    )

    result = client.generate_structured(
        schema=PlannerDecision,
        instructions="test",
        input_text="test",
    )

    assert result.status == "ok"
    assert responses.calls == 2


class _FailingResponses:
    def parse(self, **_kwargs):
        raise TimeoutError("network timeout")


def test_structured_client_normalizes_provider_failure():
    client = OpenAIStructuredClient(
        client=_FakeOpenAIClient(_FailingResponses()),
        model="test-model",
    )

    with pytest.raises(LLMClientError) as exc_info:
        client.generate_structured(
            schema=PlannerDecision,
            instructions="test",
            input_text="test",
        )

    assert exc_info.value.code == "provider_error"


def test_missing_api_key_is_normalized(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    client = OpenAIStructuredClient(api_key=None, model="test-model")

    with pytest.raises(LLMClientError) as exc_info:
        client.generate_structured(
            schema=PlannerDecision,
            instructions="test",
            input_text="test",
        )

    assert exc_info.value.code == "missing_api_key"


class RecordingLLM(FakeStructuredLLM):
    def generate_structured(self, **kwargs):
        self.kwargs = kwargs
        return super().generate_structured(**kwargs)


def test_planner_input_includes_uploaded_periods():
    llm = RecordingLLM(decision=PlannerDecision(status="ok", plan=AnalysisPlan(metric="units", period="2026-08")))
    create_analysis_plan("8월에 제일 안 팔린 상품", periods=["2026-08", "2026-09"], llm=llm)
    assert "Uploaded periods (oldest first): 2026-08, 2026-09" in llm.kwargs["input_text"]
    assert llm.kwargs["input_text"].endswith("Question: 8월에 제일 안 팔린 상품")


def test_planner_input_is_plain_question_without_periods():
    llm = RecordingLLM(decision=PlannerDecision(status="ok", plan=AnalysisPlan(metric="revenue")))
    create_analysis_plan("매출 알려줘", llm=llm)
    assert llm.kwargs["input_text"] == "매출 알려줘"
