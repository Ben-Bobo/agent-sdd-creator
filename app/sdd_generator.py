"""SDD generation orchestrator.

Pipeline:
  1. Ensure coverage is computed.
  2. Run a narrative-enrichment pass (summary + tool_selection_rationale).
  3. Generate the Mermaid applications diagram and render it to PNG.
  4. Fill the docx template (embeds the PNG inline) and delete the PNG.
  5. Persist session with phase = "generated".

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
from .diagram import generate_mermaid, render_png
from .docx_filler import fill_template
from .gap_analysis import analyze as analyze_gaps
from .llm import complete_json
from .models import Coverage, Extracted, Session
from .prompts import load_prompt


class _Narrative(BaseModel):
    summary: str
    rerun_on_failure: str
    artificial_intelligence: list[str]
    design_improvements: list[str]


def generate_sdd(session: Session) -> Iterator[tuple[str, Any]]:
    if session.extracted is None:
        raise ValueError("session.extracted is required before SDD generation")

    if session.coverage is None:
        yield "status", "Running gap analysis"
        session.coverage = analyze_gaps(session.extracted)

    yield "status", "Drafting narrative sections"
    narrative = _run_narrative(session.extracted, session.coverage)
    session.extracted.summary = narrative.summary
    session.extracted.rerun_on_failure = narrative.rerun_on_failure
    session.extracted.artificial_intelligence = narrative.artificial_intelligence
    session.extracted.design_improvements = narrative.design_improvements

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
