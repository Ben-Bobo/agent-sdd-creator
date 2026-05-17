"""Mode 1: Technology Fit report generation (markdown)."""

from __future__ import annotations

import os

from .llm import complete
from .models import Session
from .prompts import load_prompt


def generate_report(session: Session) -> str:
    if session.extracted is None:
        raise ValueError("session.extracted is required for technology fit")
    return complete(
        system=load_prompt("technology_fit"),
        messages=[
            {
                "role": "user",
                "content": session.extracted.model_dump_json(indent=2),
            }
        ],
        model=os.environ["MODEL_MAIN"],
        max_tokens=4096,
    ).strip()
