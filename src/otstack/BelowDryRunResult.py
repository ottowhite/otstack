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
            f"  1. Create branch '{self.new_branch_name}' (same as '{self.original_destination_name}')",
            f"  2. Create worktree at {self.worktree_path}",
            f"  3. Push '{self.new_branch_name}' to origin",
            f'  4. Create PR: \'{self.new_branch_name}\' -> \'{self.original_destination_name}\' with title "{self.pr_title}"',
            f"  5. Retarget PR: '{self.current_branch_name}' -> '{self.new_branch_name}' (was -> '{self.original_destination_name}')",
        ]

        step = 6
        if self.copy_files:
            files_str = ", ".join(self.copy_files)
            lines.append(f"  {step}. Copy files: {files_str}")
            step += 1

        if self.run_direnv:
            lines.append(f"  {step}. Run 'direnv allow' in {self.worktree_path}")

        return "\n".join(lines)
