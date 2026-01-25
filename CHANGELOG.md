# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## CLI Commands Reference

| Command | Description | Added |
|---------|-------------|-------|
| `add` | Add new entry to database | v0.3.0 |
| `categories` | List canonical categories | v0.1.0 |
| `check` | Validate URLs for broken links | v0.2.0 |
| `export` | Export database to YAML | v0.1.0 |
| `generate` | Generate README from database | v0.2.0 |
| `github` | Fetch GitHub repository stats | v0.2.0 |
| `import` | Import YAML to database | v0.1.0 |
| `list` | List entries with filters | v0.1.0 |
| `remove` | Remove entry from database | v0.3.0 |
| `search` | Search entries | v0.1.0 |
| `stale` | Find unmaintained projects | v0.3.0 |
| `stats` | Show database statistics | v0.1.0 |
| `validate` | Validate YAML file | v0.1.0 |

## [Unreleased]

### Added

- **`github` command enhancements**:
  - `--show-topics` flag to display repository topics
  - `--update-db` flag to store GitHub topics in database keywords field
  - `-d, --db` option to specify database path

### Changed

- **README restructure**:
  - Top-level `README.md` is now generated from database (`make generate`)
  - CLI infrastructure documentation moved to `docs/README.md`
  - Generated README links to `docs/README.md` for CLI docs

### Removed

- **`normalize` command**: One-shot normalizer removed after initial data cleanup
- **`src/normalizer.py`**: Category normalization module removed
- The `add` command now validates categories against canonical list instead of auto-normalizing
- **MkDocs site deployment**: Removed `mkdocs.yml` and docs deployment workflow; docs are now read directly from `docs/` directory

## [0.4.0] - 2026-01-25

### Added

- **MkDocs documentation site**:
  - Material theme with dark/light mode
  - Getting Started guide (installation, quickstart)
  - CLI reference with all 14 commands
  - Development guide (contributing, architecture)
  - Changelog page

- **GitHub Actions CI/CD pipeline**:
  - `ci.yml` - Tests, linting, and validation on push/PR
  - `docs.yml` - Auto-deploy docs to GitHub Pages
  - `links.yml` - Weekly broken link check with auto-issue creation
  - `release.yml` - Build and publish on version tags

- **Makefile targets**:
  - `docs` - Build documentation
  - `docs-serve` - Serve docs locally
  - `docs-deploy` - Deploy to GitHub Pages

## [0.3.0] - 2026-01-25

### Added

- **`add` command**: Add new entries via CLI with validation
  - Automatic category normalization
  - Optional append to YAML file
  - Duplicate detection

- **`normalize` command**: Consolidate non-canonical categories
  - Dry-run mode to preview changes
  - Interactive mode for confirmation
  - Maps 19 variant categories to canonical forms

- **`stale` command**: Find unmaintained projects
  - Configurable staleness threshold (default: 365 days)
  - Identifies archived repositories
  - Reports repository health percentage

- **`remove` command**: Remove entries from database
  - Confirmation prompt (skippable with -y flag)
  - Shows entry details before removal

- **Category normalizer module** (`src/normalizer.py`):
  - Mapping of 19 non-canonical to canonical categories
  - Similarity matching for suggestions
  - Case-insensitive normalization

- **Extended test coverage**:
  - 84 pytest tests (up from 72)
  - Tests for normalizer module

## [0.2.0] - 2026-01-25

### Added

- **Link checker** (`src/checker.py`):
  - Async URL validation using httpx
  - Concurrent checking with configurable limits
  - Detection of broken links, redirects, and timeouts
  - CLI command: `check`

- **GitHub API integration** (`src/github.py`):
  - Fetch repository statistics (stars, forks, activity)
  - Parse GitHub URLs to extract owner/repo
  - Activity status detection (very active, active, maintained, stale, archived)
  - Support for GITHUB_TOKEN/GH_TOKEN authentication
  - CLI command: `github` with sorting options

- **README generation** (`src/generator.py`):
  - Jinja2-based template rendering
  - Entries grouped by category
  - Configurable output path
  - CLI command: `generate`

- **Extended test coverage**:
  - 72 pytest tests (up from 37)
  - Tests for checker, github, and generator modules

## [0.1.0] - 2026-01-25

### Added

- **CLI tool** (`awesome-audio`) with commands:
  - `validate` - Validate entries YAML file, detecting errors, duplicates, and non-canonical categories
  - `import` - Import entries from YAML to SQLite database
  - `export` - Export entries from SQLite database to YAML
  - `list` - List all entries with optional category filter and format options (table/JSON/YAML)
  - `search` - Search entries by name, description, or category
  - `stats` - Show database statistics including category breakdown
  - `categories` - List canonical categories

- **Schema validation** (`src/schema.py`):
  - Pydantic-based entry validation
  - 31 canonical categories defined
  - Detection of duplicate entries
  - Validation that entries have at least URL or repo
  - Warning system for non-canonical categories

- **Database model** (`src/model.py`):
  - SQLAlchemy ORM with Entry model
  - Fields: name, category, url, repo, description, keywords, last_updated, last_checked
  - Unique constraint on entry names

- **Import/Export** (`src/importer.py`):
  - YAML to SQLite import with validation and deduplication
  - SQLite to YAML export with proper formatting
  - Skip or update existing entries on re-import

- **Testing infrastructure**:
  - pytest tests covering schema, model, importer, and CLI
  - Fixtures for temporary databases and YAML files

- **Build system**:
  - Makefile with targets: install, test, lint, format, clean, validate, import
  - pyproject.toml configured for uv package management
  - ruff for linting and formatting

### Fixed

- Malformed entry where `pyminiaudio` had URL as name instead of project name
- Duplicate entries for `isobar` (merged into single entry with URL)
- Duplicate entries for `sardine` (merged into single entry with canonical category)

### Changed

- Migrated from requirements.txt to pyproject.toml with uv
- Refactored `src/model.py` to remove hardcoded test data
