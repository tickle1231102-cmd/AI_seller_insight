from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from backend.app.ai.client import LLMClientError
from backend.app.ai.insight import create_insight
from backend.app.ai.models import AnalysisPlan, Insight, InsightDraft
from backend.app.ai.prompts import INSIGHT_INSTRUCTIONS


class FakeInsightLLM:
    def __init__(self, result: Any = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.kwargs: dict[str, Any] | None = None

    def generate_structured(self, **kwargs: Any) -> BaseModel:
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _inputs() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    return (
        {"revenue": 12600000, "ad_spend_change": 28.0, "roas_change_pp": -14.2},
        {"by_platform": [{"platform": "coupang", "roas": 291.7}]},
        [
            {
                "signal": "ROAS_DOWN_WITH_SPEND_GROWTH",
                "ad_spend_change": 28.0,
                "ad_revenue_change": 22.4,
                "roas_change_pp": -14.2,
            }
        ],
    )


def test_insight_contract_and_evidence_postprocessing():
    kpis, comparison, signals = _inputs()
    plan = AnalysisPlan(metric="roas", group_by="platform", sort="asc")
    answer = [{"platform": "coupang", "roas": 291.7}]
    llm = FakeInsightLLM(
        result=Insight(
            status="ok",
            summary="광고비 증가율이 광고매출 증가율보다 높아 ROAS가 하락했습니다.",
            evidence=["광고비 +28.0%", "광고매출 +22.4%", "ROAS -14.2%p", "잘못된 수치 99.0%"],
            checks=["플랫폼별 ROAS 하락폭 확인"],
            actions=["저효율 플랫폼의 광고비를 우선 점검"],
            limitations=["광고 소재와 CTR 영향은 현재 데이터만으로 확인할 수 없습니다."],
        )
    )

    result = create_insight(kpis, comparison, signals, plan=plan, answer=answer, llm=llm)

    assert result.status == "ok"
    assert result.plan == plan
    assert result.answer == answer
    assert result.evidence == ["광고비 +28.0%", "광고매출 +22.4%", "ROAS -14.2%p"]
    assert llm.kwargs is not None
    assert llm.kwargs["schema"] is InsightDraft
    assert '"ad_spend_change": 28.0' in llm.kwargs["input_text"]


def test_insight_provider_failure_is_normalized():
    kpis, comparison, signals = _inputs()
    result = create_insight(
        kpis,
        comparison,
        signals,
        llm=FakeInsightLLM(error=LLMClientError("provider_error", "boom")),
    )

    assert result.status == "llm_error"
    assert result.reason == "provider_error"
    assert result.evidence == []


def test_insight_prompt_contains_safety_rules():
    assert "숫자 변경 금지" in INSIGHT_INSTRUCTIONS
    assert "데이터에 없는 원인 단정 금지" in INSIGHT_INSTRUCTIONS
    assert "원인은 확정하지 말고" in INSIGHT_INSTRUCTIONS
