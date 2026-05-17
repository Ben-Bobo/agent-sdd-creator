# Tasks — Automation SDD Builder

Tickets are in dependency order. Work them top to bottom. Each is sized to be a single Claude Code session. Stop after each ticket and verify before moving on.

**Conventions:**
- Treat the `spec.md` as the source of truth. If something here disagrees with spec.md, ask.
- Don't add features beyond the ticket. Park ideas in `NOTES.md` at the repo root.
- After each ticket: run the project, confirm the acceptance criteria, then commit with a clear message.
- Python 3.11+, all work happens inside the `.venv/` created in Ticket 0.

---

## Ticket 0 — Environment setup

**Goal:** A clean, isolated Python environment + all external CLIs verified before any code is written. Run this once.

**Do:**

1. **Check Python version:**
   ```bash
   python --version    # or python3 --version
   ```
   Must be 3.11 or higher. If not, stop and tell the operator to install a newer Python (e.g., via `pyenv`, `uv python install 3.12`, or system package manager).

2. **Check for `uv`** (preferred — much faster than pip):
   ```bash
   uv --version
   ```
   If not installed, suggest the operator install it:
   - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - macOS via Homebrew: `brew install uv`
   - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

   Falling back to `python -m venv` + `pip` is acceptable but slower. Note which one was used in the commit message.

3. **Create and activate the virtual environment** at the repo root:
   - With uv: `uv venv` (creates `.venv/` using the current Python)
   - With stdlib: `python -m venv .venv`
   - Then activate:
     - macOS / Linux: `source .venv/bin/activate`
     - Windows: `.venv\Scripts\activate`

   **Verify activation:** `which python` (macOS/Linux) or `where python` (Windows) should point inside `.venv/`. If it doesn't, stop and fix before continuing.

4. **Verify Node + Mermaid CLI:**
   ```bash
   node --version          # 18+
   mmdc --version          # should print a version
   ```
   If `mmdc` is missing: `npm install -g @mermaid-js/mermaid-cli`. If `node` is missing, stop and tell the operator to install Node 18+.

5. **Create `.gitignore` at repo root** (covers everything we'll need):
   ```
   .env
   .venv/
   sessions/
   __pycache__/
   *.pyc
   dist/
   *.egg-info/
   .pytest_cache/
   .ruff_cache/
   /examples/private/
   ```

6. **Create `.env` from a fresh `.env.example`** (`.env.example` is committed, `.env` is not):

   `.env.example`:
   ```
   # LLM access via LiteLLM
   ANTHROPIC_API_KEY=your-key-here
   MODEL_MAIN=anthropic/claude-sonnet-4-6
   MODEL_CHEAP=anthropic/claude-haiku-4-5-20251001

   # App config
   SESSIONS_DIR=./sessions
   TEMPLATE_PATH=./templates/Automation_SDD_template.docx
   MERMAID_CLI=mmdc

   # Future: corporate gateway (uncomment when ready)
   # OPENAI_API_BASE=https://gateway.yourcompany.internal/v1
   # OPENAI_API_KEY=<gateway-token>
   # MODEL_MAIN=openai/internal-claude-sonnet
   # MODEL_CHEAP=openai/internal-claude-haiku
   ```

   Then: `cp .env.example .env` and remind the operator to fill in their real `ANTHROPIC_API_KEY` before Ticket 3. (API key from https://console.anthropic.com — separate from any Claude.ai subscription.)

7. **Initialize git** if not already done:
   ```bash
   git init
   git add .gitignore .env.example
   git commit -m "Ticket 0: environment scaffolding"
   ```

8. **Create a sanity-check script** at `scripts/check_env.py`:
   ```python
   """Quick sanity check that the environment is wired correctly."""
   import os, shutil, sys
   from pathlib import Path

   def main():
       checks = []
       checks.append(("Python >= 3.11", sys.version_info >= (3, 11)))
       checks.append((".venv active", sys.prefix != sys.base_prefix))
       checks.append(("mmdc on PATH", shutil.which("mmdc") is not None))
       checks.append((".env file present", Path(".env").is_file()))
       env_key = os.environ.get("ANTHROPIC_API_KEY", "")
       checks.append(("ANTHROPIC_API_KEY set",
                      env_key and env_key != "your-key-here"))
       all_pass = all(ok for _, ok in checks)
       for label, ok in checks:
           print(f"  {'✓' if ok else '✗'}  {label}")
       sys.exit(0 if all_pass else 1)

   if __name__ == "__main__":
       main()
   ```
   Run it: `python scripts/check_env.py`. All checks except `ANTHROPIC_API_KEY set` should pass at this point (the key gets filled in by the operator before Ticket 3).

**Acceptance:**
- `which python` points inside `.venv/`
- `mmdc --version` works
- `python scripts/check_env.py` shows ✓ for everything except possibly the API key check (which is fine until Ticket 3)
- `.gitignore`, `.env.example`, `.env` all exist at repo root, `.env` is gitignored
- A first commit exists

**Notes for Claude Code:**
- Do NOT install any Python packages yet — that's Ticket 1's job. Just create the venv and verify external tools.
- If the operator already has a venv in `.venv/` from a previous attempt, ask before deleting it.
- If `uv` is unavailable and the operator wants to install it, run the install command for their OS and re-check.

---

## Ticket 1 — Project scaffolding

**Goal:** Empty but runnable FastAPI app, project structure in place, README stub.

**Prerequisite:** Ticket 0 done, venv active.

**Do:**
1. Confirm venv is active: `which python` should point inside `.venv/`. If not, activate and stop to verify before proceeding.
2. Create the directory structure from `spec.md` → "File layout."
3. `pyproject.toml` with deps: `fastapi`, `uvicorn[standard]`, `litellm`, `pydantic>=2`, `python-docx`, `jinja2`, `python-dotenv`, `python-multipart`, `pytest`.
4. Install deps into the venv:
   - With uv: `uv pip install -e .` (or `uv sync` if using `uv init` style)
   - With pip: `pip install -e .`
5. `.gitignore`: already created in Ticket 0; verify it's in place.
6. `app/main.py`: FastAPI app with one route `GET /` that returns "Automation SDD Builder — running" as plain text. Configure uvicorn entry point.
7. `README.md` skeleton: title, one-paragraph description (pulled from spec "What this is"), Quickstart (install, set env, run), Status (v1 in progress).
8. Verify `uvicorn app.main:app --reload` starts and the root route responds.

**Acceptance:** server starts inside the venv, root route returns the string, no errors in console. `pip list` (or `uv pip list`) shows the installed deps.

---

## Ticket 2 — Session model and storage

**Goal:** Sessions as JSON files on disk, with a clean read/write API.

**Do:**
1. `app/models.py`: define all Pydantic models from `spec.md` → "Extraction schema," plus a `Session` model matching "Session schema." Use Pydantic v2.
2. `app/session.py`:
   - `create_session(mode, input_style) -> Session`
   - `load_session(session_id) -> Session`
   - `save_session(session: Session) -> None`
   - Sessions stored at `SESSIONS_DIR/<session_id>/state.json`. Create the directory on first save. Use `model_dump_json(indent=2)` for human-readable JSON.
3. `app/main.py`: add `POST /api/session` (body: `{mode, input_style}`) returning `{session_id}`, and `GET /api/session/{id}` returning the session JSON.
4. Quick manual test via `curl` documented in a `CURL_EXAMPLES.md` at repo root.

**Acceptance:** can create a session via curl, find the JSON file on disk, fetch the session via the GET route.

---

## Ticket 3 — LLM client (LiteLLM-based)

**Goal:** A small, focused LLM module that works with Anthropic today and any LiteLLM-supported backend (including OpenAI-compatible corporate gateways) later — by changing config, not code.

**Why LiteLLM:** the operator will eventually use an internal LLM gateway at work. LiteLLM handles ~100 providers behind one interface, including any OpenAI-compatible endpoint. No custom adapters needed.

**Do:**

1. Add `litellm` to deps in `pyproject.toml`.

2. **`app/llm.py`** — one module, plain functions, no classes:

   ```python
   import json
   import litellm
   from pydantic import BaseModel, ValidationError
   from typing import Type, TypeVar, AsyncIterator
   import os

   T = TypeVar("T", bound=BaseModel)

   # Quiet down LiteLLM's default logging
   litellm.suppress_debug_info = True

   def complete(system: str, messages: list[dict], model: str,
                max_tokens: int = 4096) -> str:
       resp = litellm.completion(
           model=model,
           messages=[{"role": "system", "content": system}] + messages,
           max_tokens=max_tokens,
       )
       return resp.choices[0].message.content

   def complete_json(system: str, messages: list[dict],
                     schema: Type[T], model: str,
                     max_tokens: int = 4096, max_retries: int = 2) -> T:
       """Ask the model for strict JSON and parse it against `schema`.
       Retry on validation failure with a feedback turn."""
       schema_json = json.dumps(schema.model_json_schema(), indent=2)
       system_with_schema = (
           f"{system}\n\n"
           f"Respond with ONLY valid JSON matching this schema. "
           f"No markdown fences, no commentary.\n\n"
           f"Schema:\n{schema_json}"
       )
       conv = list(messages)
       last_error = None
       for attempt in range(max_retries + 1):
           raw = complete(system_with_schema, conv, model, max_tokens)
           try:
               # Strip accidental fences just in case
               cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
               return schema.model_validate_json(cleaned)
           except (ValidationError, ValueError) as e:
               last_error = e
               conv.append({"role": "assistant", "content": raw})
               conv.append({"role": "user", "content":
                   f"Your output failed validation: {e}. "
                   f"Return ONLY valid JSON matching the schema. No prose."})
       raise RuntimeError(f"complete_json failed after {max_retries+1} attempts: {last_error}")

   async def stream(system: str, messages: list[dict], model: str,
                    max_tokens: int = 4096) -> AsyncIterator[str]:
       resp = await litellm.acompletion(
           model=model,
           messages=[{"role": "system", "content": system}] + messages,
           max_tokens=max_tokens,
           stream=True,
       )
       async for chunk in resp:
           delta = chunk.choices[0].delta.content
           if delta:
               yield delta
   ```

3. **Prompts loader** — `app/prompts.py`:
   ```python
   from pathlib import Path

   PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

   def load_prompt(name: str) -> str:
       return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
   ```

4. **Stub prompt** — `prompts/system_chat.md` with a one-line placeholder. Real prompts come in later tickets.

5. **Env config** — `.env.example`:
   ```
   # For personal use with your own Anthropic API key:
   ANTHROPIC_API_KEY=sk-ant-...
   MODEL_MAIN=anthropic/claude-sonnet-4-6
   MODEL_CHEAP=anthropic/claude-haiku-4-5-20251001

   # Later, for a corporate OpenAI-compatible gateway:
   # OPENAI_API_BASE=https://gateway.yourcompany.internal/v1
   # OPENAI_API_KEY=<gateway-token>
   # MODEL_MAIN=openai/internal-claude-sonnet
   # MODEL_CHEAP=openai/internal-claude-haiku
   ```

   Code uses semantic role names: `os.environ["MODEL_MAIN"]` and `os.environ["MODEL_CHEAP"]`. Never hardcode model strings outside `.env`.

6. **Smoke test** — `scripts/smoke_llm.py`:
   - Calls `complete()` with a hello-world prompt using `MODEL_MAIN`
   - Calls `complete_json()` with a trivial 2-field Pydantic model
   - Prints both results and which model was used

**Acceptance:**
- `python scripts/smoke_llm.py` works with Anthropic configured.
- `complete_json` round-trips a Pydantic model, and demonstrably retries on a deliberately-malformed schema (you can test this by temporarily passing a system prompt that says "return invalid JSON" and confirming the retry kicks in).
- README has a short "Using a different LLM backend" note showing how to point at an OpenAI-compatible gateway.

**Note on Anthropic API access:** the user needs an **API key from console.anthropic.com**, not a Claude.ai Pro/Max subscription — they're separate. If they don't have one, they sign up at the console and add a few dollars in credits. Dev costs for this project will be cents to single dollars.

---

## Ticket 4 — Drop-in input + extraction pass

**Goal:** Operator can paste text, hit a route, get back an Extracted JSON object stored in the session.

**Do:**
1. Write the real `prompts/extract.md` per `spec.md` → "Extraction schema." The prompt should:
   - Explain the operator's role and what an SDD is
   - Instruct Claude to extract all available info, leaving fields null/empty if unknown (do NOT hallucinate)
   - Embed the JSON schema (you can paste the Pydantic schema as JSON Schema or describe the fields in markdown)
   - Require strict JSON-only output
2. `app/extraction.py`: `extract_from_text(raw_text: str) -> Extracted` using `ClaudeClient.complete_json`.
3. `app/main.py`: `POST /api/dropin` accepts `{session_id, raw_text}` (and optional file upload — read text content for now, no docx parsing yet). Stores `raw_input` in session, runs extraction, stores `extracted` in session, returns the Extracted JSON.
4. Add a sample fixture: `evals/fixtures/invoice_process_transcript.md` — a realistic 1-page meeting transcript describing an invoice processing workflow. Make it medium-quality: most info present, some gaps.
5. Manual test: curl the fixture content through `/api/dropin` and inspect the resulting session JSON.

**Acceptance:** running extraction on the fixture produces a sensible Extracted object — project_name, applications, at least 3 steps, business_criticality populated.

---

## Ticket 5 — Gap analysis pass

**Goal:** Score the Extracted object against the rubric and produce focused clarifying questions.

**Do:**
1. Write `prompts/rubric.md` per `spec.md` → "The developer-ready rubric."
2. Write `prompts/gap_analysis.md`:
   - Input: the Extracted JSON + the rubric
   - Output: strict JSON matching a `Coverage` Pydantic model (add to `app/models.py`):
     ```
     class CoverageItem(BaseModel):
         id: str               # e.g., "step_3.decision_logic" or "overall.access"
         category: str         # rubric category
         status: Literal["covered", "partial", "missing"]
         question: Optional[str] = None  # populated for partial/missing
     class Coverage(BaseModel):
         overall_pct: float
         by_category: dict[str, float]
         items: list[CoverageItem]
     ```
   - Instruct Claude to be **specific** in questions ("What's the threshold amount for high-value invoices?" not "Can you clarify the decision logic?")
3. `app/gap_analysis.py`: `analyze(extracted: Extracted) -> Coverage`.
4. `app/main.py`: `POST /api/coverage/{session_id}` runs gap analysis, stores in session, returns Coverage JSON.
5. Add a vague fixture: `evals/fixtures/vague_request.md` — short, sparse description (e.g., "We need to automate invoice approval, it's a manual process").
6. Manual test: run extraction + gap analysis on both fixtures. Confirm the vague one has lower coverage and produces more questions.

**Acceptance:** the detailed fixture scores higher than the vague one, and the generated questions are specific enough to forward to a business user without editing.

---

## Ticket 6 — Mermaid diagram generation

**Goal:** Generate the applications diagram as Mermaid, render to PNG.

**Do:**
1. Document Mermaid CLI install in README ("`npm install -g @mermaid-js/mermaid-cli`"). Verify with `mmdc --version` on startup; fail fast with a clear error if missing.
2. Write `prompts/diagram.md`:
   - Input: Extracted JSON
   - Output: a Mermaid `flowchart LR` string, with subgraphs grouping applications logically (sources, processing, outputs)
   - Constraints: valid Mermaid, no markdown fences, no commentary — just the diagram source starting with `flowchart`
3. `app/diagram.py`:
   - `generate_mermaid(extracted: Extracted) -> str` — Claude call
   - `render_png(mermaid_src: str, out_path: Path) -> Path` — write `.mmd` next to it, call `mmdc -i ... -o ... -b transparent -w 1600` via subprocess
4. Don't expose a dedicated route yet — diagram gen will be invoked during generation in Ticket 8.
5. Quick test script `scripts/test_diagram.py` that takes a fixture extraction and renders a PNG; eyeball the result.

**Acceptance:** a PNG diagram renders successfully from the invoice fixture, and the apps shown match the fixture content.

---

## Ticket 7 — DOCX template + filler

**Goal:** Tokenized `.docx` template + code that fills it from an Extracted object.

**Do:**
1. Write `scripts/prepare_template.py`:
   - Reads the operator's original `templates/Automation_SDD_template.docx` (operator will place it there)
   - Doesn't actually mutate it programmatically — instead, prints out the **list of tokens** the operator should manually add to which cells, based on `prompts/template_tokens.md`
   - This is a guidance tool, not an automated rewriter. Document this clearly.
2. Write `prompts/template_tokens.md` listing every token name, what data it corresponds to, and where it lives in the SDD (e.g., `{{project_name}}` → top table, "Project Name" row).
3. `app/docx_filler.py`:
   - `fill_template(extracted: Extracted, diagram_png_path: Path, out_path: Path) -> Path`
   - Loads template, walks paragraphs and table cells, replaces `{{token}}` patterns
   - For repeating row tokens (`{{app.name}}`, `{{step.summary}}`, etc.) — find the row containing the token, duplicate it N times, replace tokens per row
   - For the diagram: find a paragraph containing `{{applications_diagram}}` and replace with an inline image (use `python-docx`'s `add_picture` workflow on the paragraph's run)
   - Use placeholder `[TBD - {{reason}}]` for tokens with no data; this surfaces gaps in the doc itself
4. Operator action item (note in README): manually tokenize the template once before running. Provide the token list from `template_tokens.md`.
5. Operator places their tokenized template at `templates/Automation_SDD_template.docx` (gitignore the original; commit a redacted/example version).

**Acceptance:** given a populated Extracted object + a rendered diagram PNG, `fill_template` produces a `.docx` that opens cleanly in Word, has the correct values in cells, repeating rows for applications/errors/steps/reports, and the diagram embedded.

---

## Ticket 8 — SDD generation orchestration + Technology Fit

**Goal:** End-to-end generation for both modes, wired into a route.

**Do:**
1. `app/sdd_generator.py`:
   - `generate_sdd(session: Session) -> list[str]`
   - Steps: ensure extraction done → ensure coverage done → generate diagram → render PNG → write narrative sections via `prompts/sdd_narrative.md` (Claude pass that produces the prose chunks like "tool selection rationale" from extracted+coverage) → call docx_filler → generate `gaps.md` (markdown bullet list of all `missing`/`partial` items with their questions) → return list of artifact filenames
2. `prompts/sdd_narrative.md`: instructs Claude to write specific narrative sections (summary, tool selection rationale, etc.) given the Extracted + Coverage.
3. `prompts/technology_fit.md`: instructs Claude to produce the Technology Fit markdown report per `spec.md` → "Mode 1: Technology Fit." Output format clearly specified.
4. `app/technology_fit.py`: `generate_report(session: Session) -> str` (markdown), saved to `sessions/<id>/report.md`.
5. `app/main.py`:
   - `POST /api/generate/{session_id}` — dispatches based on session.mode, returns `{"files": [...]}`
   - `GET /api/download/{session_id}/{filename}` — serves files from the session directory with appropriate content-type
6. Mark session.phase = "generated" on success.

**Acceptance:** for the invoice fixture in SDD mode, can hit `/api/generate` and download a real `.docx`, real `.png`, real `.mmd`, real `gaps.md`. For the vague fixture in Technology Fit mode, can download a markdown report with a real recommendation.

---

## Ticket 9 — Chat (Phase 1 intake + Phase 2/3 conversation)

**Goal:** Chat-style input flow with streaming, coverage updates, and the "ask one focused question at a time" behavior.

**Do:**
1. Write `prompts/system_chat.md` — full system prompt enforcing tone, one-question-at-a-time, no jargon, no re-asking, etc.
2. Write `prompts/clarifier_question.md` — given current Extracted, current Coverage, and recent transcript, pick the single best next question. Output: just the question text, conversational.
3. `app/chat.py`:
   - `handle_intake(session, intake_data) -> None` — stores Phase 1 answers, pre-populates Extracted fields where direct (project_name, business_criticality, etc.).
   - `handle_turn(session, user_message) -> AsyncIterator[str]` — appends user turn to transcript; depending on phase, either captures narrative (Phase 2 — minimal AI interruption) or asks clarifier (Phase 3 — uses `clarifier_question.md`); streams response via SSE. After response, append assistant turn to transcript.
   - After each turn: re-run extraction on the full transcript + intake, re-run coverage. (Yes, this is expensive — fine for v1; optimize later.)
4. Phase transition logic:
   - intake → narrative when intake submitted
   - narrative → clarification when user signals done (use Haiku 4.5 cheap classifier: "Has the user finished their initial process description?") OR explicitly says "done" / "that's it" / similar
   - clarification → ready_to_generate when overall_pct >= 0.85 OR operator clicks Generate Draft
5. `app/main.py`:
   - `POST /api/intake` (session_id + intake_data) → calls `handle_intake`
   - `POST /api/chat/{session_id}` (body: `{message}`) → streams response via SSE
6. SSE format: `data: <token>\n\n` per chunk, `event: done\n\n` at end with final coverage update.

**Acceptance:** end-to-end chat conversation produces a session with rich Extracted + Coverage, and Generate Draft produces a docx that's clearly better than the drop-in-only path on the same process.

---

## Ticket 10 — Frontend (single HTML page + HTMX)

**Goal:** Working UI matching the sketch in `spec.md` → "UI sketch."

**Do:**
1. `templates/index.html` (Jinja2, served at `/`):
   - Header with mode toggle (Technology Fit | SDD Builder)
   - Input style toggle (Drop-in | Chat)
   - Drop-in panel: textarea + file input + Process button
   - Chat panel: intake form (renders for Phase 1), then chat transcript + input
   - Coverage bar (HTMX-swapped div polled or updated on each chat turn)
   - Generate Draft button (disabled until coverage > some threshold OR operator can force)
   - Output panel: list of downloadable artifacts
2. `static/styles.css`: clean, minimal, readable. Use a neutral palette. No frameworks.
3. `static/app.js`: small amount of vanilla JS for:
   - Session creation on first interaction
   - SSE handling for chat streaming (EventSource)
   - State persistence in localStorage (just session_id, so refresh recovers)
4. Use HTMX (via CDN) for:
   - Submitting intake form → swap chat panel in
   - Submitting drop-in → swap output area in
   - Coverage updates after each chat turn (`hx-trigger="chatTurnComplete from:body"`)
5. Mount static files in FastAPI: `app.mount("/static", StaticFiles(...))`.

**Acceptance:** operator can complete a full chat-mode SDD session in the browser without using curl, and download all artifacts via the UI.

---

## Ticket 11 — Polish, README, evals

**Goal:** Repo ready to share publicly.

**Do:**
1. `README.md` — rewrite as a real readme:
   - One-paragraph hook (the pain points and the solution)
   - Screenshot or GIF of the UI (record one with the operator's real data, redact if needed)
   - Features list (two modes, two input styles, gap analysis, diagram, docx output)
   - Architecture diagram (Mermaid in the README itself)
   - Quickstart (install, set env, prepare template, run)
   - Project structure (brief)
   - Design decisions (3–4 bullets: HTMX over React, JSON sessions over DB, prompts as files, two-model strategy)
   - Roadmap (v2 items from spec.md)
   - "Built with" / acknowledgements
2. `evals/test_extraction.py`: 3 tests using the 3 fixtures, marked `@pytest.mark.live`. Each test runs extraction + gap analysis, asserts:
   - Required fields populated (or expected to be empty for the vague fixture)
   - Coverage in expected band
3. Add a `Makefile` or `justfile` with: `run`, `test`, `test-live`, `format`, `lint`.
4. Tidy: `ruff` and/or `black` pass cleanly. Type hints on public functions.
5. Commit a redacted sample SDD output to `examples/sample_output/` (real `.docx`, `.png`, `.md`, `gaps.md`) so visitors can see what the tool produces without running it.
6. Push to GitHub. Pin the repo. Write the repo description: e.g., "Turn fuzzy business descriptions into developer-ready Software Design Documents for RPA. Built with Claude, FastAPI, HTMX."

**Acceptance:** repo is presentable. A stranger can clone, follow the quickstart, and have a running app in 10 minutes.

---

## Notes for working with Claude Code on this

- Always show Claude Code `spec.md` at the start of each ticket. Don't just hand it `tasks.md`.
- After each ticket, manually verify the acceptance criteria before approving Claude Code's commit.
- If Claude Code wants to add a dep beyond what's in the spec, push back unless it's genuinely necessary.
- Iterate on the prompts in `prompts/` AS you test — they're the highest-leverage thing in this project. Don't expect them to be right first time.
- The first time you run extraction on a real meeting transcript will be the most informative moment. Save the input + output in `examples/` so you have a reference point.
