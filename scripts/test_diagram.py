"""Quick visual check for app/diagram.py.

Pipeline: load the invoice fixture text → run extraction → generate Mermaid →
render PNG. Outputs to evals/output/invoice_diagram.{mmd,png} so you can eyeball.

Requires a working LLM config (.env with ANTHROPIC_API_KEY etc.) and a working
mmdc on PATH.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.diagram import generate_mermaid, render_png  # noqa: E402
from app.extraction import extract_from_text  # noqa: E402


def main() -> int:
    fixture = Path("evals/fixtures/invoice_process_transcript.md")
    if not fixture.is_file():
        print(f"missing fixture: {fixture}", file=sys.stderr)
        return 1

    print(f"Extracting from {fixture}...")
    extracted = extract_from_text(fixture.read_text(encoding="utf-8"))
    print(f"  apps: {[a.name for a in extracted.applications]}")

    print("Generating Mermaid...")
    mermaid_src = generate_mermaid(extracted)
    print("--- Mermaid source ---")
    print(mermaid_src)
    print("--- end ---")

    out_png = Path("evals/output/invoice_diagram.png")
    print(f"Rendering PNG → {out_png}...")
    rendered = render_png(mermaid_src, out_png)
    print("Done.")
    print(f"  png: {rendered.resolve()}")
    print(f"  mmd: {rendered.with_suffix('.mmd').resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
