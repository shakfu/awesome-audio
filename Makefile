.PHONY: help clean lint format validate sort import check github stale stats generate

CURATOR := python3 scripts/curator.py

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  validate   Validate entries.json"
	@echo "  sort       Sort entries.json alphabetically"
	@echo "  import     Import JSON to SQLite database"
	@echo "  generate   Generate README.md from database"
	@echo "  check      Check all URLs for broken links"
	@echo "  github     Fetch GitHub stats for all repos"
	@echo "  stale      Find stale/unmaintained projects"
	@echo "  stats      Show database statistics"
	@echo "  lint       Run ruff linter"
	@echo "  format     Format code with ruff"
	@echo "  clean      Remove generated files"

clean:
	@rm -rf __pycache__ .pytest_cache *.pyc scripts/*.db
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

lint:
	@ruff check scripts/

format:
	@ruff format scripts/

validate:
	@$(CURATOR) validate

sort:
	@$(CURATOR) sort

import:
	@$(CURATOR) import

check:
	@$(CURATOR) check

github:
	@$(CURATOR) github

stale:
	@$(CURATOR) stale

stats:
	@$(CURATOR) stats

generate:
	@$(CURATOR) import
	@$(CURATOR) generate -o README.md -f
	@command -v rumdl >/dev/null 2>&1 && rumdl fmt README.md || true

