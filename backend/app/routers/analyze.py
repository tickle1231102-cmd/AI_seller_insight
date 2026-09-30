"""POST /api/analyze — TECH_SPEC 1장 처리 흐름 1~9단계.

C(analysis)·D(ai) 모듈을 순서대로 호출해 응답을 조립한다.
AI 단계(7·8)가 어떤 이유로 실패해도 1~6단계 결과(kpis, comparison, rows, signals)는 정상 반환한다.
"""

import importlib
import logging
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.analysis import compare, kpi, normalize, signals
from app.core.errors import AppError
from app.core.uploads import UploadedFile, read_uploads
from app.schemas import AnalyzeResponse, ErrorResponse, Insight

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

MAX_QUESTION_LENGTH = 300


def _load_ai():
    """D 의 ai 패키지. 아직 없거나 import 에 실패하면 예외 → llm_error 로 처리된다."""
    return importlib.import_module("app.ai")


def _dump(value: Any) -> Any:
    return value.model_dump() if hasattr(value, "model_dump") else value


def _run_ai(df, kpis: dict, comparison: dict, sigs: list[dict], question: str | None) -> Insight:
    """TECH_SPEC 1장 7·8단계. 예외를 밖으로 내보내지 않는다."""
    try:
        ai = _load_ai()
        plan, answer = None, None

        if question:
            periods = sorted(df["period"].unique())
            plan_result = ai.create_analysis_plan(question, periods=periods)  # D
            if plan_result.status == "unsupported_question":
                return Insight(status="unsupported_question", summary=plan_result.reason or "")
            if plan_result.status != "ok":
                logger.warning("planner failed: %s", plan_result.reason)
                return Insight(status="llm_error")
            plan = plan_result.plan
            try:
                answer = compare.run_plan(df, plan)  # C
            except AppError as exc:
                # 계획은 맞지만 데이터로 답할 수 없는 경우 (예: 없는 월). KPI 는 유지하고 이유를 안내한다.
                return Insight(status="unsupported_question", plan=_dump(plan), summary=exc.message)
            except Exception:
                # C 계산 버그가 LLM 오류와 섞이지 않도록 로그를 구분해 남긴다.
                logger.exception("run_plan failed (analysis bug, not LLM)")
                return Insight(status="llm_error")

        result = ai.create_insight(kpis, comparison, sigs, plan=plan, answer=answer)  # D
        insight = Insight.model_validate(_dump(result))
        if plan is not None:
            insight.plan = _dump(plan)
            insight.answer = answer
        return insight
    except Exception:
        logger.exception("AI step failed")
        return Insight(status="llm_error")


def _analyze(uploads: list[UploadedFile], question: str | None) -> AnalyzeResponse:
    df = normalize.normalize_files([(u.filename, u.content) for u in uploads])  # 2·3
    # 스마트스토어 판매 분석 행은 광고 리포트와 판매액이 겹칠 수 있어 kpis·comparison·신호·질문에서 뺀다.
    # 스토어 파일만 올린 경우에는 비어 있으므로 전체 행으로 계산한다.
    core = df[df["platform"] != normalize.STORE_PLATFORM]
    if core.empty:
        core = df
    kpis = kpi.compute_kpis(core)  # 4
    store = kpi.compute_store_kpis(df)  # 4-1 스마트스토어 판매 분석 (없으면 None)
    comparison = compare.build_comparison(core)  # 5
    sigs = signals.detect_signals(kpis, comparison)  # 6
    # 질문은 전체 행을 넘긴다. run_plan 이 지표마다 스마트스토어 행을 쓸지 뺄지 정한다.
    insight = _run_ai(df, kpis, comparison, sigs, question)  # 7·8
    return AnalyzeResponse(  # 9
        kpis=kpis,
        comparison=comparison,
        rows=df.to_dict(orient="records"),
        signals=sigs,
        insight=insight,
        store=store,
    )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def analyze(files: list[UploadFile] | None = File(None), question: str | None = Form(None)):
    question = (question or "").strip() or None
    if question and len(question) > MAX_QUESTION_LENGTH:
        raise AppError(
            "QUESTION_TOO_LONG",
            f"질문은 {MAX_QUESTION_LENGTH}자 이내로 입력해주세요.",
            400,
            {"max_length": MAX_QUESTION_LENGTH, "length": len(question)},
        )
    uploads = await read_uploads(files)  # 1
    # pandas 계산·LLM 호출은 블로킹이라 스레드풀에서 실행해 서버가 멈추지 않게 한다.
    return await run_in_threadpool(_analyze, uploads, question)
