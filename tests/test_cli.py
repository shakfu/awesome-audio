"""Tests for CLI commands."""

import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner

from src.cli import cli


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_valid_file(self, sample_yaml):
        """Should validate a correct YAML file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--yaml", str(sample_yaml)])
        assert result.exit_code == 0
        assert "Validation passed!" in result.output

    def test_validate_file_with_errors(self, temp_yaml):
        """Should report errors for invalid entries."""
        entries = [
            {"name": "", "category": "dsp", "desc": "Bad", "repo": "https://github.com/a/a"},
        ]
        with open(temp_yaml, "w") as f:
            yaml.dump(entries, f)

        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--yaml", str(temp_yaml)])
        assert result.exit_code == 1
        assert "ERRORS:" in result.output

    def test_validate_file_with_duplicates(self, temp_yaml):
        """Should report duplicates."""
        entries = [
            {"name": "dupe", "category": "dsp", "desc": "First", "repo": "https://github.com/a/a"},
            {"name": "dupe", "category": "dsp", "desc": "Second", "repo": "https://github.com/b/b"},
        ]
        with open(temp_yaml, "w") as f:
            yaml.dump(entries, f)

        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--yaml", str(temp_yaml)])
        assert result.exit_code == 1
        assert "DUPLICATES:" in result.output


class TestImportCommand:
    """Tests for import command."""

    def test_import_creates_database(self, sample_yaml):
        """Should create database from YAML."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            result = runner.invoke(cli, [
                "import",
                "--yaml", str(sample_yaml),
                "--db", str(db_path)
            ])
            assert result.exit_code == 0
            assert "Import complete" in result.output
            assert "Imported: 3" in result.output
        finally:
            db_path.unlink(missing_ok=True)


class TestListCommand:
    """Tests for list command."""

    def test_list_entries(self, sample_yaml):
        """Should list entries from database."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            # First import
            runner.invoke(cli, [
                "import",
                "--yaml", str(sample_yaml),
                "--db", str(db_path)
            ])

            # Then list
            result = runner.invoke(cli, ["list", "--db", str(db_path)])
            assert result.exit_code == 0
            assert "test-project-1" in result.output
            assert "Total: 3" in result.output
        finally:
            db_path.unlink(missing_ok=True)

    def test_list_with_category_filter(self, sample_yaml):
        """Should filter by category."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            runner.invoke(cli, [
                "import",
                "--yaml", str(sample_yaml),
                "--db", str(db_path)
            ])

            result = runner.invoke(cli, ["list", "--db", str(db_path), "-c", "dsp"])
            assert result.exit_code == 0
            assert "test-project-1" in result.output
            assert "Total: 1" in result.output
        finally:
            db_path.unlink(missing_ok=True)

    def test_list_json_format(self, sample_yaml):
        """Should output JSON format."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            runner.invoke(cli, [
                "import",
                "--yaml", str(sample_yaml),
                "--db", str(db_path)
            ])

            result = runner.invoke(cli, ["list", "--db", str(db_path), "-f", "json"])
            assert result.exit_code == 0
            import json
            data = json.loads(result.output)
            assert len(data) == 3
        finally:
            db_path.unlink(missing_ok=True)


class TestSearchCommand:
    """Tests for search command."""

    def test_search_by_name(self, sample_yaml):
        """Should find entries by name."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            runner.invoke(cli, [
                "import",
                "--yaml", str(sample_yaml),
                "--db", str(db_path)
            ])

            result = runner.invoke(cli, ["search", "project-1", "--db", str(db_path)])
            assert result.exit_code == 0
            assert "test-project-1" in result.output
            assert "Found 1" in result.output
        finally:
            db_path.unlink(missing_ok=True)

    def test_search_no_results(self, sample_yaml):
        """Should handle no results gracefully."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            runner.invoke(cli, [
                "import",
                "--yaml", str(sample_yaml),
                "--db", str(db_path)
            ])

            result = runner.invoke(cli, ["search", "nonexistent", "--db", str(db_path)])
            assert result.exit_code == 0
            assert "No entries found" in result.output
        finally:
            db_path.unlink(missing_ok=True)


class TestStatsCommand:
    """Tests for stats command."""

    def test_stats_shows_counts(self, sample_yaml):
        """Should show database statistics."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            runner.invoke(cli, [
                "import",
                "--yaml", str(sample_yaml),
                "--db", str(db_path)
            ])

            result = runner.invoke(cli, ["stats", "--db", str(db_path)])
            assert result.exit_code == 0
            assert "Total entries: 3" in result.output
            assert "Categories:" in result.output
        finally:
            db_path.unlink(missing_ok=True)


class TestCategoriesCommand:
    """Tests for categories command."""

    def test_categories_lists_all(self):
        """Should list canonical categories."""
        runner = CliRunner()
        result = runner.invoke(cli, ["categories"])
        assert result.exit_code == 0
        assert "dsp" in result.output
        assert "analysis" in result.output
        assert "Canonical Categories:" in result.output
