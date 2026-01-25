# Installation

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/example/awesome-audio.git
cd awesome-audio

# Install dependencies
uv sync

# Verify installation
uv run awesome-audio --version
```

## Using pip

```bash
# Clone the repository
git clone https://github.com/example/awesome-audio.git
cd awesome-audio

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
awesome-audio --version
```

## Development Installation

For development, install with dev dependencies:

```bash
uv sync --group dev
```

This includes:

- `pytest` - Testing framework
- `ruff` - Linting and formatting
- `mkdocs-material` - Documentation

## Verify Installation

Run the test suite to verify everything is working:

```bash
make test
```

You should see all 84 tests passing.
