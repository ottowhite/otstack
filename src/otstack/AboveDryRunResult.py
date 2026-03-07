from dataclasses import dataclass

from .PullRequest import PullRequest


@dataclass
class AboveDryRunResult:
    """Result of a dry-run above operation showing what would happen."""

    current_branch_name: str
    current_pr: PullRequest | None
    new_branch_name: str
    pr_title: str
    worktree_path: str
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
            dest_name = (
                self.current_pr.destination_branch.name
            )
            lines.append(
                f'  PR: "{self.current_pr.title}"'
                f" -> {dest_name}"
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
            f"  {step}. Create branch"
            f" '{self.new_branch_name}'"
            f" from '{self.current_branch_name}'"
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
            f"'{self.current_branch_name}'"
            f" with title \"{self.pr_title}\""
        )

        return "\n".join(lines)
