from dataclasses import dataclass

from .PullRequest import PullRequest


@dataclass
class BelowDryRunResult:
    """Result of a dry-run below operation showing what would happen."""

    current_branch_name: str
    current_pr: PullRequest | None
    new_branch_name: str
    pr_title: str
    worktree_path: str
    original_destination_name: str
    copy_files: list[str] | None
    run_direnv: bool
    draft: bool = False
    create_initial_pr: bool = False
    initial_pr_title: str | None = None
    initial_pr_destination: str | None = None

    def format_output(self) -> str:
        """Format the dry-run result for display."""
        lines = [
            "Dry run - no changes will be made",
            "",
            "Current state:",
            f"  Branch: {self.current_branch_name}",
        ]

        if self.current_pr is not None:
            lines.append(
                f'  PR: "{self.current_pr.title}"'
                f" -> {self.original_destination_name}"
            )
        else:
            lines.append("  PR: (none)")

        lines.append("")
        lines.append("Actions that would be performed:")

        step = 1
        if self.create_initial_pr:
            lines.append(
                f"  {step}. Push"
                f" '{self.current_branch_name}' to origin"
            )
            step += 1
            lines.append(
                f"  {step}. Create PR:"
                f" '{self.current_branch_name}' ->"
                f" '{self.initial_pr_destination}'"
                f' with title "{self.initial_pr_title}"'
            )
            step += 1

        lines.append(
            f"  {step}. Fetch latest"
            f" '{self.original_destination_name}'"
            " from origin"
        )
        step += 1
        lines.append(
            f"  {step}. Create branch"
            f" '{self.new_branch_name}'"
            f" from 'origin/{self.original_destination_name}'"
        )
        step += 1
        lines.append(
            f"  {step}. Create worktree"
            f" at {self.worktree_path}"
        )
        step += 1

        if self.copy_files:
            files_str = ", ".join(self.copy_files)
            lines.append(
                f"  {step}. Copy files: {files_str}"
            )
            step += 1

        if self.run_direnv:
            lines.append(
                f"  {step}. Run 'direnv allow'"
                f" in {self.worktree_path}"
            )
            step += 1

        lines.append(
            f"  {step}. Push"
            f" '{self.new_branch_name}' to origin"
        )
        step += 1
        draft_label = " (draft)" if self.draft else ""
        lines.append(
            f"  {step}. Create PR{draft_label}:"
            f" '{self.new_branch_name}' -> "
            f"'{self.original_destination_name}'"
            f" with title \"{self.pr_title}\""
        )
        if self.current_pr is not None:
            step += 1
            lines.append(
                f"  {step}. Retarget PR:"
                f" '{self.current_branch_name}' -> "
                f"'{self.new_branch_name}'"
                f" (was ->"
                f" '{self.original_destination_name}')"
            )

        return "\n".join(lines)
