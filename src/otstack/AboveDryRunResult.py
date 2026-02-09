from dataclasses import dataclass

from .PullRequest import PullRequest


@dataclass
class AboveDryRunResult:
    """Result of a dry-run above operation showing what would happen."""

    current_branch_name: str
    current_pr: PullRequest
    new_branch_name: str
    pr_title: str
    worktree_path: str
    copy_files: list[str] | None
    run_direnv: bool

    def format_output(self) -> str:
        """Format the dry-run result for display."""
        dest_name = self.current_pr.destination_branch.name
        lines = [
            "Dry run - no changes will be made",
            "",
            "Current state:",
            f"  Branch: {self.current_branch_name}",
            f'  PR: "{self.current_pr.title}" -> {dest_name}',
            "",
            "Actions that would be performed:",
            (
                f"  1. Create branch '{self.new_branch_name}' "
                f"from '{self.current_branch_name}'"
            ),
            f"  2. Create worktree at {self.worktree_path}",
            f"  3. Push '{self.new_branch_name}' to origin",
            (
                f"  4. Create PR: '{self.new_branch_name}' -> "
                f"'{self.current_branch_name}' with title \"{self.pr_title}\""
            ),
        ]

        step = 5
        if self.copy_files:
            files_str = ", ".join(self.copy_files)
            lines.append(f"  {step}. Copy files: {files_str}")
            step += 1

        if self.run_direnv:
            lines.append(f"  {step}. Run 'direnv allow' in {self.worktree_path}")

        return "\n".join(lines)
