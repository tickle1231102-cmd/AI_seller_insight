"""POST /api/analyze — C·D 모듈은 가짜로 대체해 B 의 연결·실패 처리만 검증한다 (WU-BE-04)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analysis import compare, kpi, normalize, signals
from app.main import app
from app.routers import analyze as analyze_router

client = TestClient(app, raise_server_exceptions=False)
CONTRACT = json.loads(
    (Path(__file__).resolve().parents[2] / "shared" / "contracts" / "analyze_response.json").read_text(encoding="utf-8")
)
FILES = [("files", ("coupang_2026-09.csv", b"a,b\n1,2\n", "text/csv"))]
PLAN = {"metric": "roas", "group_by": "platform", "sort": "asc", "limit": 1, "period": None}


class FakeAI:
    """D 의 app.ai 대역. planner 결과와 insight 동작을 테스트마다 바꾼다."""

    def __init__(self, plan_status="ok", insight_error: Exception | None = None):
        self.plan_status = plan_status
        self.insight_error = insight_error
        self.insight_calls = []

    def create_analysis_plan(self, question):
        if self.plan_status == "ok":
            return SimpleNamespace(status="ok", plan=PLAN, reason=None)
        return SimpleNamespace(status=self.plan_status, plan=None, reason="지원하지 않는 분석 질문입니다.")

    def create_insight(self, kpis, comparison, signals, *, plan=None, answer=None):
        self.insight_calls.append({"plan": plan, "answer": answer})
        if self.insight_error:
            raise self.insight_error
        return {**CONTRACT["insight"], "plan": None, "answer": None}


@pytest.fixture
def fake_analysis(monkeypatch):
    monkeypatch.setattr(normalize, "normalize_files", lambda files: pd.DataFrame(CONTRACT["rows"]))
    monkeypatch.setattr(kpi, "compute_kpis", lambda df: CONTRACT["kpis"])
    monkeypatch.setattr(compare, "build_comparison", lambda df: CONTRACT["comparison"])
    monkeypatch.setattr(compare, "run_plan", lambda df, plan: [{"platform": "coupang", "roas": 291.7}])
    monkeypatch.setattr(signals, "detect_signals", lambda kpis, comparison: CONTRACT["signals"])


def use_ai(monkeypatch, ai):
    monkeypatch.setattr(analyze_router, "_load_ai", lambda: ai)
    return ai


def assert_analysis_ok(body):
    assert body["kpis"] == CONTRACT["kpis"]
    assert body["comparison"] == CONTRACT["comparison"]
    assert body["signals"] == CONTRACT["signals"]
    assert body["rows"] == CONTRACT["rows"]


# ---- 요청 검증 ----
def test_question_too_long():
    res = client.post("/api/analyze", files=FILES, data={"question": "가" * 301})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "QUESTION_TOO_LONG"


def test_no_files():
    res = client.post("/api/analyze")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "NO_FILES"


# ---- 정상 흐름 ----
def test_without_question(fake_analysis, monkeypatch):
    ai = use_ai(monkeypatch, FakeAI())
    res = client.post("/api/analyze", files=FILES)
    assert res.status_code == 200
    body = res.json()
    assert_analysis_ok(body)
    assert body["insight"]["status"] == "ok"
    assert body["insight"]["plan"] is None
    assert ai.insight_calls[0]["plan"] is None


def test_with_question_runs_plan(fake_analysis, monkeypatch):
    ai = use_ai(monkeypatch, FakeAI())
    res = client.post("/api/analyze", files=FILES, data={"question": "광고 효율이 가장 안 좋은 플랫폼 어디야?"})
    assert res.status_code == 200
    insight = res.json()["insight"]
    assert insight["status"] == "ok"
    assert insight["plan"] == PLAN
    assert insight["answer"] == [{"platform": "coupang", "roas": 291.7}]
    assert ai.insight_calls[0]["answer"] == [{"platform": "coupang", "roas": 291.7}]


def test_unsupported_question(fake_analysis, monkeypatch):
    ai = use_ai(monkeypatch, FakeAI(plan_status="unsupported_question"))
    res = client.post("/api/analyze", files=FILES, data={"question": "오늘 날씨 어때?"})
    body = res.json()
    assert res.status_code == 200
    assert_analysis_ok(body)
    assert body["insight"]["status"] == "unsupported_question"
    assert ai.insight_calls == []


# ---- LLM 실패해도 KPI 는 정상 (F-AI-06) ----
def test_planner_llm_error_keeps_kpis(fake_analysis, monkeypatch):
    use_ai(monkeypatch, FakeAI(plan_status="llm_error"))
    res = client.post("/api/analyze", files=FILES, data={"question": "매출 제일 높은 플랫폼?"})
    assert res.status_code == 200
    assert_analysis_ok(res.json())
    assert res.json()["insight"]["status"] == "llm_error"


def test_insight_exception_keeps_kpis(fake_analysis, monkeypatch):
    use_ai(monkeypatch, FakeAI(insight_error=TimeoutError("secret provider detail")))
    res = client.post("/api/analyze", files=FILES)
    assert res.status_code == 200
    assert_analysis_ok(res.json())
    assert res.json()["insight"]["status"] == "llm_error"
    assert "secret" not in res.text


def test_ai_module_missing_keeps_kpis(fake_analysis, monkeypatch):
    def missing():
        raise ModuleNotFoundError("app.ai")

    monkeypatch.setattr(analyze_router, "_load_ai", missing)
    res = client.post("/api/analyze", files=FILES)
    assert res.status_code == 200
    assert_analysis_ok(res.json())
    assert res.json()["insight"]["status"] == "llm_error"


# ---- C 오류는 그대로 전달 ----
def test_normalize_error_passes_through(monkeypatch):
    from app.core.errors import AppError

    def raise_empty(files):
        raise AppError("EMPTY_FILE", "데이터가 없는 파일입니다.", 422, {"file": files[0][0]})

    monkeypatch.setattr(normalize, "normalize_files", raise_empty)
    res = client.post("/api/analyze", files=FILES)
    assert res.status_code == 422
    assert res.json()["error"] == {
        "code": "EMPTY_FILE",
        "message": "데이터가 없는 파일입니다.",
        "details": {"file": "coupang_2026-09.csv"},
    }


# ---- run_plan 오류 구분 (PR #5 리뷰 반영) ----
def test_run_plan_app_error_becomes_unsupported(fake_analysis, monkeypatch):
    from app.core.errors import AppError

    def no_period(df, plan):
        raise AppError("PERIOD_NOT_FOUND", "2026-07 데이터가 없습니다.", 422)

    monkeypatch.setattr(compare, "run_plan", no_period)
    ai = use_ai(monkeypatch, FakeAI())
    res = client.post("/api/analyze", files=FILES, data={"question": "7월 매출 알려줘"})
    assert res.status_code == 200
    assert_analysis_ok(res.json())
    insight = res.json()["insight"]
    assert insight["status"] == "unsupported_question"
    assert insight["summary"] == "2026-07 데이터가 없습니다."
    assert ai.insight_calls == []


def test_run_plan_bug_logged_separately(fake_analysis, monkeypatch, caplog):
    def bug(df, plan):
        raise KeyError("roas")

    monkeypatch.setattr(compare, "run_plan", bug)
    use_ai(monkeypatch, FakeAI())
    res = client.post("/api/analyze", files=FILES, data={"question": "ROAS 제일 낮은 플랫폼?"})
    assert res.status_code == 200
    assert_analysis_ok(res.json())
    assert res.json()["insight"]["status"] == "llm_error"
    assert "run_plan failed" in caplog.text
