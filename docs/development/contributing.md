# Contributing

Thank you for your interest in contributing to awesome-audio!

## Adding New Entries

### Via CLI

The easiest way to add an entry:

```bash
awesome-audio add \
  -n "project-name" \
  -c "category" \
  -d "Project description" \
  -r "https://github.com/owner/repo" \
  -y data/entries.yml
```

### Via YAML

Add an entry directly to `data/entries.yml`:

```yaml
- name: project-name
  category: dsp
  desc: A description of the project.
  url: https://project-website.com
  repo: https://github.com/owner/project
```

### Entry Requirements

1. **Open Source**: Project must be open source
2. **Maintained**: Project should be actively maintained (updated within last 2 years)
3. **Audio-Related**: Must be related to audio, music, or sound
4. **Unique**: No duplicates of existing entries

### Categories

Use canonical categories. Run `awesome-audio categories` to see the full list:

- `analysis` - Audio analysis tools
- `dsp` - Digital signal processing
- `midi` - MIDI tools and libraries
- `synthesis` - Sound synthesis
- `daw` - Digital audio workstations
- `plugins` - Audio plugins (VST, AU, etc.)
- `livecoding` - Live coding environments
- And more...

## Development Setup

```bash
# Clone repository
git clone https://github.com/example/awesome-audio.git
cd awesome-audio

# Install with dev dependencies
uv sync --group dev

# Run tests
make test

# Run linter
make lint

# Format code
make format
```

## Code Style

- Python 3.13+
- Formatting: `ruff format`
- Linting: `ruff check`
- Type hints encouraged
- Docstrings for public functions

## Testing

All new features must include tests:

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/test_schema.py -v

# Run with coverage
uv run pytest --cov=src tests/
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make test`
5. Run linter: `make lint`
6. Commit with descriptive message
7. Push and create a Pull Request

## Reporting Issues

When reporting issues, please include:

- awesome-audio version (`awesome-audio --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
