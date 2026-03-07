"""Integration tests for above command using real git repos.

All git operations (branch, commit, worktree) are real.
Only GitHub API (PRs) is mocked.
"""

import io
from pathlib import Path

from git import Repo

from otstack.AboveResult import AboveResult
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


class TestAboveSimpleStack:
    """Journey: above on simple stack (feature -> main)."""

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
            tmp_path / "worktrees" / "new-feat"
        )
        client, output = _make_client()
        return repo, client, worktree_path, pr

    def test_new_branch_exists(self, tmp_path):
        """New branch is created in the real git repo."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.above(
            repo, "new-feat", "New feature", wt_path
        )

        branch_names = [
            h.name for h in repo._git_repo.heads
        ]
        assert "new-feat" in branch_names

    def test_new_branch_created_from_current(
        self, tmp_path
    ):
        """New branch has files from current branch."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.above(
            repo, "new-feat", "New feature", wt_path
        )

        # Worktree should have feature.txt (from feature)
        assert (Path(wt_path) / "feature.txt").exists()

    def test_worktree_exists(self, tmp_path):
        """Worktree directory exists at the specified path."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.above(
            repo, "new-feat", "New feature", wt_path
        )

        assert Path(wt_path).is_dir()

    def test_worktree_on_correct_branch(self, tmp_path):
        """Worktree is checked out on the new branch."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.above(
            repo, "new-feat", "New feature", wt_path
        )

        wt_repo = Repo(wt_path)
        assert wt_repo.active_branch.name == "new-feat"

    def test_pr_targets_current_branch(self, tmp_path):
        """PR is created targeting the current branch."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.above(
            repo, "new-feat", "New feature", wt_path
        )

        assert len(repo.created_prs) == 1
        src, dest, title, _draft = repo.created_prs[0]
        assert src.name == "new-feat"
        assert dest.name == "feature"
        assert title == "New feature"

    def test_new_branch_pushed_to_remote(self, tmp_path):
        """New branch exists on the bare remote."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        client.above(
            repo, "new-feat", "New feature", wt_path
        )

        repo._git_repo.git.fetch("origin")
        remote_refs = [
            ref.remote_head
            for ref in repo._git_repo.remote().refs
            if ref.remote_head != "HEAD"
        ]
        assert "new-feat" in remote_refs

    def test_returns_above_result(self, tmp_path):
        """Returns an AboveResult with correct data."""
        repo, client, wt_path, _ = self._setup(tmp_path)

        result = client.above(
            repo, "new-feat", "New feature", wt_path
        )

        assert isinstance(result, AboveResult)
        assert result.new_branch.name == "new-feat"
        assert result.new_pr.title == "New feature"
        assert result.worktree_path == wt_path


class TestAboveThreeDeepStack:
    """Journey: above on top of a 3-deep stack."""

    def _setup(self, tmp_path):
        git_repo, repo_path = _init_repo_with_remote(
            tmp_path
        )

        # Build a 3-deep stack: main <- a <- b <- c
        git_repo.git.checkout("-b", "feature-a")
        (repo_path / "a.txt").write_text("a")
        git_repo.index.add(["a.txt"])
        git_repo.index.commit("Add a")
        git_repo.git.push("-u", "origin", "feature-a")

        git_repo.git.checkout("-b", "feature-b")
        (repo_path / "b.txt").write_text("b")
        git_repo.index.add(["b.txt"])
        git_repo.index.commit("Add b")
        git_repo.git.push("-u", "origin", "feature-b")

        git_repo.git.checkout("-b", "feature-c")
        (repo_path / "c.txt").write_text("c")
        git_repo.index.add(["c.txt"])
        git_repo.index.commit("Add c")
        git_repo.git.push("-u", "origin", "feature-c")

        # PRs for all three levels
        prs = [
            MockPullRequest(
                title="Feature A",
                description=None,
                source_branch=MockBranch(
                    name="feature-a"
                ),
                destination_branch=MockBranch(name="main"),
                url="https://github.com/t/r/pull/1",
            ),
            MockPullRequest(
                title="Feature B",
                description=None,
                source_branch=MockBranch(
                    name="feature-b"
                ),
                destination_branch=MockBranch(
                    name="feature-a"
                ),
                url="https://github.com/t/r/pull/2",
            ),
            MockPullRequest(
                title="Feature C",
                description=None,
                source_branch=MockBranch(
                    name="feature-c"
                ),
                destination_branch=MockBranch(
                    name="feature-b"
                ),
                url="https://github.com/t/r/pull/3",
            ),
        ]

        repo = IntegrationTestRepository(
            name="test-repo",
            full_name="test/test-repo",
            description=None,
            private=False,
            url="https://github.com/test/test-repo",
            _git_repo=git_repo,
            _pull_requests=prs,
        )

        worktree_path = str(
            tmp_path / "worktrees" / "feature-d"
        )
        client, output = _make_client()
        return repo, client, worktree_path

    def test_pr_targets_current_branch(self, tmp_path):
        """New PR targets feature-c (the current branch)."""
        repo, client, wt_path = self._setup(tmp_path)

        client.above(
            repo, "feature-d", "Feature D", wt_path
        )

        assert len(repo.created_prs) == 1
        src, dest, _, _ = repo.created_prs[0]
        assert src.name == "feature-d"
        assert dest.name == "feature-c"

    def test_new_branch_has_all_stack_files(
        self, tmp_path
    ):
        """New branch has files from entire stack."""
        repo, client, wt_path = self._setup(tmp_path)

        client.above(
            repo, "feature-d", "Feature D", wt_path
        )

        # Should have all files since branched from c
        assert (Path(wt_path) / "a.txt").exists()
        assert (Path(wt_path) / "b.txt").exists()
        assert (Path(wt_path) / "c.txt").exists()

    def test_worktree_on_correct_branch(self, tmp_path):
        """Worktree is on the new branch."""
        repo, client, wt_path = self._setup(tmp_path)

        client.above(
            repo, "feature-d", "Feature D", wt_path
        )

        wt_repo = Repo(wt_path)
        assert wt_repo.active_branch.name == "feature-d"


class TestBelowThenAbove:
    """Journey: below then above on same branch."""

    def _setup(self, tmp_path):
        git_repo, repo_path = _init_repo_with_remote(
            tmp_path
        )

        # Create feature branch
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

        client, output = _make_client()
        return repo, client, pr

    def test_below_then_above_both_succeed(
        self, tmp_path
    ):
        """Both operations complete without error."""
        repo, client, pr = self._setup(tmp_path)
        below_wt = str(
            tmp_path / "worktrees" / "prep-work"
        )
        above_wt = str(
            tmp_path / "worktrees" / "follow-up"
        )

        below_result = client.below(
            repo, "prep-work", "Prep work", below_wt
        )
        above_result = client.above(
            repo, "follow-up", "Follow up", above_wt
        )

        assert isinstance(below_result, BelowResult)
        assert isinstance(above_result, AboveResult)

    def test_both_branches_exist(self, tmp_path):
        """Both new branches exist in the git repo."""
        repo, client, _ = self._setup(tmp_path)
        below_wt = str(
            tmp_path / "worktrees" / "prep-work"
        )
        above_wt = str(
            tmp_path / "worktrees" / "follow-up"
        )

        client.below(
            repo, "prep-work", "Prep work", below_wt
        )
        client.above(
            repo, "follow-up", "Follow up", above_wt
        )

        branch_names = [
            h.name for h in repo._git_repo.heads
        ]
        assert "prep-work" in branch_names
        assert "follow-up" in branch_names

    def test_both_worktrees_exist(self, tmp_path):
        """Both worktree directories exist."""
        repo, client, _ = self._setup(tmp_path)
        below_wt = str(
            tmp_path / "worktrees" / "prep-work"
        )
        above_wt = str(
            tmp_path / "worktrees" / "follow-up"
        )

        client.below(
            repo, "prep-work", "Prep work", below_wt
        )
        client.above(
            repo, "follow-up", "Follow up", above_wt
        )

        assert Path(below_wt).is_dir()
        assert Path(above_wt).is_dir()

    def test_prs_created_correctly(self, tmp_path):
        """Below PR targets main, above PR targets feature."""
        repo, client, _ = self._setup(tmp_path)
        below_wt = str(
            tmp_path / "worktrees" / "prep-work"
        )
        above_wt = str(
            tmp_path / "worktrees" / "follow-up"
        )

        client.below(
            repo, "prep-work", "Prep work", below_wt
        )
        client.above(
            repo, "follow-up", "Follow up", above_wt
        )

        assert len(repo.created_prs) == 2
        # below creates: prep-work -> main
        b_src, b_dest, _, _ = repo.created_prs[0]
        assert b_src.name == "prep-work"
        assert b_dest.name == "main"
        # above creates: follow-up -> feature
        a_src, a_dest, _, _ = repo.created_prs[1]
        assert a_src.name == "follow-up"
        assert a_dest.name == "feature"

    def test_original_pr_retargeted_by_below(
        self, tmp_path
    ):
        """Original PR retargeted to prep-work by below."""
        repo, client, pr = self._setup(tmp_path)
        below_wt = str(
            tmp_path / "worktrees" / "prep-work"
        )
        above_wt = str(
            tmp_path / "worktrees" / "follow-up"
        )

        client.below(
            repo, "prep-work", "Prep work", below_wt
        )
        client.above(
            repo, "follow-up", "Follow up", above_wt
        )

        assert pr.destination_branch.name == "prep-work"
