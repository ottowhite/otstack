from dataclasses import dataclass, field

from git import Repo
from github.Repository import Repository as GHRepository

from .Branch import Branch
from .LocalBranch import LocalBranch
from .PullRequest import PullRequest
from .PyGitHubPullRequest import PyGitHubPullRequest
from .Repository import Repository
from .SimpleBranch import SimpleBranch


@dataclass
class PyGitHubRepository(Repository):
    """Concrete implementation of Repository."""

    name: str
    full_name: str
    description: str | None
    private: bool
    url: str
    _gh_repo: GHRepository | None = field(default=None, repr=False)
    _git_repo: Repo | None = field(default=None, repr=False)

    def get_open_pull_requests(self) -> list[PullRequest]:
        """Get all open pull requests for this repository."""
        if self._gh_repo is None:
            return []

        # Build a map of locally checked out branches by name
        local_branch_map: dict[str, Branch] = {}
        if self._git_repo is not None:
            for branch in self.get_local_branches():
                local_branch_map[branch.name] = branch

        prs: list[PullRequest] = []
        for pr in self._gh_repo.get_pulls(state="open"):
            # Use LocalBranch if checked out locally, otherwise SimpleBranch
            source_branch: Branch = local_branch_map.get(
                pr.head.ref, SimpleBranch(name=pr.head.ref)
            )
            dest_branch: Branch = local_branch_map.get(
                pr.base.ref, SimpleBranch(name=pr.base.ref)
            )
            prs.append(
                PyGitHubPullRequest(
                    title=pr.title,
                    description=pr.body,
                    source_branch=source_branch,
                    destination_branch=dest_branch,
                    url=pr.html_url,
                    _gh_pr=pr,
                )
            )
        return prs

    def create_pr(
        self, source_branch: Branch, destination_branch: Branch, title: str
    ) -> PullRequest:
        """Create a pull request from source_branch to destination_branch."""
        if self._gh_repo is None:
            raise ValueError("Cannot create PR without GitHub repository reference")
        pr = self._gh_repo.create_pull(
            title=title,
            body="",
            head=source_branch.name,
            base=destination_branch.name,
        )

        # Build a map of locally checked out branches by name
        local_branch_map: dict[str, Branch] = {}
        if self._git_repo is not None:
            for branch in self.get_local_branches():
                local_branch_map[branch.name] = branch

        # Use LocalBranch if checked out locally, otherwise SimpleBranch
        new_source: Branch = local_branch_map.get(
            pr.head.ref, SimpleBranch(name=pr.head.ref)
        )
        new_dest: Branch = local_branch_map.get(
            pr.base.ref, SimpleBranch(name=pr.base.ref)
        )

        return PyGitHubPullRequest(
            title=pr.title,
            description=pr.body,
            source_branch=new_source,
            destination_branch=new_dest,
            url=pr.html_url,
            _gh_pr=pr,
        )

    def get_branches(self) -> list[Branch]:
        """Get all branches in this repository."""
        if self._git_repo is None:
            return []

        # Build a map of locally checked out branches by name
        local_branch_map: dict[str, Branch] = {}
        for branch in self.get_local_branches():
            local_branch_map[branch.name] = branch

        branches: list[Branch] = []
        for ref in self._git_repo.references:
            if hasattr(ref, "name") and not ref.name.startswith("origin/"):
                # Use LocalBranch if checked out locally, otherwise SimpleBranch
                branch = local_branch_map.get(ref.name, SimpleBranch(name=ref.name))
                branches.append(branch)
        return branches

    def get_local_branches(self) -> list[Branch]:
        """
        Get all branches with local filesystem checkouts (main repo and worktrees).

        Raises ValueError if no local git repository is associated.
        """
        if self._git_repo is None:
            raise ValueError("No local git repository associated")

        branches: list[Branch] = []

        # Get the main repo's currently checked out branch
        if not self._git_repo.head.is_detached:
            branches.append(
                LocalBranch(name=self._git_repo.active_branch.name, _repo=self._git_repo)
            )

        # Get worktree branches
        try:
            worktree_output = self._git_repo.git.worktree("list", "--porcelain")
            current_worktree_path = None
            for line in worktree_output.splitlines():
                if line.startswith("worktree "):
                    current_worktree_path = line[9:]  # Remove "worktree " prefix
                elif line.startswith("branch "):
                    branch_ref = line[7:]  # Remove "branch " prefix
                    # Extract branch name from refs/heads/branch-name
                    if branch_ref.startswith("refs/heads/"):
                        branch_name = branch_ref[11:]  # Remove "refs/heads/" prefix
                        # Skip if this is the main repo (already added above)
                        if current_worktree_path != str(self._git_repo.working_dir):
                            # Open a Repo for the worktree directory so git operations
                            # work correctly (can't checkout a branch already in a worktree)
                            worktree_repo = Repo(current_worktree_path)
                            branches.append(
                                LocalBranch(name=branch_name, _repo=worktree_repo)
                            )
        except Exception:
            # Worktree command failed or not supported, just return main branch
            pass

        return branches

    def get_current_branch(self) -> Branch | None:
        """
        Get the currently checked-out branch.

        Returns None if in detached HEAD state.
        Raises ValueError if no local git repository is associated.
        """
        if self._git_repo is None:
            raise ValueError("No local git repository associated")

        if self._git_repo.head.is_detached:
            return None

        return LocalBranch(name=self._git_repo.active_branch.name, _repo=self._git_repo)

    def has_uncommitted_changes(self) -> bool:
        """
        Check if there are uncommitted changes in the working directory.

        Returns True if there are uncommitted changes, False otherwise.
        Raises ValueError if no local git repository is associated.
        """
        if self._git_repo is None:
            raise ValueError("No local git repository associated")

        return self._git_repo.is_dirty()

    def create_branch(self, name: str, from_branch: Branch) -> Branch:
        """
        Create a new branch at the same commit as from_branch.

        Args:
            name: Name for the new branch.
            from_branch: Branch to create the new branch from.

        Returns:
            The newly created Branch.
        """
        if self._git_repo is None:
            raise ValueError("No local git repository associated")

        self._git_repo.git.branch(name, from_branch.name)
        return LocalBranch(name=name, _repo=self._git_repo)

    def create_worktree(self, branch: Branch, path: str) -> None:
        """
        Create a git worktree for the given branch at the specified path.

        Args:
            branch: Branch to create worktree for.
            path: Path where the worktree will be created.
        """
        if self._git_repo is None:
            raise ValueError("No local git repository associated")

        self._git_repo.git.worktree("add", path, branch.name)

    def get_working_dir(self) -> str:
        """
        Get the working directory path for this repository.

        Raises ValueError if no local git repository is associated.
        """
        if self._git_repo is None:
            raise ValueError("No local git repository associated")

        return str(self._git_repo.working_dir)
