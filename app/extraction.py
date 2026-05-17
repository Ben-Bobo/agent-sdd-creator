"""Extraction pass: raw text in, validated Extracted out."""
from __future__ import annotations

import os

from .llm import complete_json
from .models import Extracted
from .prompts import load_prompt


def extract_from_text(raw_text: str) -> Extracted:
    return complete_json(
        system=load_prompt("extract"),
        messages=[{"role": "user", "content": raw_text}],
        schema=Extracted,
        model=os.environ["MODEL_MAIN"],
        max_tokens=8192,
    )
