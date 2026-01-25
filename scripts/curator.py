#!/usr/bin/env python3
"""
curator: A zero-dependency CLI tool for managing curated project lists.

Zero external dependencies - stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import ssl
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from string import Template
from typing import Any, Callable, Optional

__version__ = "0.1.0"

# =============================================================================
# Configuration
# =============================================================================

# Auto-detect project root: if curator.py is in scripts/, go up one level
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent if _SCRIPT_DIR.name == "scripts" else _SCRIPT_DIR
DEFAULT_JSON = _PROJECT_ROOT / "data" / "entries.json"
DEFAULT_DB = _PROJECT_ROOT / "data" / "curator.db"


def load_data(json_path: Optional[Path] = None) -> dict[str, Any]:
    """Load the full data structure (categories + entries) from JSON."""
    path = json_path or DEFAULT_JSON
    if not path.exists():
        return {"categories": [], "entries": []}
    with open(path) as f:
        data: dict[str, Any] = json.load(f)
    # Handle legacy format (just a list of entries)
    if isinstance(data, list):
        return {"categories": [], "entries": data}
    return data


def save_data(data: dict[str, Any], json_path: Optional[Path] = None) -> None:
    """Save the full data structure to JSON."""
    path = json_path or DEFAULT_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def load_categories(json_path: Optional[Path] = None) -> set[str]:
    """Load categories from JSON file."""
    data = load_data(json_path)
    return set(data.get("categories", []))


def save_categories(categories: set[str], json_path: Optional[Path] = None) -> None:
    """Save categories to JSON file."""
    data = load_data(json_path)
    data["categories"] = sorted(categories)
    save_data(data, json_path)


def sort_entries_file(
    json_path: Optional[Path] = None, by_category: bool = False
) -> tuple[int, int]:
    """Sort entries.json file: categories alphabetically, entries by name or category+name.

    Args:
        json_path: Path to JSON file (defaults to DEFAULT_JSON)
        by_category: If True, sort entries by category first, then by name.
                     If False, sort entries by name only.

    Returns:
        Tuple of (num_categories, num_entries) sorted.
    """
    data = load_data(json_path)

    # Sort categories alphabetically
    categories = data.get("categories", [])
    data["categories"] = sorted(categories, key=str.lower)

    # Sort entries
    entries = data.get("entries", [])
    if by_category:
        data["entries"] = sorted(
            entries,
            key=lambda e: (e.get("category", "").lower(), e.get("name", "").lower()),
        )
    else:
        data["entries"] = sorted(entries, key=lambda e: e.get("name", "").lower())

    save_data(data, json_path)
    return len(data["categories"]), len(data["entries"])


# =============================================================================
# Database (sqlite3)
# =============================================================================

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    url TEXT,
    repo TEXT,
    description TEXT NOT NULL,
    keywords TEXT,
    last_updated DATE,
    last_checked DATE,
    stars INTEGER,
    forks INTEGER,
    language TEXT,
    license TEXT,
    archived BOOLEAN DEFAULT 0,
    last_pushed DATE
)
"""

# Columns added in schema migration
_MIGRATION_COLUMNS = [
    ("stars", "INTEGER"),
    ("forks", "INTEGER"),
    ("language", "TEXT"),
    ("license", "TEXT"),
    ("archived", "BOOLEAN DEFAULT 0"),
    ("last_pushed", "DATE"),
]


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize database and return connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(DB_SCHEMA)
    conn.commit()
    _migrate_db(conn)
    return conn


def _migrate_db(conn: sqlite3.Connection) -> None:
    """Add missing columns to existing database tables."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(entry)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    for col_name, col_type in _MIGRATION_COLUMNS:
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE entry ADD COLUMN {col_name} {col_type}")

    conn.commit()


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class Entry:
    """Database entry."""

    id: Optional[int]
    name: str
    category: str
    url: Optional[str]
    repo: Optional[str]
    description: str
    keywords: Optional[str] = None
    last_updated: Optional[str] = None
    last_checked: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    language: Optional[str] = None
    license: Optional[str] = None
    archived: Optional[bool] = None
    last_pushed: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Entry:
        return cls(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            url=row["url"],
            repo=row["repo"],
            description=row["description"],
            keywords=row["keywords"],
            last_updated=row["last_updated"],
            last_checked=row["last_checked"],
            stars=row["stars"] if "stars" in row.keys() else None,
            forks=row["forks"] if "forks" in row.keys() else None,
            language=row["language"] if "language" in row.keys() else None,
            license=row["license"] if "license" in row.keys() else None,
            archived=bool(row["archived"])
            if "archived" in row.keys() and row["archived"] is not None
            else None,
            last_pushed=row["last_pushed"] if "last_pushed" in row.keys() else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "url": self.url,
            "repo": self.repo,
            "description": self.description,
            "keywords": self.keywords,
            "last_updated": self.last_updated,
            "last_checked": self.last_checked,
            "stars": self.stars,
            "forks": self.forks,
            "language": self.language,
            "license": self.license,
            "archived": self.archived,
            "last_pushed": self.last_pushed,
        }


# =============================================================================
# Category Helpers
# =============================================================================


def normalize_category_input(category: str) -> str:
    """Normalize user input to canonical category format (lowercase, hyphenated)."""
    return category.strip().lower().replace(" ", "-").replace("_", "-")


# =============================================================================
# Schema Validation
# =============================================================================


@dataclass
class ValidationResult:
    """Result of validating entries."""

    valid: list[dict[str, Any]] = field(default_factory=list)
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)
    warnings: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)
    duplicates: list[tuple[str, list[int]]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        return "\n".join(
            [
                f"Valid entries: {len(self.valid)}",
                f"Errors: {len(self.errors)}",
                f"Warnings: {len(self.warnings)}",
                f"Duplicates: {len(self.duplicates)}",
            ]
        )


def validate_entry(entry: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate a single entry. Returns (is_valid, error_message)."""
    name = entry.get("name", "")

    if not name or not str(name).strip():
        return False, "name cannot be empty"

    name = str(name).strip()
    if name.startswith("http://") or name.startswith("https://"):
        return False, f"name should not be a URL: {name}"

    desc = entry.get("desc", "")
    if not desc or not str(desc).strip():
        return False, "desc cannot be empty"

    url = entry.get("url")
    repo = entry.get("repo")
    if not url and not repo:
        return False, f"entry '{name}' must have url or repo"

    return True, None


def validate_entries(
    entries: list[dict[str, Any]],
    strict_categories: bool = True,
    json_path: Optional[Path] = None,
) -> ValidationResult:
    """Validate a list of entry dictionaries.

    Args:
        entries: List of entry dictionaries to validate
        strict_categories: If True, invalid categories are errors; if False, warnings
        json_path: Path to JSON file (for loading categories)
    """
    result = ValidationResult()
    seen_names: dict[str, list[int]] = {}
    categories = load_categories(json_path)

    for idx, entry in enumerate(entries):
        name = entry.get("name", "")

        if name:
            if name not in seen_names:
                seen_names[name] = []
            seen_names[name].append(idx + 1)

        is_valid, error = validate_entry(entry)
        if not is_valid:
            result.errors.append((idx + 1, entry, error or "Unknown error"))
            continue

        # Check category
        category = entry.get("category", "")
        normalized_cat = normalize_category_input(category)
        if normalized_cat not in categories:
            msg = f"invalid category: '{category}'"
            if strict_categories:
                result.errors.append((idx + 1, entry, msg))
            else:
                result.warnings.append((idx + 1, entry, msg))
                result.valid.append(entry)
        else:
            # Warn if category is not in canonical format
            if category != normalized_cat:
                msg = f"category '{category}' should be '{normalized_cat}'"
                result.warnings.append((idx + 1, entry, msg))
            result.valid.append(entry)

    for name, indices in seen_names.items():
        if len(indices) > 1:
            result.duplicates.append((name, indices))

    return result


def load_and_validate(path: Path) -> ValidationResult:
    """Load a JSON file and validate its entries."""
    entries = load_entries(path)
    return validate_entries(entries, json_path=path)


# =============================================================================
# Import/Export
# =============================================================================


def import_from_json(
    json_path: Path,
    db_path: Path,
    skip_duplicates: bool = True,
) -> tuple[int, int, list[str]]:
    """Import entries from JSON to database."""
    raw_entries = load_entries(json_path)

    result = validate_entries(raw_entries, json_path=json_path)
    if not result.is_valid:
        errors = [
            f"{entry.get('name', 'UNKNOWN')}: {err}" for _, entry, err in result.errors
        ]
        return 0, 0, errors

    conn = init_db(db_path)
    cursor = conn.cursor()

    imported = 0
    skipped = 0
    errors = []
    processed_names = set()

    for entry in result.valid:
        name = entry["name"]
        if name in processed_names:
            skipped += 1
            continue
        processed_names.add(name)

        cursor.execute("SELECT id FROM entry WHERE name = ?", (name,))
        existing = cursor.fetchone()

        if existing:
            if skip_duplicates:
                skipped += 1
            else:
                cursor.execute(
                    """UPDATE entry SET category=?, url=?, repo=?, description=?
                       WHERE name=?""",
                    (
                        entry["category"],
                        entry.get("url"),
                        entry.get("repo"),
                        entry["desc"],
                        name,
                    ),
                )
                imported += 1
        else:
            cursor.execute(
                """INSERT INTO entry (name, category, url, repo, description)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    name,
                    entry["category"],
                    entry.get("url"),
                    entry.get("repo"),
                    entry["desc"],
                ),
            )
            imported += 1

    conn.commit()
    conn.close()
    return imported, skipped, errors


def export_to_json(db_path: Path, output_path: Path) -> int:
    """Export entries from database to JSON."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entry ORDER BY name")
    rows = cursor.fetchall()
    conn.close()

    json_entries = []
    for row in rows:
        entry = {
            "name": row["name"],
            "category": row["category"],
            "desc": row["description"],
            "url": row["url"],
            "repo": row["repo"],
        }
        json_entries.append(entry)

    with open(output_path, "w") as f:
        json.dump(json_entries, f, indent=2)

    return len(json_entries)


# =============================================================================
# Link Checker (using urllib + ThreadPoolExecutor)
# =============================================================================


class LinkStatus(Enum):
    """Status of a checked link."""

    OK = "ok"
    REDIRECT = "redirect"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class LinkResult:
    """Result of checking a single link."""

    url: str
    status: LinkStatus
    status_code: Optional[int] = None
    redirect_url: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None


@dataclass
class CheckResult:
    """Result of checking all links for an entry."""

    entry_name: str
    url_result: Optional[LinkResult] = None
    repo_result: Optional[LinkResult] = None
    checked_at: datetime = field(default_factory=datetime.now)

    @property
    def has_issues(self) -> bool:
        for result in [self.url_result, self.repo_result]:
            if result and result.status not in (
                LinkStatus.OK,
                LinkStatus.REDIRECT,
                LinkStatus.SKIPPED,
            ):
                return True
        return False


# Create SSL context that doesn't verify (for link checking)
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE


def check_url(url: str, timeout: float = 10.0) -> LinkResult:
    """Check a single URL."""
    if not url:
        return LinkResult(url="", status=LinkStatus.SKIPPED)

    import time

    start_time = time.time()

    try:
        req = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "curator/0.6.0"}
        )
        with urllib.request.urlopen(
            req, timeout=timeout, context=_ssl_context
        ) as response:
            elapsed_ms = (time.time() - start_time) * 1000
            final_url = response.geturl()

            if final_url != url:
                return LinkResult(
                    url=url,
                    status=LinkStatus.REDIRECT,
                    status_code=response.status,
                    redirect_url=final_url,
                    response_time_ms=elapsed_ms,
                )
            return LinkResult(
                url=url,
                status=LinkStatus.OK,
                status_code=response.status,
                response_time_ms=elapsed_ms,
            )
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        if e.code == 404:
            return LinkResult(
                url=url,
                status=LinkStatus.NOT_FOUND,
                status_code=e.code,
                response_time_ms=elapsed_ms,
            )
        elif e.code == 405:
            # Method not allowed - try GET
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "curator/0.6.0"}
                )
                with urllib.request.urlopen(
                    req, timeout=timeout, context=_ssl_context
                ) as response:
                    elapsed_ms = (time.time() - start_time) * 1000
                    final_url = response.geturl()
                    if final_url != url:
                        return LinkResult(
                            url=url,
                            status=LinkStatus.REDIRECT,
                            status_code=response.status,
                            redirect_url=final_url,
                            response_time_ms=elapsed_ms,
                        )
                    return LinkResult(
                        url=url,
                        status=LinkStatus.OK,
                        status_code=response.status,
                        response_time_ms=elapsed_ms,
                    )
            except Exception as e2:
                return LinkResult(
                    url=url,
                    status=LinkStatus.ERROR,
                    error_message=str(e2),
                    response_time_ms=elapsed_ms,
                )
        return LinkResult(
            url=url,
            status=LinkStatus.ERROR,
            status_code=e.code,
            error_message=f"HTTP {e.code}",
            response_time_ms=elapsed_ms,
        )
    except TimeoutError:
        return LinkResult(url=url, status=LinkStatus.TIMEOUT, error_message="Timeout")
    except Exception as e:
        return LinkResult(url=url, status=LinkStatus.ERROR, error_message=str(e))


def check_entry(
    name: str, url: Optional[str], repo: Optional[str], timeout: float
) -> CheckResult:
    """Check all links for a single entry."""
    url_result = check_url(url, timeout) if url else None
    repo_result = check_url(repo, timeout) if repo else None
    return CheckResult(entry_name=name, url_result=url_result, repo_result=repo_result)


def run_check(
    entries: list[dict[str, Any]],
    concurrency: int = 10,
    timeout: float = 10.0,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[CheckResult]:
    """Check all entries using thread pool."""
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                check_entry,
                entry.get("name", "unknown"),
                entry.get("url"),
                entry.get("repo"),
                timeout,
            ): (i, entry)
            for i, entry in enumerate(entries)
        }

        for future in as_completed(futures):
            i, entry = futures[future]
            result = future.result()
            results.append(result)
            if progress_callback:
                progress_callback(len(results), len(entries), entry.get("name", ""))

    return results


# =============================================================================
# GitHub API (using urllib + ThreadPoolExecutor)
# =============================================================================

GITHUB_API = "https://api.github.com"
GITHUB_REPO_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$"
)


@dataclass
class RepoStats:
    """Statistics for a GitHub repository."""

    owner: str
    name: str
    full_name: str
    description: Optional[str]
    stars: int
    forks: int
    open_issues: int
    watchers: int
    language: Optional[str]
    license: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    pushed_at: Optional[datetime]
    archived: bool
    fork: bool
    default_branch: str
    topics: list[str]
    homepage: Optional[str] = None

    @property
    def days_since_push(self) -> Optional[int]:
        if self.pushed_at:
            return (datetime.now() - self.pushed_at).days
        return None

    @property
    def is_active(self) -> bool:
        days = self.days_since_push
        return days is not None and days < 365

    @property
    def activity_status(self) -> str:
        if self.archived:
            return "archived"
        days = self.days_since_push
        if days is None:
            return "unknown"
        if days < 30:
            return "very active"
        if days < 90:
            return "active"
        if days < 365:
            return "maintained"
        return "stale"


@dataclass
class RepoResult:
    """Result of fetching repo stats."""

    entry_name: str
    repo_url: str
    stats: Optional[RepoStats] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.stats is not None


def parse_github_url(url: str) -> Optional[tuple[str, str]]:
    """Extract owner and repo name from a GitHub URL."""
    if not url:
        return None
    match = GITHUB_REPO_PATTERN.match(url)
    if match:
        return match.group(1), match.group(2)
    return None


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def fetch_repo_stats(owner: str, repo: str) -> RepoStats:
    """Fetch repository statistics from GitHub API."""
    token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "curator/0.6.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())

    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
        return None

    license_name = None
    if data.get("license"):
        license_name = data["license"].get("spdx_id") or data["license"].get("name")

    return RepoStats(
        owner=data["owner"]["login"],
        name=data["name"],
        full_name=data["full_name"],
        description=data.get("description"),
        stars=data.get("stargazers_count", 0),
        forks=data.get("forks_count", 0),
        open_issues=data.get("open_issues_count", 0),
        watchers=data.get("subscribers_count", 0),
        language=data.get("language"),
        license=license_name,
        created_at=parse_date(data.get("created_at")),
        updated_at=parse_date(data.get("updated_at")),
        pushed_at=parse_date(data.get("pushed_at")),
        archived=data.get("archived", False),
        fork=data.get("fork", False),
        default_branch=data.get("default_branch", "main"),
        topics=data.get("topics", []),
        homepage=data.get("homepage") or None,
    )


def fetch_entry_stats(entry_name: str, repo_url: str) -> RepoResult:
    """Fetch stats for a single entry's repository."""
    parsed = parse_github_url(repo_url)
    if not parsed:
        return RepoResult(entry_name=entry_name, repo_url=repo_url, error="Not GitHub")

    owner, repo = parsed
    try:
        stats = fetch_repo_stats(owner, repo)
        return RepoResult(entry_name=entry_name, repo_url=repo_url, stats=stats)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return RepoResult(
                entry_name=entry_name, repo_url=repo_url, error="Not found"
            )
        elif e.code == 403:
            return RepoResult(
                entry_name=entry_name, repo_url=repo_url, error="Rate limited"
            )
        return RepoResult(
            entry_name=entry_name, repo_url=repo_url, error=f"HTTP {e.code}"
        )
    except Exception as e:
        return RepoResult(entry_name=entry_name, repo_url=repo_url, error=str(e))


def run_fetch_stats(
    entries: list[dict[str, Any]],
    concurrency: int = 5,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[RepoResult]:
    """Fetch stats for all entries with GitHub repos using thread pool."""
    github_entries = [
        e for e in entries if e.get("repo") and "github.com" in e.get("repo", "")
    ]

    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                fetch_entry_stats, entry.get("name", "unknown"), entry.get("repo", "")
            ): (i, entry)
            for i, entry in enumerate(github_entries)
        }

        for future in as_completed(futures):
            i, entry = futures[future]
            result = future.result()
            results.append(result)
            if progress_callback:
                progress_callback(
                    len(results), len(github_entries), entry.get("name", "")
                )

    return results


# =============================================================================
# Entry API (CRUD operations on JSON file with DB sync)
# =============================================================================


def load_entries(json_path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Load entries from JSON file."""
    data = load_data(json_path)
    entries: list[dict[str, Any]] = data.get("entries", [])
    return entries


def save_entries(
    entries: list[dict[str, Any]], json_path: Optional[Path] = None
) -> None:
    """Save entries to JSON file (preserves categories)."""
    data = load_data(json_path)
    data["entries"] = entries
    save_data(data, json_path)


def sync_to_db(
    json_path: Optional[Path] = None, db_path: Optional[Path] = None
) -> tuple[int, int]:
    """Sync JSON entries to database. Returns (imported, skipped)."""
    json_file = json_path or DEFAULT_JSON
    db_file = db_path or DEFAULT_DB
    imported, skipped, _ = import_from_json(json_file, db_file, skip_duplicates=False)
    return imported, skipped


def add_entry(
    name: str,
    category: str,
    desc: str,
    url: Optional[str] = None,
    repo: Optional[str] = None,
    json_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
    sync: bool = True,
) -> dict[str, Any]:
    """
    Add a new entry to the JSON file.

    Args:
        name: Project name
        category: Category (should be from CATEGORIES)
        desc: Project description
        url: Optional project URL
        repo: Optional repository URL
        json_path: Path to JSON file (default: data/entries.json)
        db_path: Path to database (default: curator.db)
        sync: Whether to sync to database after adding

    Returns:
        The added entry dict

    Raises:
        ValueError: If validation fails (missing url/repo, invalid category, etc.)
        KeyError: If entry with same name already exists
    """
    if not url and not repo:
        raise ValueError("Must provide at least url or repo")

    # Normalize category input
    category = normalize_category_input(category)

    # Check category
    categories = load_categories(json_path)
    if category not in categories:
        raise ValueError(f"Unknown category: {category}")

    entry = {
        "name": name,
        "category": category,
        "desc": desc,
        "url": url,
        "repo": repo,
    }

    # Validate the entry
    is_valid, error = validate_entry(entry)
    if not is_valid:
        raise ValueError(error)

    # Load existing entries
    entries = load_entries(json_path)

    # Check for duplicates
    for existing in entries:
        if existing.get("name") == name:
            raise KeyError(f"Entry '{name}' already exists")

    # Add and save
    entries.append(entry)
    save_entries(entries, json_path)

    # Sync to database
    if sync:
        sync_to_db(json_path, db_path)

    return entry


def remove_entry(
    name: str,
    json_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
    sync: bool = True,
) -> dict[str, Any]:
    """
    Remove an entry from the JSON file.

    Args:
        name: Project name to remove
        json_path: Path to JSON file (default: data/entries.json)
        db_path: Path to database (default: curator.db)
        sync: Whether to sync to database after removing

    Returns:
        The removed entry dict

    Raises:
        KeyError: If entry not found
    """
    entries = load_entries(json_path)

    # Find the entry
    removed = None
    for e in entries:
        if e.get("name") == name:
            removed = e
            break

    if removed is None:
        raise KeyError(f"Entry '{name}' not found")

    # Remove and save
    entries = [e for e in entries if e.get("name") != name]
    save_entries(entries, json_path)

    # Sync to database (remove from DB too)
    if sync:
        db_file = db_path or DEFAULT_DB
        if db_file.exists():
            conn = get_connection(db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM entry WHERE name = ?", (name,))
            conn.commit()
            conn.close()

    return removed


def update_entry(
    name: str,
    category: Optional[str] = None,
    desc: Optional[str] = None,
    url: Optional[str] = None,
    repo: Optional[str] = None,
    json_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
    sync: bool = True,
) -> dict[str, Any]:
    """
    Update an existing entry in the JSON file.

    Args:
        name: Project name to update
        category: New category (optional)
        desc: New description (optional)
        url: New URL (optional, use empty string to clear)
        repo: New repo (optional, use empty string to clear)
        json_path: Path to JSON file (default: data/entries.json)
        db_path: Path to database (default: curator.db)
        sync: Whether to sync to database after updating

    Returns:
        The updated entry dict

    Raises:
        KeyError: If entry not found
        ValueError: If validation fails
    """
    entries = load_entries(json_path)

    # Find the entry
    found_idx = None
    for i, e in enumerate(entries):
        if e.get("name") == name:
            found_idx = i
            break

    if found_idx is None:
        raise KeyError(f"Entry '{name}' not found")

    entry = entries[found_idx]

    # Apply updates
    if category is not None:
        category = normalize_category_input(category)
        categories = load_categories(json_path)
        if category not in categories:
            raise ValueError(f"Unknown category: {category}")
        entry["category"] = category
    if desc is not None:
        entry["desc"] = desc
    if url is not None:
        entry["url"] = url if url else None
    if repo is not None:
        entry["repo"] = repo if repo else None

    # Validate the updated entry
    is_valid, error = validate_entry(entry)
    if not is_valid:
        raise ValueError(error)

    # Save
    entries[found_idx] = entry
    save_entries(entries, json_path)

    # Sync to database
    if sync:
        sync_to_db(json_path, db_path)

    return entry


def get_entry(name: str, json_path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Get an entry by name from the JSON file."""
    entries = load_entries(json_path)
    for e in entries:
        if e.get("name") == name:
            return e
    return None


def add_entry_from_github(
    github_url: str,
    category: str,
    name: Optional[str] = None,
    desc: Optional[str] = None,
    json_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
    sync: bool = True,
) -> dict[str, Any]:
    """
    Add a new entry by fetching metadata from a GitHub URL.

    Args:
        github_url: GitHub repository URL
        category: Category (should be from CATEGORIES)
        name: Override for project name (default: repo name)
        desc: Override for description (default: GitHub description)
        json_path: Path to JSON file (default: data/entries.json)
        db_path: Path to database (default: curator.db)
        sync: Whether to sync to database after adding

    Returns:
        The added entry dict

    Raises:
        ValueError: If URL is invalid, not a GitHub URL, or API fetch fails
        KeyError: If entry with same name already exists
    """
    # Parse GitHub URL
    parsed = parse_github_url(github_url)
    if not parsed:
        raise ValueError(f"Invalid GitHub URL: {github_url}")

    owner, repo = parsed

    # Fetch metadata from GitHub API
    try:
        stats = fetch_repo_stats(owner, repo)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Repository not found: {github_url}")
        elif e.code == 403:
            raise ValueError("GitHub API rate limit exceeded. Set GITHUB_TOKEN.")
        raise ValueError(f"GitHub API error: HTTP {e.code}")
    except Exception as e:
        raise ValueError(f"Failed to fetch GitHub data: {e}")

    # Use provided values or defaults from GitHub
    entry_name = name or stats.name
    entry_desc = (
        desc or stats.description or f"A {stats.language or 'software'} project"
    )

    # Build the GitHub repo URL (canonical form)
    repo_url = f"https://github.com/{stats.full_name}"

    # Use homepage if available, otherwise None
    entry_url = stats.homepage if stats.homepage else None

    # Convert topics to comma-separated keywords
    keywords = ", ".join(stats.topics) if stats.topics else None

    # Format last_pushed as date string
    last_pushed = stats.pushed_at.strftime("%Y-%m-%d") if stats.pushed_at else None

    # Add to JSON via existing add_entry
    entry = add_entry(
        name=entry_name,
        category=category,
        desc=entry_desc,
        url=entry_url,
        repo=repo_url,
        json_path=json_path,
        db_path=db_path,
        sync=False,  # We'll sync manually to include GitHub fields
    )

    # Now update the database with GitHub-specific fields
    if sync:
        db_file = db_path or DEFAULT_DB
        conn = init_db(db_file)
        cursor = conn.cursor()

        # First sync the basic entry
        sync_to_db(json_path, db_file)

        # Then update with GitHub fields
        cursor.execute(
            """UPDATE entry SET
               keywords = ?,
               stars = ?,
               forks = ?,
               language = ?,
               license = ?,
               archived = ?,
               last_pushed = ?
               WHERE name = ?""",
            (
                keywords,
                stats.stars,
                stats.forks,
                stats.language,
                stats.license,
                1 if stats.archived else 0,
                last_pushed,
                entry_name,
            ),
        )
        conn.commit()
        conn.close()

    return entry


# =============================================================================
# README Generator (string.Template)
# =============================================================================

DEFAULT_TEMPLATE = Template("""# Awesome Audio

> A curated guide to open-source audio and music projects.

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)

This list contains **$total_entries** projects across **$total_categories** categories.

*Last updated: $generated_at*

## Contents

$toc

---

$sections

---

## Contributing

Contributions welcome! Please read the contribution guidelines first.

## License

[![CC0](https://licensebuttons.net/p/zero/1.0/88x31.png)](http://creativecommons.org/publicdomain/zero/1.0/)

To the extent possible under law, the authors have waived all copyright and related rights to this work.
""")


def normalize_category(category: str) -> str:
    """Normalize a category string for display."""
    words = category.replace("-", " ").replace("_", " ").split()
    return " ".join(word.capitalize() for word in words)


def category_anchor(category: str) -> str:
    """Generate a markdown anchor from a category name."""
    return category.lower().replace(" ", "-").replace("_", "-")


def generate_readme(
    db_path: Path,
    template_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    force: bool = False,
) -> str:
    """Generate README.md from database entries."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entry ORDER BY category, name")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "# Awesome Audio\n\nNo entries yet.\n"

    groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        groups[row["category"]].append(row)

    toc_lines = []
    for cat_name in sorted(groups.keys()):
        title = normalize_category(cat_name)
        anchor = category_anchor(title)
        toc_lines.append(f"- [{title}](#{anchor})")

    section_lines = []
    for cat_name in sorted(groups.keys()):
        title = normalize_category(cat_name)
        section_lines.append(f"## {title}\n")

        for row in sorted(groups[cat_name], key=lambda r: r["name"].lower()):
            url = row["url"] or row["repo"]
            section_lines.append(
                f"- **[{row['name']}]({url})** - {row['description']}\n"
            )

        section_lines.append("")

    content = DEFAULT_TEMPLATE.substitute(
        total_entries=len(rows),
        total_categories=len(groups),
        generated_at=datetime.now().strftime("%Y-%m-%d"),
        toc="\n".join(toc_lines),
        sections="\n".join(section_lines),
    )

    if output_path:
        if output_path.exists() and not force:
            response = input(f"{output_path} already exists. Overwrite? [y/N]: ")
            if response.lower() not in ("y", "yes"):
                print("Aborted.")
                return content
        with open(output_path, "w") as f:
            f.write(content)

    return content


# =============================================================================
# Terminal Colors (ANSI)
# =============================================================================


class Color:
    """ANSI color codes."""

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def cprint(msg: str, color: str = "", bold: bool = False) -> None:
    """Print with color."""
    prefix = ""
    if bold:
        prefix += Color.BOLD
    prefix += color
    suffix = Color.RESET if (color or bold) else ""
    print(f"{prefix}{msg}{suffix}")


# =============================================================================
# CLI Commands
# =============================================================================


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate the entries JSON file."""
    path = Path(args.json) if args.json else DEFAULT_JSON
    result = load_and_validate(path)

    print(result.summary())
    print()

    if result.errors:
        cprint("ERRORS:", Color.RED, bold=True)
        for idx, entry, error in result.errors:
            print(f"  Entry {idx}: {entry.get('name', 'UNKNOWN')}")
            print(f"    {error}")
        print()

    if result.duplicates:
        cprint("DUPLICATES:", Color.YELLOW, bold=True)
        for name, indices in result.duplicates:
            print(f"  '{name}' appears at entries: {indices}")
        print()

    if result.warnings:
        cprint("WARNINGS:", Color.YELLOW)
        for idx, entry, warning in result.warnings:
            print(f"  Entry {idx}: {entry.get('name', 'UNKNOWN')}: {warning}")

    if result.is_valid and not result.duplicates:
        cprint("Validation passed!", Color.GREEN, bold=True)
        return 0
    return 1


def cmd_import(args: argparse.Namespace) -> int:
    """Import entries from JSON to SQLite database."""
    json_file = Path(args.json) if args.json else DEFAULT_JSON
    db_file = Path(args.db) if args.db else DEFAULT_DB

    print(f"Importing from {json_file} to {db_file}...")
    imported, skipped, errors = import_from_json(json_file, db_file, not args.update)

    print(f"Imported: {imported}")
    print(f"Skipped: {skipped}")

    if errors:
        cprint("Errors:", Color.RED)
        for err in errors:
            print(f"  {err}")
        return 1

    cprint("Import complete.", Color.GREEN)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export entries from SQLite database to JSON."""
    db_file = Path(args.db) if args.db else DEFAULT_DB
    out_file = Path(args.output)

    count = export_to_json(db_file, out_file)
    print(f"Exported {count} entries to {out_file}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all entries in the database."""
    db_file = Path(args.db) if args.db else DEFAULT_DB

    if not db_file.exists():
        cprint(f"Database not found: {db_file}", Color.RED)
        print("Run 'curator import' first to create the database.")
        return 1

    conn = get_connection(db_file)
    cursor = conn.cursor()

    if args.category:
        cursor.execute(
            "SELECT * FROM entry WHERE category LIKE ? ORDER BY name",
            (f"%{args.category}%",),
        )
    else:
        cursor.execute("SELECT * FROM entry ORDER BY name")

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No entries found.")
        return 0

    if args.format == "json":
        data = [dict(row) for row in rows]
        print(json.dumps(data, indent=2))
    else:
        print(f"{'Name':<30} {'Category':<20} {'URL/Repo':<50}")
        print("-" * 100)
        for r in rows:
            url = r["url"] or r["repo"] or ""
            if len(url) > 47:
                url = url[:47] + "..."
            print(f"{r['name']:<30} {r['category']:<20} {url:<50}")
        print(f"\nTotal: {len(rows)} entries")

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search entries by name or description."""
    db_file = Path(args.db) if args.db else DEFAULT_DB

    if not db_file.exists():
        cprint(f"Database not found: {db_file}", Color.RED)
        return 1

    conn = get_connection(db_file)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM entry WHERE name LIKE ? OR description LIKE ? OR category LIKE ?
           ORDER BY name""",
        (f"%{args.query}%", f"%{args.query}%", f"%{args.query}%"),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"No entries found matching '{args.query}'")
        return 0

    for r in rows:
        cprint(r["name"], Color.GREEN, bold=True)
        print(f"  Category: {r['category']}")
        print(f"  {r['description']}")
        if r["url"]:
            print(f"  URL: {r['url']}")
        if r["repo"]:
            print(f"  Repo: {r['repo']}")
        print()

    print(f"Found {len(rows)} entries matching '{args.query}'")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show statistics about the database."""
    db_file = Path(args.db) if args.db else DEFAULT_DB

    if not db_file.exists():
        cprint(f"Database not found: {db_file}", Color.RED)
        return 1

    conn = get_connection(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM entry")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM entry WHERE url IS NOT NULL")
    with_url = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM entry WHERE repo IS NOT NULL")
    with_repo = cursor.fetchone()[0]

    cursor.execute(
        "SELECT category, COUNT(*) as cnt FROM entry GROUP BY category ORDER BY cnt DESC"
    )
    categories = cursor.fetchall()
    conn.close()

    cprint("Database Statistics", Color.BLUE, bold=True)
    print(f"Total entries: {total}")
    print(f"With URL: {with_url}")
    print(f"With repo: {with_repo}")
    print()

    cprint("Categories:", Color.BLUE, bold=True)
    for row in categories:
        print(f"  {row['category']}: {row['cnt']}")

    return 0


def cmd_category_list(args: argparse.Namespace) -> int:
    """List all categories."""
    json_file = Path(args.json) if args.json else None
    categories = load_categories(json_file)

    cprint("Categories:", Color.BLUE, bold=True)
    for cat in sorted(categories):
        print(f"  {cat}")
    print(f"\nTotal: {len(categories)} categories")
    return 0


def cmd_category_add(args: argparse.Namespace) -> int:
    """Add a new category."""
    json_file = Path(args.json) if args.json else None
    name = normalize_category_input(args.name)

    categories = load_categories(json_file)
    if name in categories:
        cprint(f"Category '{name}' already exists", Color.YELLOW)
        return 1

    categories.add(name)
    save_categories(categories, json_file)
    cprint(f"Added category '{name}'", Color.GREEN)
    return 0


def cmd_category_rm(args: argparse.Namespace) -> int:
    """Remove a category."""
    json_file = Path(args.json) if args.json else None
    name = normalize_category_input(args.name)

    categories = load_categories(json_file)
    if name not in categories:
        cprint(f"Category '{name}' not found", Color.YELLOW)
        return 1

    # Check if category is in use
    entries = load_entries(json_file)
    in_use = [e["name"] for e in entries if e.get("category") == name]
    if in_use and not args.force:
        cprint(f"Category '{name}' is used by {len(in_use)} entries:", Color.RED)
        for entry_name in in_use[:5]:
            print(f"  {entry_name}")
        if len(in_use) > 5:
            print(f"  ... and {len(in_use) - 5} more")
        print("Use --force to remove anyway")
        return 1

    categories.remove(name)
    save_categories(categories, json_file)
    cprint(f"Removed category '{name}'", Color.GREEN)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check all URLs for broken links."""
    json_file = Path(args.json) if args.json else None
    entries = load_entries(json_file)

    print(f"Checking {len(entries)} entries...")

    def progress(current: int, total: int, name: str) -> None:
        print(f"  [{current}/{total}] {name}")

    results = run_check(entries, args.concurrency, args.timeout, progress)

    ok_count = 0
    redirect_count = 0
    issues = []

    for result in results:
        for link_result in [result.url_result, result.repo_result]:
            if link_result is None:
                continue
            if link_result.status == LinkStatus.OK:
                ok_count += 1
            elif link_result.status == LinkStatus.REDIRECT:
                redirect_count += 1
            elif link_result.status != LinkStatus.SKIPPED:
                issues.append((result.entry_name, link_result))

    print()
    cprint("Results:", Color.BLUE, bold=True)
    print(f"  OK: {ok_count}")
    print(f"  Redirects: {redirect_count}")
    print(f"  Issues: {len(issues)}")

    if issues:
        print()
        cprint("Issues found:", Color.RED, bold=True)
        for entry_name, link_result in issues:
            color = (
                Color.RED
                if link_result.status == LinkStatus.NOT_FOUND
                else Color.YELLOW
            )
            cprint(f"  {entry_name}", color)
            print(f"    URL: {link_result.url}")
            print(f"    Status: {link_result.status.value}")
            if link_result.error_message:
                print(f"    Error: {link_result.error_message}")
        return 1

    return 0


def cmd_github(args: argparse.Namespace) -> int:
    """Fetch GitHub statistics for all repositories."""
    json_file = Path(args.json) if args.json else None
    entries = load_entries(json_file)

    github_entries = [
        e for e in entries if e.get("repo") and "github.com" in e.get("repo", "")
    ]

    if not github_entries:
        print("No GitHub repositories found.")
        return 0

    token = get_github_token()
    if not token:
        cprint(
            "Warning: No GITHUB_TOKEN set. Rate limits will be strict.", Color.YELLOW
        )
        print("Set GITHUB_TOKEN or GH_TOKEN environment variable for higher limits.")
        print()

    print(f"Fetching stats for {len(github_entries)} GitHub repos...")

    def progress(current: int, total: int, name: str) -> None:
        print(f"  [{current}/{total}] {name}")

    results = run_fetch_stats(entries, args.concurrency, progress)

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    if not successful:
        cprint("No stats retrieved.", Color.RED)
        if failed:
            print("Errors:")
            for r in failed:
                print(f"  {r.entry_name}: {r.error}")
        return 1

    if args.sort == "stars":
        successful.sort(key=lambda r: r.stats.stars if r.stats else 0, reverse=True)
    elif args.sort == "activity":
        successful.sort(
            key=lambda r: (r.stats.days_since_push or 9999) if r.stats else 9999
        )
    else:
        successful.sort(key=lambda r: r.entry_name.lower())

    print()
    cprint("GitHub Statistics:", Color.BLUE, bold=True)
    print(f"{'Name':<25} {'Stars':>8} {'Forks':>7} {'Activity':<15} {'Language':<12}")
    print("-" * 75)

    for r in successful:
        s = r.stats
        if s is None:
            continue
        print(
            f"{r.entry_name:<25} {s.stars:>8} {s.forks:>7} "
            f"{s.activity_status:<15} {(s.language or 'N/A'):<12}"
        )
        if args.show_topics and s.topics:
            print(f"  Topics: {', '.join(s.topics)}")

    print()
    print(f"Total: {len(successful)} repos")
    total_stars = sum(r.stats.stars for r in successful if r.stats is not None)
    print(f"Combined stars: {total_stars:,}")

    stale = [
        r
        for r in successful
        if r.stats is not None and r.stats.activity_status in ("stale", "archived")
    ]
    if stale:
        print()
        cprint("Stale/Archived repos:", Color.YELLOW)
        for r in stale:
            if r.stats is None:
                continue
            days = r.stats.days_since_push
            print(
                f"  {r.entry_name}: {r.stats.activity_status} ({days} days since push)"
            )

    if failed:
        print()
        cprint(f"Failed to fetch {len(failed)} repos:", Color.RED)
        for r in failed:
            print(f"  {r.entry_name}: {r.error}")

    if args.update_db:
        db_file = Path(args.db) if args.db else DEFAULT_DB
        if not db_file.exists():
            cprint(f"Database not found: {db_file}", Color.RED)
            return 1

        conn = get_connection(db_file)
        cursor = conn.cursor()
        updated = 0
        for r in successful:
            if r.stats is not None and r.stats.topics:
                cursor.execute(
                    "UPDATE entry SET keywords = ? WHERE name = ?",
                    (", ".join(r.stats.topics), r.entry_name),
                )
                if cursor.rowcount > 0:
                    updated += 1
        conn.commit()
        conn.close()
        print()
        cprint(f"Updated {updated} entries with topics in database", Color.GREEN)

    return 0


def cmd_stale(args: argparse.Namespace) -> int:
    """Find stale/unmaintained projects using GitHub data."""
    json_file = Path(args.json) if args.json else None
    entries = load_entries(json_file)

    github_entries = [
        e for e in entries if e.get("repo") and "github.com" in e.get("repo", "")
    ]

    if not github_entries:
        print("No GitHub repositories found.")
        return 0

    token = get_github_token()
    if not token:
        cprint(
            "Warning: No GITHUB_TOKEN set. Rate limits will be strict.", Color.YELLOW
        )
        print()

    print(f"Checking {len(github_entries)} GitHub repos for staleness...")

    def progress(current: int, total: int, name: str) -> None:
        print(f"  [{current}/{total}] {name}")

    results = run_fetch_stats(entries, args.concurrency, progress)

    stale_repos: list[RepoResult] = []
    archived_repos: list[RepoResult] = []
    active_repos: list[RepoResult] = []

    for r in results:
        if not r.success or r.stats is None:
            continue
        if r.stats.archived:
            archived_repos.append(r)
        elif r.stats.days_since_push and r.stats.days_since_push > args.days:
            stale_repos.append(r)
        else:
            active_repos.append(r)

    stale_repos.sort(
        key=lambda r: (r.stats.days_since_push or 0) if r.stats else 0, reverse=True
    )

    print()
    cprint("Results:", Color.BLUE, bold=True)
    print(f"  Active: {len(active_repos)}")
    print(f"  Stale (>{args.days} days): {len(stale_repos)}")
    print(f"  Archived: {len(archived_repos)}")

    if archived_repos:
        print()
        cprint("Archived repositories:", Color.RED, bold=True)
        for r in archived_repos:
            print(f"  {r.entry_name}")
            print(f"    {r.repo_url}")

    if stale_repos:
        print()
        cprint(
            f"Stale repositories (>{args.days} days since push):",
            Color.YELLOW,
            bold=True,
        )
        for r in stale_repos:
            if r.stats is None:
                continue
            print(f"  {r.entry_name}: {r.stats.days_since_push} days ago")
            print(f"    {r.repo_url}")

    total_checked = len(active_repos) + len(stale_repos) + len(archived_repos)
    if total_checked > 0:
        health_pct = len(active_repos) / total_checked * 100
        print()
        print(f"Repository health: {health_pct:.1f}% active")

    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate README.md from database."""
    db_file = Path(args.db) if args.db else DEFAULT_DB

    if not db_file.exists():
        cprint(f"Database not found: {db_file}", Color.RED)
        print("Run 'curator import' first to create the database.")
        return 1

    template = Path(args.template) if args.template else None
    output = Path(args.output) if args.output else None
    force = getattr(args, "force", False)

    content = generate_readme(db_file, template, output, force=force)

    if output:
        cprint(f"Generated README at {output}", Color.GREEN)
    else:
        print(content)

    return 0


def cmd_sort(args: argparse.Namespace) -> int:
    """Sort entries.json file."""
    json_file = Path(args.json) if args.json else None
    by_category = args.by_category

    num_categories, num_entries = sort_entries_file(json_file, by_category=by_category)

    sort_desc = "by category, then name" if by_category else "by name"
    cprint(
        f"Sorted {num_categories} categories and {num_entries} entries ({sort_desc})",
        Color.GREEN,
    )
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    """Add a new entry to the JSON file and sync to database."""
    json_file = Path(args.json) if args.json else None
    db_file = Path(args.db) if args.db else None

    # Check if repo is a GitHub URL and we're missing name/description
    is_github = args.repo and "github.com" in args.repo
    needs_github_fetch = is_github and (not args.name or not args.description)

    if needs_github_fetch:
        print(f"Fetching metadata from {args.repo}...")
        try:
            entry = add_entry_from_github(
                github_url=args.repo,
                category=args.category,
                name=args.name,
                desc=args.description,
                json_path=json_file,
                db_path=db_file,
                sync=True,
            )
            cprint(f"Added '{entry['name']}'", Color.GREEN)
            print(f"  Category: {entry['category']}")
            print(f"  Description: {entry['desc']}")
            if entry.get("url"):
                print(f"  URL: {entry['url']}")
            print(f"  Repo: {entry['repo']}")

            # Show GitHub metadata
            db_path = db_file or DEFAULT_DB
            if db_path.exists():
                conn = get_connection(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM entry WHERE name = ?", (entry["name"],))
                row = cursor.fetchone()
                conn.close()
                if row:
                    if row["stars"] is not None:
                        print(f"  Stars: {row['stars']}")
                    if row["forks"] is not None:
                        print(f"  Forks: {row['forks']}")
                    if row["language"]:
                        print(f"  Language: {row['language']}")
                    if row["license"]:
                        print(f"  License: {row['license']}")
                    if row["keywords"]:
                        print(f"  Keywords: {row['keywords']}")
            return 0
        except (ValueError, KeyError) as e:
            cprint(str(e), Color.RED)
            return 1

    # Standard add (non-GitHub or all fields provided)
    if not args.name:
        cprint("Error: --name is required (or use a GitHub URL for -r to auto-detect)", Color.RED)
        return 1
    if not args.description:
        cprint("Error: --description is required (or use a GitHub URL for -r to auto-detect)", Color.RED)
        return 1

    try:
        entry = add_entry(
            name=args.name,
            category=args.category,
            desc=args.description,
            url=args.url,
            repo=args.repo,
            json_path=json_file,
            db_path=db_file,
            sync=True,
        )
        cprint(f"Added '{entry['name']}'", Color.GREEN)
        return 0
    except (ValueError, KeyError) as e:
        cprint(str(e), Color.RED)
        return 1


def cmd_remove(args: argparse.Namespace) -> int:
    """Remove an entry from the JSON file and database."""
    json_file = Path(args.json) if args.json else None
    db_file = Path(args.db) if args.db else None

    # Show entry info before removing
    entry = get_entry(args.name, json_file)
    if not entry:
        cprint(f"Entry '{args.name}' not found", Color.YELLOW)
        return 1

    print(f"Entry: {entry['name']}")
    print(f"  Category: {entry['category']}")
    print(f"  Description: {entry['desc']}")
    if entry.get("url"):
        print(f"  URL: {entry['url']}")
    if entry.get("repo"):
        print(f"  Repo: {entry['repo']}")

    if not args.yes:
        confirm = input("Remove this entry? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled")
            return 0

    try:
        removed = remove_entry(
            name=args.name,
            json_path=json_file,
            db_path=db_file,
            sync=True,
        )
        cprint(f"Removed '{removed['name']}'", Color.GREEN)
        return 0
    except KeyError as e:
        cprint(str(e), Color.RED)
        return 1


def cmd_update(args: argparse.Namespace) -> int:
    """Update an existing entry in the JSON file and sync to database."""
    json_file = Path(args.json) if args.json else None
    db_file = Path(args.db) if args.db else None

    # Show current entry info
    entry = get_entry(args.name, json_file)
    if not entry:
        cprint(f"Entry '{args.name}' not found", Color.YELLOW)
        return 1

    print("Current entry:")
    print(f"  Name: {entry['name']}")
    print(f"  Category: {entry['category']}")
    print(f"  Description: {entry['desc']}")
    if entry.get("url"):
        print(f"  URL: {entry['url']}")
    if entry.get("repo"):
        print(f"  Repo: {entry['repo']}")
    print()

    try:
        updated = update_entry(
            name=args.name,
            category=args.category,
            desc=args.description,
            url=args.url,
            repo=args.repo,
            json_path=json_file,
            db_path=db_file,
            sync=True,
        )
        cprint(f"Updated '{updated['name']}'", Color.GREEN)
        print("\nUpdated entry:")
        print(f"  Name: {updated['name']}")
        print(f"  Category: {updated['category']}")
        print(f"  Description: {updated['desc']}")
        if updated.get("url"):
            print(f"  URL: {updated['url']}")
        if updated.get("repo"):
            print(f"  Repo: {updated['repo']}")
        return 0
    except (ValueError, KeyError) as e:
        cprint(str(e), Color.RED)
        return 1


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="curator",
        description="A CLI tool for managing curated project lists.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate
    p = subparsers.add_parser("validate", help="Validate the entries JSON file")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.set_defaults(func=cmd_validate)

    # import
    p = subparsers.add_parser("import", help="Import entries from JSON to SQLite")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument("--db", help="Path to SQLite database")
    p.add_argument("--update", action="store_true", help="Update existing entries")
    p.set_defaults(func=cmd_import)

    # export
    p = subparsers.add_parser("export", help="Export entries from SQLite to JSON")
    p.add_argument("--db", help="Path to SQLite database")
    p.add_argument("-o", "--output", required=True, help="Output JSON file path")
    p.set_defaults(func=cmd_export)

    # list
    p = subparsers.add_parser("list", help="List all entries in the database")
    p.add_argument("--db", help="Path to SQLite database")
    p.add_argument("-c", "--category", help="Filter by category")
    p.add_argument(
        "-f",
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format",
    )
    p.set_defaults(func=cmd_list)

    # search
    p = subparsers.add_parser("search", help="Search entries by name or description")
    p.add_argument("query", help="Search query")
    p.add_argument("--db", help="Path to SQLite database")
    p.set_defaults(func=cmd_search)

    # stats
    p = subparsers.add_parser("stats", help="Show database statistics")
    p.add_argument("--db", help="Path to SQLite database")
    p.set_defaults(func=cmd_stats)

    # category (with subcommands)
    category_parser = subparsers.add_parser("category", help="Manage categories")
    category_sub = category_parser.add_subparsers(dest="category_command")

    # category list
    p = category_sub.add_parser("list", help="List all categories")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.set_defaults(func=cmd_category_list)

    # category add
    p = category_sub.add_parser("add", help="Add a new category")
    p.add_argument("name", help="Category name")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.set_defaults(func=cmd_category_add)

    # category rm
    p = category_sub.add_parser("rm", help="Remove a category")
    p.add_argument("name", help="Category name")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument(
        "-f", "--force", action="store_true", help="Force removal even if in use"
    )
    p.set_defaults(func=cmd_category_rm)

    # check
    p = subparsers.add_parser("check", help="Check all URLs for broken links")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument(
        "-c", "--concurrency", type=int, default=10, help="Concurrent requests"
    )
    p.add_argument(
        "-t", "--timeout", type=float, default=10.0, help="Timeout per request"
    )
    p.set_defaults(func=cmd_check)

    # github
    p = subparsers.add_parser("github", help="Fetch GitHub statistics")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument(
        "-c", "--concurrency", type=int, default=5, help="Concurrent requests"
    )
    p.add_argument(
        "-s",
        "--sort",
        choices=["stars", "name", "activity"],
        default="stars",
        help="Sort results by",
    )
    p.add_argument(
        "--show-topics", action="store_true", help="Display repository topics"
    )
    p.add_argument(
        "--update-db", action="store_true", help="Update database with topics"
    )
    p.add_argument("--db", help="Path to SQLite database")
    p.set_defaults(func=cmd_github)

    # stale
    p = subparsers.add_parser("stale", help="Find stale/unmaintained projects")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument("--days", type=int, default=365, help="Days since last push")
    p.add_argument(
        "-c", "--concurrency", type=int, default=5, help="Concurrent requests"
    )
    p.set_defaults(func=cmd_stale)

    # generate
    p = subparsers.add_parser("generate", help="Generate README.md from database")
    p.add_argument("--db", help="Path to SQLite database")
    p.add_argument("-o", "--output", help="Output README path")
    p.add_argument("-t", "--template", help="Custom template file")
    p.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite output file without prompting",
    )
    p.set_defaults(func=cmd_generate)

    # sort
    p = subparsers.add_parser("sort", help="Sort entries.json file")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument(
        "-c",
        "--by-category",
        action="store_true",
        help="Sort entries by category first, then by name (default: sort by name only)",
    )
    p.set_defaults(func=cmd_sort)

    # add
    p = subparsers.add_parser("add", help="Add a new entry to JSON and database")
    p.add_argument("-n", "--name", help="Project name (auto-detected from GitHub URL)")
    p.add_argument("-c", "--category", required=True, help="Category")
    p.add_argument(
        "-d", "--description", help="Project description (auto-detected from GitHub URL)"
    )
    p.add_argument("-u", "--url", help="Project URL")
    p.add_argument("-r", "--repo", help="Repository URL (GitHub URLs auto-populate fields)")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument("--db", help="Path to SQLite database")
    p.set_defaults(func=cmd_add)

    # remove
    p = subparsers.add_parser("remove", help="Remove an entry from JSON and database")
    p.add_argument("name", help="Entry name to remove")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument("--db", help="Path to SQLite database")
    p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    p.set_defaults(func=cmd_remove)

    # update
    p = subparsers.add_parser("update", help="Update an existing entry")
    p.add_argument("name", help="Entry name to update")
    p.add_argument("-c", "--category", help="New category")
    p.add_argument("-d", "--description", help="New description")
    p.add_argument("-u", "--url", help="New URL (use '' to clear)")
    p.add_argument("-r", "--repo", help="New repo URL (use '' to clear)")
    p.add_argument("-j", "--json", help="Path to JSON file")
    p.add_argument("--db", help="Path to SQLite database")
    p.set_defaults(func=cmd_update)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
