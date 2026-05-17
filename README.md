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

## Using a different LLM backend

The app talks to models through [LiteLLM](https://docs.litellm.ai), so any provider LiteLLM supports works — Anthropic direct, Azure, Bedrock, Ollama, or any OpenAI-compatible corporate gateway. Switch by editing `.env` only; no code changes.

For example, to route through an internal OpenAI-compatible gateway:

```
OPENAI_API_BASE=https://gateway.yourcompany.internal/v1
OPENAI_API_KEY=<gateway-token>
MODEL_MAIN=openai/internal-claude-sonnet
MODEL_CHEAP=openai/internal-claude-haiku
```

The model string's prefix (`anthropic/`, `openai/`, `bedrock/`, …) tells LiteLLM how to route. App code only references the semantic roles `MODEL_MAIN` and `MODEL_CHEAP`.

## Status

v1 in progress. See `tasks.md` for the ticket plan and `spec.md` for the full design.
