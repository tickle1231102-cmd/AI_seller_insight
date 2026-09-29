import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analysis import normalize
from app.core.config import settings
from app.core.errors import AppError
from app.main import app
from app.schemas import AnalyzeResponse, PreviewResponse

client = TestClient(app, raise_server_exceptions=False)
CONTRACTS = Path(__file__).resolve().parents[2] / "shared" / "contracts"


def csv_file(name: str = "coupang_2026-09.csv", body: bytes = b"a,b\n1,2\n"):
    return ("files", (name, body, "text/csv"))


def fake_preview(filename: str, content: bytes) -> dict:
    return {
        "filename": filename,
        "platform": "coupang",
        "periods": ["2026-09"],
        "row_count": 1,
        "columns": ["총매출"],
        "preview": [{"총매출": 120000}],
    }


# ---- health / CORS ----
def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_cors_allows_local_frontend():
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"


# ---- 계약 예시 JSON 이 스키마를 통과 (WU-BE-02) ----
def test_contract_examples_match_schemas():
    PreviewResponse.model_validate(json.loads((CONTRACTS / "preview_response.json").read_text(encoding="utf-8")))
    AnalyzeResponse.model_validate(json.loads((CONTRACTS / "analyze_response.json").read_text(encoding="utf-8")))


# ---- /api/preview 파일 검증 (WU-BE-03) ----
def assert_error(res, status: int, code: str):
    assert res.status_code == status
    body = res.json()
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return body["error"]


def test_preview_no_files():
    assert_error(client.post("/api/preview"), 400, "NO_FILES")


def test_preview_too_many_files():
    files = [csv_file(f"f{i}.csv") for i in range(settings.max_files + 1)]
    assert_error(client.post("/api/preview", files=files), 400, "TOO_MANY_FILES")


def test_preview_unsupported_extension():
    err = assert_error(client.post("/api/preview", files=[csv_file("report.pdf")]), 400, "UNSUPPORTED_FILE_TYPE")
    assert err["details"]["file"] == "report.pdf"


def test_preview_file_too_large():
    big = b"x" * (settings.max_file_size_mb * 1024 * 1024 + 1)
    err = assert_error(client.post("/api/preview", files=[csv_file(body=big)]), 413, "FILE_TOO_LARGE")
    assert err["details"]["file"] == "coupang_2026-09.csv"


def test_preview_ok(monkeypatch):
    monkeypatch.setattr(normalize, "preview_file", fake_preview)
    res = client.post("/api/preview", files=[csv_file("a.csv"), csv_file("b.xlsx")])
    assert res.status_code == 200
    assert [f["filename"] for f in res.json()["files"]] == ["a.csv", "b.xlsx"]


def test_preview_passes_through_normalize_error(monkeypatch):
    def raise_missing(filename, content):
        raise AppError("MISSING_COLUMNS", "컬럼 누락", 422, {"file": filename, "missing": ["광고매출"]})

    monkeypatch.setattr(normalize, "preview_file", raise_missing)
    err = assert_error(client.post("/api/preview", files=[csv_file()]), 422, "MISSING_COLUMNS")
    assert err["details"] == {"file": "coupang_2026-09.csv", "missing": ["광고매출"]}


def test_unexpected_error_hides_stacktrace(monkeypatch):
    def boom(filename, content):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(normalize, "preview_file", boom)
    err = assert_error(client.post("/api/preview", files=[csv_file()]), 500, "INTERNAL_ERROR")
    assert "secret" not in json.dumps(err)
