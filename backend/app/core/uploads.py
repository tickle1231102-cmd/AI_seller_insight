from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError

ALLOWED_EXTENSIONS = {".xlsx", ".csv"}


@dataclass
class UploadedFile:
    filename: str
    content: bytes


async def read_uploads(files: list[UploadFile] | None) -> list[UploadedFile]:
    """파일 개수·확장자·크기 검증 후 내용을 메모리로 읽는다 (서버에 저장하지 않음)."""
    if not files:
        raise AppError("NO_FILES", "업로드할 파일을 선택해주세요.", 400)
    if len(files) > settings.max_files:
        raise AppError(
            "TOO_MANY_FILES",
            f"파일은 최대 {settings.max_files}개까지 업로드할 수 있습니다.",
            400,
            {"max_files": settings.max_files, "count": len(files)},
        )

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    result: list[UploadedFile] = []
    for f in files:
        name = f.filename or ""
        if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise AppError(
                "UNSUPPORTED_FILE_TYPE",
                f"{name}: .xlsx 또는 .csv 파일만 업로드할 수 있습니다.",
                400,
                {"file": name},
            )
        # 한도 + 1 바이트까지만 읽어 큰 파일을 끝까지 메모리에 올리지 않는다.
        content = await f.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise AppError(
                "FILE_TOO_LARGE",
                f"{name}: 파일 크기는 {settings.max_file_size_mb}MB 이하여야 합니다.",
                413,
                {"file": name, "max_mb": settings.max_file_size_mb},
            )
        result.append(UploadedFile(filename=name, content=content))
    return result
