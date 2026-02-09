import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TextIO

from dotenv import load_dotenv

from git import InvalidGitRepositoryError, Repo

from .BelowDryRunResult import BelowDryRunResult
from .BelowResult import BelowResult
from .CommandRunner import CommandRunner
from .GitHubClient import GitHubClient
from .GitRepoDetector import GitPythonRepoDetector, GitRepoDetector
from .PRTree import PRTree
from .PullRequest import PullRequest
from .PyGitHubClient import PyGitHubClient
from .PyGitHubRepository import PyGitHubRepository
from .Repository import Repository
from .SubprocessCommandRunner import SubprocessCommandRunner


class OtStackClient:
    """Main client for OtStack operations."""

    def __init__(
        self,
        github_client: GitHubClient | None = None,
        access_token: str | None = None,
        output: TextIO | None = None,
        terminal_width: int | None = None,
        repo_detector: GitRepoDetector | None = None,
        command_runner: CommandRunner | None = None,
    ) -> None:
        """
        Initialize OtStackClient.

        Args:
            github_client: Optional GitHubClient to use (for testing/mocking).
            access_token: Optional GitHub access token. If not provided,
                         will load from GITHUB_PERSONAL_ACCESS_TOKEN env var.
            output: Optional output stream for printing. Defaults to stdout.
            terminal_width: Optional terminal width. If not provided,
                           will use os.get_terminal_size().columns with fallback to 80.
            repo_detector: Optional GitRepoDetector for detecting the current repo
                          from git remotes. Defaults to GitPythonRepoDetector.
            command_runner: Optional CommandRunner for running shell commands.
                           Defaults to SubprocessCommandRunner.

        Raises:
            ValueError: If no access token is provided or found in environment.
        """
        load_dotenv()

        self._output = output or sys.stdout
        if terminal_width is None:
            try:
                terminal_width = os.get_terminal_size().columns
            except OSError:
                terminal_width = 80
        self._terminal_width = terminal_width

        if github_client is not None:
            self._github_client = github_client
        else:
            token = access_token or os.environ.get(
                "GITHUB_PERSONAL_ACCESS_TOKEN", None
            )

            if token is None:
                raise ValueError(
                    "GitHub access token required. Set GITHUB_PERSONAL_ACCESS_TOKEN "
                    "in .env or pass access_token parameter."
                )

            self._github_client = PyGitHubClient(token)

        self._repo_detector = repo_detector or GitPythonRepoDetector()
        self._command_runner = command_runner or SubprocessCommandRunner()

    def detect_repo_name(self) -> str | None:
        """
        Detect the GitHub repository name from the current git directory.

        Returns:
            Repository name in 'owner/repo' format, or None if not detectable.
        """
        return self._repo_detector.get_repo_name()

    def detect_repo(self, local_path: str = ".") -> Repository | None:
        """
        Detect and return the Repository from a git directory.

        This method detects the repo name from git remotes and also associates
        the local git repository, enabling local branch detection for sync operations.

        Args:
            local_path: Path to the local git repository. Defaults to current directory.

        Returns:
            Repository with local git repo associated, or None if not detectable.
        """
        detector = GitPythonRepoDetector(local_path)
        repo_name = detector.get_repo_name()
        if repo_name is None:
            return None

        repo = self._github_client.get_repo(repo_name)

        # Associate local git repo if available
        if isinstance(repo, PyGitHubRepository):
            try:
                git_repo = Repo(local_path, search_parent_directories=True)
                repo._git_repo = git_repo
            except InvalidGitRepositoryError:
                pass

        return repo

    def tree(self, repo: Repository) -> None:
        """Display the PR dependency tree for a repository."""
        prs = repo.get_open_pull_requests()
        if not prs:
            return

        # Find root branches (destinations that are not source branches of any PR)
        source_branches = {pr.source_branch.name for pr in prs}
        dest_branches = {pr.destination_branch.name for pr in prs}
        roots = [dest for dest in dest_branches if dest not in source_branches]

        for root in roots:
            pr_tree = self.get_pr_tree(repo, root)
            self._print_horizontal_tree(pr_tree)

    def get_repo(self, name: str, local_path: str = ".") -> Repository:
        """Get a repository by name (e.g., 'owner/repo').

        If a local git directory is provided, associates the local git repo
        to enable local branch detection for sync operations.

        Args:
            name: Repository name (e.g., 'owner/repo').
            local_path: Path to the local git repository. Defaults to current directory.
        """
        repo = self._github_client.get_repo(name)

        # Associate local git repo if available
        if isinstance(repo, PyGitHubRepository):
            try:
                git_repo = Repo(local_path, search_parent_directories=True)
                repo._git_repo = git_repo
            except InvalidGitRepositoryError:
                pass

        return repo

    def get_pr_tree(self, repo: Repository, branch: str) -> PRTree:
        """Get the PR dependency tree rooted at the given branch."""
        prs = repo.get_open_pull_requests()
        return self._build_pr_tree(branch, None, prs)

    def _build_pr_tree(
        self,
        branch: str,
        pull_request: PullRequest | None,
        all_prs: list[PullRequest],
    ) -> PRTree:
        """Recursively build a PRTree for the given branch."""
        children = [
            self._build_pr_tree(pr.source_branch.name, pr, all_prs)
            for pr in all_prs
            if pr.destination_branch.name == branch
        ]
        return PRTree(branch_name=branch, pull_request=pull_request, children=children)

    def _print_horizontal_tree(self, pr_tree: PRTree) -> None:
        """Print the PR tree in horizontal format."""
        width = self._terminal_width

        # Get the top-level children (PRs targeting root)
        children = pr_tree.children
        if not children:
            return

        # For single child (possibly with its own children forming a chain)
        if len(children) == 1:
            self._print_chain(children[0], width)
            # Print root branch
            self._output.write(self._center_text(pr_tree.branch_name, width) + "\n")
        else:
            # For multiple PRs, divide into columns
            col_width = width // len(children)
            max_text_width = col_width - 2  # Leave 1 char margin on each side

            # Get chains for each column (from deepest to shallowest)
            chains = [self._get_chain(child) for child in children]
            max_depth = max(len(chain) for chain in chains)

            # Print chains from top (deepest level) to bottom
            for level in range(max_depth - 1, -1, -1):
                # Print branch names at this level
                line = ""
                for chain in chains:
                    if level < len(chain):
                        branch_name = self._truncate_text(
                            chain[level].branch_name, max_text_width
                        )
                        line += branch_name.center(col_width)
                    else:
                        line += "".center(col_width)
                self._output.write(line.rstrip() + "\n")

                # Print PR titles at this level
                line = ""
                for chain in chains:
                    if level < len(chain):
                        node = chain[level]
                        pr_title = (
                            f'"{node.pull_request.title}"' if node.pull_request else ""
                        )
                        pr_title = self._truncate_text(pr_title, max_text_width)
                        line += pr_title.center(col_width)
                    else:
                        line += "".center(col_width)
                self._output.write(line.rstrip() + "\n")

                # Print connectors at this level
                line = ""
                for chain in chains:
                    if level < len(chain):
                        line += "|".center(col_width)
                    else:
                        line += "".center(col_width)
                self._output.write(line.rstrip() + "\n")

            # Print horizontal connecting line
            self._output.write(
                self._build_horizontal_connector(col_width, len(children)) + "\n"
            )
            # Print vertical connector to root
            self._output.write(self._center_text("|", width) + "\n")
            # Print root branch
            self._output.write(self._center_text(pr_tree.branch_name, width) + "\n")

    def _get_chain(self, node: PRTree) -> list[PRTree]:
        """Get a list of nodes from this node up to the deepest descendant (single-child chains only)."""
        chain = [node]
        current = node
        while current.children and len(current.children) == 1:
            current = current.children[0]
            chain.append(current)
        return chain

    def _print_chain(self, node: PRTree, width: int) -> None:
        """Print a chain of PRs vertically (top-down from deepest to this node)."""
        # Get the chain and print from deepest to shallowest
        chain = self._get_chain(node)
        max_text_width = width - 2  # Leave 1 char margin on each side
        for n in reversed(chain):
            branch_name = self._truncate_text(n.branch_name, max_text_width)
            pr_title = f'"{n.pull_request.title}"' if n.pull_request else ""
            pr_title = self._truncate_text(pr_title, max_text_width)

            self._output.write(self._center_text(branch_name, width) + "\n")
            self._output.write(self._center_text(pr_title, width) + "\n")
            self._output.write(self._center_text("|", width) + "\n")

    def _center_text(self, text: str, width: int) -> str:
        """Center text within width, without trailing whitespace."""
        padding = (width - len(text)) // 2
        return " " * padding + text

    def _truncate_text(self, text: str, max_width: int) -> str:
        """Truncate text with ... if it exceeds max_width."""
        if len(text) <= max_width:
            return text
        return text[: max_width - 3] + "..."

    def _build_horizontal_connector(self, col_width: int, num_cols: int) -> str:
        """Build a horizontal line connecting all columns with + at junctions."""
        # Each column's center point (matching str.center behavior)
        # str.center(30) for a 1-char string gives (30-1)//2 = 14 spaces before
        centers = [(col_width - 1) // 2 + i * col_width for i in range(num_cols)]

        # Build the line from first center to last center
        first_center = centers[0]
        last_center = centers[-1]

        result = " " * first_center + "+"
        result += "-" * (last_center - first_center - 1) + "+"

        return result

    def sync(self, repo: Repository) -> bool:
        """
        Sync all local PRs by performing top-down traversal from root toward leaves.

        For each PR where is_local() is True, calls sync() which:
        - Pulls destination branch
        - Merges destination into source
        - Pushes source branch

        Returns True if all syncs succeeded, False if any merge would conflict.
        """
        self._output.write(f"Fetching open pull requests...\n")
        prs = repo.get_open_pull_requests()
        if not prs:
            self._output.write("No open pull requests found.\n")
            return True

        # Count local PRs
        local_prs = [pr for pr in prs if pr.is_local()]
        self._output.write(
            f"Found {len(prs)} open PR(s), {len(local_prs)} with local checkouts.\n"
        )

        if not local_prs:
            self._output.write("No local PRs to sync.\n")
            return True

        # Find root branches (destinations that are not source branches of any PR)
        source_branches = {pr.source_branch.name for pr in prs}
        dest_branches = {pr.destination_branch.name for pr in prs}
        roots = [dest for dest in dest_branches if dest not in source_branches]

        self._output.write(f"Starting sync from root(s): {', '.join(roots)}\n\n")

        # Process PRs level by level (top-down from root toward leaves)
        for root in roots:
            pr_tree = self.get_pr_tree(repo, root)
            if not self._sync_tree(pr_tree):
                return False

        return True

    def _sync_tree(self, pr_tree: PRTree) -> bool:
        """Recursively sync PRs in top-down order (root toward leaves)."""
        # First, sync PRs at this level (children of current node)
        for child in pr_tree.children:
            if child.pull_request is not None:
                pr = child.pull_request
                if pr.is_local():
                    self._output.write(
                        f"Syncing '{pr.source_branch.name}' <- '{pr.destination_branch.name}'...\n"
                    )
                    self._output.write(f"  Pulling {pr.destination_branch.name}...\n")
                    if not pr.sync():
                        # Merge has conflicts - drop user into subshell to resolve
                        if not self._handle_merge_conflict(pr):
                            return False
                    else:
                        self._output.write(f"  Merged and pushed.\n")
                else:
                    self._output.write(
                        f"Skipping '{pr.source_branch.name}' (not checked out locally)\n"
                    )

            # Then recursively sync children (deeper in the tree)
            if not self._sync_tree(child):
                return False

        return True

    def _handle_merge_conflict(self, pr: PullRequest) -> bool:
        """
        Handle a merge conflict by dropping user into a subshell.

        Returns True if user resolved the conflict, False if they aborted.
        """
        working_dir = pr.source_branch.get_working_dir()

        self._output.write(
            f"\n  Merge conflict detected!\n"
            f"  Dropping you into a shell at: {working_dir}\n"
            f"  Resolve the conflicts, then 'git add' and 'git commit'.\n"
            f"  Type 'exit' when done to continue syncing.\n"
            f"  Type 'exit 1' to abort the sync.\n\n"
        )
        self._output.flush()

        # Get user's shell
        shell = os.environ.get("SHELL", "/bin/sh")

        # Run subshell in the worktree directory with clean environment
        # Remove VIRTUAL_ENV so the target repo's hooks use their own venv
        subshell_env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        subshell_env["OTSTACK_MERGE_CONFLICT"] = "1"

        result = subprocess.run(
            [shell],
            cwd=working_dir,
            env=subshell_env,
        )

        # Check if user aborted (non-zero exit)
        if result.returncode != 0:
            self._output.write(f"\n  Sync aborted by user.\n")
            pr.source_branch.abort_merge()
            return False

        # Check if merge was resolved
        if pr.source_branch.has_merge_conflicts():
            self._output.write(
                f"\n  Merge conflicts still present. Aborting sync.\n"
            )
            pr.source_branch.abort_merge()
            return False

        # Push the resolved merge
        self._output.write(f"  Conflict resolved. Pushing...\n")
        pr.source_branch.push()
        self._output.write(f"  Merged and pushed.\n")
        return True

    def below(
        self,
        repo: Repository,
        new_branch_name: str,
        pr_title: str,
        worktree_path: str,
        copy_files: list[str] | None = None,
        run_direnv: bool = False,
        dry_run: bool = False,
    ) -> BelowResult | BelowDryRunResult:
        """
        Insert a new PR below the current PR in the stack.

        This creates a new branch and PR that becomes the new base for the current PR.
        """
        current_branch = repo.get_current_branch()
        if current_branch is None:
            raise ValueError(
                "You are in detached HEAD state. Checkout a branch first."
            )

        if repo.has_uncommitted_changes():
            raise ValueError(
                "You have uncommitted changes. Commit or stash them first."
            )

        # Find PR for current branch
        prs = repo.get_open_pull_requests()
        current_pr_list = [
            pr for pr in prs if pr.source_branch.name == current_branch.name
        ]

        if not current_pr_list:
            raise ValueError(
                f"No open PR found for branch '{current_branch.name}'. Create a PR first."
            )

        if len(current_pr_list) > 1:
            raise ValueError(
                f"Multiple open PRs found for branch '{current_branch.name}'. This is ambiguous."
            )

        # Check if new branch already exists
        existing_branches = repo.get_branches()
        if any(b.name == new_branch_name for b in existing_branches):
            raise ValueError(f"Branch '{new_branch_name}' already exists.")

        # Check if worktree path already exists
        if os.path.exists(worktree_path):
            raise ValueError(
                f"Path '{worktree_path}' already exists. Choose a different worktree path."
            )

        # Get the current PR (we already validated there's exactly one)
        current_pr = current_pr_list[0]
        original_destination = current_pr.destination_branch

        if dry_run:
            return BelowDryRunResult(
                current_branch_name=current_branch.name,
                current_pr=current_pr,
                new_branch_name=new_branch_name,
                pr_title=pr_title,
                worktree_path=worktree_path,
                original_destination_name=original_destination.name,
                copy_files=copy_files,
                run_direnv=run_direnv,
            )

        # Create new branch from the original destination
        new_branch = repo.create_branch(new_branch_name, original_destination)

        # Create worktree for the new branch
        repo.create_worktree(new_branch, worktree_path)

        # Push new branch to origin
        new_branch.push()

        # Create PR from new branch to original destination
        new_pr = repo.create_pr(new_branch, original_destination, pr_title)

        # Retarget original PR to new branch
        current_pr.change_destination(new_branch)

        # Copy files if specified
        if copy_files:
            current_working_dir = repo.get_working_dir()
            for file_path in copy_files:
                src = Path(current_working_dir) / file_path
                dst = Path(worktree_path) / file_path
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                else:
                    raise ValueError(f"Cannot copy '{file_path}': file does not exist.")

        # Run direnv allow if requested
        if run_direnv:
            try:
                self._command_runner.run(["direnv", "allow"], cwd=worktree_path)
            except FileNotFoundError:
                self._output.write(
                    "Warning: 'direnv' command not found. Skipping direnv allow.\n"
                )

        return BelowResult(
            new_branch=new_branch,
            new_pr=new_pr,
            original_pr=current_pr,
            worktree_path=worktree_path,
        )

    @property
    def github(self) -> GitHubClient:
        """Get the GitHub client."""
        return self._github_client

    def close(self) -> None:
        """Close the client and release resources."""
        self._github_client.close()

    def __enter__(self) -> "OtStackClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
