# awesome-audio

A curated guide to open-source audio, midi and music projects.

[![CI](https://github.com/shakfu/awesome-audio/actions/workflows/ci.yml/badge.svg)](https://github.com/shakfu/awesome-audio/actions/workflows/ci.yml)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)

## Overview

**awesome-audio** is a comprehensive, maintained database of free/open-source audio software and music programming tools featuring:

- **78+ curated entries** across 31 categories
- **CLI tool** for searching, validating, and managing entries
- **SQLite database** for fast querying
- **GitHub integration** for repository statistics
- **Link checker** for URL validation
- **README generation** from templates

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository
git clone https://github.com/shakfu/awesome-audio.git
cd awesome-audio

# Install dependencies
uv sync

# Verify installation
uv run awesome-audio --version
```

## Quick Start

```bash
# Validate the YAML data file
awesome-audio validate

# Import entries to SQLite database
awesome-audio import

# Search for projects
awesome-audio search "dsp"

# List all entries
awesome-audio list

# Check for broken links
awesome-audio check

# Fetch GitHub statistics
awesome-audio github

# Generate README from database
awesome-audio generate -o README.md
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `validate` | Validate YAML file for errors and duplicates |
| `import` | Import YAML to SQLite database |
| `export` | Export database to YAML |
| `list` | List entries with optional filters |
| `search` | Search by name, description, or category |
| `stats` | Show database statistics |
| `categories` | List canonical categories |
| `add` | Add new entry to database |
| `remove` | Remove entry from database |
| `check` | Validate URLs for broken links |
| `github` | Fetch GitHub repository stats |
| `stale` | Find unmaintained projects |
| `generate` | Generate README from database |

## Categories

Projects are organized into 31 canonical categories:

`ableton` `algorithmic-music` `analysis` `audio-driver` `audio-framework` `audio-interface` `augmentation` `beatmatching` `chuck` `csound` `daw` `dsp` `editor` `fx` `livecoding` `looping` `midi` `monome` `music-programming` `plugins` `random` `resampling` `sequencer` `speech` `supercollider` `synthesis` `timestretching` `tracker` `utility` `visualization` `wavetables`

## Documentation

See the [docs/](docs/) directory for detailed documentation on the CLI tool infrastructure, including:

- [Getting Started](docs/getting-started/) - Installation and quickstart
- [CLI Reference](docs/cli/) - Command documentation
- [Development](docs/development/) - Contributing and architecture

## Development

```bash
# Run tests (72 tests)
make test

# Run linter
make lint

# Format code
make format
```

## Project Structure

```
awesome-audio/
├── data/
│   └── entries.yml       # Primary YAML data (78 entries)
├── src/
│   ├── checker.py        # Async link checker
│   ├── cli.py            # CLI commands (13 commands)
│   ├── generator.py      # README generation
│   ├── github.py         # GitHub API integration
│   ├── importer.py       # YAML import/export
│   ├── model.py          # SQLAlchemy ORM
│   ├── normalizer.py     # Category normalization
│   └── schema.py         # Pydantic validation
├── tests/                # 84 pytest tests
├── docs/                 # CLI infrastructure documentation
└── .github/workflows/    # CI/CD pipelines
```

## Contributing

Contributions welcome! You can:

1. **Add entries via CLI**:
   ```bash
   awesome-audio add -n "project-name" -c "category" -d "Description" -r "https://github.com/..."
   ```

2. **Edit YAML directly**: Add entries to `data/entries.yml`

3. **Open an issue**: Propose new entries on the [issues page](https://github.com/shakfu/awesome-audio/issues)

### Entry Requirements

- Open source
- Actively maintained (updated within last 2 years)
- Audio/music related
- Not a duplicate

## License

[![CC0](https://licensebuttons.net/p/zero/1.0/88x31.png)](http://creativecommons.org/publicdomain/zero/1.0/)

This work is dedicated to the public domain under [CC0 1.0 Universal](http://creativecommons.org/publicdomain/zero/1.0/).
