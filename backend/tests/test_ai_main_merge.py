"""D checks that merging main preserves timeout and SmartStore API behavior."""

from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.analysis import compare, kpi, normalize, signals
from app.main import app
from app.routers import analyze as analyze_router
from backend.app.ai.client import OpenAIStructuredClient
from backend.app.ai.insight import create_insight
from backend.app.ai.models import AnalysisPlan, Insight, PlannerResult


@pytest.mark.parametrize("env_timeout, explicit_timeout, expected", [
    (None, None, 30),
    ("", None, 30),
    ("45", None, 45),
    ("0.5", None, 0.5),
    ("45", 8, 8),
])
def test_main_timeout_configuration_is_preserved(monkeypatch, env_timeout, explicit_timeout, expected):
    if env_timeout is None:
        monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    else:
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", env_timeout)
    # No key, SDK construction, or external request is needed for config checks.
    client = OpenAIStructuredClient(client=object(), timeout_seconds=explicit_timeout)
    assert client.timeout_seconds == expected


@pytest.mark.parametrize("with_question", [False, True])
@pytest.mark.parametrize("unsafe", [False, True])
def test_mixed_smartstore_upload_preserves_store_and_caller_results(monkeypatch, with_question, unsafe):
    fixtures = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
    paths = [*sorted((fixtures / "smartstore").glob("sales_*_sample.xlsx")),
             fixtures / "coupang_2026-09.csv"]
    uploads = [(p.name, p.read_bytes()) for p in paths]
    df = normalize.normalize_files(uploads)
    expected_kpis = kpi.compute_kpis(df)
    expected_store = kpi.compute_store_kpis(df)
    expected_comparison = compare.build_comparison(df)
    expected_signals = signals.detect_signals(expected_kpis, expected_comparison)
    plan = AnalysisPlan(metric="revenue", group_by="platform", sort="desc")
    answer = compare.run_plan(df, plan) if with_question else []
    summary = ("매출 999999999999999원입니다." if unsafe
               else f"9월 매출은 {expected_kpis['current']['revenue']:,}원입니다.")

    class FakeLLM:
        def generate_structured(self, **kwargs):
            # A provider attempting metadata injection must not corrupt either
            # the new store response or the original upstream plan/answer.
            return Insight(status="skipped", plan=AnalysisPlan(metric="roas"),
                           answer=[{"revenue": 999999999999999}], reason="injected",
                           summary=summary)

    monkeypatch.setattr(analyze_router, "_load_ai", lambda: SimpleNamespace(
        create_analysis_plan=lambda question: PlannerResult(status="ok", plan=plan),
        create_insight=partial(create_insight, llm=FakeLLM()),
    ))
    files = [("files", (name, data, "application/octet-stream")) for name, data in uploads]
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/analyze", files=files,
                               data={"question": "매출이 가장 높은 플랫폼?"} if with_question else {})
    assert response.status_code == 200
    body = response.json()
    assert body["kpis"] == expected_kpis
    assert body["store"] == expected_store
    assert body["comparison"] == expected_comparison
    assert body["signals"] == expected_signals
    assert len(body["rows"]) == len(df)
    insight = body["insight"]
    assert insight["plan"] == (plan.model_dump() if with_question else None)
    assert insight["answer"] == answer
    assert insight["status"] == ("llm_error" if unsafe else "ok")
    assert insight["summary"] == ("" if unsafe else summary)
    assert "999999999999999" not in response.text
    # reason is internal to D's model, not part of B's public Insight schema.
    assert "reason" not in insight
    assert "injected" not in response.text
