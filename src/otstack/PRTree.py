from dataclasses import dataclass

from .PullRequest import PullRequest


@dataclass
class PRTree:
    """A node in the PR dependency tree."""

    branch_name: str
    pull_request: PullRequest | None
    children: list["PRTree"]
