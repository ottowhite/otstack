import re
from dataclasses import dataclass

import questionary


@dataclass
class BelowAboveInputs:
    branch: str
    title: str
    worktree: str
    direnv: bool
    copy_files: list[str] | None
    dry_run: bool
    draft: bool


def _validate_branch_name(name: str) -> bool | str:
    """Validate git branch name."""
    if not name or not name.strip():
        return "Branch name cannot be empty"
    name = name.strip()
    # Git branch name restrictions
    if name.startswith("-"):
        return "Branch name cannot start with '-'"
    if name.endswith("."):
        return "Branch name cannot end with '.'"
    if name.endswith(".lock"):
        return "Branch name cannot end with '.lock'"
    if ".." in name:
        return "Branch name cannot contain '..'"
    if " " in name or "\t" in name:
        return "Branch name cannot contain whitespace"
    if re.search(r"[\x00-\x1f\x7f~^:?*\[\\]", name):
        return "Branch name contains invalid characters"
    return True


def _validate_non_empty(text: str) -> bool | str:
    """Validate that text is non-empty."""
    if not text or not text.strip():
        return "This field cannot be empty"
    return True


class InteractivePrompter:
    def prompt_below_above_inputs(
        self,
        command: str,
        branch: str | None = None,
        title: str | None = None,
        worktree: str | None = None,
        repo_dir_name: str | None = None,
    ) -> BelowAboveInputs:
        """Prompt the user for inputs needed for below/above commands.

        Pre-filled values are used as-is; only missing values are prompted.
        """
        print(f"\nInteractive mode for 'ots {command}'\n")

        if branch is None:
            branch_input = questionary.text(
                "Branch name:",
                validate=_validate_branch_name,
            ).ask()
            if branch_input is None:
                raise KeyboardInterrupt()
            branch = branch_input.strip()

        if title is None:
            title_input = questionary.text(
                "PR title:",
                validate=_validate_non_empty,
            ).ask()
            if title_input is None:
                raise KeyboardInterrupt()
            title = title_input.strip()

        if worktree is None:
            if repo_dir_name:
                default_worktree = (
                    f"../{repo_dir_name}-worktrees"
                    f"/{branch}"
                )
            else:
                default_worktree = f"../{branch}"
            worktree_input = questionary.text(
                "Worktree path:",
                default=default_worktree,
                validate=_validate_non_empty,
            ).ask()
            if worktree_input is None:
                raise KeyboardInterrupt()
            worktree = worktree_input.strip()

        draft = questionary.confirm(
            "Create as draft PR?",
            default=True,
        ).ask()
        if draft is None:
            raise KeyboardInterrupt()

        direnv = questionary.confirm(
            "Enable direnv in new worktree?",
            default=False,
        ).ask()
        if direnv is None:
            raise KeyboardInterrupt()

        copy_files_input = questionary.text(
            "Copy files to new worktree (comma-separated, empty to skip):",
        ).ask()
        if copy_files_input is None:
            raise KeyboardInterrupt()

        copy_files: list[str] | None = None
        if copy_files_input.strip():
            copy_files = [
                f.strip()
                for f in copy_files_input.split(",")
                if f.strip()
            ]

        dry_run = questionary.confirm(
            "Dry run (preview without making changes)?",
            default=False,
        ).ask()
        if dry_run is None:
            raise KeyboardInterrupt()

        return BelowAboveInputs(
            branch=branch,
            title=title,
            worktree=worktree,
            direnv=direnv,
            copy_files=copy_files if copy_files else None,
            dry_run=dry_run,
            draft=draft,
        )
