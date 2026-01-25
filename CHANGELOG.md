# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Replaced module-based CLI (`src/`) with single zero-dependency script (`scripts/curator.py`)
- Updated Makefile to use `curator.py` directly
- Updated GitHub workflows to use `curator.py` exclusively
- Simplified CI workflow to pure Python validation (no uv/pytest required)
- Re-enabled scheduled link checking (weekly on Sundays)
- Re-enabled tag-based releases

### Removed

- Removed `src/` module structure (cli, checker, generator, github, importer, model, schema)
- Removed `tests/` directory
- Removed `docs/` directory (mkdocs documentation)
- Removed `pyproject.toml` and `uv.lock`
- Removed `.python-version`

## [0.1.0]

