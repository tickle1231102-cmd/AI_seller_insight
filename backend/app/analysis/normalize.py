"""담당: C — TECH_SPEC 4~6장 참고.

아래 함수 이름·시그니처는 B 의 routers/preview.py · analyze.py 가 호출하는 계약이다.
본문은 C 가 구현한다. 오류는 app.core.errors.AppError 로 던진다
(예: AppError("MISSING_COLUMNS", "...", 422, {"file": filename, "missing": [...]})).
"""


def preview_file(filename: str, content: bytes) -> dict:
    """업로드 파일 1개 → TECH_SPEC 7-3 의 files[] 항목.

    반환: {"filename", "platform", "periods", "row_count", "columns", "preview"(최대 10행)}
    """
    raise NotImplementedError("C: preview_file 구현 필요")


def normalize_files(files: list[tuple[str, bytes]]) -> "pd.DataFrame":
    """업로드 파일 전체 [(filename, content), ...] → 공통 스키마 9개 필드 DataFrame (TECH_SPEC 4장).

    routers/analyze.py 가 호출한다.
    """
    raise NotImplementedError("C: normalize_files 구현 필요")
