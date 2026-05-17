"""Fill the SDD template from an Extracted object + a rendered diagram PNG.

The template at `templates/Automation_SDD_template.docx` is tokenized with
`{{name}}` placeholders. See `prompts/template_tokens.md` for the full token
list. Three kinds of fill operations happen here:

  1. **Repeating rows.** Tables whose data row contains `{{prefix.field}}`
     tokens (`app.*`, `err.*`, `report.*`) get the row cloned once per item.
  2. **Anchor paragraphs.** A paragraph containing `{{applications_diagram}}`
     is replaced by an inline PNG. A paragraph containing `{{steps}}` is
     replaced by one block of paragraphs per step.
  3. **Scalar tokens.** Everything else is a straight `{{name}}` → string
     replacement, with `[TBD - <reason>]` for missing values.
"""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Iterable, Iterator

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.text.paragraph import Paragraph

from .models import Extracted, Step

TOKEN_RE = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


def _tbd(reason: str = "missing") -> str:
    return f"[TBD - {reason}]"


def fill_template(
    extracted: Extracted,
    diagram_png_path: Path | None,
    out_path: Path,
    template_path: Path | None = None,
) -> Path:
    template_path = template_path or Path("templates/Automation_SDD_template.docx")
    doc = Document(str(template_path))

    # Repeating rows first — they add new XML and shift indices.
    for table in doc.tables:
        _fill_repeating_rows(table, "app", extracted.applications)
        _fill_repeating_rows(table, "err", extracted.known_errors)
        _fill_repeating_rows(table, "report", extracted.reports)

    # Steps block.
    steps_anchor = _find_paragraph_with_token(doc, "steps")
    if steps_anchor is not None:
        _render_steps_block(steps_anchor, extracted.steps)

    # Diagram embed.
    diagram_anchor = _find_paragraph_with_token(doc, "applications_diagram")
    if diagram_anchor is not None:
        if diagram_png_path is not None and Path(diagram_png_path).is_file():
            _embed_diagram(diagram_anchor, Path(diagram_png_path))
        else:
            _set_paragraph_text(diagram_anchor, _tbd("diagram PNG not provided"))

    # Scalar tokens last.
    scalars = _build_scalar_values(extracted)
    for para in _iter_all_paragraphs(doc):
        _replace_simple_tokens(para, scalars)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


def _build_scalar_values(ex: Extracted) -> dict[str, str]:
    def s(val, reason: str = "missing") -> str:
        if val is None or val == "":
            return _tbd(reason)
        if isinstance(val, list):
            return "; ".join(str(x) for x in val) if val else _tbd(reason)
        return str(val)

    return {
        "project_name": s(ex.project_name, "project name missing"),
        "summary": s(ex.summary, "summary missing"),
        "business_owner": s(ex.business_owner, "owner missing"),
        "flow_diagrams_location": _tbd("populate manually"),
        "jira_project": _tbd("populate manually"),
        "automation_tools": s(ex.automation_tools),
        "btp_services": s(ex.btp_services),
        "document_processing": s(ex.document_processing),
        "new_sdks_objects": s(ex.new_sdks_objects),
        "artificial_intelligence": s(ex.artificial_intelligence),
        "credential_management": s(ex.credential_management),
        "tool_selection_rationale": s(ex.tool_selection_rationale),
        "business_criticality": s(ex.business_criticality),
        "complexity_score": s(ex.complexity_score),
        "accepted_failure_threshold": s(ex.accepted_failure_threshold),
        "rerun_on_failure": s(ex.rerun_on_failure),
        "schedule_frequency": s(ex.schedule_frequency),
        "bot_utilization_pct": s(ex.bot_utilization_pct),
        "triggers": s(ex.triggers),
    }


def _iter_all_paragraphs(doc) -> Iterator[Paragraph]:
    yield from doc.paragraphs
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def _paragraph_text(para: Paragraph) -> str:
    return "".join(r.text for r in para.runs)


def _set_paragraph_text(para: Paragraph, text: str) -> None:
    for r in para.runs[1:]:
        r._element.getparent().remove(r._element)
    if para.runs:
        para.runs[0].text = text
    else:
        para.add_run(text)


def _replace_simple_tokens(para: Paragraph, values: dict[str, str]) -> None:
    text = _paragraph_text(para)
    if "{{" not in text:
        return
    new_text = TOKEN_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)
    if new_text == text:
        return
    _set_paragraph_text(para, new_text)


def _find_paragraph_with_token(doc, token_name: str) -> Paragraph | None:
    target = "{{" + token_name + "}}"
    for para in _iter_all_paragraphs(doc):
        if target in _paragraph_text(para):
            return para
    return None


def _fill_repeating_rows(table, prefix: str, items: Iterable) -> None:
    pattern = re.compile(r"\{\{" + re.escape(prefix) + r"\.[a-zA-Z0-9_]+\}\}")
    template_rows = [
        row for row in table.rows
        if pattern.search(" ".join(c.text for c in row.cells))
    ]
    if not template_rows:
        return

    proto_xml = template_rows[0]._element
    parent = proto_xml.getparent()
    proto_index = list(parent).index(proto_xml)

    items_list = list(items)
    new_row_xmls = []
    for item in items_list:
        cloned = deepcopy(proto_xml)
        for t in cloned.iter(qn("w:t")):
            if t.text and "{{" in t.text:
                t.text = TOKEN_RE.sub(
                    lambda m: _resolve_item_token(m.group(1), prefix, item),
                    t.text,
                )
        new_row_xmls.append(cloned)

    for offset, nr in enumerate(new_row_xmls):
        parent.insert(proto_index + 1 + offset, nr)

    for row in template_rows:
        parent.remove(row._element)


def _resolve_item_token(token: str, prefix: str, item) -> str:
    expected = prefix + "."
    if not token.startswith(expected):
        return "{{" + token + "}}"
    field = token[len(expected):]
    val = getattr(item, field, None)
    if val is None or val == "":
        return _tbd(f"{prefix}.{field}")
    if isinstance(val, list):
        return "; ".join(str(x) for x in val) if val else _tbd(f"{prefix}.{field}")
    return str(val)


def _embed_diagram(anchor: Paragraph, png_path: Path) -> None:
    for r in anchor.runs:
        r.text = ""
    if anchor.runs:
        for r in anchor.runs[1:]:
            r._element.getparent().remove(r._element)
        run = anchor.runs[0]
    else:
        run = anchor.add_run()
    run.add_picture(str(png_path), width=Inches(6.5))


def _render_steps_block(anchor: Paragraph, steps: list[Step]) -> None:
    if not steps:
        _set_paragraph_text(anchor, _tbd("no steps extracted"))
        return

    lines: list[str] = []
    for step in steps:
        lines.append(f"Step {step.number}: {step.summary}")

        if step.action_detail:
            for sub in step.action_detail.splitlines():
                lines.append(f"    {sub}" if sub.strip() else "")
        else:
            lines.append(f"    {_tbd('exact click-by-click / API sequence missing — ask the business')}")

        if step.decision_logic:
            lines.append(f"    Decision rule: {step.decision_logic}")
        if step.exception_paths:
            lines.append(f"    Exception handling: {'; '.join(step.exception_paths)}")
        if step.success_criterion:
            lines.append(f"    Done when: {step.success_criterion}")

        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()

    _set_paragraph_text(anchor, lines[0])
    cursor_xml = anchor._element
    for line in lines[1:]:
        new_p = deepcopy(cursor_xml)
        for child in list(new_p):
            if child.tag == qn("w:r"):
                new_p.remove(child)
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = line
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        new_p.append(r)
        cursor_xml.addnext(new_p)
        cursor_xml = new_p
