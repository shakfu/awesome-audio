"""Async link checker for validating URLs."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx


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
        """Check if any link has issues."""
        for result in [self.url_result, self.repo_result]:
            if result and result.status not in (LinkStatus.OK, LinkStatus.REDIRECT, LinkStatus.SKIPPED):
                return True
        return False


async def check_url(client: httpx.AsyncClient, url: str, timeout: float = 10.0) -> LinkResult:
    """Check a single URL asynchronously."""
    if not url:
        return LinkResult(url="", status=LinkStatus.SKIPPED)

    start_time = asyncio.get_event_loop().time()

    try:
        response = await client.head(url, timeout=timeout, follow_redirects=True)
        elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        if response.status_code == 200:
            # Check if we were redirected
            if response.url and str(response.url) != url:
                return LinkResult(
                    url=url,
                    status=LinkStatus.REDIRECT,
                    status_code=response.status_code,
                    redirect_url=str(response.url),
                    response_time_ms=elapsed_ms,
                )
            return LinkResult(
                url=url,
                status=LinkStatus.OK,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
            )
        elif response.status_code == 404:
            return LinkResult(
                url=url,
                status=LinkStatus.NOT_FOUND,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
            )
        elif response.status_code == 405:
            # Method not allowed - try GET instead
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            if response.status_code == 200:
                if response.url and str(response.url) != url:
                    return LinkResult(
                        url=url,
                        status=LinkStatus.REDIRECT,
                        status_code=response.status_code,
                        redirect_url=str(response.url),
                        response_time_ms=elapsed_ms,
                    )
                return LinkResult(
                    url=url,
                    status=LinkStatus.OK,
                    status_code=response.status_code,
                    response_time_ms=elapsed_ms,
                )
            else:
                return LinkResult(
                    url=url,
                    status=LinkStatus.ERROR,
                    status_code=response.status_code,
                    error_message=f"HTTP {response.status_code}",
                    response_time_ms=elapsed_ms,
                )
        else:
            return LinkResult(
                url=url,
                status=LinkStatus.ERROR,
                status_code=response.status_code,
                error_message=f"HTTP {response.status_code}",
                response_time_ms=elapsed_ms,
            )

    except httpx.TimeoutException:
        return LinkResult(
            url=url,
            status=LinkStatus.TIMEOUT,
            error_message="Request timed out",
        )
    except httpx.RequestError as e:
        return LinkResult(
            url=url,
            status=LinkStatus.ERROR,
            error_message=str(e),
        )
    except Exception as e:
        return LinkResult(
            url=url,
            status=LinkStatus.ERROR,
            error_message=f"Unexpected error: {e}",
        )


async def check_entry(
    client: httpx.AsyncClient,
    name: str,
    url: Optional[str],
    repo: Optional[str],
    timeout: float = 10.0,
) -> CheckResult:
    """Check all links for a single entry."""
    url_result = None
    repo_result = None

    if url:
        url_result = await check_url(client, url, timeout)
    if repo:
        repo_result = await check_url(client, repo, timeout)

    return CheckResult(
        entry_name=name,
        url_result=url_result,
        repo_result=repo_result,
    )


async def check_entries(
    entries: list[dict],
    concurrency: int = 10,
    timeout: float = 10.0,
    progress_callback=None,
) -> list[CheckResult]:
    """Check all entries concurrently with limited concurrency."""
    results = []
    semaphore = asyncio.Semaphore(concurrency)

    async def check_with_semaphore(entry: dict, index: int) -> CheckResult:
        async with semaphore:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "awesome-audio-checker/0.1.0"},
            ) as client:
                result = await check_entry(
                    client,
                    entry.get("name", "unknown"),
                    entry.get("url"),
                    entry.get("repo"),
                    timeout,
                )
                if progress_callback:
                    progress_callback(index + 1, len(entries), entry.get("name", "unknown"))
                return result

    tasks = [check_with_semaphore(entry, i) for i, entry in enumerate(entries)]
    results = await asyncio.gather(*tasks)

    return list(results)


def run_check(
    entries: list[dict],
    concurrency: int = 10,
    timeout: float = 10.0,
    progress_callback=None,
) -> list[CheckResult]:
    """Synchronous wrapper for check_entries."""
    return asyncio.run(check_entries(entries, concurrency, timeout, progress_callback))
