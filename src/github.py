"""GitHub API integration for fetching repository statistics."""

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

# GitHub API base URL
GITHUB_API = "https://api.github.com"

# Regex to extract owner/repo from GitHub URLs
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

    @property
    def days_since_push(self) -> Optional[int]:
        """Days since last push."""
        if self.pushed_at:
            return (datetime.now() - self.pushed_at).days
        return None

    @property
    def is_active(self) -> bool:
        """Consider repo active if pushed within last 365 days."""
        days = self.days_since_push
        return days is not None and days < 365

    @property
    def activity_status(self) -> str:
        """Human-readable activity status."""
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


async def fetch_repo_stats(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
) -> RepoStats:
    """Fetch repository statistics from GitHub API."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    response = await client.get(url)
    response.raise_for_status()

    data = response.json()

    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
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
    )


async def fetch_entry_stats(
    client: httpx.AsyncClient,
    entry_name: str,
    repo_url: str,
) -> RepoResult:
    """Fetch stats for a single entry's repository."""
    parsed = parse_github_url(repo_url)
    if not parsed:
        return RepoResult(
            entry_name=entry_name,
            repo_url=repo_url,
            error="Not a GitHub URL",
        )

    owner, repo = parsed

    try:
        stats = await fetch_repo_stats(client, owner, repo)
        return RepoResult(
            entry_name=entry_name,
            repo_url=repo_url,
            stats=stats,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return RepoResult(
                entry_name=entry_name,
                repo_url=repo_url,
                error="Repository not found",
            )
        elif e.response.status_code == 403:
            return RepoResult(
                entry_name=entry_name,
                repo_url=repo_url,
                error="Rate limited or access denied",
            )
        else:
            return RepoResult(
                entry_name=entry_name,
                repo_url=repo_url,
                error=f"HTTP {e.response.status_code}",
            )
    except Exception as e:
        return RepoResult(
            entry_name=entry_name,
            repo_url=repo_url,
            error=str(e),
        )


async def fetch_all_stats(
    entries: list[dict],
    concurrency: int = 5,
    progress_callback=None,
) -> list[RepoResult]:
    """Fetch stats for all entries with GitHub repos."""
    token = get_github_token()
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_with_semaphore(entry: dict, index: int) -> Optional[RepoResult]:
        repo_url = entry.get("repo")
        if not repo_url or "github.com" not in repo_url:
            return None

        async with semaphore:
            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                result = await fetch_entry_stats(
                    client,
                    entry.get("name", "unknown"),
                    repo_url,
                )
                if progress_callback:
                    progress_callback(index + 1, len(entries), entry.get("name", "unknown"))
                return result

    tasks = [fetch_with_semaphore(entry, i) for i, entry in enumerate(entries)]
    all_results = await asyncio.gather(*tasks)

    return [r for r in all_results if r is not None]


def run_fetch_stats(
    entries: list[dict],
    concurrency: int = 5,
    progress_callback=None,
) -> list[RepoResult]:
    """Synchronous wrapper for fetch_all_stats."""
    return asyncio.run(fetch_all_stats(entries, concurrency, progress_callback))
