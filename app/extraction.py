"""Extraction pass: raw text in, validated Extracted out."""

from __future__ import annotations

import os

from .llm import complete_json
from .models import Extracted
from .prompts import load_prompt


def extract_from_text(raw_text: str, model: str | None = None) -> Extracted:
    """Run extraction. ``model`` defaults to ``MODEL_MAIN`` (Sonnet-class) for
    final-quality runs; pass ``MODEL_CHEAP`` (Haiku-class) for per-turn
    background passes during chat, where speed matters more than perfect
    coverage of edge cases."""
    return complete_json(
        system=load_prompt("extract"),
        messages=[{"role": "user", "content": raw_text}],
        schema=Extracted,
        model=model or os.environ["MODEL_MAIN"],
        max_tokens=8192,
    )
