from fastapi import APIRouter, File, UploadFile

from app.analysis import normalize
from app.core.uploads import read_uploads
from app.schemas import ErrorResponse, PreviewResponse

router = APIRouter(prefix="/api")


@router.post(
    "/preview",
    response_model=PreviewResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def preview(files: list[UploadFile] | None = File(None)):
    uploads = await read_uploads(files)
    # 파싱·플랫폼 판별·정규화 오류(EMPTY_FILE, MISSING_COLUMNS 등)는 C 모듈이 AppError 로 던진다.
    return PreviewResponse(files=[normalize.preview_file(u.filename, u.content) for u in uploads])
