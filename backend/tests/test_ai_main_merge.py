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
from backend.app.ai.models import AnalysisPlan, PlannerResult


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
    # PR #17 keeps overlapping SmartStore sales out of the ad-report/AI
    # scope. The store panel and raw rows still include the uploaded sheets.
    core = df[df["platform"] != normalize.STORE_PLATFORM]
    assert set(core["platform"]) == {"coupang"}
    expected_kpis = kpi.compute_kpis(core)
    expected_store = kpi.compute_store_kpis(df)
    expected_comparison = compare.build_comparison(core)
    expected_signals = signals.detect_signals(expected_kpis, expected_comparison)
    plan = AnalysisPlan(metric="revenue", group_by="platform", sort="desc")
    answer = compare.run_plan(core, plan) if with_question else []
    from backend.tests.test_insight import selection

    class FakeLLM:
        def generate_structured(self, **kwargs):
            # A provider attempting metadata injection must not corrupt either
            # the new store response or the original upstream plan/answer.
            return {**selection(summary_fact_ids=["fabricated"] if unsafe else ["kpis.current.revenue"]),
                    "status": "skipped", "plan": {"metric": "roas"},
                    "answer": [{"revenue": 999999999999999}], "reason": "injected"}

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
    if unsafe:
        assert insight["summary"] == ""
    else:
        assert "매출:" in insight["summary"]
    assert "999999999999999" not in response.text
    # reason is internal to D's model, not part of B's public Insight schema.
    assert "reason" not in insight
    assert "injected" not in response.text
