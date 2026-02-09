from collections.abc import Sequence

from otstack.GitHubClient import GitHubClient
from otstack.Repository import Repository


class MockGitHubClient(GitHubClient):
    def __init__(self, repos: Sequence[Repository] | None = None) -> None:
        self._repos = list(repos) if repos else []
        self._closed = False

    def get_user_repos(self) -> list[Repository]:
        return self._repos

    def get_repo(self, name: str) -> Repository:
        for repo in self._repos:
            if repo.full_name == name or repo.name == name:
                return repo
        raise ValueError(f"Repository not found: {name}")

    def get_authenticated_user_login(self) -> str:
        return "test-user"

    def close(self) -> None:
        self._closed = True
