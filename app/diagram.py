"""Applications/systems diagram: Generates Mermaid, mmdc renders PNG."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .llm import complete
from .models import Extracted
from .prompts import load_prompt


def generate_mermaid(extracted: Extracted) -> str:
    raw = complete(
        system=load_prompt("diagram"),
        messages=[{"role": "user", "content": extracted.model_dump_json(indent=2)}],
        model=os.environ["MODEL_MAIN"],
        max_tokens=2048,
    )
    return _strip_fences(raw)


def render_png(mermaid_src: str, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mmdc_name = os.environ.get("MERMAID_CLI", "mmdc")
    mmdc_path = shutil.which(mmdc_name)
    if mmdc_path is None:
        raise RuntimeError(
            f"Mermaid CLI '{mmdc_name}' not found on PATH. "
            "Install with: npm install -g @mermaid-js/mermaid-cli"
        )

    # mmdc needs the source on disk. Use a tempfile so we don't litter the
    # session directory with a .mmd file we don't expose as an output.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".mmd", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(mermaid_src)
        mmd_path = Path(tmp.name)
    try:
        result = subprocess.run(
            [
                mmdc_path,
                "-i",
                str(mmd_path),
                "-o",
                str(out_path),
                "-b",
                "transparent",
                "-w",
                "1600",
            ],
            capture_output=True,
            text=True,
        )
    finally:
        mmd_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"mmdc failed (exit {result.returncode}).\nstderr:\n{result.stderr}\n"
            f"stdout:\n{result.stdout}"
        )
    return out_path


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()
