from dataclasses import dataclass

from otstack.GitRepoDetector import GitRepoDetector


@dataclass
class MockGitRepoDetector(GitRepoDetector):
    """Mock implementation of GitRepoDetector for testing."""

    repo_name: str | None = None

    def get_repo_name(self) -> str | None:
        return self.repo_name
