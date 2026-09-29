import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """도메인 오류. 모든 모듈(B·C·D)은 이 예외로 오류를 알린다.

    예: raise AppError("MISSING_COLUMNS", "…컬럼이 없습니다.", 422, {"missing": ["광고매출"]})
    """

    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception):
        # 스택트레이스는 로그에만 남기고 응답에는 노출하지 않는다.
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(status_code=500, content=_error_body("INTERNAL_ERROR", "서버 오류가 발생했습니다."))
