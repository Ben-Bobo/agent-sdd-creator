"""Mode 2: SDD generation orchestrator.

Pipeline:
  1. Ensure coverage is computed.
  2. Run a narrative-enrichment pass (summary + tool_selection_rationale).
  3. Generate the Mermaid applications diagram, render PNG (sibling .mmd).
  4. Fill the docx template.
  5. Write gaps.md (markdown bullets of partial/missing rubric items).
  6. Persist session with phase = "generated".
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

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
    tool_selection_rationale: str


def generate_sdd(session: Session) -> list[str]:
    if session.extracted is None:
        raise ValueError("session.extracted is required before SDD generation")

    if session.coverage is None:
        session.coverage = analyze_gaps(session.extracted)

    narrative = _run_narrative(session.extracted, session.coverage)
    session.extracted.summary = narrative.summary
    session.extracted.tool_selection_rationale = narrative.tool_selection_rationale

    session_dir = _session_dir(session.session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    mermaid_src = generate_mermaid(session.extracted)
    session.extracted.applications_diagram_mermaid = mermaid_src
    png_path = session_dir / "applications_diagram.png"
    render_png(mermaid_src, png_path)

    docx_path = session_dir / "sdd.docx"
    fill_template(session.extracted, png_path, docx_path)

    gaps_path = session_dir / "gaps.md"
    gaps_path.write_text(
        _render_gaps_md(session.extracted, session.coverage),
        encoding="utf-8",
    )

    files = ["sdd.docx", "applications_diagram.png",
             "applications_diagram.mmd", "gaps.md"]
    session.generated_files = files
    session.phase = "generated"
    session_store.save_session(session)
    return files


def _session_dir(session_id: str) -> Path:
    return Path(os.environ.get("SESSIONS_DIR", "./sessions")) / session_id


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


def _render_gaps_md(extracted: Extracted, coverage: Coverage) -> str:
    project = extracted.project_name or "this process"
    lines: list[str] = [
        f"# Open questions for the business — {project}",
        "",
        "These details are missing or only partially covered in the source material. "
        "Forward to the relevant stakeholder before development starts.",
        "",
        f"_Overall coverage: {coverage.overall_pct:.0%}_",
        "",
    ]

    by_step: dict[str, list] = defaultdict(list)
    overall: list = []
    for item in coverage.items:
        if item.status == "covered":
            continue
        if item.id.startswith("step_"):
            step_key = item.id.split(".", 1)[0]  # e.g. "step_3"
            by_step[step_key].append(item)
        else:
            overall.append(item)

    if by_step:
        lines.append("## Per-step gaps")
        lines.append("")
        step_by_number = {f"step_{s.number}": s for s in extracted.steps}
        for step_key in sorted(by_step.keys(), key=_step_sort_key):
            step = step_by_number.get(step_key)
            heading = (f"### {step_key} — {step.summary}"
                       if step else f"### {step_key}")
            lines.append(heading)
            for item in by_step[step_key]:
                if item.question:
                    lines.append(f"- **{item.category} ({item.status}):** {item.question}")
            lines.append("")

    if overall:
        lines.append("## Overall")
        lines.append("")
        for item in overall:
            if item.question:
                lines.append(f"- **{item.category} ({item.status}):** {item.question}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _step_sort_key(step_key: str) -> int:
    try:
        return int(step_key.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0
