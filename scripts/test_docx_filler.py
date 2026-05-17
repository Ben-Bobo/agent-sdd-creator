"""End-to-end check of app.docx_filler.

Loads the Extracted from an existing session, uses the rendered diagram from
scripts/test_diagram.py if present, fills the template, and prints a summary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.docx_filler import fill_template
from app.models import Extracted


def _pick_session() -> Path:
    sessions = Path("sessions")
    if not sessions.is_dir():
        raise SystemExit("no sessions/ directory yet — run /api/dropin first")
    candidates = [p / "state.json" for p in sessions.iterdir() if p.is_dir()]
    candidates = [p for p in candidates if p.is_file()]
    # Prefer the session with the richest `extracted` (most steps).
    scored = []
    for p in candidates:
        state = json.loads(p.read_text(encoding="utf-8"))
        ex = state.get("extracted") or {}
        scored.append((len(ex.get("steps") or []), p))
    scored.sort(reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    raise SystemExit("no session with extracted.steps populated yet")


def main() -> int:
    session_path = _pick_session()
    print(f"Using session: {session_path}")
    state = json.loads(session_path.read_text(encoding="utf-8"))
    extracted = Extracted.model_validate(state["extracted"])
    print(f"  project_name: {extracted.project_name}")
    print(f"  applications: {[a.name for a in extracted.applications]}")
    print(f"  steps:        {len(extracted.steps)}")

    diagram = Path("evals/output/invoice_diagram.png")
    if not diagram.is_file():
        print(f"  diagram not found at {diagram} (run scripts/test_diagram.py first)")
        diagram = None
    else:
        print(f"  diagram:      {diagram}")

    out_path = Path("evals/output/filled_sdd.docx")
    print(f"\nFilling template -> {out_path}")
    written = fill_template(extracted, diagram, out_path)
    print(f"Done. {written.resolve()}  ({written.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
