"""Integration tests for worktree context and file copying.

All git operations (branch, commit, worktree) are real.
Only GitHub API (PRs) is mocked.
"""

import io
from pathlib import Path

from git import Repo

from otstack.BelowResult import BelowResult
from otstack.OtStackClient import OtStackClient
from otstack.SubprocessCommandRunner import SubprocessCommandRunner

from .helpers.IntegrationTestRepository import (
    IntegrationTestRepository,
)
from .helpers.MockBranch import MockBranch
from .helpers.MockGitHubClient import MockGitHubClient
from .helpers.MockPullRequest import MockPullRequest


def _init_repo_with_remote(tmp_path, repo_name="local"):
    """Create a git repo with a bare remote and main branch."""
    bare_path = tmp_path / "remote.git"
    Repo.init(str(bare_path), bare=True)

    repo_path = tmp_path / repo_name
    git_repo = Repo.init(str(repo_path))

    git_repo.config_writer().set_value(
        "user", "name", "Test User"
    ).release()
    git_repo.config_writer().set_value(
        "user", "email", "test@example.com"
    ).release()

    git_repo.git.checkout("-b", "main")
    (repo_path / "README.md").write_text("# Test repo")
    git_repo.index.add(["README.md"])
    git_repo.index.commit("Initial commit")

    git_repo.create_remote("origin", str(bare_path))
    git_repo.git.push("-u", "origin", "main")

    return git_repo, repo_path


def _make_client():
    """Create an OtStackClient with real command runner."""
    output = io.StringIO()
    client = OtStackClient(
        github_client=MockGitHubClient(repos=[]),
        command_runner=SubprocessCommandRunner(),
        output=output,
    )
    return client, output


class TestBelowFromWorktree:
    """Journey: running below from inside a worktree."""

    def _setup(self, tmp_path):
        git_repo, repo_path = _init_repo_with_remote(
            tmp_path
        )

        # Create feature branch and push
        git_repo.git.checkout("-b", "feature")
        (repo_path / "feature.txt").write_text("feature")
        git_repo.index.add(["feature.txt"])
        git_repo.index.commit("Add feature")
        git_repo.git.push("-u", "origin", "feature")

        # Switch main repo to main, then create a
        # worktree for feature (can't worktree a
        # branch that's already checked out)
        git_repo.git.checkout("main")
        wt_feature_path = str(
            tmp_path / "wt-feature"
        )
        git_repo.git.worktree(
            "add", wt_feature_path, "feature"
        )

        # Open repo from the worktree path
        # (this is the key: user's cwd is a worktree)
        wt_repo = Repo(wt_feature_path)

        # Mock PR: feature -> main
        pr = MockPullRequest(
            title="Add feature",
            description=None,
            source_branch=MockBranch(name="feature"),
            destination_branch=MockBranch(name="main"),
            url="https://github.com/test/repo/pull/1",
        )

        repo = IntegrationTestRepository(
            name="test-repo",
            full_name="test/test-repo",
            description=None,
            private=False,
            url="https://github.com/test/test-repo",
            _git_repo=wt_repo,
            _pull_requests=[pr],
        )

        new_wt_path = str(
            tmp_path / "worktrees" / "prep-work"
        )
        client, output = _make_client()
        return repo, client, new_wt_path, pr

    def test_detects_correct_branch(self, tmp_path):
        """Repo opened from worktree sees feature branch."""
        repo, _, _, _ = self._setup(tmp_path)

        branch = repo.get_current_branch()
        assert branch is not None
        assert branch.name == "feature"

    def test_below_succeeds(self, tmp_path):
        """below completes successfully from worktree."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        result = client.below(
            repo, "prep-work", "Prep work", wt_path
        )

        assert isinstance(result, BelowResult)

    def test_new_branch_exists(self, tmp_path):
        """New branch is created when running from worktree."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep work", wt_path
        )

        branch_names = [
            h.name for h in repo._git_repo.heads
        ]
        assert "prep-work" in branch_names

    def test_new_worktree_exists(self, tmp_path):
        """New worktree is created."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep work", wt_path
        )

        assert Path(wt_path).is_dir()

    def test_pr_created(self, tmp_path):
        """PR was created with correct branches."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep work", wt_path
        )

        assert len(repo.created_prs) == 1
        src, dest, _, _ = repo.created_prs[0]
        assert src.name == "prep-work"
        assert dest.name == "main"

    def test_original_pr_retargeted(self, tmp_path):
        """Original PR retargeted to new branch."""
        repo, client, wt_path, pr = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep work", wt_path
        )

        assert pr.destination_branch.name == "prep-work"


class TestBelowWithFileCopy:
    """Journey: file copying with --copy flag."""

    def _setup(self, tmp_path):
        git_repo, repo_path = _init_repo_with_remote(
            tmp_path
        )

        # Create feature branch with extra files
        git_repo.git.checkout("-b", "feature")
        (repo_path / "feature.txt").write_text("feature")
        git_repo.index.add(["feature.txt"])

        # Create files to copy (not tracked by git)
        (repo_path / ".envrc").write_text(
            "use flake . --impure"
        )
        config_dir = repo_path / "config"
        config_dir.mkdir()
        (config_dir / "local.yaml").write_text(
            "key: value\nport: 8080"
        )

        git_repo.index.commit("Add feature")
        git_repo.git.push("-u", "origin", "feature")

        # Mock PR: feature -> main
        pr = MockPullRequest(
            title="Add feature",
            description=None,
            source_branch=MockBranch(name="feature"),
            destination_branch=MockBranch(name="main"),
            url="https://github.com/test/repo/pull/1",
        )

        repo = IntegrationTestRepository(
            name="test-repo",
            full_name="test/test-repo",
            description=None,
            private=False,
            url="https://github.com/test/test-repo",
            _git_repo=git_repo,
            _pull_requests=[pr],
        )

        worktree_path = str(
            tmp_path / "worktrees" / "prep-work"
        )
        client, output = _make_client()
        return repo, client, worktree_path

    def test_copied_file_exists_in_worktree(
        self, tmp_path
    ):
        """Copied file is present in the new worktree."""
        repo, client, wt_path = self._setup(tmp_path)

        client.below(
            repo,
            "prep-work",
            "Prep work",
            wt_path,
            copy_files=[".envrc"],
        )

        assert (Path(wt_path) / ".envrc").exists()

    def test_copied_file_has_correct_content(
        self, tmp_path
    ):
        """Copied file has the same content as source."""
        repo, client, wt_path = self._setup(tmp_path)

        client.below(
            repo,
            "prep-work",
            "Prep work",
            wt_path,
            copy_files=[".envrc"],
        )

        content = (Path(wt_path) / ".envrc").read_text()
        assert content == "use flake . --impure"

    def test_nested_file_copied(self, tmp_path):
        """File in a subdirectory is copied correctly."""
        repo, client, wt_path = self._setup(tmp_path)

        client.below(
            repo,
            "prep-work",
            "Prep work",
            wt_path,
            copy_files=["config/local.yaml"],
        )

        copied = Path(wt_path) / "config" / "local.yaml"
        assert copied.exists()
        assert "port: 8080" in copied.read_text()

    def test_multiple_files_copied(self, tmp_path):
        """Multiple files can be copied at once."""
        repo, client, wt_path = self._setup(tmp_path)

        client.below(
            repo,
            "prep-work",
            "Prep work",
            wt_path,
            copy_files=[".envrc", "config/local.yaml"],
        )

        assert (Path(wt_path) / ".envrc").exists()
        assert (
            Path(wt_path) / "config" / "local.yaml"
        ).exists()

    def test_below_still_succeeds_with_copy(
        self, tmp_path
    ):
        """below returns BelowResult when copying files."""
        repo, client, wt_path = self._setup(tmp_path)

        result = client.below(
            repo,
            "prep-work",
            "Prep work",
            wt_path,
            copy_files=[".envrc"],
        )

        assert isinstance(result, BelowResult)
        assert result.new_branch.name == "prep-work"
