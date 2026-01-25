"""Tests for schema validation."""

import pytest

from src.schema import CATEGORIES, EntrySchema, validate_entries


class TestEntrySchema:
    """Tests for EntrySchema validation."""

    def test_valid_entry_with_url_and_repo(self):
        """Entry with both url and repo should be valid."""
        entry = EntrySchema(
            name="test-project",
            category="dsp",
            desc="A test project",
            url="https://example.com",
            repo="https://github.com/test/test",
        )
        assert entry.name == "test-project"
        assert entry.category == "dsp"

    def test_valid_entry_with_only_repo(self):
        """Entry with only repo should be valid."""
        entry = EntrySchema(
            name="test-project",
            category="dsp",
            desc="A test project",
            repo="https://github.com/test/test",
        )
        assert entry.repo == "https://github.com/test/test"
        assert entry.url is None

    def test_valid_entry_with_only_url(self):
        """Entry with only url should be valid."""
        entry = EntrySchema(
            name="test-project",
            category="dsp",
            desc="A test project",
            url="https://example.com",
        )
        assert entry.url == "https://example.com"
        assert entry.repo is None

    def test_invalid_entry_no_url_or_repo(self):
        """Entry without url or repo should be invalid."""
        with pytest.raises(ValueError, match="must have url or repo"):
            EntrySchema(
                name="test-project",
                category="dsp",
                desc="A test project",
            )

    def test_invalid_entry_name_is_url(self):
        """Entry with URL as name should be invalid."""
        with pytest.raises(ValueError, match="name should not be a URL"):
            EntrySchema(
                name="https://github.com/test/test",
                category="dsp",
                desc="A test project",
                repo="https://github.com/test/test",
            )

    def test_invalid_entry_empty_name(self):
        """Entry with empty name should be invalid."""
        with pytest.raises(ValueError, match="cannot be empty"):
            EntrySchema(
                name="",
                category="dsp",
                desc="A test project",
                repo="https://github.com/test/test",
            )

    def test_name_whitespace_stripped(self):
        """Entry name should have whitespace stripped."""
        entry = EntrySchema(
            name="  test-project  ",
            category="dsp",
            desc="A test project",
            repo="https://github.com/test/test",
        )
        assert entry.name == "test-project"


class TestValidateEntries:
    """Tests for validate_entries function."""

    def test_valid_entries(self, sample_entries):
        """Valid entries should pass validation."""
        result = validate_entries(sample_entries)
        assert result.is_valid
        assert len(result.valid) == 3
        assert len(result.errors) == 0

    def test_duplicate_detection(self):
        """Duplicate entries should be detected."""
        entries = [
            {"name": "dupe", "category": "dsp", "desc": "First", "repo": "https://github.com/a/a"},
            {"name": "unique", "category": "dsp", "desc": "Unique", "repo": "https://github.com/b/b"},
            {"name": "dupe", "category": "analysis", "desc": "Second", "repo": "https://github.com/c/c"},
        ]
        result = validate_entries(entries)
        assert len(result.duplicates) == 1
        assert result.duplicates[0][0] == "dupe"
        assert result.duplicates[0][1] == [1, 3]

    def test_non_canonical_category_warning(self):
        """Non-canonical categories should produce warnings."""
        entries = [
            {"name": "test", "category": "weird-category", "desc": "Test", "repo": "https://github.com/a/a"},
        ]
        result = validate_entries(entries)
        assert result.is_valid  # Warnings don't make it invalid
        assert len(result.warnings) == 1
        assert "non-canonical category" in result.warnings[0][2]

    def test_canonical_category_no_warning(self):
        """Canonical categories should not produce warnings."""
        entries = [
            {"name": "test", "category": "dsp", "desc": "Test", "repo": "https://github.com/a/a"},
        ]
        result = validate_entries(entries)
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_error_propagation(self):
        """Invalid entries should produce errors."""
        entries = [
            {"name": "", "category": "dsp", "desc": "Bad name", "repo": "https://github.com/a/a"},
            {"name": "good", "category": "dsp", "desc": "Good", "repo": "https://github.com/b/b"},
        ]
        result = validate_entries(entries)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert len(result.valid) == 1


class TestCategories:
    """Tests for category constants."""

    def test_categories_are_lowercase(self):
        """All canonical categories should be lowercase."""
        for cat in CATEGORIES:
            assert cat == cat.lower(), f"Category '{cat}' should be lowercase"

    def test_essential_categories_present(self):
        """Essential categories should be in the set."""
        essential = {"dsp", "analysis", "midi", "daw", "synthesis", "plugins"}
        assert essential.issubset(CATEGORIES)
