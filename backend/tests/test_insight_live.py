"""Opt-in paid smoke test for the text-only insight schema."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.analysis import compare, kpi, normalize, signals
from backend.app.ai.insight import create_insight


@pytest.mark.integration
def test_real_openai_insight_preserves_csv_results():
    if os.getenv("RUN_LLM_INTEGRATION") != "1":
        pytest.skip("Set RUN_LLM_INTEGRATION=1 to run a paid OpenAI smoke test.")
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")):
        pytest.skip("An OpenAI API key is required.")

    fixtures = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
    expected = json.loads((fixtures / "expected_kpis.json").read_text(encoding="utf-8"))
    df = normalize.normalize_files([(p.name, p.read_bytes()) for p in sorted(fixtures.glob("*.csv"))])
    kpis = kpi.compute_kpis(df)
    comparison = compare.build_comparison(df)
    sigs = signals.detect_signals(kpis, comparison)
    assert kpis == expected["kpis"]
    assert comparison == expected["comparison"]
    assert sigs == expected["signals"]

    result = create_insight(kpis, comparison, sigs)
    # Only normalized status/code are included if the API request fails.
    assert result.status == "ok", f"status={result.status}; reason={result.reason}"
    assert result.plan is None and result.answer == [] and result.reason is None
    assert result.summary.strip()
    assert kpis == expected["kpis"]
    assert comparison == expected["comparison"]
    assert sigs == expected["signals"]
