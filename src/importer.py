"""Import entries from YAML into SQLite database."""

from pathlib import Path
from typing import Optional

import yaml

from src.model import Entry, init_db
from src.schema import validate_entries


def import_from_yaml(
    yaml_path: Path,
    db_path: Optional[Path] = None,
    skip_duplicates: bool = True,
    echo: bool = False,
) -> tuple[int, int, list[str]]:
    """
    Import entries from a YAML file into the database.

    Args:
        yaml_path: Path to the YAML file containing entries
        db_path: Path to the SQLite database (uses default if None)
        skip_duplicates: If True, skip entries that already exist by name
        echo: If True, print SQL statements

    Returns:
        Tuple of (imported_count, skipped_count, error_messages)
    """
    # Load and validate YAML
    with open(yaml_path) as f:
        raw_entries = yaml.safe_load(f)

    result = validate_entries(raw_entries)

    if not result.is_valid:
        errors = [f"{entry.get('name', 'UNKNOWN')}: {err}" for _, entry, err in result.errors]
        return 0, 0, errors

    # Initialize database
    session = init_db(db_path, echo)

    imported = 0
    skipped = 0
    errors = []

    # Track names we've already processed in this import
    processed_names = set()

    for entry_schema in result.valid:
        # Skip duplicates within the same import
        if entry_schema.name in processed_names:
            skipped += 1
            continue
        processed_names.add(entry_schema.name)

        # Check if entry already exists in database
        existing = session.query(Entry).filter_by(name=entry_schema.name).first()

        if existing:
            if skip_duplicates:
                skipped += 1
                continue
            else:
                # Update existing entry
                existing.category = entry_schema.category
                existing.url = entry_schema.url
                existing.repo = entry_schema.repo
                existing.description = entry_schema.desc
                imported += 1
        else:
            # Create new entry
            entry = Entry(
                name=entry_schema.name,
                category=entry_schema.category,
                url=entry_schema.url,
                repo=entry_schema.repo,
                description=entry_schema.desc,
            )
            session.add(entry)
            imported += 1

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        errors.append(f"Database error: {e}")
        return 0, 0, errors
    finally:
        session.close()

    return imported, skipped, errors


def export_to_yaml(db_path: Optional[Path] = None, output_path: Optional[Path] = None) -> int:
    """
    Export entries from database to YAML file.

    Args:
        db_path: Path to the SQLite database
        output_path: Path for output YAML file

    Returns:
        Number of entries exported
    """
    from src.model import get_session

    session = get_session(db_path)

    entries = session.query(Entry).order_by(Entry.name).all()

    yaml_entries = []
    for entry in entries:
        yaml_entry = {
            "name": entry.name,
            "category": entry.category,
            "desc": entry.description,
        }
        if entry.url:
            yaml_entry["url"] = entry.url
        else:
            yaml_entry["url"] = None
        if entry.repo:
            yaml_entry["repo"] = entry.repo

        yaml_entries.append(yaml_entry)

    session.close()

    if output_path:
        with open(output_path, "w") as f:
            for entry in yaml_entries:
                f.write(yaml.dump([entry], sort_keys=False, indent=2))
                f.write("\n")

    return len(yaml_entries)


if __name__ == "__main__":
    import sys

    entries_path = Path(__file__).parent.parent / "data" / "entries.yml"

    print(f"Importing from {entries_path}...")
    imported, skipped, errors = import_from_yaml(entries_path)

    print(f"Imported: {imported}")
    print(f"Skipped (duplicates): {skipped}")

    if errors:
        print("Errors:")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)

    print("Import complete.")
