"""Tests for GitHub API integration."""


from src.github import RepoResult, RepoStats, parse_github_url


class TestParseGithubUrl:
    """Tests for parse_github_url function."""

    def test_parse_https_url(self):
        """Should parse standard HTTPS URL."""
        result = parse_github_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_parse_https_url_with_www(self):
        """Should parse URL with www prefix."""
        result = parse_github_url("https://www.github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_parse_http_url(self):
        """Should parse HTTP URL."""
        result = parse_github_url("http://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_parse_url_with_trailing_slash(self):
        """Should handle trailing slash."""
        result = parse_github_url("https://github.com/owner/repo/")
        assert result == ("owner", "repo")

    def test_parse_url_with_subpath(self):
        """Should handle URLs with subpaths."""
        result = parse_github_url("https://github.com/owner/repo/tree/main")
        assert result == ("owner", "repo")

    def test_parse_url_with_git_suffix(self):
        """Should handle .git suffix."""
        result = parse_github_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_non_github_url(self):
        """Should return None for non-GitHub URLs."""
        result = parse_github_url("https://gitlab.com/owner/repo")
        assert result is None

    def test_parse_empty_url(self):
        """Should return None for empty URL."""
        result = parse_github_url("")
        assert result is None

    def test_parse_none_url(self):
        """Should return None for None."""
        result = parse_github_url(None)
        assert result is None


class TestRepoStats:
    """Tests for RepoStats dataclass."""

    def test_days_since_push(self):
        """Should calculate days since last push."""
        from datetime import datetime, timedelta

        yesterday = datetime.now() - timedelta(days=1)
        stats = RepoStats(
            owner="test",
            name="repo",
            full_name="test/repo",
            description="Test repo",
            stars=100,
            forks=10,
            open_issues=5,
            watchers=50,
            language="Python",
            license="MIT",
            created_at=datetime.now() - timedelta(days=365),
            updated_at=datetime.now(),
            pushed_at=yesterday,
            archived=False,
            fork=False,
            default_branch="main",
            topics=["audio", "python"],
        )
        assert stats.days_since_push == 1

    def test_is_active_recent_push(self):
        """Should be active if pushed recently."""
        from datetime import datetime, timedelta

        stats = RepoStats(
            owner="test",
            name="repo",
            full_name="test/repo",
            description=None,
            stars=0,
            forks=0,
            open_issues=0,
            watchers=0,
            language=None,
            license=None,
            created_at=None,
            updated_at=None,
            pushed_at=datetime.now() - timedelta(days=30),
            archived=False,
            fork=False,
            default_branch="main",
            topics=[],
        )
        assert stats.is_active

    def test_is_not_active_old_push(self):
        """Should not be active if not pushed in over a year."""
        from datetime import datetime, timedelta

        stats = RepoStats(
            owner="test",
            name="repo",
            full_name="test/repo",
            description=None,
            stars=0,
            forks=0,
            open_issues=0,
            watchers=0,
            language=None,
            license=None,
            created_at=None,
            updated_at=None,
            pushed_at=datetime.now() - timedelta(days=400),
            archived=False,
            fork=False,
            default_branch="main",
            topics=[],
        )
        assert not stats.is_active

    def test_activity_status_archived(self):
        """Archived repos should have archived status."""
        from datetime import datetime

        stats = RepoStats(
            owner="test",
            name="repo",
            full_name="test/repo",
            description=None,
            stars=0,
            forks=0,
            open_issues=0,
            watchers=0,
            language=None,
            license=None,
            created_at=None,
            updated_at=None,
            pushed_at=datetime.now(),
            archived=True,
            fork=False,
            default_branch="main",
            topics=[],
        )
        assert stats.activity_status == "archived"

    def test_activity_status_very_active(self):
        """Recently pushed repos should be very active."""
        from datetime import datetime, timedelta

        stats = RepoStats(
            owner="test",
            name="repo",
            full_name="test/repo",
            description=None,
            stars=0,
            forks=0,
            open_issues=0,
            watchers=0,
            language=None,
            license=None,
            created_at=None,
            updated_at=None,
            pushed_at=datetime.now() - timedelta(days=7),
            archived=False,
            fork=False,
            default_branch="main",
            topics=[],
        )
        assert stats.activity_status == "very active"

    def test_activity_status_stale(self):
        """Old repos should be stale."""
        from datetime import datetime, timedelta

        stats = RepoStats(
            owner="test",
            name="repo",
            full_name="test/repo",
            description=None,
            stars=0,
            forks=0,
            open_issues=0,
            watchers=0,
            language=None,
            license=None,
            created_at=None,
            updated_at=None,
            pushed_at=datetime.now() - timedelta(days=500),
            archived=False,
            fork=False,
            default_branch="main",
            topics=[],
        )
        assert stats.activity_status == "stale"


class TestRepoResult:
    """Tests for RepoResult dataclass."""

    def test_success_with_stats(self):
        """Should be successful when stats are present."""
        from datetime import datetime

        stats = RepoStats(
            owner="test",
            name="repo",
            full_name="test/repo",
            description=None,
            stars=0,
            forks=0,
            open_issues=0,
            watchers=0,
            language=None,
            license=None,
            created_at=None,
            updated_at=None,
            pushed_at=datetime.now(),
            archived=False,
            fork=False,
            default_branch="main",
            topics=[],
        )
        result = RepoResult(
            entry_name="test",
            repo_url="https://github.com/test/repo",
            stats=stats,
        )
        assert result.success

    def test_not_success_with_error(self):
        """Should not be successful when there's an error."""
        result = RepoResult(
            entry_name="test",
            repo_url="https://github.com/test/repo",
            error="Not found",
        )
        assert not result.success
