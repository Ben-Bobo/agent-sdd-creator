"""Guidance helper for tokenizing the operator's SDD template.

This script DOES NOT modify any docx file. It prints the list of placeholders
from prompts/template_tokens.md so you can open your template in Word, type
each `{{token}}` into the correct cell, and save the result to
`templates/Automation_SDD_template.docx`.

If your starting docx matches the layout described in template_tokens.md, the
one-off bootstrap done during Ticket 7 already produced a tokenized template at
that path. This script is for re-tokenizing after the operator changes the
SDD layout.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    doc_path = Path(__file__).resolve().parent.parent / "prompts" / "template_tokens.md"
    if not doc_path.is_file():
        print(f"missing: {doc_path}", file=sys.stderr)
        return 1
    print(doc_path.read_text(encoding="utf-8"))
    print()
    print("--- INSTRUCTIONS ---")
    print("1. Open your starting docx in Word.")
    print("2. For each section above, type the listed {{token}} into the matching cell.")
    print("3. For repeating sections (applications, errors, reports), keep ONE template")
    print("   row containing the {{prefix.field}} tokens. Delete any extra empty rows.")
    print("4. Add a paragraph containing {{applications_diagram}} where the diagram should go.")
    print("5. Add a paragraph containing {{steps}} where the step-by-step list should go.")
    print("6. Save As: templates/Automation_SDD_template.docx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
