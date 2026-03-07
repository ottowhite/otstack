from dataclasses import dataclass

from .Branch import Branch
from .PullRequest import PullRequest


@dataclass
class AboveResult:
    """Result of the above operation."""

    new_branch: Branch
    new_pr: PullRequest
    current_pr: PullRequest | None
    worktree_path: str
