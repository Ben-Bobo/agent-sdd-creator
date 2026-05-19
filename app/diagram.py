"""Applications/systems diagram.

The LLM emits a structured ``_Diagram`` object (nodes + edges), and this
module deterministically renders it to Mermaid `flowchart LR` source. The
LLM never writes Mermaid syntax directly — that way labels with arbitrary
characters (parens, ampersands, slashes) can't crash the mmdc parser.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .llm import complete_json
from .models import Extracted
from .prompts import load_prompt


class _DiagramNode(BaseModel):
    id: str
    label: str
    subgraph: Literal["source", "processing", "output"]


class _DiagramEdge(BaseModel):
    from_id: str
    to_id: str
    label: str


class _Diagram(BaseModel):
    nodes: list[_DiagramNode]
    edges: list[_DiagramEdge]


def generate_mermaid(extracted: Extracted) -> str:
    diagram = complete_json(
        system=load_prompt("diagram"),
        messages=[{"role": "user", "content": extracted.model_dump_json(indent=2)}],
        schema=_Diagram,
        model=os.environ["MODEL_MAIN"],
        max_tokens=2048,
    )
    return _diagram_to_mermaid(diagram)


_ID_SAFE = re.compile(r"[^A-Za-z0-9_]")


def _safe_id(raw: str, fallback_index: int) -> str:
    """Strip non-alphanumeric chars from an id. If the result is empty (LLM
    returned garbage), generate a deterministic placeholder."""
    cleaned = _ID_SAFE.sub("", raw or "")
    return cleaned or f"n{fallback_index}"


def _sanitize_label(label: str) -> str:
    """Mermaid quoted labels accept anything except an unescaped double
    quote. Replace ``"`` with `'`. ``<br/>`` is preserved for line breaks."""
    return (label or "").replace('"', "'").strip()


def _diagram_to_mermaid(d: _Diagram) -> str:
    # Sanitize + dedupe node ids. If the LLM emitted two nodes with the same
    # cleaned id, suffix the duplicate so both remain in the diagram.
    seen_ids: set[str] = set()
    id_map: dict[int, str] = {}  # original index -> final id
    nodes_by_subgraph: dict[str, list[tuple[str, str]]] = {
        "source": [],
        "processing": [],
        "output": [],
    }
    for i, node in enumerate(d.nodes):
        candidate = _safe_id(node.id, i)
        final = candidate
        suffix = 2
        while final in seen_ids:
            final = f"{candidate}{suffix}"
            suffix += 1
        seen_ids.add(final)
        id_map[i] = final
        nodes_by_subgraph[node.subgraph].append((final, _sanitize_label(node.label)))

    lines: list[str] = ["flowchart LR"]
    pretty_name = {"source": "Source", "processing": "Processing", "output": "Output"}
    for sub_key in ("source", "processing", "output"):
        lines.append(f"    subgraph {pretty_name[sub_key]}")
        if nodes_by_subgraph[sub_key]:
            for nid, label in nodes_by_subgraph[sub_key]:
                lines.append(f'        {nid}["{label}"]')
        else:
            # Empty subgraph: placeholder so the operator sees what's missing.
            placeholder_id = f"_{sub_key}_empty"
            lines.append(f'        {placeholder_id}["(none)"]')
        lines.append("    end")

    # Drop edges that reference an id we didn't define (orphan edges would
    # silently render as new auto-named nodes, polluting the diagram).
    for edge in d.edges:
        from_final = next(
            (id_map[i] for i, n in enumerate(d.nodes) if _safe_id(n.id, i) == _safe_id(edge.from_id, -1)),
            None,
        )
        to_final = next(
            (id_map[i] for i, n in enumerate(d.nodes) if _safe_id(n.id, i) == _safe_id(edge.to_id, -1)),
            None,
        )
        if from_final is None or to_final is None:
            continue
        edge_label = _sanitize_label(edge.label)
        if edge_label:
            lines.append(f"    {from_final} -->|{edge_label}| {to_final}")
        else:
            lines.append(f"    {from_final} --> {to_final}")

    return "\n".join(lines)


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
