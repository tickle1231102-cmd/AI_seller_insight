"""Opt-in paid local API integration test using only public fixture data.

Run explicitly with RUN_LLM_INTEGRATION=1 and an OpenAI API key. The normal
test suite deselects this file because it makes paid external API requests.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_real_openai_route_keeps_calculated_results_and_grounded_insight():
    if os.getenv("RUN_LLM_INTEGRATION") != "1":
        pytest.skip("Set RUN_LLM_INTEGRATION=1 to run the paid API route test.")
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")):
        pytest.skip("An OpenAI API key is required.")

    fixtures = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
    expected = json.loads(
        (fixtures / "expected_kpis.json").read_text(encoding="utf-8")
    )
    paths = sorted(fixtures.glob("*.csv"))
    files = [
        ("files", (path.name, path.read_bytes(), "text/csv"))
        for path in paths
    ]

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/analyze",
            files=files,
            data={"question": "광고 효율이 가장 안 좋은 플랫폼 어디야?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["kpis"] == expected["kpis"]
    assert body["comparison"] == expected["comparison"]
    assert body["signals"] == expected["signals"]

    insight = body["insight"]
    assert insight["status"] == "ok"
    assert insight["plan"] == {
        "metric": "roas",
        "group_by": "platform",
        "sort": "asc",
        "limit": 5,
        "period": None,
    }
    assert insight["answer"]
    assert insight["answer"][0]["platform"] == "coupang"
    assert insight["answer"][0]["roas"] == 291.7
    assert insight["summary"]
    assert insight["evidence"]
    assert insight["limitations"]

