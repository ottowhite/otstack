import re
from typing import Protocol

from git import InvalidGitRepositoryError, Repo


class GitRepoDetector(Protocol):
    """Protocol for detecting GitHub repository info from local git repo."""

    def get_repo_name(self) -> str | None:
        """
        Get the GitHub repository name from the current directory's git remote.

        Returns:
            Repository name in 'owner/repo' format, or None if not in a git repo
            or no GitHub remote is found.
        """
        ...


class GitPythonRepoDetector(GitRepoDetector):
    """GitPython implementation of GitRepoDetector."""

    def __init__(self, path: str = ".") -> None:
        self._path = path

    def get_repo_name(self) -> str | None:
        """
        Get the GitHub repository name from the current directory's git remote.

        Supports both HTTPS and SSH remote URL formats:
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git

        Returns:
            Repository name in 'owner/repo' format, or None if not in a git repo
            or no GitHub remote is found.
        """
        try:
            repo = Repo(self._path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            return None

        # Try to find a GitHub remote (prefer 'origin')
        remotes = repo.remotes
        if not remotes:
            return None

        # Look for 'origin' first, otherwise use the first remote
        remote = None
        for r in remotes:
            if r.name == "origin":
                remote = r
                break
        if remote is None:
            remote = remotes[0]

        # Parse the remote URL to extract owner/repo
        url = remote.url
        return self._parse_github_url(url)

    def _parse_github_url(self, url: str) -> str | None:
        """
        Parse a GitHub URL to extract the owner/repo name.

        Args:
            url: Git remote URL (HTTPS or SSH format)

        Returns:
            Repository name in 'owner/repo' format, or None if not a GitHub URL.
        """
        # SSH format: git@github.com:owner/repo.git
        ssh_match = re.match(r"git@github\.com:(.+?)/(.+?)(?:\.git)?$", url)
        if ssh_match:
            owner, repo = ssh_match.groups()
            return f"{owner}/{repo}"

        # HTTPS format: https://github.com/owner/repo.git
        https_match = re.match(
            r"https://github\.com/(.+?)/(.+?)(?:\.git)?$", url
        )
        if https_match:
            owner, repo = https_match.groups()
            return f"{owner}/{repo}"

        return None
