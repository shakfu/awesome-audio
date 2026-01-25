# Architecture

Overview of the awesome-audio codebase structure.

## Project Structure

```
awesome-audio/
├── data/
│   └── entries.yml       # Primary YAML data file
├── docs/                  # MkDocs documentation
├── src/
│   ├── __init__.py
│   ├── checker.py        # Async link checker
│   ├── cli.py            # Click CLI commands
│   ├── generator.py      # README generation
│   ├── github.py         # GitHub API integration
│   ├── importer.py       # YAML import/export
│   ├── model.py          # SQLAlchemy ORM
│   ├── normalizer.py     # Category normalization
│   ├── schema.py         # Pydantic validation
│   └── stopwords.py      # NLP stopwords
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   └── test_*.py         # Test modules
├── Makefile              # Build commands
├── mkdocs.yml            # Documentation config
└── pyproject.toml        # Project config
```

## Core Modules

### schema.py

Pydantic-based validation for entries:

```python
class EntrySchema(BaseModel):
    name: str
    category: str
    desc: str
    url: Optional[str] = None
    repo: Optional[str] = None
```

Defines 31 canonical categories and validates entries.

### model.py

SQLAlchemy ORM for database operations:

```python
class Entry(Base):
    __tablename__ = "entry"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    # ...
```

### importer.py

Handles YAML to SQLite import/export with validation.

### checker.py

Async link checking with httpx:

- Concurrent URL validation
- Timeout handling
- Redirect detection
- Status reporting

### github.py

GitHub API integration:

- Repository statistics (stars, forks, issues)
- Activity detection
- Rate limit handling

### generator.py

README generation with Jinja2:

- Template-based output
- Category grouping
- Star counts (optional)

### normalizer.py

Category normalization:

- Maps 19 variants to canonical forms
- Similarity matching

### cli.py

Click-based CLI with 14 commands.

## Data Flow

```
entries.yml
    │
    ▼
┌─────────────┐
│   validate  │ ─── schema.py (Pydantic)
└─────────────┘
    │
    ▼
┌─────────────┐
│   import    │ ─── importer.py
└─────────────┘
    │
    ▼
awesome-audio.db
    │
    ├──► search ──► model.py (SQLAlchemy)
    ├──► list
    ├──► stats
    └──► generate ──► generator.py (Jinja2)
```

## Testing Strategy

- **Unit tests**: Individual functions/classes
- **Integration tests**: CLI commands with temp databases
- **Fixtures**: Shared test data in conftest.py

```python
@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = Path(f.name)
    session = init_db(db_path)
    yield db_path, session
    session.close()
```

## Dependencies

| Package | Purpose |
|---------|---------|
| click | CLI framework |
| pydantic | Validation |
| sqlalchemy | ORM |
| pyyaml | YAML parsing |
| httpx | Async HTTP |
| jinja2 | Templates |

## Extension Points

### Custom Templates

Create custom Jinja2 template for README:

```bash
awesome-audio generate -t my-template.md.j2 -o README.md
```

### Database Location

Override default database path:

```bash
awesome-audio import -d /path/to/custom.db
awesome-audio search "audio" -d /path/to/custom.db
```
