"""Pytest fixtures for awesome-audio tests."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.model import init_db


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    session = init_db(db_path)
    yield db_path, session

    session.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def temp_yaml():
    """Create a temporary YAML file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
        yaml_path = Path(f.name)

    yield yaml_path

    yaml_path.unlink(missing_ok=True)


@pytest.fixture
def sample_entries():
    """Sample valid entries for testing."""
    return [
        {
            "name": "test-project-1",
            "category": "dsp",
            "desc": "A test DSP project",
            "url": "https://example.com/test1",
            "repo": "https://github.com/test/test1",
        },
        {
            "name": "test-project-2",
            "category": "analysis",
            "desc": "A test analysis project",
            "url": None,
            "repo": "https://github.com/test/test2",
        },
        {
            "name": "test-project-3",
            "category": "midi sequencer",
            "desc": "A test MIDI sequencer",
            "url": "https://example.com/test3",
            "repo": None,
        },
    ]


@pytest.fixture
def sample_yaml(temp_yaml, sample_entries):
    """Create a temporary YAML file with sample entries."""
    with open(temp_yaml, "w") as f:
        yaml.dump(sample_entries, f)
    return temp_yaml
