"""D integration regressions for main's #23 calculation contract."""
from copy import deepcopy
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import get_args

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.analysis import compare, kpi, normalize, signals
from app.routers import analyze as analyze_router
from backend.app.ai.facts import EvidenceCatalogue, METRICS
from backend.app.ai.insight import create_insight
from backend.app.ai.models import AnalysisPlan, Metric, PlannerDecision
from backend.app.ai.planner import create_analysis_plan
from backend.tests.test_ai import FakeStructuredLLM
from backend.tests.test_insight import FakeInsightLLM, selection

FIXTURES = Path(__file__).resolve().parents[2] / "shared" / "fixtures"


def uploads():
    paths = [*sorted(FIXTURES.glob("*.csv")),
             *sorted((FIXTURES / "smartstore").glob("sales_*_sample.xlsx"))]
    return [(p.name, p.read_bytes()) for p in paths]


@pytest.mark.parametrize("metric", get_args(Metric))
def test_all_public_metrics_have_exact_c_answer_evidence(metric):
    df = normalize.normalize_files(uploads())
    core = df[df["platform"] != normalize.STORE_PLATFORM]
    data = (kpi.compute_kpis(core), compare.build_comparison(core), [])
    plan = AnalysisPlan(metric=metric, period="2026-09")
    answer = compare.run_plan(df, plan)
    original = deepcopy(answer)
    catalogue = EvidenceCatalogue.build(*data, plan, answer)
    assert not catalogue.conflicts and catalogue.answer_ids == [f"answer.0.{metric}"]
    result = create_insight(*data, plan=plan, answer=answer, llm=FakeInsightLLM(selection(summary_fact_ids=[])))
    assert result.status == "ok" and result.plan == plan and result.answer == original == answer
    primary = catalogue.facts[f"answer.0.{metric}"]
    assert result.summary == primary.text and primary.value == str(answer[0][metric])
    if metric.endswith(("_change", "_change_pp")):
        assert primary.period == "2026-08 → 2026-09"
        assert primary.unit == ("%p" if metric.endswith("_change_pp") else "%")
        base = compare.CHANGE_METRICS[metric]
        assert catalogue.facts[f"answer.0.previous.{base}"].value == str(answer[0][base + "_previous"])


def test_evidence_labels_cover_every_contract_metric():
    assert {m.removesuffix("_change_pp").removesuffix("_change") for m in get_args(Metric)} == set(METRICS)


@pytest.mark.parametrize("metric", ["visits", "visits_change", "refund_rate_change_pp"])
def test_implicit_store_month_is_not_labeled_with_core_kpi_month(metric):
    df = normalize.normalize_files(uploads())
    df.loc[df["platform"] == normalize.STORE_PLATFORM, "period"] = df.loc[
        df["platform"] == normalize.STORE_PLATFORM, "period"].replace({"2026-08": "2026-10", "2026-09": "2026-11"})
    core = df[df["platform"] != normalize.STORE_PLATFORM]
    plan = AnalysisPlan(metric=metric)
    answer = compare.run_plan(df, plan)
    catalogue = EvidenceCatalogue.build(kpi.compute_kpis(core), compare.build_comparison(core), [], plan, answer)
    fact = catalogue.facts[f"answer.0.{metric}"]
    assert "2026-09" not in fact.text and "2026-11" not in fact.text
    assert "스마트스토어 최신 업로드 월" in fact.text and not catalogue.conflicts
    assert any("기준 월" in s for s in catalogue.limitations)


@pytest.mark.parametrize("metric", ["revenue_change", "roas_change_pp", "visits", "conversion_rate", "refund_rate", "discount_rate", "aov"])
def test_real_route_preserves_data_with_actual_planner_and_grounded_insight(monkeypatch, metric):
    plan = AnalysisPlan(metric=metric, period="2026-09")
    questions = {"revenue_change":"2026-09 매출 전월 대비", "roas_change_pp":"2026-09 ROAS 전월 대비",
                 "visits":"2026-09 방문수", "conversion_rate":"2026-09 구매전환율",
                 "refund_rate":"2026-09 환불률", "discount_rate":"2026-09 할인율", "aov":"2026-09 객단가"}
    monkeypatch.setattr(analyze_router, "_load_ai", lambda: SimpleNamespace(
        create_analysis_plan=partial(create_analysis_plan, llm=FakeStructuredLLM(PlannerDecision(status="ok", plan=plan))),
        create_insight=partial(create_insight, llm=FakeInsightLLM(selection(summary_fact_ids=[])))))
    source = uploads()
    df = normalize.normalize_files(source)
    core = df[df["platform"] != normalize.STORE_PLATFORM]
    with TestClient(app) as client:
        response = client.post("/api/analyze", files=[("files", (n, b, "application/octet-stream")) for n,b in source],
                               data={"question": questions[metric]})
    body = response.json()
    assert response.status_code == 200 and body["insight"]["status"] == "ok"
    assert body["insight"]["plan"] == plan.model_dump()
    assert body["insight"]["answer"] == compare.run_plan(df, plan)
    assert body["kpis"] == kpi.compute_kpis(core) and body["store"] == kpi.compute_store_kpis(df)
    assert body["comparison"] == compare.build_comparison(core)
    assert body["signals"] == signals.detect_signals(body["kpis"], body["comparison"])
    assert len(body["rows"]) == len(df) and "reason" not in body["insight"]


def test_missing_store_data_remains_explicit_and_preserves_core_kpis(monkeypatch):
    plan = AnalysisPlan(metric="visits")
    monkeypatch.setattr(analyze_router, "_load_ai", lambda: SimpleNamespace(
        create_analysis_plan=partial(create_analysis_plan, llm=FakeStructuredLLM(PlannerDecision(status="ok", plan=plan))),
        create_insight=lambda *a, **k: pytest.fail("Unavailable results must not reach the model")))
    p = FIXTURES / "coupang_2026-09.csv"
    with TestClient(app) as client:
        body = client.post("/api/analyze", files=[("files", (p.name,p.read_bytes(),"text/csv"))],
                           data={"question":"방문수"}).json()
    assert body["insight"]["status"] == "unsupported_question"
    assert "SALES" in body["insight"]["summary"] and body["kpis"]["current"]["revenue"] == 8000000
