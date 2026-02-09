from typing import Protocol


class Branch(Protocol):
    """Protocol defining the interface for a git branch."""

    name: str

    def merge(self, other_branch: "Branch") -> bool:
        """
        Merge other_branch into this branch.

        Returns True if merge would succeed without conflicts.
        Returns False if there would be conflicts (no changes made to branch).
        """
        ...

    def pull(self) -> bool:
        """
        Pull latest changes from remote for this branch.

        Returns True if new commits were pulled.
        Returns False if already up to date.
        """
        ...

    def is_local(self) -> bool:
        """Return True if this branch has a local filesystem checkout."""
        ...

    def push(self) -> bool:
        """Push this branch to origin. Returns True if successful, False otherwise."""
        ...

    def has_merge_conflicts(self) -> bool:
        """Check if the repo is currently in a conflicted merge state."""
        ...

    def abort_merge(self) -> None:
        """Abort any in-progress merge."""
        ...

    def get_working_dir(self) -> str:
        """Get the working directory path for this branch's repo."""
        ...
