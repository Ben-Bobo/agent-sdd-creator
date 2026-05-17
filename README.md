# Automation SDD Builder

A local web app that helps a business analyst turn fuzzy business descriptions of a process into one of two outputs: a **Technology Fit Report** (markdown — should we automate this, and how?) or a fully filled **Software Design Document** (`.docx` matching the operator's template, with an embedded applications diagram and a separate `gaps.md` of follow-up questions). Accepts both drop-in source material (transcripts, emails) and a guided chat flow.

## Quickstart

Prerequisites: Python 3.11+, Node 18+, [`uv`](https://docs.astral.sh/uv/), and `@mermaid-js/mermaid-cli` (`npm install -g @mermaid-js/mermaid-cli`).

```powershell
# Clone, then from the repo root:
uv venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
uv pip install -e .

# Configure your LLM access:
Copy-Item .env.example .env       # macOS/Linux: cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY (from console.anthropic.com).

# Run:
uvicorn app.main:app --reload
# Visit http://127.0.0.1:8000/
```

## Status

v1 in progress. See `tasks.md` for the ticket plan and `spec.md` for the full design.
