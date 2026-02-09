from typing import Protocol

from .Branch import Branch


class PullRequest(Protocol):
    """Protocol defining the interface for a pull request."""

    title: str
    description: str | None
    source_branch: Branch
    destination_branch: Branch
    url: str

    def change_destination(self, new_destination: Branch) -> None:
        """Change the destination branch of this pull request."""
        ...

    def get_branch(self) -> Branch:
        """Get the source branch of this pull request."""
        ...

    def is_local(self) -> bool:
        """Return True if both source and destination branches are local."""
        ...

    def sync(self) -> bool:
        """
        Sync the PR by pulling destination, merging into source, and pushing source.

        Precondition: is_local() must return True.
        Raises ValueError if is_local() returns False.
        Returns True if sync succeeded, False if merge would conflict (no push performed).
        """
        ...
