.PHONY: install test lint format clean validate import generate

install:
	@uv sync

test:
	@uv run pytest tests/ -v

lint:
	@uv run ruff check src/ tests/ scripts/

format:
	@uv run ruff format src/ tests/ scripts/

clean:
	@rm -rf __pycache__ .pytest_cache *.pyc site/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

validate:
	@uv run python -m src.schema

import:
	@uv run python -m src.importer

generate:
	@uv run awesome-audio generate -o README.md
	@command -v rumdl >/dev/null 2>&1 && rumdl fmt README.md || true

