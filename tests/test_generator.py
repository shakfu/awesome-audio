"""Tests for README generator."""

import tempfile
from pathlib import Path


from src.generator import category_anchor, generate_readme, normalize_category
from src.model import Entry, init_db


class TestNormalizeCategory:
    """Tests for normalize_category function."""

    def test_simple_category(self):
        """Should capitalize simple category."""
        assert normalize_category("dsp") == "Dsp"

    def test_hyphenated_category(self):
        """Should handle hyphenated categories."""
        assert normalize_category("audio-interface") == "Audio Interface"

    def test_multi_word_category(self):
        """Should handle multi-word categories."""
        assert normalize_category("music programming language") == "Music Programming Language"


class TestCategoryAnchor:
    """Tests for category_anchor function."""

    def test_simple_anchor(self):
        """Should generate simple anchor."""
        assert category_anchor("DSP") == "dsp"

    def test_space_to_hyphen(self):
        """Should convert spaces to hyphens."""
        assert category_anchor("Audio Interface") == "audio-interface"


class TestGenerateReadme:
    """Tests for generate_readme function."""

    def test_generate_from_empty_db(self):
        """Should handle empty database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            init_db(db_path)
            content = generate_readme(db_path)
            assert "No entries yet" in content
        finally:
            db_path.unlink(missing_ok=True)

    def test_generate_with_entries(self):
        """Should generate README with entries."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            session = init_db(db_path)
            entries = [
                Entry(
                    name="test-project",
                    category="dsp",
                    description="A test project",
                    repo="https://github.com/test/test",
                ),
                Entry(
                    name="another-project",
                    category="analysis",
                    description="Another project",
                    url="https://example.com",
                ),
            ]
            for e in entries:
                session.add(e)
            session.commit()
            session.close()

            content = generate_readme(db_path)

            assert "test-project" in content
            assert "another-project" in content
            assert "A test project" in content
            assert "2 projects" in content or "**2**" in content
        finally:
            db_path.unlink(missing_ok=True)

    def test_generate_to_file(self):
        """Should write to output file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            output_path = Path(f.name)

        try:
            session = init_db(db_path)
            entry = Entry(
                name="test",
                category="dsp",
                description="Test",
                repo="https://github.com/test/test",
            )
            session.add(entry)
            session.commit()
            session.close()

            generate_readme(db_path, output_path=output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "test" in content
        finally:
            db_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    def test_entries_grouped_by_category(self):
        """Should group entries by category."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            session = init_db(db_path)
            entries = [
                Entry(name="dsp1", category="dsp", description="DSP 1", repo="https://github.com/a/a"),
                Entry(name="dsp2", category="dsp", description="DSP 2", repo="https://github.com/b/b"),
                Entry(name="analysis1", category="analysis", description="Analysis 1", repo="https://github.com/c/c"),
            ]
            for e in entries:
                session.add(e)
            session.commit()
            session.close()

            content = generate_readme(db_path)

            # Both DSP entries should appear together
            assert "## Dsp" in content
            assert "## Analysis" in content
        finally:
            db_path.unlink(missing_ok=True)
