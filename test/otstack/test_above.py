import io

import pytest

from otstack.AboveDryRunResult import AboveDryRunResult
from otstack.AboveResult import AboveResult
from otstack.OtStackClient import OtStackClient

from .helpers.MockBranch import MockBranch
from .helpers.MockGitHubClient import MockGitHubClient
from .helpers.MockPullRequest import MockPullRequest
from .helpers.MockRepository import MockRepository
from .helpers.TrackingCommandRunner import TrackingCommandRunner


class TestAboveResult:
    def test_above_result_holds_new_branch_new_pr_current_pr_and_worktree_path(
        self,
    ) -> None:
        """AboveResult dataclass holds all result artifacts."""
        new_branch = MockBranch(name="feature-b")
        new_pr = _make_pr(source_branch="feature-b", destination_branch="feature-a")
        current_pr = _make_pr(source_branch="feature-a", destination_branch="main")

        result = AboveResult(
            new_branch=new_branch,
            new_pr=new_pr,
            current_pr=current_pr,
            worktree_path="/tmp/new-worktree",
        )

        assert result.new_branch.name == "feature-b"
        assert result.new_pr.source_branch.name == "feature-b"
        assert result.current_pr.source_branch.name == "feature-a"
        assert result.worktree_path == "/tmp/new-worktree"


class TestAboveDryRunResult:
    def test_holds_all_planned_action_information(self) -> None:
        """AboveDryRunResult holds all information about planned actions."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=[".env"],
            run_direnv=True,
        )

        assert result.current_branch_name == "feature-a"
        assert result.current_pr.title == "Feature A"
        assert result.new_branch_name == "feature-b"
        assert result.pr_title == "Feature B"
        assert result.worktree_path == "/tmp/new-worktree"
        assert result.copy_files == [".env"]
        assert result.run_direnv is True

    def test_format_output_includes_dry_run_header(self) -> None:
        """AboveDryRunResult.format_output() includes dry-run header."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=None,
            run_direnv=False,
        )

        output = result.format_output()
        assert "Dry run - no changes will be made" in output

    def test_format_output_includes_current_state(self) -> None:
        """AboveDryRunResult.format_output() includes current state section."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=None,
            run_direnv=False,
        )

        output = result.format_output()
        assert "Current state:" in output
        assert "Branch: feature-a" in output
        assert '"Feature A"' in output
        assert "main" in output

    def test_format_output_includes_planned_actions(self) -> None:
        """AboveDryRunResult.format_output() includes all planned actions."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=[".env", ".env.local"],
            run_direnv=True,
        )

        output = result.format_output()
        assert "Actions that would be performed:" in output
        # Key difference from below: branch is created from current, not destination
        assert "Create branch 'feature-b' from 'feature-a'" in output
        assert "Create worktree at /tmp/new-worktree" in output
        assert "Push 'feature-b' to origin" in output
        # Key difference: PR targets current branch, not destination
        assert "Create PR: 'feature-b' -> 'feature-a'" in output
        assert '"Feature B"' in output
        # Key difference: NO retargeting step
        assert "Retarget" not in output
        assert "Copy files:" in output
        assert ".env" in output
        assert ".env.local" in output
        assert "direnv allow" in output


class TestAbove:
    def test_raises_error_when_in_detached_head_state(self) -> None:
        """above() raises ValueError when in detached HEAD state."""
        repo = _make_repo(current_branch=None)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You are in detached HEAD state"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_uncommitted_changes_exist(self) -> None:
        """above() raises ValueError when there are uncommitted changes."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(current_branch=current_branch, has_uncommitted_changes=True)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You have uncommitted changes"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_no_open_pr_for_current_branch(self) -> None:
        """above() raises ValueError when no open PR exists for current branch."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(current_branch=current_branch, pull_requests=[])
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="No open PR found for branch 'feature-a'"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_multiple_open_prs_for_current_branch(self) -> None:
        """above() raises ValueError when multiple open PRs exist for current branch."""
        current_branch = MockBranch(name="feature-a")
        pr1 = _make_pr(source_branch="feature-a", destination_branch="main")
        pr2 = _make_pr(source_branch="feature-a", destination_branch="develop")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr1, pr2])
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="Multiple open PRs found for branch 'feature-a'"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_new_branch_already_exists(self) -> None:
        """above() raises ValueError when new branch name already exists."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        existing_branch = MockBranch(name="feature-b")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[existing_branch],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="Branch 'feature-b' already exists"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_worktree_path_already_exists(self, tmp_path) -> None:
        """above() raises ValueError when worktree path already exists."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        existing_path = tmp_path / "existing-dir"
        existing_path.mkdir()

        with pytest.raises(ValueError, match="Path .* already exists"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=str(existing_path),
            )


# Test helpers


def _make_client(
    repos: list[MockRepository],
    command_runner: TrackingCommandRunner | None = None,
    output: "io.StringIO | None" = None,
) -> OtStackClient:
    """Create an OtStackClient with the given repos."""
    mock_client = MockGitHubClient(repos=repos)
    return OtStackClient(
        github_client=mock_client, command_runner=command_runner, output=output
    )


def _make_repo(
    current_branch: MockBranch | None = None,
    pull_requests: list[MockPullRequest] | None = None,
    has_uncommitted_changes: bool = False,
    branches: list[MockBranch] | None = None,
    working_dir: str | None = None,
    name: str = "test-repo",
) -> MockRepository:
    """Create a MockRepository with configurable current branch."""
    return MockRepository(
        name=name,
        full_name=f"test-user/{name}",
        description="Test repository",
        private=False,
        url=f"https://github.com/test-user/{name}",
        _pull_requests=pull_requests or [],
        _current_branch=current_branch,
        _has_uncommitted_changes=has_uncommitted_changes,
        _branches=branches or [],
        _working_dir=working_dir,
    )


def _make_pr(
    source_branch: str,
    destination_branch: str,
    title: str = "Test PR",
    destination_branch_obj: MockBranch | None = None,
) -> MockPullRequest:
    """Create a MockPullRequest with the given branches."""
    return MockPullRequest(
        title=title,
        description=None,
        source_branch=MockBranch(name=source_branch),
        destination_branch=(
            destination_branch_obj or MockBranch(name=destination_branch)
        ),
        url="https://github.com/test-user/test-repo/pull/1",
    )
