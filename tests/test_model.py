"""Tests for database model."""

import pytest
from sqlalchemy.exc import IntegrityError

from src.model import Entry


class TestEntry:
    """Tests for Entry model."""

    def test_create_entry(self, temp_db):
        """Should be able to create an entry."""
        db_path, session = temp_db

        entry = Entry(
            name="test-project",
            category="dsp",
            url="https://example.com",
            repo="https://github.com/test/test",
            description="A test project",
        )
        session.add(entry)
        session.commit()

        assert entry.id is not None
        assert entry.name == "test-project"

    def test_entry_repr(self, temp_db):
        """Entry repr should be informative."""
        db_path, session = temp_db

        entry = Entry(
            name="test-project",
            category="dsp",
            description="A test project",
            repo="https://github.com/test/test",
        )
        session.add(entry)
        session.commit()

        assert "test-project" in repr(entry)
        assert "dsp" in repr(entry)

    def test_entry_to_dict(self, temp_db):
        """Entry should convert to dict properly."""
        db_path, session = temp_db

        entry = Entry(
            name="test-project",
            category="dsp",
            url="https://example.com",
            repo="https://github.com/test/test",
            description="A test project",
            keywords="test,dsp",
        )
        session.add(entry)
        session.commit()

        d = entry.to_dict()
        assert d["name"] == "test-project"
        assert d["category"] == "dsp"
        assert d["url"] == "https://example.com"
        assert d["repo"] == "https://github.com/test/test"
        assert d["description"] == "A test project"
        assert d["keywords"] == "test,dsp"

    def test_unique_name_constraint(self, temp_db):
        """Duplicate names should raise an error."""
        db_path, session = temp_db

        entry1 = Entry(
            name="duplicate",
            category="dsp",
            description="First",
            repo="https://github.com/test/test1",
        )
        entry2 = Entry(
            name="duplicate",
            category="analysis",
            description="Second",
            repo="https://github.com/test/test2",
        )

        session.add(entry1)
        session.commit()

        session.add(entry2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_query_by_category(self, temp_db):
        """Should be able to query entries by category."""
        db_path, session = temp_db

        entries = [
            Entry(name="dsp1", category="dsp", description="DSP 1", repo="https://github.com/a/a"),
            Entry(name="dsp2", category="dsp", description="DSP 2", repo="https://github.com/b/b"),
            Entry(name="analysis1", category="analysis", description="Analysis 1", repo="https://github.com/c/c"),
        ]
        for e in entries:
            session.add(e)
        session.commit()

        dsp_entries = session.query(Entry).filter_by(category="dsp").all()
        assert len(dsp_entries) == 2

        analysis_entries = session.query(Entry).filter_by(category="analysis").all()
        assert len(analysis_entries) == 1

    def test_nullable_fields(self, temp_db):
        """Optional fields should be nullable."""
        db_path, session = temp_db

        entry = Entry(
            name="minimal",
            category="dsp",
            description="Minimal entry",
            # url, repo, keywords, last_updated, last_checked all None
        )
        session.add(entry)
        session.commit()

        retrieved = session.query(Entry).filter_by(name="minimal").first()
        assert retrieved.url is None
        assert retrieved.repo is None
        assert retrieved.keywords is None
        assert retrieved.last_updated is None
        assert retrieved.last_checked is None
