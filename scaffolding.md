# Scaffolding — Pre-Flight Guide

You only need to do three things before handing this to Claude Code. The rest (venv creation, dep installs, CLI checks) is handled by Ticket 0 in `tasks.md`.

## 1. Prerequisites (manual install — Claude Code can't do these for you)

- **Python 3.11+** — check with `python --version`. Install via `pyenv`, `uv python install 3.12`, or your OS package manager if needed.
- **Node 18+** — check with `node --version`. Needed for Mermaid CLI.
- **`uv` (recommended)** — much faster than pip. Install:
  - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - macOS via Homebrew: `brew install uv`
  - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Anthropic API key** — get one from https://console.anthropic.com. This is **separate from a Claude.ai Pro/Max subscription** — the subscription doesn't grant API access. Add a few dollars in credits; dev costs for this project will be small.

## 2. Create the repo

```bash
mkdir automation-sdd-builder
cd automation-sdd-builder
```

Drop the three handoff files (`spec.md`, `tasks.md`, `scaffolding.md`) into the root.

## 3. Place your SDD template (optional now, required before Ticket 7)

Copy your `Automation_SDD.docx` to `templates/Automation_SDD_template.docx`. You'll tokenize it after Ticket 7 — for now, just have it ready.

**Don't commit the real internal template** if it contains anything proprietary. Commit a redacted version, or gitignore the real one and add a `templates/README.md` noting where to drop it.

---

## Hand off to Claude Code

Open Claude Code at the repo root. Your first message:

> Read `spec.md` and `tasks.md` in full. We're going to work through the tickets in order, one at a time. Start with **Ticket 0 — Environment setup**. Don't move past it until I confirm. After each ticket, stop and wait for me to verify before continuing.

Then iterate ticket by ticket:
1. Read what Claude Code produced
2. Run the acceptance test yourself
3. Commit (let Claude Code commit, but review the message first)
4. Move to the next ticket

## Re-activating the venv in future sessions

If you close your terminal and start a new Claude Code session tomorrow, the venv still exists on disk but isn't active in the new shell. Tell Claude Code:

> Activate the existing `.venv/` before doing anything else.

Or just run `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`) yourself before starting Claude Code.

## Recommended order of operations

| Day part | Tickets | Expected time |
|---|---|---|
| Setup | 0, 1 | 30-60 min (env + scaffolding) |
| Morning | 2, 3 | 2 hours (sessions + LLM client) |
| Midday | 4, 5 | 2-3 hours (extraction + gap analysis — most important) |
| Afternoon | 6, 7, 8 | 3-4 hours (diagram + docx + orchestration) |
| Evening | 9 | 2 hours (chat — can split to day 2) |
| Day 2 | 10, 11 | 4-6 hours (UI + polish) |

Tickets 4 and 5 are where the project either works or doesn't. Spend time on the prompts there. Everything downstream depends on those outputs being good.

## What to keep watching as you build

- **Extraction quality on real input.** Run it on actual transcripts from past projects, not just the fixtures. If it misses things, the fix is almost always in the prompt, not the code.
- **Gap analysis specificity.** The questions Claude generates should be ones you could literally copy-paste into an email to the business. If they're too generic, iterate `prompts/gap_analysis.md` and `prompts/rubric.md`.
- **The chat's one-question-at-a-time discipline.** This will be the first thing to drift. Watch for the AI dumping a numbered list of questions — when it does, sharpen the system prompt.
- **The docx output rendering.** Check it in actual Word, not just LibreOffice. Tables with repeating rows are where things can go subtly wrong.
