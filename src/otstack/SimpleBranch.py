from dataclasses import dataclass

from .Branch import Branch


@dataclass
class SimpleBranch(Branch):
    """Simple branch implementation that only holds a name.

    Use this when you only need branch metadata (e.g., for displaying PR info)
    but don't need local git operations.
    """

    name: str

    def merge(self, other_branch: Branch) -> bool:
        raise NotImplementedError(
            "SimpleBranch does not support merge. Use LocalBranch for local git operations."
        )

    def pull(self) -> bool:
        raise NotImplementedError(
            "SimpleBranch does not support pull. Use LocalBranch for local git operations."
        )

    def is_local(self) -> bool:
        return False

    def push(self) -> bool:
        raise NotImplementedError(
            "SimpleBranch does not support push. Use LocalBranch for local git operations."
        )

    def has_merge_conflicts(self) -> bool:
        raise NotImplementedError(
            "SimpleBranch does not support has_merge_conflicts. Use LocalBranch for local git operations."
        )

    def abort_merge(self) -> None:
        raise NotImplementedError(
            "SimpleBranch does not support abort_merge. Use LocalBranch for local git operations."
        )

    def get_working_dir(self) -> str:
        raise NotImplementedError(
            "SimpleBranch does not support get_working_dir. Use LocalBranch for local git operations."
        )
