"""WU-DA-06: 실패 케이스 7종을 /api/preview 와 /api/analyze 양쪽에서 확인한다.

7종: 빈 파일, 누락 컬럼, 잘못된 숫자, 파일 크기 초과, 파일 개수 초과, 미지원 확장자, 미지원 플랫폼.
각 케이스는 (1) 기대한 HTTP 상태·오류 코드, (2) 사람이 읽을 수 있는 message, (3) 화면이 쓰는 details 를 확인한다.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from tests.test_normalize import FAILURES, FIXTURES, NORMAL_FILES, read

client = TestClient(app, raise_server_exceptions=False)
ENDPOINTS = ["/api/preview", "/api/analyze"]
MAX_BYTES = settings.max_file_size_mb * 1024 * 1024


def upload(name: str, body: bytes):
    return ("files", (name, body, "application/octet-stream"))


def good_files():
    return [upload(n, read(FIXTURES / n)) for n in NORMAL_FILES]


def fixture_case(name: str):
    return [upload(name, read(FAILURES / name))]


def oversized_csv() -> bytes:
    """정상 헤더로 시작하지만 한도(5MB)보다 1바이트 큰 파일."""
    header = read(FIXTURES / "coupang_2026-09.csv").splitlines()[0] + b"\n"
    return header + b"x" * (MAX_BYTES + 1 - len(header))


# (id, files, http, code, details 중 일부)
CASES = [
    ("empty_file", lambda: fixture_case("coupang_2026-09_empty.csv"), 422, "EMPTY_FILE", {"file": "coupang_2026-09_empty.csv"}),
    (
        "missing_columns",
        lambda: fixture_case("coupang_2026-09_missing_columns.csv"),
        422,
        "MISSING_COLUMNS",
        {"file": "coupang_2026-09_missing_columns.csv", "missing": ["광고매출"]},
    ),
    (
        "invalid_number",
        lambda: fixture_case("coupang_2026-09_invalid_number.csv"),
        422,
        "INVALID_NUMBER",
        {"file": "coupang_2026-09_invalid_number.csv", "row": 2, "column": "총매출", "value": "abc"},
    ),
    ("file_too_large", lambda: [upload("coupang_2026-09.csv", oversized_csv())], 413, "FILE_TOO_LARGE", {"file": "coupang_2026-09.csv"}),
    (
        "too_many_files",
        lambda: [upload(f"coupang_2026-{i:02d}.csv", b"a\n1\n") for i in range(1, settings.max_files + 2)],
        400,
        "TOO_MANY_FILES",
        {"max_files": settings.max_files, "count": settings.max_files + 1},
    ),
    ("unsupported_extension", lambda: [upload("report.pdf", b"%PDF-1.4")], 400, "UNSUPPORTED_FILE_TYPE", {"file": "report.pdf"}),
    ("unknown_platform", lambda: fixture_case("unknown_platform_2026-09.csv"), 422, "UNKNOWN_PLATFORM", {"file": "unknown_platform_2026-09.csv"}),
]


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_failure_case_returns_expected_error(endpoint, case):
    _, make_files, http, code, details = case
    res = client.post(endpoint, files=make_files())
    assert res.status_code == http, res.text
    error = res.json()["error"]
    assert error["code"] == code
    assert error["message"].strip()
    for key, value in details.items():
        assert error["details"][key] == value


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_error_message_names_the_offending_file(endpoint):
    """사용자가 어느 파일이 문제인지 알 수 있어야 한다 (파일 단위 오류는 message 에 파일명 포함)."""
    for name in ["coupang_2026-09_empty.csv", "coupang_2026-09_missing_columns.csv", "coupang_2026-09_invalid_number.csv"]:
        res = client.post(endpoint, files=fixture_case(name))
        assert name in res.json()["error"]["message"]


# ---- 경계값: 한도 "정확히" 는 통과해야 한다 ----
def test_exactly_max_files_is_accepted():
    files = [upload(f"coupang_2026-{i:02d}.csv", read(FIXTURES / "coupang_2026-09.csv")) for i in range(1, settings.max_files + 1)]
    res = client.post("/api/preview", files=files)
    assert res.status_code == 200
    assert len(res.json()["files"]) == settings.max_files


def test_file_exactly_at_size_limit_is_not_rejected_as_too_large():
    body = oversized_csv()[:-1]  # 정확히 5MB
    assert len(body) == MAX_BYTES
    res = client.post("/api/preview", files=[upload("coupang_2026-09.csv", body)])
    assert res.json().get("error", {}).get("code") != "FILE_TOO_LARGE"


@pytest.mark.parametrize("name", ["COUPANG_2026-09.CSV", "Coupang_2026-09.Csv"])
def test_extension_check_ignores_case(name):
    res = client.post("/api/preview", files=[upload(name, read(FIXTURES / "coupang_2026-09.csv"))])
    assert res.status_code == 200


@pytest.mark.parametrize("name", ["report.xls", "report", "report.csv.exe", "report.csv "])
def test_other_extensions_are_rejected(name):
    res = client.post("/api/preview", files=[upload(name, b"a,b\n1,2\n")])
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


# ---- 여러 파일 중 하나만 나쁠 때 ----
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_one_bad_file_among_good_files_fails_whole_request_with_its_code(endpoint):
    files = good_files() + fixture_case("coupang_2026-09_invalid_number.csv")
    res = client.post(endpoint, files=files)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_NUMBER"
    assert res.json()["error"]["details"]["file"] == "coupang_2026-09_invalid_number.csv"


def test_bad_extension_is_reported_before_content_problems():
    files = [upload("report.pdf", b"x")] + fixture_case("coupang_2026-09_empty.csv")
    res = client.post("/api/preview", files=files)
    assert res.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


# ---- 깨진 파일 ----
@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize(
    "name, body",
    [
        ("coupang_2026-09.xlsx", b"this is not a zip"),  # 확장자만 xlsx
        ("coupang_2026-09.csv", bytes(range(256)) * 20),  # UTF-8 도 CP949 도 아님
    ],
    ids=["corrupted_xlsx", "undecodable_csv"],
)
def test_unreadable_file_is_reported_not_server_crash(endpoint, name, body):
    res = client.post(endpoint, files=[upload(name, body)])
    assert res.status_code == 422, res.text
    error = res.json()["error"]
    assert error["code"] == "UNREADABLE_FILE"
    assert name in error["message"]
    assert error["details"] == {"file": name}
