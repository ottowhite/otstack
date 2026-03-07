from dataclasses import dataclass, field

from git import Repo

from otstack.Branch import Branch
from otstack.LocalBranch import LocalBranch
from otstack.PullRequest import PullRequest
from otstack.Repository import Repository
from otstack.SimpleBranch import SimpleBranch

from .MockPullRequest import MockPullRequest


@dataclass
class IntegrationTestRepository(Repository):
    """Repository using real git for local ops, mocks for PRs.

    Uses a real git.Repo for branch, worktree, and working dir
    operations. PR operations (get_open_pull_requests, create_pr)
    are mocked with configurable data.
    """

    name: str
    full_name: str
    description: str | None
    private: bool
    url: str
    _git_repo: Repo = field(repr=False)
    _pull_requests: list[PullRequest] = field(
        default_factory=list
    )
    _default_branch: str = field(default="main")
    created_prs: list[tuple[Branch, Branch, str, bool]] = (
        field(default_factory=list)
    )

    def get_open_pull_requests(self) -> list[PullRequest]:
        return list(self._pull_requests)

    def create_pr(
        self,
        source_branch: Branch,
        destination_branch: Branch,
        title: str,
        draft: bool = False,
    ) -> PullRequest:
        self.created_prs.append(
            (
                source_branch,
                destination_branch,
                title,
                draft,
            )
        )
        return MockPullRequest(
            title=title,
            description=None,
            source_branch=source_branch,
            destination_branch=destination_branch,
            url=f"{self.url}/pull/{len(self.created_prs)}",
        )

    def get_branches(self) -> list[Branch]:
        return [
            SimpleBranch(name=head.name)
            for head in self._git_repo.heads
        ]

    def get_remote_branches(self) -> list[str]:
        branches: list[str] = []
        for ref in self._git_repo.remote().refs:
            name = ref.remote_head
            if name != "HEAD":
                branches.append(name)
        return branches

    def get_local_branches(self) -> list[Branch]:
        if self._git_repo.head.is_detached:
            return []
        return [
            LocalBranch(
                name=self._git_repo.active_branch.name,
                _repo=self._git_repo,
            )
        ]

    def get_current_branch(self) -> Branch | None:
        if self._git_repo.head.is_detached:
            return None
        return LocalBranch(
            name=self._git_repo.active_branch.name,
            _repo=self._git_repo,
        )

    def has_uncommitted_changes(self) -> bool:
        return self._git_repo.is_dirty()

    def create_branch(
        self, name: str, from_branch: Branch
    ) -> Branch:
        self._git_repo.git.branch(name, from_branch.name)
        return LocalBranch(
            name=name, _repo=self._git_repo
        )

    def create_worktree(
        self, branch: Branch, path: str
    ) -> None:
        self._git_repo.git.worktree(
            "add", path, branch.name
        )

    def get_default_branch(self) -> str:
        return self._default_branch

    def get_working_dir(self) -> str:
        return str(self._git_repo.working_dir)
