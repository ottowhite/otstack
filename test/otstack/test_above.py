import io

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
