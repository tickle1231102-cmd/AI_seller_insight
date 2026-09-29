"""담당: C — TECH_SPEC 4~6장 참고.

아래 함수 이름·시그니처는 B 의 routers/preview.py · analyze.py 가 호출하는 계약이다.
오류는 app.core.errors.AppError 로 던진다
(예: AppError("MISSING_COLUMNS", "...", 422, {"file": filename, "missing": [...]})).

검사 순서 (먼저 걸리는 오류 하나만 던진다):
EMPTY_FILE → UNKNOWN_PLATFORM → MISSING_COLUMNS → INVALID_PERIOD → INVALID_NUMBER
"""

import io
import re
from dataclasses import dataclass

import pandas as pd

from app.core.errors import AppError

# TECH_SPEC 4-1. 공통 필드 ← 플랫폼 원본 컬럼. 새 플랫폼은 여기에 추가하면 된다.
PLATFORM_COLUMN_MAP: dict[str, dict[str, str]] = {
    "coupang": {"revenue": "총매출", "orders": "주문", "units": "판매량", "ad_spend": "광고비", "ad_revenue": "광고매출"},
    "naver": {
        "revenue": "판매금액(순)",
        "orders": "상품결제건수",
        "units": "결제상품수량",
        "ad_spend": "광고비용",
        "ad_revenue": "전환매출",
    },
}
# 플랫폼 공통 원본 컬럼. period 는 컬럼이 아니라 파일명의 _YYYY-MM 에서 뽑는다.
PRODUCT_ID_COLUMN = "상품ID"
PRODUCT_NAME_COLUMN = "상품명"

MIN_PLATFORM_MATCH = 3  # 플랫폼 지표 컬럼 5개 중 이 개수 이상 맞아야 그 플랫폼으로 본다
PREVIEW_ROWS = 10

_PERIOD_RE = re.compile(r"(?<!\d)(\d{4})-(0[1-9]|1[0-2])(?!\d)")
_NUMBER_RE = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)")


@dataclass
class _Parsed:
    platform: str
    period: str
    metric_columns: list[str]  # 원본 지표 컬럼명 (revenue, orders, units, ad_spend, ad_revenue 순)
    product_names: list[str]
    metrics: dict[str, list[int | float]]  # 원본 컬럼명 → 숫자로 바꾼 값


def _decode(content: bytes) -> str:
    """UTF-8(BOM 포함)을 먼저 시도하고, 안 되면 한글 엑셀 CSV 의 CP949 로 읽는다."""
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp949")


def _read_table(filename: str, content: bytes) -> pd.DataFrame:
    """CSV/XLSX → 모든 셀을 공백 제거한 문자열로 읽은 DataFrame. 데이터 행이 없으면 EMPTY_FILE."""
    try:
        if filename.lower().endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content), dtype=str, keep_default_na=False)
        else:
            df = pd.read_csv(io.StringIO(_decode(content)), dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    df = df.map(lambda v: str(v).strip())
    df = df[(df != "").any(axis=1)].reset_index(drop=True)  # 완전히 빈 행은 버린다
    if df.empty:
        raise AppError("EMPTY_FILE", f"{filename}: 데이터 행이 없습니다.", 422, {"file": filename})
    return df


def _detect_platform(filename: str, columns: list[str]) -> str:
    """컬럼 구조로 플랫폼을 판별한다. 맞는 지표 컬럼이 가장 많은 쪽을 고르되, 기준 미달이거나 동률이면 판별 불가."""
    scores = {p: len(set(m.values()) & set(columns)) for p, m in PLATFORM_COLUMN_MAP.items()}
    best = max(scores.values())
    winners = [p for p, s in scores.items() if s == best]
    if best < MIN_PLATFORM_MATCH or len(winners) > 1:
        raise AppError(
            "UNKNOWN_PLATFORM",
            f"{filename}: 쿠팡·네이버 파일 형식으로 판별할 수 없습니다.",
            422,
            {"file": filename},
        )
    return winners[0]


def _extract_period(filename: str) -> str:
    """파일명의 _YYYY-MM 에서 기간을 뽑는다 (예: coupang_2026-09.csv → 2026-09)."""
    match = _PERIOD_RE.search(filename)
    if not match:
        raise AppError(
            "INVALID_PERIOD",
            f"{filename}: 파일명에서 기간(YYYY-MM)을 찾을 수 없습니다. 예: coupang_2026-09.csv",
            422,
            {"file": filename},
        )
    return match.group(0)


def _to_number(raw: str) -> int | float:
    """TECH_SPEC 4-2: ',' '원' 공백 제거 후 숫자 변환. 빈 셀은 0. 변환 불가면 ValueError."""
    text = raw.replace(",", "").replace("원", "").replace(" ", "")
    if text == "":
        return 0
    if not _NUMBER_RE.fullmatch(text):  # float() 가 받아주는 nan, inf, 1e5, 1_000 은 숫자로 보지 않는다
        raise ValueError(raw)
    value = float(text)
    return int(value) if value.is_integer() else value


def _parse(filename: str, content: bytes) -> _Parsed:
    df = _read_table(filename, content)
    columns = list(df.columns)
    platform = _detect_platform(filename, columns)
    metric_columns = list(PLATFORM_COLUMN_MAP[platform].values())

    missing = [c for c in (PRODUCT_ID_COLUMN, PRODUCT_NAME_COLUMN, *metric_columns) if c not in columns]
    if missing:
        raise AppError(
            "MISSING_COLUMNS",
            f"{filename} 파일에 {', '.join(repr(c) for c in missing)} 컬럼이 없습니다.",
            422,
            {"file": filename, "missing": missing},
        )

    period = _extract_period(filename)

    metrics: dict[str, list[int | float]] = {c: [] for c in metric_columns}
    for row_no, record in enumerate(df[metric_columns].to_dict("records"), start=1):  # row_no: 데이터 행 기준 1부터
        for column in metric_columns:
            try:
                metrics[column].append(_to_number(record[column]))
            except ValueError:
                raise AppError(
                    "INVALID_NUMBER",
                    f"{filename}: {row_no}행 '{column}' 값 '{record[column]}' 을(를) 숫자로 바꿀 수 없습니다.",
                    422,
                    {"file": filename, "row": row_no, "column": column, "value": record[column]},
                ) from None

    return _Parsed(platform, period, metric_columns, df[PRODUCT_NAME_COLUMN].tolist(), metrics)


def preview_file(filename: str, content: bytes) -> dict:
    """업로드 파일 1개 → TECH_SPEC 7-3 의 files[] 항목.

    반환: {"filename", "platform", "periods", "row_count", "columns", "preview"(최대 10행)}
    프론트 미리보기 표가 columns 를 행의 키로 쓰므로 columns 맨 앞은 "product_name" 이다.
    """
    parsed = _parse(filename, content)
    columns = ["product_name", *parsed.metric_columns]
    preview = [
        {"product_name": name, **{c: parsed.metrics[c][i] for c in parsed.metric_columns}}
        for i, name in enumerate(parsed.product_names[:PREVIEW_ROWS])
    ]
    return {
        "filename": filename,
        "platform": parsed.platform,
        "periods": [parsed.period],
        "row_count": len(parsed.product_names),
        "columns": columns,
        "preview": preview,
    }


def normalize_files(files: list[tuple[str, bytes]]) -> "pd.DataFrame":
    """업로드 파일 전체 [(filename, content), ...] → 공통 스키마 9개 필드 DataFrame (TECH_SPEC 4장).

    routers/analyze.py 가 호출한다.
    """
    raise NotImplementedError("C: normalize_files 구현 필요")
