from dataclasses import dataclass, field

from otstack.Branch import Branch
from otstack.PullRequest import PullRequest
from otstack.Repository import Repository

from .MockBranch import MockBranch
from .MockPullRequest import MockPullRequest


@dataclass
class MockRepository(Repository):
    name: str
    full_name: str
    description: str | None
    private: bool
    url: str
    _branches: list[Branch] = field(default_factory=list)
    _pull_requests: list[PullRequest] = field(default_factory=list)
    _local_branches: list[Branch] | None = field(default_factory=list)
    _current_branch: Branch | None = field(default=None)
    _has_uncommitted_changes: bool = field(default=False)
    created_branches: list[tuple[str, Branch]] = field(default_factory=list)
    created_worktrees: list[tuple[Branch, str]] = field(default_factory=list)
    created_prs: list[tuple[Branch, Branch, str]] = field(default_factory=list)
    _working_dir: str | None = field(default=None)

    def get_open_pull_requests(self) -> list[PullRequest]:
        return self._pull_requests

    def create_pr(
        self, source_branch: Branch, destination_branch: Branch, title: str
    ) -> PullRequest:
        self.created_prs.append((source_branch, destination_branch, title))
        return MockPullRequest(
            title=title,
            description=None,
            source_branch=source_branch,
            destination_branch=destination_branch,
            url=f"{self.url}/pull/1",
        )

    def get_branches(self) -> list[Branch]:
        return self._branches

    def get_local_branches(self) -> list[Branch]:
        if self._local_branches is None:
            raise ValueError("No local git repository associated")
        return self._local_branches

    def get_current_branch(self) -> Branch | None:
        return self._current_branch

    def has_uncommitted_changes(self) -> bool:
        return self._has_uncommitted_changes

    def create_branch(self, name: str, from_branch: Branch) -> Branch:
        new_branch = MockBranch(name=name)
        self.created_branches.append((name, from_branch))
        return new_branch

    def create_worktree(self, branch: Branch, path: str) -> None:
        self.created_worktrees.append((branch, path))

    def get_working_dir(self) -> str:
        if self._working_dir is None:
            raise ValueError("No local git repository associated")
        return self._working_dir
