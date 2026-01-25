# awesome-audio

A curated guide to open-source audio and music projects.

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)

## Overview

**awesome-audio** is a comprehensive, maintained database of free/open-source audio software and music programming tools. It provides:

- **78+ curated entries** across 31 categories
- **CLI tool** for searching, validating, and managing entries
- **SQLite database** for fast querying
- **GitHub integration** for repository statistics
- **Link checker** for validating URLs

## Features

| Feature | Description |
|---------|-------------|
| Schema Validation | Pydantic-based validation with duplicate detection |
| Category Normalization | Consolidate variants to canonical categories |
| Link Checking | Async URL validation with broken link detection |
| GitHub Stats | Fetch stars, forks, and activity status |
| README Generation | Jinja2 templates for auto-generating docs |
| Stale Detection | Find unmaintained projects |

## Quick Example

```bash
# Install
uv sync

# Validate entries
awesome-audio validate

# Import to database
awesome-audio import

# Search for DSP projects
awesome-audio search dsp

# Check for broken links
awesome-audio check

# Generate README
awesome-audio generate -o README.md
```

## Project Status

- **Version**: 0.3.0
- **Tests**: 84 passing
- **CLI Commands**: 14

## License

This project is licensed under [CC0 1.0 Universal](http://creativecommons.org/publicdomain/zero/1.0/) - public domain dedication.
