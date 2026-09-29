"""D regressions for C's PR #2 review; no external API calls."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import analyze as analyze_router
from backend.app.ai.client import LLMClientError
from backend.app.ai.insight import create_insight
from backend.app.ai.models import AnalysisPlan, Insight, InsightContent, PlannerResult


class FakeLLM:
    def __init__(self, result):
        self.result = result
        self.schema = None

    def generate_structured(self, **kwargs):
        self.schema = kwargs["schema"]
        return self.result


def content(**updates):
    return InsightContent(
        **{
            "summary": "ROAS 변화를 확인하세요.",
            "evidence": ["ROAS 291.7%"],
            "checks": ["플랫폼별 광고비를 확인하세요."],
            "actions": ["예산 조정 전 추가 데이터를 확인하세요."],
            "limitations": ["광고 소재의 영향은 확인할 수 없습니다."],
            **updates,
        }
    )


KPI = {"revenue": 12600000, "roas_change_pp": -14.2}
COMPARISON = {"by_platform": [{"platform": "coupang", "roas": 291.7}]}
PLAN = AnalysisPlan(metric="roas", group_by="platform", sort="asc", limit=1)
ANSWER = [{"platform": "coupang", "roas": 291.7}]


def run(llm, **kwargs):
    return create_insight(KPI, COMPARISON, [], llm=llm, **kwargs)


def test_generation_schema_contains_only_explanation_fields():
    llm = FakeLLM(content())
    assert run(llm).status == "ok"
    assert llm.schema is InsightContent
    assert set(InsightContent.model_json_schema()["properties"]) == {
        "summary", "evidence", "checks", "actions", "limitations"
    }


@pytest.mark.parametrize("status", ["ok", "skipped", "unsupported_question", "llm_error"])
def test_no_question_cannot_receive_fabricated_metadata(status):
    llm = FakeLLM(Insight(
        status=status,
        plan=AnalysisPlan(metric="revenue"),
        answer=[{"platform": "naver", "roas": 999.9}],
        reason="fabricated provider reason",
        **content().model_dump(),
    ))
    result = run(llm)
    assert result.status == "ok"
    assert result.plan is None
    assert result.answer == []
    assert result.reason is None


@pytest.mark.parametrize("answer", [None, [], ANSWER])
def test_caller_plan_and_answer_always_win(answer):
    llm = FakeLLM({
        **content().model_dump(),
        "status": "skipped",
        "plan": {"metric": "revenue"},
        "answer": [{"platform": "naver", "roas": 999.9}],
        "reason": "untrusted",
    })
    result = run(llm, plan=PLAN, answer=answer)
    assert result.status == "ok"
    assert result.plan == PLAN
    assert result.answer == (answer if answer is not None else [])
    assert result.reason is None


@pytest.mark.parametrize("field", ["summary", "checks", "actions", "limitations"])
@pytest.mark.parametrize("claim", ["ROAS 999.9%", "예산을 77% 줄이세요.", "ROAS 9.999e2%"])
def test_unsupported_numbers_in_all_other_display_fields_fail_closed(field, claim):
    generated = content(**{field: claim if field == "summary" else [claim]})
    result = run(FakeLLM(generated), plan=PLAN, answer=ANSWER)
    assert result.status == "llm_error"
    assert result.reason == "ungrounded_insight_number"
    assert result.plan == PLAN
    assert result.answer == ANSWER
    assert result.summary == ""
    assert result.evidence == result.checks == result.actions == result.limitations == []


def test_unsafe_evidence_is_removed_without_discarding_safe_explanation():
    result = run(FakeLLM(content(evidence=["ROAS 291.7%", "ROAS 999.9%", "목표 .5%"])))
    assert result.status == "ok"
    assert result.evidence == ["ROAS 291.7%"]


def test_input_numbers_commas_and_unicode_negative_are_preserved_in_all_fields():
    text = "매출 12,600,000원, ROAS 291.7%, 변화 −14.2%p"
    result = run(FakeLLM(content(
        summary=text, evidence=[text], checks=[text], actions=[text], limitations=[text]
    )))
    assert result.status == "ok"
    assert result.summary == text
    assert result.evidence == result.checks == result.actions == result.limitations == [text]


def test_numbers_available_only_in_caller_answer_are_valid():
    answer = [{"product_id": "P004", "orders": 42}]
    result = run(FakeLLM(content(summary="주문 42건", evidence=["주문 42건"])), answer=answer)
    assert result.status == "ok"
    assert result.answer == answer


def test_plan_limit_is_not_a_source_for_invented_numeric_claims():
    result = run(FakeLLM(content(summary="예산을 5% 줄이세요.")), plan=AnalysisPlan(metric="roas"))
    assert result.status == "llm_error"


@pytest.mark.parametrize("generated", [None, {}, {"summary": 77}, {**content().model_dump(), "actions": [77]}])
def test_invalid_output_is_normalized_without_raw_provider_details(generated):
    result = run(FakeLLM(generated), plan=PLAN, answer=ANSWER)
    assert result.status == "llm_error"
    assert result.reason == "invalid_structured_output"
    assert result.plan == PLAN and result.answer == ANSWER


def test_provider_failure_retains_deterministic_plan_and_answer():
    class FailingLLM:
        def generate_structured(self, **kwargs):
            raise LLMClientError("provider_error", "private provider diagnostic")

    result = run(FailingLLM(), plan=PLAN, answer=ANSWER)
    assert result.status == "llm_error"
    assert result.reason == "provider_error"
    assert result.plan == PLAN and result.answer == ANSWER
    assert "private" not in result.model_dump_json()


@pytest.mark.parametrize("with_question", [False, True])
def test_real_csv_pipeline_with_fake_llm_preserves_caller_data(monkeypatch, with_question):
    # Real B route and C CSV/KPI/run_plan code; only the external model is fake.
    llm = FakeLLM(Insight(
        status="skipped",
        plan=AnalysisPlan(metric="revenue"),
        answer=[{"platform": "naver", "roas": 999.9}],
        **content().model_dump(),
    ))
    monkeypatch.setattr(analyze_router, "_load_ai", lambda: SimpleNamespace(
        create_analysis_plan=lambda question: PlannerResult(status="ok", plan=PLAN),
        create_insight=partial(create_insight, llm=llm),
    ))
    fixtures = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
    files = [
        ("files", (path.name, path.read_bytes(), "text/csv"))
        for path in sorted(fixtures.glob("*.csv"))
    ]
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/analyze", files=files,
                               data={"question": "ROAS 제일 낮은 플랫폼?"} if with_question else {})
    assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["current"]["revenue"] == 12600000
    assert body["insight"]["status"] == "ok"
    assert body["insight"]["plan"] == (PLAN.model_dump() if with_question else None)
    assert body["insight"]["answer"] == (ANSWER if with_question else [])
    assert "999.9" not in response.text


def test_real_csv_pipeline_rejects_unsafe_text_but_keeps_kpis(monkeypatch):
    monkeypatch.setattr(analyze_router, "_load_ai", lambda: SimpleNamespace(
        create_insight=partial(create_insight, llm=FakeLLM(content(summary="ROAS 999.9%"))),
    ))
    fixtures = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
    files = [("files", (p.name, p.read_bytes(), "text/csv")) for p in sorted(fixtures.glob("*.csv"))]
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["current"]["revenue"] == 12600000
    assert len(body["rows"]) == 12
    assert body["insight"]["status"] == "llm_error"
    assert body["insight"]["summary"] == ""
    assert "999.9" not in response.text


@pytest.mark.parametrize("with_question", [False, True])
@pytest.mark.parametrize("summary, expected_status", [
    ("9월 매출은 12,600,000원입니다.", "ok"),
    ("2026-09 매출은 1,260만 원입니다.", "ok"),
    ("2026년 9월 ROAS가 14.2%p 하락했습니다.", "ok"),
    ("10월 매출은 12,600,000원입니다.", "llm_error"),
    ("9월 매출은 1,261만 원입니다.", "llm_error"),
])
def test_real_csv_route_accepts_grounded_formats_and_keeps_data_on_rejection(
    monkeypatch, with_question, summary, expected_status
):
    llm = FakeLLM(content(
        summary=summary, checks=["1. 광고비를 확인하세요."],
        actions=["2가지 확인 항목을 검토하세요."],
    ))
    monkeypatch.setattr(analyze_router, "_load_ai", lambda: SimpleNamespace(
        create_analysis_plan=lambda question: PlannerResult(status="ok", plan=PLAN),
        create_insight=partial(create_insight, llm=llm),
    ))
    fixtures = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
    files = [("files", (p.name, p.read_bytes(), "text/csv")) for p in sorted(fixtures.glob("*.csv"))]
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/analyze", files=files,
                               data={"question": "ROAS 제일 낮은 플랫폼?"} if with_question else {})
    assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["current"]["revenue"] == 12600000
    assert len(body["rows"]) == 12
    assert body["insight"]["status"] == expected_status
    assert body["insight"]["plan"] == (PLAN.model_dump() if with_question else None)
    assert body["insight"]["answer"] == (ANSWER if with_question else [])
    assert body["insight"]["summary"] == (summary if expected_status == "ok" else "")
