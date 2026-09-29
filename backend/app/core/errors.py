import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# FastAPI/Starlette 가 직접 내는 HTTP 오류 → 공통 오류 코드
HTTP_ERROR_CODES = {
    404: ("NOT_FOUND", "요청한 주소를 찾을 수 없습니다."),
    405: ("METHOD_NOT_ALLOWED", "지원하지 않는 요청 방식입니다."),
}


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


def _error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def register_error_handlers(app: FastAPI) -> None:
    """모든 오류를 {"error":{code,message,details}} 형식으로 통일한다 (WU-BE-05)."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException):
        code, message = HTTP_ERROR_CODES.get(exc.status_code, ("HTTP_ERROR", "요청을 처리할 수 없습니다."))
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        errors = [{"field": ".".join(str(p) for p in e.get("loc", ())), "message": e.get("msg", "")} for e in exc.errors()]
        return _error_response(422, "INVALID_REQUEST", "요청 형식이 올바르지 않습니다.", {"errors": errors})

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception):
        # 스택트레이스는 로그에만 남기고 응답에는 노출하지 않는다.
        logger.exception("Unhandled error: %s", exc)
        return _error_response(500, "INTERNAL_ERROR", "서버 오류가 발생했습니다.")
