"""Integration tests for below command using real git repos.

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


class TestBelowSimpleStack:
    """Journey: below on simple stack (feature -> main)."""

    def _setup(self, tmp_path):
        git_repo, repo_path = _init_repo_with_remote(
            tmp_path
        )

        # Create feature branch with a commit
        git_repo.git.checkout("-b", "feature")
        (repo_path / "feature.txt").write_text("feature")
        git_repo.index.add(["feature.txt"])
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
        return repo, client, worktree_path, pr

    def test_new_branch_exists(self, tmp_path):
        """New branch is created in the real git repo."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep refactor", wt_path
        )

        branch_names = [
            h.name for h in repo._git_repo.heads
        ]
        assert "prep-work" in branch_names

    def test_worktree_exists(self, tmp_path):
        """Worktree directory exists at the specified path."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep refactor", wt_path
        )

        assert Path(wt_path).is_dir()

    def test_worktree_on_correct_branch(self, tmp_path):
        """Worktree is checked out on the new branch."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep refactor", wt_path
        )

        wt_repo = Repo(wt_path)
        assert wt_repo.active_branch.name == "prep-work"

    def test_pr_created(self, tmp_path):
        """PR was created from new branch to original dest."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep refactor", wt_path
        )

        assert len(repo.created_prs) == 1
        src, dest, title, _draft = repo.created_prs[0]
        assert src.name == "prep-work"
        assert dest.name == "main"
        assert title == "Prep refactor"

    def test_original_pr_retargeted(self, tmp_path):
        """Original PR destination changed to new branch."""
        repo, client, wt_path, pr = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep refactor", wt_path
        )

        assert pr.destination_branch.name == "prep-work"

    def test_new_branch_pushed_to_remote(self, tmp_path):
        """New branch exists on the bare remote."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-work", "Prep refactor", wt_path
        )

        # Fetch in main repo to see remote branches
        repo._git_repo.git.fetch("origin")
        remote_refs = [
            ref.remote_head
            for ref in repo._git_repo.remote().refs
            if ref.remote_head != "HEAD"
        ]
        assert "prep-work" in remote_refs

    def test_returns_below_result(self, tmp_path):
        """Returns a BelowResult with correct data."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        result = client.below(
            repo, "prep-work", "Prep refactor", wt_path
        )

        assert isinstance(result, BelowResult)
        assert result.new_branch.name == "prep-work"
        assert result.new_pr.title == "Prep refactor"
        assert result.worktree_path == wt_path


class TestBelowMidStack:
    """Journey: below mid-stack (feature-b -> feature-a)."""

    def _setup(self, tmp_path):
        git_repo, repo_path = _init_repo_with_remote(
            tmp_path
        )

        # Create feature-a from main
        git_repo.git.checkout("-b", "feature-a")
        (repo_path / "a.txt").write_text("feature-a work")
        git_repo.index.add(["a.txt"])
        git_repo.index.commit("Add feature-a")
        git_repo.git.push("-u", "origin", "feature-a")

        # Create feature-b from feature-a
        git_repo.git.checkout("-b", "feature-b")
        (repo_path / "b.txt").write_text("feature-b work")
        git_repo.index.add(["b.txt"])
        git_repo.index.commit("Add feature-b")
        git_repo.git.push("-u", "origin", "feature-b")

        # Mock PR: feature-b -> feature-a (mid-stack)
        pr = MockPullRequest(
            title="Add feature-b",
            description=None,
            source_branch=MockBranch(name="feature-b"),
            destination_branch=MockBranch(
                name="feature-a"
            ),
            url="https://github.com/test/repo/pull/2",
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
            tmp_path / "worktrees" / "prep-mid"
        )
        client, output = _make_client()
        return repo, client, worktree_path, pr

    def test_new_branch_created_from_destination(
        self, tmp_path
    ):
        """New branch is created from feature-a (dest), not main."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-mid", "Mid-stack prep", wt_path
        )

        # prep-mid should branch from feature-a, so
        # it should have a.txt but not b.txt
        assert (Path(wt_path) / "a.txt").exists()
        assert not (Path(wt_path) / "b.txt").exists()

    def test_pr_targets_original_destination(
        self, tmp_path
    ):
        """New PR targets feature-a (the original dest)."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-mid", "Mid-stack prep", wt_path
        )

        assert len(repo.created_prs) == 1
        src, dest, _, _ = repo.created_prs[0]
        assert src.name == "prep-mid"
        assert dest.name == "feature-a"

    def test_original_pr_retargeted_to_new_branch(
        self, tmp_path
    ):
        """feature-b PR now targets prep-mid."""
        repo, client, wt_path, pr = self._setup(tmp_path)

        client.below(
            repo, "prep-mid", "Mid-stack prep", wt_path
        )

        assert pr.destination_branch.name == "prep-mid"

    def test_new_branch_exists(self, tmp_path):
        """New branch exists in the git repo."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-mid", "Mid-stack prep", wt_path
        )

        branch_names = [
            h.name for h in repo._git_repo.heads
        ]
        assert "prep-mid" in branch_names

    def test_worktree_on_correct_branch(self, tmp_path):
        """Worktree is on the new branch."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.below(
            repo, "prep-mid", "Mid-stack prep", wt_path
        )

        wt_repo = Repo(wt_path)
        assert wt_repo.active_branch.name == "prep-mid"
