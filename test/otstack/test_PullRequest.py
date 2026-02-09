import pytest

from otstack.PullRequest import PullRequest
from otstack.PyGitHubPullRequest import PyGitHubPullRequest

from .helpers.MockBranch import MockBranch
from .helpers.MockPullRequest import MockPullRequest


class TestPullRequestIsLocal:
    def test_pull_request_protocol_has_is_local_method(self) -> None:
        """PullRequest protocol defines is_local() method."""
        pr: PullRequest = _make_pr(
            source_is_local=True,
            destination_is_local=True,
        )

        result = pr.is_local()

        assert result is True

    def test_mock_pull_request_returns_true_when_both_branches_local(self) -> None:
        """MockPullRequest.is_local() returns True when both branches are local."""
        pr = _make_pr(source_is_local=True, destination_is_local=True)

        assert pr.is_local() is True

    def test_mock_pull_request_returns_false_when_source_not_local(self) -> None:
        """MockPullRequest.is_local() returns False when source branch is not local."""
        pr = _make_pr(source_is_local=False, destination_is_local=True)

        assert pr.is_local() is False

    def test_mock_pull_request_returns_false_when_destination_not_local(self) -> None:
        """MockPullRequest.is_local() returns False when destination branch is not local."""
        pr = _make_pr(source_is_local=True, destination_is_local=False)

        assert pr.is_local() is False

    def test_mock_pull_request_returns_false_when_neither_branch_local(self) -> None:
        """MockPullRequest.is_local() returns False when neither branch is local."""
        pr = _make_pr(source_is_local=False, destination_is_local=False)

        assert pr.is_local() is False


class TestPyGitHubPullRequestIsLocal:
    def test_pygithub_pr_returns_true_when_both_branches_local(self) -> None:
        """PyGitHubPullRequest.is_local() returns True when both branches are local."""
        pr = _make_pygithub_pr(source_is_local=True, destination_is_local=True)

        assert pr.is_local() is True

    def test_pygithub_pr_returns_false_when_source_not_local(self) -> None:
        """PyGitHubPullRequest.is_local() returns False when source is not local."""
        pr = _make_pygithub_pr(source_is_local=False, destination_is_local=True)

        assert pr.is_local() is False


class TestPullRequestSync:
    def test_pull_request_protocol_has_sync_method(self) -> None:
        """PullRequest protocol defines sync() method."""
        pr: PullRequest = _make_pr(source_is_local=True, destination_is_local=True)

        result = pr.sync()

        assert result is True

    def test_mock_pull_request_sync_raises_value_error_when_not_local(self) -> None:
        """MockPullRequest.sync() raises ValueError when is_local() is False."""
        pr = _make_pr(source_is_local=False, destination_is_local=True)

        with pytest.raises(ValueError, match="is_local.*False"):
            pr.sync()

    def test_mock_pull_request_sync_returns_true_on_success(self) -> None:
        """MockPullRequest.sync() returns True when merge succeeds."""
        pr = _make_pr(
            source_is_local=True,
            destination_is_local=True,
            source_merge_will_conflict=False,
        )

        result = pr.sync()

        assert result is True

    def test_mock_pull_request_sync_returns_false_on_conflict(self) -> None:
        """MockPullRequest.sync() returns False when merge would conflict."""
        pr = _make_pr(
            source_is_local=True,
            destination_is_local=True,
            source_merge_will_conflict=True,
        )

        result = pr.sync()

        assert result is False


class TestPyGitHubPullRequestSync:
    def test_pygithub_pr_sync_raises_value_error_when_not_local(self) -> None:
        """PyGitHubPullRequest.sync() raises ValueError when is_local() is False."""
        pr = _make_pygithub_pr_with_mock_branches(
            source_is_local=False,
            destination_is_local=True,
        )

        with pytest.raises(ValueError, match="is_local.*False"):
            pr.sync()

    def test_pygithub_pr_sync_returns_true_on_success(self) -> None:
        """PyGitHubPullRequest.sync() returns True when merge succeeds."""
        pr = _make_pygithub_pr_with_mock_branches(
            source_is_local=True,
            destination_is_local=True,
            source_merge_will_conflict=False,
        )

        result = pr.sync()

        assert result is True

    def test_pygithub_pr_sync_returns_false_on_conflict(self) -> None:
        """PyGitHubPullRequest.sync() returns False when merge would conflict."""
        pr = _make_pygithub_pr_with_mock_branches(
            source_is_local=True,
            destination_is_local=True,
            source_merge_will_conflict=True,
        )

        result = pr.sync()

        assert result is False


# Test helpers


def _make_pr(
    source_is_local: bool,
    destination_is_local: bool,
    source_merge_will_conflict: bool = False,
) -> MockPullRequest:
    """Create a MockPullRequest with branches having specified locality."""
    return MockPullRequest(
        title="Test PR",
        description=None,
        source_branch=MockBranch(
            name="feature",
            _is_local=source_is_local,
            _merge_will_conflict=source_merge_will_conflict,
        ),
        destination_branch=MockBranch(name="main", _is_local=destination_is_local),
        url="https://github.com/test/repo/pull/1",
    )


def _make_pygithub_pr(
    source_is_local: bool,
    destination_is_local: bool,
) -> PyGitHubPullRequest:
    """Create a PyGitHubPullRequest with branches having specified locality."""
    return PyGitHubPullRequest(
        title="Test PR",
        description=None,
        source_branch=MockBranch(name="feature", _is_local=source_is_local),
        destination_branch=MockBranch(name="main", _is_local=destination_is_local),
        url="https://github.com/test/repo/pull/1",
    )


def _make_pygithub_pr_with_mock_branches(
    source_is_local: bool,
    destination_is_local: bool,
    source_merge_will_conflict: bool = False,
) -> PyGitHubPullRequest:
    """Create a PyGitHubPullRequest with mock branches for sync testing."""
    return PyGitHubPullRequest(
        title="Test PR",
        description=None,
        source_branch=MockBranch(
            name="feature",
            _is_local=source_is_local,
            _merge_will_conflict=source_merge_will_conflict,
        ),
        destination_branch=MockBranch(name="main", _is_local=destination_is_local),
        url="https://github.com/test/repo/pull/1",
    )
