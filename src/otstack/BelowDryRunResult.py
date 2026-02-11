from dataclasses import dataclass

from .PullRequest import PullRequest


@dataclass
class BelowDryRunResult:
    """Result of a dry-run below operation showing what would happen."""

    current_branch_name: str
    current_pr: PullRequest
    new_branch_name: str
    pr_title: str
    worktree_path: str
    original_destination_name: str
    copy_files: list[str] | None
    run_direnv: bool

    def format_output(self) -> str:
        """Format the dry-run result for display."""
        lines = [
            "Dry run - no changes will be made",
            "",
            "Current state:",
            f"  Branch: {self.current_branch_name}",
            f'  PR: "{self.current_pr.title}" -> {self.original_destination_name}',
            "",
            "Actions that would be performed:",
            (
                f"  1. Create branch '{self.new_branch_name}' "
                f"(same as '{self.original_destination_name}')"
            ),
            f"  2. Create worktree at {self.worktree_path}",
        ]

        step = 3
        if self.copy_files:
            files_str = ", ".join(self.copy_files)
            lines.append(f"  {step}. Copy files: {files_str}")
            step += 1

        if self.run_direnv:
            lines.append(f"  {step}. Run 'direnv allow' in {self.worktree_path}")
            step += 1

        lines.append(f"  {step}. Push '{self.new_branch_name}' to origin")
        step += 1
        lines.append(
            f"  {step}. Create PR: '{self.new_branch_name}' -> "
            f"'{self.original_destination_name}' with title \"{self.pr_title}\""
        )
        step += 1
        lines.append(
            f"  {step}. Retarget PR: '{self.current_branch_name}' -> "
            f"'{self.new_branch_name}' (was -> '{self.original_destination_name}')"
        )

        return "\n".join(lines)
