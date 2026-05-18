"""SDD generation orchestrator.

Pipeline:
  1. (Chat mode only) Re-run extraction with ``MODEL_MAIN`` over the full
     transcript. Per-turn extraction during chat uses ``MODEL_CHEAP`` for
     speed; this pass restores full quality before any downstream
     generation. Drop-in mode skips this because its initial extraction
     already ran on ``MODEL_MAIN``.
  2. Ensure coverage is computed.
  3. Run a narrative-enrichment pass (summary + rerun + improvements + AI).
  4. Generate the Mermaid applications diagram and render it to PNG.
  5. Fill the docx template (embeds the PNG inline) and delete the PNG.
  6. Persist session with phase = "generated".

The only output exposed to the user is ``sdd.docx``. The diagram source
and the PNG are intermediate artifacts and are not kept on disk.

``generate_sdd`` is a generator: it yields ``("status", str)`` events at
phase boundaries so callers can stream progress to the UI, and a final
``("done", list[str])`` event with the generated filenames.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel

from . import session as session_store
from .chat import _build_chat_context
from .diagram import generate_mermaid, render_png
from .docx_filler import fill_template
from .extraction import extract_from_text
from .gap_analysis import analyze as analyze_gaps
from .llm import complete_json
from .models import Coverage, Extracted, Session
from .prompts import load_prompt


class _StepDesignNote(BaseModel):
    step_number: int
    note: str


class _Narrative(BaseModel):
    summary: str
    rerun_on_failure: str
    artificial_intelligence: list[str]
    step_design_notes: list[_StepDesignNote]


def generate_sdd(session: Session) -> Iterator[tuple[str, Any]]:
    if session.extracted is None:
        raise ValueError("session.extracted is required before SDD generation")

    # Chat-mode sessions: per-turn extraction used MODEL_CHEAP, so re-extract
    # with the main model once before we build the final doc.
    if session.input_style == "chat":
        yield "status", "Final pass on your description"
        session.extracted = extract_from_text(_build_chat_context(session))
        # Coverage is derived from Extracted; recompute against the fresh one.
        session.coverage = None

    if session.coverage is None:
        yield "status", "Running gap analysis"
        session.coverage = analyze_gaps(session.extracted)

    yield "status", "Drafting narrative sections"
    narrative = _run_narrative(session.extracted, session.coverage)
    session.extracted.summary = narrative.summary
    session.extracted.rerun_on_failure = narrative.rerun_on_failure
    session.extracted.artificial_intelligence = narrative.artificial_intelligence

    # Apply per-step design notes back onto the extracted steps. Unknown step
    # numbers are ignored defensively (the LLM occasionally invents one).
    notes_by_step = {n.step_number: n.note for n in narrative.step_design_notes}
    for step in session.extracted.steps:
        if step.number in notes_by_step and notes_by_step[step.number].strip():
            step.design_note = notes_by_step[step.number].strip()

    session_dir = session_store.session_dir(session.session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    yield "status", "Generating applications diagram"
    mermaid_src = generate_mermaid(session.extracted)
    session.extracted.applications_diagram_mermaid = mermaid_src

    yield "status", "Rendering diagram image"
    png_path = session_dir / "applications_diagram.png"
    render_png(mermaid_src, png_path)

    yield "status", "Filling docx template"
    docx_path = session_dir / "sdd.docx"
    fill_template(session.extracted, png_path, docx_path)

    # PNG is embedded inside the .docx; the standalone file isn't needed.
    png_path.unlink(missing_ok=True)

    files = ["sdd.docx"]
    session.generated_files = files
    session.phase = "generated"
    session_store.save_session(session)
    yield "done", files


def _run_narrative(extracted: Extracted, coverage: Coverage) -> _Narrative:
    body = (
        "## Extracted\n\n"
        f"{extracted.model_dump_json(indent=2)}\n\n"
        "## Coverage\n\n"
        f"{coverage.model_dump_json(indent=2)}\n"
    )
    return complete_json(
        system=load_prompt("sdd_narrative"),
        messages=[{"role": "user", "content": body}],
        schema=_Narrative,
        model=os.environ["MODEL_MAIN"],
        max_tokens=2048,
    )
