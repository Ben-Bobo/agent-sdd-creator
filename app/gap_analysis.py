"""Gap analysis: score Extracted against the developer-readiness rubric."""
from __future__ import annotations

import os
from collections import defaultdict

from .llm import complete_json
from .models import Coverage, CoverageItem, Extracted
from .prompts import load_prompt

_STATUS_SCORE = {"covered": 1.0, "partial": 0.5, "missing": 0.0}


def analyze(extracted: Extracted) -> Coverage:
    system = load_prompt("gap_analysis") + "\n\n" + load_prompt("rubric")
    raw = complete_json(
        system=system,
        messages=[{"role": "user", "content": extracted.model_dump_json(indent=2)}],
        schema=Coverage,
        model=os.environ["MODEL_MAIN"],
        max_tokens=8192,
    )
    return _with_recomputed_totals(raw.items)


def _with_recomputed_totals(items: list[CoverageItem]) -> Coverage:
    if not items:
        return Coverage(overall_pct=0.0, by_category={}, items=[])

    overall_pct = sum(_STATUS_SCORE[i.status] for i in items) / len(items)

    by_cat_sum: dict[str, float] = defaultdict(float)
    by_cat_count: dict[str, int] = defaultdict(int)
    for i in items:
        by_cat_sum[i.category] += _STATUS_SCORE[i.status]
        by_cat_count[i.category] += 1
    by_category = {
        cat: by_cat_sum[cat] / by_cat_count[cat] for cat in by_cat_sum
    }

    return Coverage(
        overall_pct=round(overall_pct, 4),
        by_category={k: round(v, 4) for k, v in by_category.items()},
        items=items,
    )
