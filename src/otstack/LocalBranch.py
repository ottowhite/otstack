import os
from dataclasses import dataclass, field
from contextlib import contextmanager
from typing import Iterator

from git import Repo
from git.exc import GitCommandError

from .Branch import Branch


@contextmanager
def _clean_git_env() -> Iterator[None]:
    """Context manager that temporarily unsets VIRTUAL_ENV for git operations."""
    old_value = os.environ.pop("VIRTUAL_ENV", None)
    try:
        yield
    finally:
        if old_value is not None:
            os.environ["VIRTUAL_ENV"] = old_value


@dataclass
class LocalBranch(Branch):
    """Concrete implementation of Branch using GitPython for local filesystem operations."""

    name: str
    _repo: Repo = field(repr=False)

    def merge(self, other_branch: Branch) -> bool:
        """
        Merge other_branch into this branch.

        Returns True if merge succeeded (or already up to date).
        Returns False if there are conflicts (left in conflicted state for manual resolution).
        """
        with _clean_git_env():
            self._repo.git.checkout(self.name)

            # Attempt the merge
            try:
                self._repo.git.merge("--no-commit", "--no-ff", other_branch.name)
            except GitCommandError as e:
                # Check if "already up to date" (not an error)
                if "Already up to date" in str(e.stdout):
                    return True
                # Merge has conflicts - leave in conflicted state for manual resolution
                return False

            # Merge succeeded, commit it (may fail if nothing to commit)
            try:
                self._repo.git.commit(
                    "-m", f"Merge (patch propagation) {other_branch.name} -> {self.name}"
                )
            except GitCommandError as e:
                # "nothing to commit" or "no changes added" is fine - already up to date
                stdout = str(e.stdout).lower()
                if "nothing to commit" in stdout or "no changes added" in stdout:
                    return True
                raise
            return True

    def has_merge_conflicts(self) -> bool:
        """Check if the repo is currently in a conflicted merge state."""
        with _clean_git_env():
            try:
                # Check for MERGE_HEAD which indicates an in-progress merge
                self._repo.git.rev_parse("MERGE_HEAD")
                return True
            except GitCommandError:
                return False

    def abort_merge(self) -> None:
        """Abort any in-progress merge."""
        with _clean_git_env():
            try:
                self._repo.git.merge("--abort")
            except GitCommandError:
                pass  # No merge in progress

    def get_working_dir(self) -> str:
        """Get the working directory path for this branch's repo."""
        return str(self._repo.working_dir)

    def pull(self) -> bool:
        """
        Pull latest changes from remote for this branch.

        Returns True if new commits were pulled.
        Returns False if already up to date.
        """
        with _clean_git_env():
            self._repo.git.checkout(self.name)

            # Get current HEAD before pull
            head_before = self._repo.head.commit.hexsha

            try:
                self._repo.git.pull("origin", self.name)
            except GitCommandError:
                return False

            # Check if HEAD changed
            head_after = self._repo.head.commit.hexsha
            return head_before != head_after

    def is_local(self) -> bool:
        return True

    def push(self) -> bool:
        """Push this branch to origin. Returns True if successful, False otherwise."""
        with _clean_git_env():
            try:
                self._repo.git.push("origin", self.name)
                return True
            except GitCommandError:
                return False
