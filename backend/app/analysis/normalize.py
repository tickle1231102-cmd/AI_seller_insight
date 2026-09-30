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

# 네이버 스마트스토어 통계 > 판매 분석(SALES) 내보내기. 광고 지표가 없어 ad_spend·ad_revenue 는 0 으로 둔다.
SMARTSTORE_SALES_MAP: dict[str, str] = {
    "revenue": "판매금액(순)",
    "orders": "상품결제건수",
    "units": "결제상품수량",
    "gross_revenue": "판매금액(총)",
    "visits": "방문수",
    "refund_count": "환불건수",
    "refund_amount": "환불금액",
    "discount_amount": "전체 할인액",
}
SMARTSTORE_ID_COLUMN = "채널상품번호"
SMARTSTORE_NAME_COLUMN = "채널상품명"
SMARTSTORE_DATE_COLUMN = "날짜"
SMARTSTORE_TOTAL_LABEL = "전체"  # 기간·일자 합계 행의 상품명·상품번호 값
# 스마트스토어 판매 분석은 광고 리포트(naver)와 같은 판매액이 겹칠 수 있어 별도 platform 으로 분리한다.
# kpis·comparison·신호·질문 실행은 이 platform 을 제외하고 계산하고, store 섹션과 rows 에만 나온다.
STORE_PLATFORM = "naver_store"
SMARTSTORE_SALES_KEYS = {SMARTSTORE_ID_COLUMN, SMARTSTORE_NAME_COLUMN, "판매금액(총)"}
# 스마트스토어 방문·검색·고객 분석 파일. 판별만 하고 분석은 아직 지원하지 않는다 (WORK_UNITS P1).
SMARTSTORE_OTHER_KEYS = {"visit": {"경로(1단계)", "방문수"}, "query": {"검색어", "방문수"}, "customer": {"고객분류", "방문고객수"}}

NORMALIZED_COLUMNS = ["period", "platform", "product_id", "product_name", "revenue", "orders", "units", "ad_spend", "ad_revenue"]
# 스마트스토어 판매 분석 파일에만 있는 지표. 다른 파일의 행은 None.
STORE_FIELDS = ["gross_revenue", "visits", "refund_count", "refund_amount", "discount_amount"]

MIN_PLATFORM_MATCH = 3  # 플랫폼 지표 컬럼 5개 중 이 개수 이상 맞아야 그 플랫폼으로 본다
PREVIEW_ROWS = 10

_PERIOD_RE = re.compile(r"(?<!\d)(\d{4})-(0[1-9]|1[0-2])(?!\d)")
_DATE_RE = re.compile(r"(?<!\d)(\d{4})[-.]?(0[1-9]|1[0-2])[-.]?(0[1-9]|[12]\d|3[01])(?!\d)")
_NUMBER_RE = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)")


@dataclass
class _Parsed:
    platform: str
    periods: list[str]  # 행마다의 기간 (YYYY-MM)
    field_map: dict[str, str]  # 공통 필드 → 원본 지표 컬럼명
    product_ids: list[str]
    product_names: list[str]
    metrics: dict[str, list[int | float]]  # 원본 컬럼명 → 숫자로 바꾼 값

    @property
    def metric_columns(self) -> list[str]:
        return list(self.field_map.values())

    @property
    def is_smartstore(self) -> bool:
        return self.field_map is SMARTSTORE_SALES_MAP


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
    except Exception:  # 깨진 xlsx(zip 아님), 인코딩 불명, 표 형식이 아닌 CSV 등 — 500 대신 파일 문제로 알린다
        raise AppError(
            "UNREADABLE_FILE",
            f"{filename}: 파일을 읽을 수 없습니다. 파일이 손상되지 않았는지, 엑셀 또는 CSV 형식이 맞는지 확인해주세요.",
            422,
            {"file": filename},
        ) from None

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


def _midpoint_month(text: str) -> str | None:
    """문자열 속 날짜(YYYYMMDD, YYYY-MM-DD)들의 첫·끝 날짜 중간이 속한 월. 날짜가 없으면 None.

    스마트스토어 내보내기는 20260830-20260928 처럼 월 경계를 걸치므로 기간의 대부분이 속한 월로 본다.
    """
    dates = [pd.Timestamp(int(y), int(m), int(d)) for y, m, d in _DATE_RE.findall(text)]
    if not dates:
        return None
    mid = dates[0] + (dates[-1] - dates[0]) / 2
    return f"{mid.year:04d}-{mid.month:02d}"


def _extract_period(filename: str) -> str:
    """파일명에서 기간을 뽑는다. _YYYY-MM (coupang_2026-09.csv) 또는 날짜 범위 (sales_20260901-20260930.xlsx)."""
    match = _PERIOD_RE.search(filename)
    if match:
        return match.group(0)
    period = _midpoint_month(filename)
    if period is None:
        raise AppError(
            "INVALID_PERIOD",
            f"{filename}: 파일명에서 기간(YYYY-MM)을 찾을 수 없습니다. 예: coupang_2026-09.csv",
            422,
            {"file": filename},
        )
    return period


def _to_number(raw: str, *, dash_is_zero: bool = False) -> int | float:
    """TECH_SPEC 4-2: ',' '원' 공백 제거 후 숫자 변환. 빈 셀은 0. 변환 불가면 ValueError.

    dash_is_zero: 스마트스토어 판매 분석 파일은 값이 없으면 '-' 로 적으므로 이 파일에서만 0 으로 본다.
    """
    text = raw.replace(",", "").replace("원", "").replace(" ", "")
    if text == "" or (dash_is_zero and text == "-"):
        return 0
    if not _NUMBER_RE.fullmatch(text):  # float() 가 받아주는 nan, inf, 1e5, 1_000 은 숫자로 보지 않는다
        raise ValueError(raw)
    value = float(text)
    return int(value) if value.is_integer() else value


def _reject_other_smartstore(filename: str, columns: list[str]) -> None:
    for kind, keys in SMARTSTORE_OTHER_KEYS.items():
        if keys <= set(columns):
            raise AppError(
                "UNSUPPORTED_DATASET",
                f"{filename}: 스마트스토어 {kind} 분석 파일은 아직 지원하지 않습니다. 판매 분석(SALES) 파일을 올려주세요.",
                422,
                {"file": filename, "dataset": kind},
            )


def _parse(filename: str, content: bytes) -> _Parsed:
    df = _read_table(filename, content)
    columns = list(df.columns)
    if SMARTSTORE_SALES_KEYS <= set(columns):
        platform, field_map = STORE_PLATFORM, SMARTSTORE_SALES_MAP
        id_column, name_column = SMARTSTORE_ID_COLUMN, SMARTSTORE_NAME_COLUMN
    else:
        _reject_other_smartstore(filename, columns)
        platform = _detect_platform(filename, columns)
        field_map = PLATFORM_COLUMN_MAP[platform]
        id_column, name_column = PRODUCT_ID_COLUMN, PRODUCT_NAME_COLUMN
    metric_columns = list(field_map.values())

    missing = [c for c in (id_column, name_column, *metric_columns) if c not in columns]
    if missing:
        raise AppError(
            "MISSING_COLUMNS",
            f"{filename} 파일에 {', '.join(repr(c) for c in missing)} 컬럼이 없습니다.",
            422,
            {"file": filename, "missing": missing},
        )

    if field_map is SMARTSTORE_SALES_MAP and SMARTSTORE_DATE_COLUMN in columns:
        # 행의 '날짜' (예: 2026-09-01~2026-09-30) 가 우선, 없으면 파일명 기간
        row_periods = [_midpoint_month(v) for v in df[SMARTSTORE_DATE_COLUMN]]
        fallback = None if all(row_periods) else _extract_period(filename)
        periods = [p or fallback for p in row_periods]
    else:
        periods = [_extract_period(filename)] * len(df)

    metrics: dict[str, list[int | float]] = {c: [] for c in metric_columns}
    for row_no, record in enumerate(df[metric_columns].to_dict("records"), start=1):  # row_no: 데이터 행 기준 1부터
        for column in metric_columns:
            try:
                metrics[column].append(_to_number(record[column], dash_is_zero=field_map is SMARTSTORE_SALES_MAP))
            except ValueError:
                raise AppError(
                    "INVALID_NUMBER",
                    f"{filename}: {row_no}행 '{column}' 값 '{record[column]}' 을(를) 숫자로 바꿀 수 없습니다.",
                    422,
                    {"file": filename, "row": row_no, "column": column, "value": record[column]},
                ) from None

    product_ids, product_names = df[id_column].tolist(), df[name_column].tolist()
    if field_map is SMARTSTORE_SALES_MAP:
        # 내보내기에는 기간·일자별 '전체' 요약 행이 상품 행과 섞여 있다. 그대로 더하면 매출이 여러 배가 되므로
        # 상품 행이 있으면 요약 행은 뺀다 (오류 행 번호는 파일 기준을 유지하려고 숫자 검증 뒤에 거른다).
        keep = [i for i, (pid, name) in enumerate(zip(product_ids, product_names)) if SMARTSTORE_TOTAL_LABEL not in (pid, name)]
        if keep and len(keep) < len(product_ids):
            periods = [periods[i] for i in keep]
            product_ids = [product_ids[i] for i in keep]
            product_names = [product_names[i] for i in keep]
            metrics = {c: [values[i] for i in keep] for c, values in metrics.items()}

    return _Parsed(platform, periods, field_map, product_ids, product_names, metrics)


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
        "periods": sorted(set(parsed.periods)),
        "row_count": len(parsed.product_names),
        "columns": columns,
        "preview": preview,
    }


def normalize_files(files: list[tuple[str, bytes]]) -> pd.DataFrame:
    """업로드 파일 전체 [(filename, content), ...] → 공통 스키마 9개 필드 DataFrame (TECH_SPEC 4장).

    금액·수량은 int 로 반올림한다 (B 의 스키마가 정수만 받는다). 행은 기간·플랫폼·상품ID 순.
    오류는 preview_file 과 같고, 어느 파일인지는 details.file 로 구분된다.
    routers/analyze.py 가 호출한다.

    스마트스토어 판매 분석 파일이 있으면 STORE_FIELDS 5개 컬럼이 붙고(그 외 파일의 행은 None), 광고 지표는 0 이다.
    일자별로 내려받아 같은 월·상품이 여러 행이면 합친다.
    """
    frames = []
    for filename, content in files:
        parsed = _parse(filename, content)
        values = {field: [int(round(v)) for v in parsed.metrics[column]] for field, column in parsed.field_map.items()}
        frame = pd.DataFrame(
            {
                "period": parsed.periods,
                "platform": parsed.platform,
                "product_id": parsed.product_ids,
                "product_name": parsed.product_names,
                **values,
            }
        )
        if parsed.is_smartstore:
            frame["ad_spend"] = 0
            frame["ad_revenue"] = 0
            keys = ["period", "platform", "product_id"]
            names = frame.groupby(keys, sort=False)["product_name"].first()
            frame = frame.drop(columns="product_name").groupby(keys, sort=False).sum().join(names).reset_index()
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=NORMALIZED_COLUMNS)
    if any(field in df.columns for field in STORE_FIELDS):
        df = df.reindex(columns=NORMALIZED_COLUMNS + STORE_FIELDS)
        for field in STORE_FIELDS:  # 스마트스토어가 아닌 파일의 행은 NaN → None (JSON null)
            df[field] = df[field].astype(object).where(df[field].notna(), None)
    else:
        df = df[NORMALIZED_COLUMNS]
    return df.sort_values(["period", "platform", "product_id"], kind="stable").reset_index(drop=True)
