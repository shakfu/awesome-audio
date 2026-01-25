"""Tests for link checker."""


from src.checker import CheckResult, LinkResult, LinkStatus


class TestLinkResult:
    """Tests for LinkResult dataclass."""

    def test_ok_result(self):
        """OK result should have correct status."""
        result = LinkResult(
            url="https://example.com",
            status=LinkStatus.OK,
            status_code=200,
            response_time_ms=100.0,
        )
        assert result.status == LinkStatus.OK
        assert result.status_code == 200

    def test_not_found_result(self):
        """Not found result should have 404 status."""
        result = LinkResult(
            url="https://example.com/missing",
            status=LinkStatus.NOT_FOUND,
            status_code=404,
        )
        assert result.status == LinkStatus.NOT_FOUND

    def test_error_result(self):
        """Error result should include message."""
        result = LinkResult(
            url="https://example.com",
            status=LinkStatus.ERROR,
            error_message="Connection refused",
        )
        assert result.status == LinkStatus.ERROR
        assert result.error_message == "Connection refused"


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_no_issues_when_ok(self):
        """Should have no issues when all links are OK."""
        result = CheckResult(
            entry_name="test",
            url_result=LinkResult(url="https://example.com", status=LinkStatus.OK),
            repo_result=LinkResult(url="https://github.com/test/test", status=LinkStatus.OK),
        )
        assert not result.has_issues

    def test_no_issues_when_redirect(self):
        """Redirects should not be considered issues."""
        result = CheckResult(
            entry_name="test",
            url_result=LinkResult(
                url="https://example.com",
                status=LinkStatus.REDIRECT,
                redirect_url="https://www.example.com",
            ),
        )
        assert not result.has_issues

    def test_has_issues_when_not_found(self):
        """Not found should be an issue."""
        result = CheckResult(
            entry_name="test",
            url_result=LinkResult(url="https://example.com", status=LinkStatus.NOT_FOUND),
        )
        assert result.has_issues

    def test_has_issues_when_error(self):
        """Errors should be issues."""
        result = CheckResult(
            entry_name="test",
            repo_result=LinkResult(url="https://github.com/test/test", status=LinkStatus.ERROR),
        )
        assert result.has_issues

    def test_no_issues_when_skipped(self):
        """Skipped links should not be issues."""
        result = CheckResult(
            entry_name="test",
            url_result=LinkResult(url="", status=LinkStatus.SKIPPED),
        )
        assert not result.has_issues


class TestLinkStatus:
    """Tests for LinkStatus enum."""

    def test_all_statuses_exist(self):
        """All expected statuses should exist."""
        assert LinkStatus.OK.value == "ok"
        assert LinkStatus.REDIRECT.value == "redirect"
        assert LinkStatus.NOT_FOUND.value == "not_found"
        assert LinkStatus.TIMEOUT.value == "timeout"
        assert LinkStatus.ERROR.value == "error"
        assert LinkStatus.SKIPPED.value == "skipped"
