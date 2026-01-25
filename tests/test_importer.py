"""Tests for YAML import functionality."""

import yaml

from src.importer import export_to_yaml, import_from_yaml
from src.model import Entry, get_session


class TestImportFromYaml:
    """Tests for import_from_yaml function."""

    def test_import_valid_entries(self, sample_yaml, temp_db):
        """Should import valid entries successfully."""
        db_path, session = temp_db
        session.close()

        imported, skipped, errors = import_from_yaml(sample_yaml, db_path)

        assert imported == 3
        assert skipped == 0
        assert len(errors) == 0

        # Verify entries in database
        session = get_session(db_path)
        entries = session.query(Entry).all()
        assert len(entries) == 3
        session.close()

    def test_import_skips_duplicates(self, temp_yaml, temp_db):
        """Should skip duplicate entries when skip_duplicates=True."""
        db_path, session = temp_db
        session.close()

        entries = [
            {"name": "dupe", "category": "dsp", "desc": "First", "repo": "https://github.com/a/a"},
            {"name": "dupe", "category": "analysis", "desc": "Second", "repo": "https://github.com/b/b"},
            {"name": "unique", "category": "dsp", "desc": "Unique", "repo": "https://github.com/c/c"},
        ]
        with open(temp_yaml, "w") as f:
            yaml.dump(entries, f)

        imported, skipped, errors = import_from_yaml(temp_yaml, db_path)

        assert imported == 2  # dupe + unique
        assert skipped == 1  # second dupe
        assert len(errors) == 0

    def test_import_rejects_invalid_entries(self, temp_yaml, temp_db):
        """Should reject invalid entries with errors."""
        db_path, session = temp_db
        session.close()

        entries = [
            {"name": "", "category": "dsp", "desc": "Bad", "repo": "https://github.com/a/a"},
        ]
        with open(temp_yaml, "w") as f:
            yaml.dump(entries, f)

        imported, skipped, errors = import_from_yaml(temp_yaml, db_path)

        assert imported == 0
        assert len(errors) > 0

    def test_import_twice_skips_existing(self, sample_yaml, temp_db):
        """Importing same file twice should skip existing entries."""
        db_path, session = temp_db
        session.close()

        # First import
        imported1, skipped1, errors1 = import_from_yaml(sample_yaml, db_path)
        assert imported1 == 3
        assert skipped1 == 0

        # Second import
        imported2, skipped2, errors2 = import_from_yaml(sample_yaml, db_path)
        assert imported2 == 0
        assert skipped2 == 3  # All skipped as duplicates


class TestExportToYaml:
    """Tests for export_to_yaml function."""

    def test_export_entries(self, temp_db, temp_yaml):
        """Should export entries to YAML."""
        db_path, session = temp_db

        # Add some entries
        entries = [
            Entry(name="alpha", category="dsp", description="Alpha project", repo="https://github.com/a/a"),
            Entry(name="beta", category="analysis", description="Beta project", url="https://beta.com"),
        ]
        for e in entries:
            session.add(e)
        session.commit()
        session.close()

        # Export
        count = export_to_yaml(db_path, temp_yaml)
        assert count == 2

        # Verify YAML content
        with open(temp_yaml) as f:
            content = f.read()
            exported = list(yaml.safe_load_all(content))

        # yaml.safe_load_all returns documents, but our format is single doc
        with open(temp_yaml) as f:
            exported = yaml.safe_load(f)

        assert len(exported) == 2
        # Should be sorted by name
        assert exported[0]["name"] == "alpha"
        assert exported[1]["name"] == "beta"

    def test_export_empty_database(self, temp_db, temp_yaml):
        """Should handle empty database gracefully."""
        db_path, session = temp_db
        session.close()

        count = export_to_yaml(db_path, temp_yaml)
        assert count == 0
