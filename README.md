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

## Bringing your own SDD template

`templates/Automation_SDD_template.docx` is the docx the generator fills. It's already tokenized to match the included sample SDD layout. If you want to use your own template instead:

1. Save your starting docx somewhere outside `templates/` (e.g. the repo root).
2. Run `python scripts/prepare_template.py` to print the list of `{{tokens}}` and where each one belongs (this script just prints guidance — it doesn't modify your docx).
3. In Word, paste each token into the matching cell. For the Applications, Errors, and Reports tables, keep one template data row with the `{{prefix.field}}` tokens; delete any extra empty rows (the filler clones the template row once per item).
4. Add a paragraph containing `{{applications_diagram}}` where the diagram should go, and a paragraph containing `{{steps}}` where the step-by-step flow should go.
5. Save the tokenized result to `templates/Automation_SDD_template.docx`, overwriting the shipped example.

Token names and locations are documented in `prompts/template_tokens.md`.

## Status

v1 in progress. See `tasks.md` for the ticket plan and `spec.md` for the full design.
