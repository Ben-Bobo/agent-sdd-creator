# Task runner. Targets are thin wrappers over commands documented in README.md.
# On Windows without `make`, run the underlying commands directly.

VENV_PY := .venv/Scripts/python
ifeq ($(OS),Windows_NT)
  ACTIVATE_HINT := .venv\\Scripts\\activate
else
  VENV_PY := .venv/bin/python
  ACTIVATE_HINT := source .venv/bin/activate
endif

.PHONY: help install run format lint check

help:
	@echo "Targets:"
	@echo "  install    Install runtime + dev deps into .venv (requires: uv venv)"
	@echo "  run        Start the dev server on http://127.0.0.1:8000"
	@echo "  format     Format code with ruff"
	@echo "  lint       Lint with ruff (no fixes applied)"
	@echo "  check      Lint + format-check; fails if anything would change"
	@echo ""
	@echo "Activate the venv first: $(ACTIVATE_HINT)"

install:
	uv pip install -e ".[dev]"

run:
	$(VENV_PY) -m uvicorn app.main:app --reload

format:
	$(VENV_PY) -m ruff format app
	$(VENV_PY) -m ruff check --fix app

lint:
	$(VENV_PY) -m ruff check app

check:
	$(VENV_PY) -m ruff check app
	$(VENV_PY) -m ruff format --check app
