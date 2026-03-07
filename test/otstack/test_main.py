import sys
from io import StringIO
from unittest.mock import patch

import pytest

from otstack.main import main

from .helpers.MockBranch import MockBranch
from .helpers.MockGitHubClient import MockGitHubClient
from .helpers.MockGitRepoDetector import MockGitRepoDetector
from .helpers.MockPullRequest import MockPullRequest
from .helpers.MockRepository import MockRepository
from .helpers.TrackingCommandRunner import TrackingCommandRunner


class TestSyncCommand:
    def test_sync_command_prints_success_message(self) -> None:
        """sync command prints success message when all PRs are synced."""
        repo = _make_repo_with_local_pr()
        mock_client = MockGitHubClient(repos=[repo])
        mock_detector = MockGitRepoDetector(repo_name="test-user/test-repo")

        with (
            patch.object(sys, "argv", ["otstack", "sync"]),
            patch(
                "otstack.main.OtStackClient",
                return_value=_make_mock_client_context(mock_client, mock_detector),
            ),
            patch.object(sys, "stdout", new_callable=StringIO) as mock_stdout,
        ):
            main()
            output = mock_stdout.getvalue()
            assert "All PRs synced successfully!" in output

    def test_sync_command_with_repo_argument(self) -> None:
        """sync command accepts --repo argument."""
        repo = _make_repo_with_local_pr()
        mock_client = MockGitHubClient(repos=[repo])
        mock_detector = MockGitRepoDetector(repo_name=None)

        with (
            patch.object(
                sys, "argv", ["otstack", "sync", "--repo", "test-user/test-repo"]
            ),
            patch(
                "otstack.main.OtStackClient",
                return_value=_make_mock_client_context(mock_client, mock_detector),
            ),
            patch.object(sys, "stdout", new_callable=StringIO) as mock_stdout,
        ):
            main()
            output = mock_stdout.getvalue()
            assert "All PRs synced successfully!" in output


class TestBelowCreatePrCommand:
    def test_create_pr_flag_passes_through(
        self, tmp_path
    ) -> None:
        """--create-pr flag creates PR and proceeds."""
        repo = _make_repo_without_pr()
        mock_client = MockGitHubClient(repos=[repo])
        mock_detector = MockGitRepoDetector(
            repo_name=None
        )
        worktree_path = str(tmp_path / "new-worktree")

        with (
            patch.object(
                sys,
                "argv",
                [
                    "otstack",
                    "below",
                    "-b",
                    "prep-work",
                    "-t",
                    "Preparatory refactor",
                    "-w",
                    worktree_path,
                    "--repo",
                    "test-user/test-repo",
                    "--create-pr",
                ],
            ),
            patch(
                "otstack.main.OtStackClient",
                return_value=_make_mock_client_context(
                    mock_client, mock_detector
                ),
            ),
            patch.object(
                sys, "stdout", new_callable=StringIO
            ) as mock_stdout,
        ):
            main()
            output = mock_stdout.getvalue()
            assert "prep-work" in output

    def test_no_create_pr_flag_errors(self) -> None:
        """Without --create-pr, errors with hint."""
        repo = _make_repo_without_pr()
        mock_client = MockGitHubClient(repos=[repo])
        mock_detector = MockGitRepoDetector(
            repo_name=None
        )

        with (
            patch.object(
                sys,
                "argv",
                [
                    "otstack",
                    "below",
                    "-b",
                    "prep-work",
                    "-t",
                    "Preparatory refactor",
                    "-w",
                    "/tmp/wt",
                    "--repo",
                    "test-user/test-repo",
                ],
            ),
            patch(
                "otstack.main.OtStackClient",
                return_value=_make_mock_client_context(
                    mock_client, mock_detector
                ),
            ),
            patch.object(
                sys, "stdout", new_callable=StringIO
            ),
            pytest.raises(SystemExit),
        ):
            main()


class TestBelowCommand:
    def test_below_command_prints_summary(self, tmp_path) -> None:
        """below command prints summary with PR URLs and worktree path."""
        repo = _make_repo_with_pr()
        mock_client = MockGitHubClient(repos=[repo])
        mock_detector = MockGitRepoDetector(repo_name=None)
        worktree_path = str(tmp_path / "new-worktree")

        with (
            patch.object(
                sys,
                "argv",
                [
                    "otstack",
                    "below",
                    "-b",
                    "prep-work",
                    "-t",
                    "Preparatory refactor",
                    "-w",
                    worktree_path,
                    "--repo",
                    "test-user/test-repo",
                ],
            ),
            patch(
                "otstack.main.OtStackClient",
                return_value=_make_mock_client_context(mock_client, mock_detector),
            ),
            patch.object(sys, "stdout", new_callable=StringIO) as mock_stdout,
        ):
            main()
            output = mock_stdout.getvalue()
            assert "prep-work" in output
            assert worktree_path in output

    def test_below_auto_defaults_worktree_from_branch(
        self, tmp_path
    ) -> None:
        """below auto-defaults worktree to ../<branch> when omitted."""
        repo = _make_repo_with_pr()
        mock_client = MockGitHubClient(repos=[repo])
        mock_detector = MockGitRepoDetector(repo_name=None)

        with (
            patch.object(
                sys,
                "argv",
                [
                    "otstack",
                    "below",
                    "-b",
                    "prep-work",
                    "-t",
                    "Preparatory refactor",
                    "--repo",
                    "test-user/test-repo",
                ],
            ),
            patch(
                "otstack.main.OtStackClient",
                return_value=_make_mock_client_context(
                    mock_client, mock_detector
                ),
            ),
            patch.object(
                sys, "stdout", new_callable=StringIO
            ) as mock_stdout,
        ):
            main()
            output = mock_stdout.getvalue()
            assert "prep-work" in output

    def test_below_explicit_worktree_overrides_default(
        self, tmp_path
    ) -> None:
        """Explicit --worktree overrides auto-default."""
        repo = _make_repo_with_pr()
        mock_client = MockGitHubClient(repos=[repo])
        mock_detector = MockGitRepoDetector(repo_name=None)
        custom_path = str(tmp_path / "custom-wt")

        with (
            patch.object(
                sys,
                "argv",
                [
                    "otstack",
                    "below",
                    "-b",
                    "prep-work",
                    "-t",
                    "Preparatory refactor",
                    "-w",
                    custom_path,
                    "--repo",
                    "test-user/test-repo",
                ],
            ),
            patch(
                "otstack.main.OtStackClient",
                return_value=_make_mock_client_context(
                    mock_client, mock_detector
                ),
            ),
            patch.object(
                sys, "stdout", new_callable=StringIO
            ) as mock_stdout,
        ):
            main()
            output = mock_stdout.getvalue()
            assert custom_path in output


# Test helpers


def _make_repo_with_local_pr() -> MockRepository:
    """Create a repo with a local PR for testing."""
    pr = MockPullRequest(
        title="Add feature",
        description=None,
        source_branch=MockBranch(name="feature", _is_local=True),
        destination_branch=MockBranch(name="main", _is_local=True),
        url="https://github.com/test-user/test-repo/pull/1",
    )
    return MockRepository(
        name="test-repo",
        full_name="test-user/test-repo",
        description="Test repository",
        private=False,
        url="https://github.com/test-user/test-repo",
        _pull_requests=[pr],
    )


def _make_repo_without_pr() -> MockRepository:
    """Create a repo with no PRs (current branch has no PR)."""
    return MockRepository(
        name="test-repo",
        full_name="test-user/test-repo",
        description="Test repository",
        private=False,
        url="https://github.com/test-user/test-repo",
        _pull_requests=[],
        _current_branch=MockBranch(name="feature"),
        _working_dir="/tmp/repo",
    )


def _make_repo_with_pr() -> MockRepository:
    """Create a repo with a PR for testing below command."""
    pr = MockPullRequest(
        title="Add feature",
        description=None,
        source_branch=MockBranch(name="feature"),
        destination_branch=MockBranch(name="main"),
        url="https://github.com/test-user/test-repo/pull/1",
    )
    return MockRepository(
        name="test-repo",
        full_name="test-user/test-repo",
        description="Test repository",
        private=False,
        url="https://github.com/test-user/test-repo",
        _pull_requests=[pr],
        _current_branch=MockBranch(name="feature"),
        _working_dir="/tmp/repo",
    )


class _MockOtStackClientContext:
    """Context manager for mocking OtStackClient."""

    def __init__(self, github_client, repo_detector):
        from otstack.OtStackClient import OtStackClient

        self._client = OtStackClient(
            github_client=github_client,
            repo_detector=repo_detector,
            command_runner=TrackingCommandRunner(),
        )

    def __enter__(self):
        return self._client

    def __exit__(self, *args):
        pass


def _make_mock_client_context(mock_client, mock_detector) -> _MockOtStackClientContext:
    """Create a mock OtStackClient context manager."""
    return _MockOtStackClientContext(mock_client, mock_detector)
