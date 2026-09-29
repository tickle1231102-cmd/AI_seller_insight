"""analysis/normalize.preview_file 테스트. 정답은 shared/fixtures 의 expected_kpis.json · failures/expected_errors.json."""

import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.analysis import normalize
from app.core.errors import AppError
from app.main import app
from app.schemas import PreviewResponse

FIXTURES = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
FAILURES = FIXTURES / "failures"
EXPECTED_ROWS = json.loads((FIXTURES / "expected_kpis.json").read_text(encoding="utf-8"))["rows"]
EXPECTED_ERRORS = {k: v for k, v in json.loads((FAILURES / "expected_errors.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}

NORMAL_FILES = ["coupang_2026-08.csv", "coupang_2026-09.csv", "naver_2026-08.csv", "naver_2026-09.csv"]
client = TestClient(app, raise_server_exceptions=False)


def read(path: Path) -> bytes:
    return path.read_bytes()


def csv_bytes(header: str, *rows: str) -> bytes:
    return ("\n".join([header, *rows]) + "\n").encode("utf-8")


COUPANG_HEADER = "상품ID,상품명,총매출,주문,판매량,광고비,광고매출"


# ---- 정상 fixture ----
@pytest.mark.parametrize("name", NORMAL_FILES)
def test_preview_matches_expected_rows(name):
    """미리보기 값이 expected_kpis.json 의 rows(다른 코드로 만든 정답)와 같다."""
    result = normalize.preview_file(name, read(FIXTURES / name))
    platform, period = name.removesuffix(".csv").split("_")
    metrics = normalize.PLATFORM_COLUMN_MAP[platform]

    assert result["filename"] == name
    assert result["platform"] == platform
    assert result["periods"] == [period]
    assert result["row_count"] == 3
    assert result["columns"] == ["product_name", *metrics.values()]

    expected = [r for r in EXPECTED_ROWS if r["platform"] == platform and r["period"] == period]
    assert len(result["preview"]) == len(expected) == 3
    for got, want in zip(result["preview"], expected):
        assert got["product_name"] == want["product_name"]
        for field, column in metrics.items():
            assert got[column] == want[field], f"{name} {want['product_id']} {column}"


def test_preview_is_capped_at_10_rows():
    rows = [f"P{i:03d},상품{i},1000,1,1,100,200" for i in range(25)]
    result = normalize.preview_file("coupang_2026-09.csv", csv_bytes(COUPANG_HEADER, *rows))
    assert result["row_count"] == 25
    assert len(result["preview"]) == 10


# ---- 실패 fixture ----
@pytest.mark.parametrize("name", sorted(EXPECTED_ERRORS))
def test_failure_fixtures_raise_expected_error(name):
    expected = EXPECTED_ERRORS[name]
    with pytest.raises(AppError) as exc:
        normalize.preview_file(name, read(FAILURES / name))
    assert exc.value.code == expected["code"]
    assert exc.value.status_code == expected["http"]
    assert exc.value.message
    assert exc.value.details["file"] == name
    for key, value in expected.get("details", {}).items():
        assert exc.value.details[key] == value


def test_zero_byte_file_is_empty_file():
    with pytest.raises(AppError) as exc:
        normalize.preview_file("coupang_2026-09.csv", b"")
    assert exc.value.code == "EMPTY_FILE"


def test_rows_with_only_blank_cells_do_not_count():
    with pytest.raises(AppError) as exc:
        normalize.preview_file("coupang_2026-09.csv", csv_bytes(COUPANG_HEADER, ",,,,,,", ",,,,,,"))
    assert exc.value.code == "EMPTY_FILE"


# ---- 기간 (파일명) ----
@pytest.mark.parametrize("name", ["sales.csv", "coupang_2026-13.csv", "coupang_2026-9.csv", "coupang_20260-09.csv"])
def test_filename_without_valid_period(name):
    with pytest.raises(AppError) as exc:
        normalize.preview_file(name, csv_bytes(COUPANG_HEADER, "P001,이어폰,1000,1,1,100,200"))
    assert exc.value.code == "INVALID_PERIOD"
    assert exc.value.status_code == 422
    assert exc.value.details == {"file": name}


def test_period_is_taken_from_filename():
    result = normalize.preview_file("내보내기_쿠팡_2026-08(최종).csv", csv_bytes(COUPANG_HEADER, "P001,이어폰,1000,1,1,100,200"))
    assert result["periods"] == ["2026-08"]


# ---- 숫자 변환 (TECH_SPEC 4-2) ----
def test_numbers_with_commas_won_and_blank_cells():
    body = csv_bytes(COUPANG_HEADER, 'P001,이어폰,"1,900,000원", 12 ,,"50,000",0', "P002,밴드,700.5,1,1,,")
    row0, row1 = normalize.preview_file("coupang_2026-09.csv", body)["preview"]
    assert (row0["총매출"], row0["주문"], row0["판매량"], row0["광고비"], row0["광고매출"]) == (1900000, 12, 0, 50000, 0)
    assert row1["총매출"] == 700.5 and row1["광고비"] == 0 and row1["광고매출"] == 0


@pytest.mark.parametrize("bad", ["abc", "1e5", "nan", "inf", "1_000", "12.3.4", "--5"])
def test_invalid_numbers_are_rejected(bad):
    body = csv_bytes(COUPANG_HEADER, "P001,이어폰,1000,1,1,100,200", f"P002,밴드,{bad},1,1,100,200")
    with pytest.raises(AppError) as exc:
        normalize.preview_file("coupang_2026-09.csv", body)
    assert exc.value.code == "INVALID_NUMBER"
    assert exc.value.details == {"file": "coupang_2026-09.csv", "row": 2, "column": "총매출", "value": bad}


def test_invalid_number_reports_first_error_in_reading_order():
    """행 우선으로 읽어 가장 앞의 오류를 알린다: 1행의 뒤쪽 컬럼이 2행의 앞쪽 컬럼보다 먼저."""
    body = csv_bytes(COUPANG_HEADER, "P001,이어폰,1000,1,1,x,200", "P002,밴드,y,1,1,100,200")
    with pytest.raises(AppError) as exc:
        normalize.preview_file("coupang_2026-09.csv", body)
    assert (exc.value.details["row"], exc.value.details["column"]) == (1, "광고비")


# ---- 플랫폼 판별 / 컬럼 ----
def test_platform_is_detected_by_columns_not_filename():
    body = read(FIXTURES / "naver_2026-09.csv")
    result = normalize.preview_file("coupang_2026-09.csv", body)  # 파일명은 쿠팡, 컬럼은 네이버
    assert result["platform"] == "naver"


def test_missing_product_columns_are_reported():
    body = csv_bytes("총매출,주문,판매량,광고비,광고매출", "1000,1,1,100,200")
    with pytest.raises(AppError) as exc:
        normalize.preview_file("coupang_2026-09.csv", body)
    assert exc.value.code == "MISSING_COLUMNS"
    assert exc.value.details["missing"] == ["상품ID", "상품명"]


def test_ambiguous_columns_are_unknown_platform():
    """쿠팡·네이버 지표 컬럼이 같은 개수로 섞여 있으면 판별하지 않는다."""
    # 쿠팡 지표 3개(총매출·주문·판매량) 대 네이버 지표 3개(상품결제건수·결제상품수량·광고비용)
    body = csv_bytes("상품ID,상품명,총매출,주문,판매량,상품결제건수,결제상품수량,광고비용", "P001,이어폰,1,1,1,1,1,1")
    with pytest.raises(AppError) as exc:
        normalize.preview_file("coupang_2026-09.csv", body)
    assert exc.value.code == "UNKNOWN_PLATFORM"


# ---- 파일 형식 ----
def test_csv_with_bom_and_cp949():
    text = csv_bytes(COUPANG_HEADER, "P001,이어폰,1000,1,1,100,200").decode("utf-8")
    expected = normalize.preview_file("coupang_2026-09.csv", text.encode("utf-8"))
    assert normalize.preview_file("coupang_2026-09.csv", b"\xef\xbb\xbf" + text.encode("utf-8")) == expected
    assert normalize.preview_file("coupang_2026-09.csv", text.encode("cp949")) == expected


def test_xlsx_gives_same_result_as_csv():
    lines = read(FIXTURES / "coupang_2026-09.csv").decode("utf-8").splitlines()
    wb = Workbook()
    ws = wb.active
    for i, line in enumerate(lines):
        cells = line.split(",")
        ws.append(cells if i == 0 else [cells[0], cells[1], *(int(c) for c in cells[2:])])  # 지표는 숫자 셀
    buf = io.BytesIO()
    wb.save(buf)

    from_xlsx = normalize.preview_file("coupang_2026-09.xlsx", buf.getvalue())
    from_csv = normalize.preview_file("coupang_2026-09.csv", read(FIXTURES / "coupang_2026-09.csv"))
    assert from_xlsx["preview"] == from_csv["preview"]
    assert {k: v for k, v in from_xlsx.items() if k not in ("filename", "preview")} == {
        k: v for k, v in from_csv.items() if k not in ("filename", "preview")
    }


# ---- /api/preview 엔드투엔드 (B 의 라우터 ↔ C 의 normalize) ----
def test_api_preview_with_real_fixtures():
    files = [("files", (n, read(FIXTURES / n), "text/csv")) for n in NORMAL_FILES]
    res = client.post("/api/preview", files=files)
    assert res.status_code == 200
    body = PreviewResponse.model_validate(res.json())  # B 의 응답 스키마를 통과
    assert [f.platform for f in body.files] == ["coupang", "coupang", "naver", "naver"]
    assert [f.periods for f in body.files] == [["2026-08"], ["2026-09"], ["2026-08"], ["2026-09"]]


@pytest.mark.parametrize("name", sorted(EXPECTED_ERRORS))
def test_api_preview_returns_error_format_for_failure_fixtures(name):
    expected = EXPECTED_ERRORS[name]
    res = client.post("/api/preview", files=[("files", (name, read(FAILURES / name), "text/csv"))])
    assert res.status_code == expected["http"]
    error = res.json()["error"]
    assert error["code"] == expected["code"]
    assert error["message"]
    for key, value in expected.get("details", {}).items():
        assert error["details"][key] == value
