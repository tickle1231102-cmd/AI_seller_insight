from __future__ import annotations
import json
from copy import deepcopy
from typing import Any
from backend.app.ai.client import LLMClientError
from backend.app.ai.insight import create_insight
from backend.app.ai.models import AnalysisPlan, InsightSelection
from backend.app.ai.prompts import INSIGHT_INSTRUCTIONS


class FakeInsightLLM:
    def __init__(self, result: Any = None, error: Exception | None = None):
        self.result, self.error, self.kwargs = result, error, None
    def generate_structured(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


KPI = {
    "period": "2026-09", "previous_period": "2026-08",
    "current": {"revenue": 12600000, "roas": 312.5, "ad_spend": 1920000},
    "previous": {"revenue": 10400000, "roas": 326.7},
    "change": {"revenue_change": 21.2, "ad_spend_change": 28.0,
               "ad_revenue_change": 22.4, "roas_change_pp": -14.2},
}
COMPARISON = {"by_platform": [
    {"platform": "coupang", "revenue": 8000000, "roas": 291.7},
    {"platform": "naver", "revenue": 4600000, "roas": 347.2},
]}
SIGNALS = [{"signal": "ROAS_DOWN_WITH_SPEND_GROWTH", "platform": "all"}]


def selection(**changes):
    return {"summary_fact_ids": ["kpis.current.revenue"],
            "evidence_fact_ids": ["kpis.current.revenue"],
            "check_ids": ["check_source"], "action_ids": ["verify_before_change"], **changes}


def test_insight_contract_and_evidence_postprocessing():
    kpis = deepcopy(KPI)
    llm = FakeInsightLLM(selection(evidence_fact_ids=["kpis.change.roas_change_pp", "unknown"]))
    result = create_insight(kpis, COMPARISON, SIGNALS, llm=llm)
    assert result.status == "ok"
    assert result.summary == "2026-09 / 전체 / 매출: 12,600,000원."
    assert result.evidence == [result.summary, "2026-08 → 2026-09 / 전체 / ROAS 증감: -14.2%p."]
    assert llm.kwargs["schema"] is InsightSelection
    payload = json.loads(llm.kwargs["input_text"])
    assert any(f["id"] == "kpis.current.revenue" and f["value"] == "12600000" for f in payload["facts"])
    assert kpis == KPI


def test_insight_provider_failure_is_normalized():
    result = create_insight(KPI, COMPARISON, SIGNALS,
                           llm=FakeInsightLLM(error=LLMClientError("provider_error", "private")))
    assert result.status == "llm_error" and result.reason == "provider_error"
    assert result.evidence == [] and "private" not in result.model_dump_json()


def test_insight_prompt_contains_safety_rules():
    for text in ("숫자 변경 금지", "데이터에 없는 원인 단정 금지", "원인은 확정하지 말고"):
        assert text in INSIGHT_INSTRUCTIONS
