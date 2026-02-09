from typing import Protocol

from .Branch import Branch
from .PullRequest import PullRequest


class Repository(Protocol):
    """Protocol defining the interface for a repository."""

    name: str
    full_name: str
    description: str | None
    private: bool
    url: str

    def get_open_pull_requests(self) -> list[PullRequest]:
        """Get all open pull requests for this repository."""
        ...

    def create_pr(
        self, source_branch: Branch, destination_branch: Branch, title: str
    ) -> PullRequest:
        """Create a pull request from source_branch to destination_branch."""
        ...

    def get_branches(self) -> list[Branch]:
        """Get all branches in this repository."""
        ...

    def get_local_branches(self) -> list[Branch]:
        """
        Get all branches with local filesystem checkouts (main repo and worktrees).

        Raises ValueError if no local git repository is associated.
        Invariant: No two branches in the returned list have the same name.
        """
        ...

    def get_current_branch(self) -> Branch | None:
        """
        Get the currently checked-out branch.

        Returns None if in detached HEAD state.
        Raises ValueError if no local git repository is associated.
        """
        ...

    def has_uncommitted_changes(self) -> bool:
        """
        Check if there are uncommitted changes in the working directory.

        Returns True if there are uncommitted changes, False otherwise.
        Raises ValueError if no local git repository is associated.
        """
        ...

    def create_branch(self, name: str, from_branch: Branch) -> Branch:
        """
        Create a new branch at the same commit as from_branch.

        Args:
            name: Name for the new branch.
            from_branch: Branch to create the new branch from.

        Returns:
            The newly created Branch.
        """
        ...

    def create_worktree(self, branch: Branch, path: str) -> None:
        """
        Create a git worktree for the given branch at the specified path.

        Args:
            branch: Branch to create worktree for.
            path: Path where the worktree will be created.
        """
        ...

    def get_working_dir(self) -> str:
        """
        Get the working directory path for this repository.

        Raises ValueError if no local git repository is associated.
        """
        ...
