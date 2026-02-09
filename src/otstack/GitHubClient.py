from typing import Protocol

from .Repository import Repository


class GitHubClient(Protocol):
    """Protocol defining the high-level interface for GitHub operations."""

    def get_user_repos(self) -> list[Repository]:
        """Get all repositories for the authenticated user."""
        ...

    def get_repo(self, name: str) -> Repository:
        """Get a repository by name. Uses authenticated user if no owner given."""
        ...

    def get_authenticated_user_login(self) -> str:
        """Get the login name of the authenticated user."""
        ...

    def close(self) -> None:
        """Close the client and release resources."""
        ...
