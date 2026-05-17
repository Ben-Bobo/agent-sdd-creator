"""Live LLM tests over the fixture set.

These tests make real Anthropic API calls and are marked `live`, so they're
excluded from the default `pytest` run. To execute them:

    pytest -m live

They cost a few cents per run and take ~30-90 seconds each.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from app.extraction import extract_from_text  # noqa: E402
from app.gap_analysis import analyze as analyze_gaps  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.live
def test_invoice_fixture_extracts_richly():
    """The rich invoice transcript should produce a substantial Extracted +
    above-average coverage."""
    extracted = extract_from_text(_load("invoice_process_transcript.md"))

    assert extracted.project_name, "project_name must be populated"
    assert "invoice" in extracted.project_name.lower()
    assert len(extracted.applications) >= 2, "should pick up multiple apps"
    assert len(extracted.steps) >= 5, "should infer multiple steps"
    assert extracted.business_criticality in {"low", "medium", "high", "critical"}

    coverage = analyze_gaps(extracted)
    assert coverage.overall_pct >= 0.5, (
        f"rich fixture should score >= 0.5 coverage, got {coverage.overall_pct}"
    )


@pytest.mark.live
def test_expense_fixture_extracts_mid_quality():
    """The expense email thread is medium quality — covers the flow but
    leaves several details vague."""
    extracted = extract_from_text(_load("expense_approval_email_thread.md"))

    assert extracted.project_name
    assert any("concur" in a.name.lower() for a in extracted.applications), (
        "Concur should appear as an application"
    )
    assert len(extracted.steps) >= 3

    coverage = analyze_gaps(extracted)
    assert 0.3 <= coverage.overall_pct <= 0.85, (
        f"medium fixture should land mid-range, got {coverage.overall_pct}"
    )


@pytest.mark.live
def test_vague_fixture_extracts_sparsely():
    """The vague request should produce very thin Extracted + low coverage."""
    extracted = extract_from_text(_load("vague_request.md"))

    assert extracted.project_name, "even the vague fixture should produce a name"
    assert len(extracted.steps) <= 2, (
        f"vague fixture should produce <=2 inferred steps, got {len(extracted.steps)}"
    )

    coverage = analyze_gaps(extracted)
    assert coverage.overall_pct < 0.4, (
        f"vague fixture should score < 0.4 coverage, got {coverage.overall_pct}"
    )
