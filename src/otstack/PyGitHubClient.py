from github import Auth, Github

from .GitHubClient import GitHubClient
from .PyGitHubRepository import PyGitHubRepository
from .Repository import Repository


class PyGitHubClient(GitHubClient):
    """Concrete implementation of GitHubClient using PyGithub."""

    def __init__(self, access_token: str) -> None:
        auth = Auth.Token(access_token)
        self._github = Github(auth=auth)

    def get_user_repos(self) -> list[Repository]:
        """Get all repositories for the authenticated user."""
        repos: list[Repository] = []
        for repo in self._github.get_user().get_repos():
            repos.append(
                PyGitHubRepository(
                    name=repo.name,
                    full_name=repo.full_name,
                    description=repo.description,
                    private=repo.private,
                    url=repo.html_url,
                    _gh_repo=repo,
                )
            )
        return repos

    def get_repo(self, name: str) -> Repository:
        """Get a repository by name. Searches user's repos if no owner given."""
        if "/" not in name:
            # Search user's accessible repos by name
            for repo in self._github.get_user().get_repos():
                if repo.name == name:
                    return PyGitHubRepository(
                        name=repo.name,
                        full_name=repo.full_name,
                        description=repo.description,
                        private=repo.private,
                        url=repo.html_url,
                        _gh_repo=repo,
                    )
            raise ValueError(f"Repository '{name}' not found in your accessible repos")
        repo = self._github.get_repo(name)
        return PyGitHubRepository(
            name=repo.name,
            full_name=repo.full_name,
            description=repo.description,
            private=repo.private,
            url=repo.html_url,
            _gh_repo=repo,
        )

    def get_authenticated_user_login(self) -> str:
        """Get the login name of the authenticated user."""
        return self._github.get_user().login

    def close(self) -> None:
        """Close the client and release resources."""
        self._github.close()
