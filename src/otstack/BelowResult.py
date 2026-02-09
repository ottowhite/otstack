from dataclasses import dataclass

from .Branch import Branch
from .PullRequest import PullRequest


@dataclass
class BelowResult:
    """Result of the below operation."""

    new_branch: Branch
    new_pr: PullRequest
    original_pr: PullRequest
    worktree_path: str
