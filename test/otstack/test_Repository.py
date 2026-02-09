import pytest
from git import Repo

from otstack.LocalBranch import LocalBranch
from otstack.PyGitHubRepository import PyGitHubRepository
from otstack.Repository import Repository

from .helpers.MockBranch import MockBranch
from .helpers.MockRepository import MockRepository


class TestRepositoryGetLocalBranches:
    def test_repository_protocol_has_get_local_branches_method(self) -> None:
        """Repository protocol defines get_local_branches() method."""
        repo: Repository = _make_repo(local_branches=[])

        result = repo.get_local_branches()

        assert result == []

    def test_mock_repository_returns_configured_local_branches(self) -> None:
        """MockRepository returns the configured _local_branches value."""
        branch1 = MockBranch(name="feature-1", _is_local=True)
        branch2 = MockBranch(name="feature-2", _is_local=True)
        repo = _make_repo(local_branches=[branch1, branch2])

        result = repo.get_local_branches()

        assert result == [branch1, branch2]

    def test_mock_repository_raises_value_error_when_no_git_repo(self) -> None:
        """MockRepository.get_local_branches() raises ValueError when no git repo."""
        repo = _make_repo(local_branches=None)

        with pytest.raises(ValueError, match="No local git repository"):
            repo.get_local_branches()


class TestPyGitHubRepositoryGetCurrentBranch:
    def test_raises_value_error_when_no_git_repo(self) -> None:
        """PyGitHubRepository.get_current_branch() raises ValueError when _git_repo is None."""
        repo = _make_pygithub_repo(git_repo=None)

        with pytest.raises(ValueError, match="No local git repository"):
            repo.get_current_branch()

    def test_returns_current_branch_in_main_repo(self, tmp_path) -> None:
        """Returns the branch currently checked out in the main repo."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.get_current_branch()

        assert result is not None
        assert result.name == "master"
        assert isinstance(result, LocalBranch)

    def test_returns_none_when_head_is_detached(self, tmp_path) -> None:
        """Returns None when HEAD is in detached state."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        commit = git_repo.index.commit("Initial commit")
        # Detach HEAD by checking out a specific commit
        git_repo.git.checkout(commit.hexsha)
        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.get_current_branch()

        assert result is None

    def test_returns_current_branch_when_opened_from_worktree(self, tmp_path) -> None:
        """Returns the worktree's branch when Repo is opened from within a worktree."""
        main_path = tmp_path / "main"
        main_path.mkdir()
        main_repo = Repo.init(main_path)
        (main_path / "file.txt").write_text("content")
        main_repo.index.add(["file.txt"])
        main_repo.index.commit("Initial commit")

        # Create a feature branch and worktree
        main_repo.git.branch("feature-1")
        worktree_path = tmp_path / "worktree-feature-1"
        main_repo.git.worktree("add", str(worktree_path), "feature-1")

        # Open Repo from the worktree directory (simulating running command from worktree)
        worktree_repo = Repo(worktree_path)
        repo = _make_pygithub_repo(git_repo=worktree_repo)

        result = repo.get_current_branch()

        assert result is not None
        assert result.name == "feature-1"
        assert isinstance(result, LocalBranch)


class TestPyGitHubRepositoryHasUncommittedChanges:
    def test_raises_value_error_when_no_git_repo(self) -> None:
        """PyGitHubRepository.has_uncommitted_changes() raises ValueError when _git_repo is None."""
        repo = _make_pygithub_repo(git_repo=None)

        with pytest.raises(ValueError, match="No local git repository"):
            repo.has_uncommitted_changes()

    def test_returns_false_when_working_tree_is_clean(self, tmp_path) -> None:
        """Returns False when there are no uncommitted changes."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.has_uncommitted_changes()

        assert result is False

    def test_returns_true_when_there_are_staged_changes(self, tmp_path) -> None:
        """Returns True when there are staged changes."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        # Make a change and stage it
        (tmp_path / "file.txt").write_text("modified content")
        git_repo.index.add(["file.txt"])
        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.has_uncommitted_changes()

        assert result is True

    def test_returns_true_when_there_are_unstaged_changes(self, tmp_path) -> None:
        """Returns True when there are unstaged changes to tracked files."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        # Make a change but don't stage it
        (tmp_path / "file.txt").write_text("modified content")
        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.has_uncommitted_changes()

        assert result is True


class TestPyGitHubRepositoryGetLocalBranches:
    def test_raises_value_error_when_no_git_repo(self) -> None:
        """PyGitHubRepository.get_local_branches() raises ValueError when _git_repo is None."""
        repo = _make_pygithub_repo(git_repo=None)

        with pytest.raises(ValueError, match="No local git repository"):
            repo.get_local_branches()

    def test_returns_main_repo_current_branch(self, tmp_path) -> None:
        """Returns the branch currently checked out in the main repo."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.get_local_branches()

        assert len(result) == 1
        assert result[0].name == "master"
        assert isinstance(result[0], LocalBranch)
        assert result[0].is_local() is True

    def test_returns_worktree_branches(self, tmp_path) -> None:
        """Returns branches checked out in worktrees."""
        main_path = tmp_path / "main"
        main_path.mkdir()
        git_repo = Repo.init(main_path)
        (main_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")

        # Create a feature branch
        git_repo.git.branch("feature-1")

        # Create a worktree for the feature branch
        worktree_path = tmp_path / "worktree-feature-1"
        git_repo.git.worktree("add", str(worktree_path), "feature-1")

        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.get_local_branches()

        branch_names = {b.name for b in result}
        assert "master" in branch_names
        assert "feature-1" in branch_names
        assert len(result) == 2
        for branch in result:
            assert isinstance(branch, LocalBranch)


class TestPyGitHubRepositoryCreateBranch:
    def test_raises_value_error_when_no_git_repo(self) -> None:
        """PyGitHubRepository.create_branch() raises ValueError when _git_repo is None."""
        repo = _make_pygithub_repo(git_repo=None)
        from_branch = MockBranch(name="master")

        with pytest.raises(ValueError, match="No local git repository"):
            repo.create_branch("new-branch", from_branch)

    def test_creates_new_branch_at_same_commit_as_from_branch(self, tmp_path) -> None:
        """Creates a new branch pointing to the same commit as from_branch."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        repo = _make_pygithub_repo(git_repo=git_repo)
        from_branch = LocalBranch(name="master", _repo=git_repo)

        result = repo.create_branch("feature-1", from_branch)

        assert result.name == "feature-1"
        assert isinstance(result, LocalBranch)
        # Verify the new branch exists in git
        branch_names = [ref.name for ref in git_repo.branches]
        assert "feature-1" in branch_names


class TestPyGitHubRepositoryCreateWorktree:
    def test_raises_value_error_when_no_git_repo(self) -> None:
        """PyGitHubRepository.create_worktree() raises ValueError when _git_repo is None."""
        repo = _make_pygithub_repo(git_repo=None)
        branch = MockBranch(name="feature-1")

        with pytest.raises(ValueError, match="No local git repository"):
            repo.create_worktree(branch, "/tmp/worktree")

    def test_creates_worktree_at_specified_path(self, tmp_path) -> None:
        """Creates a git worktree at the specified path."""
        git_repo = Repo.init(tmp_path / "main")
        ((tmp_path / "main") / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        git_repo.git.branch("feature-1")
        repo = _make_pygithub_repo(git_repo=git_repo)
        branch = LocalBranch(name="feature-1", _repo=git_repo)
        worktree_path = str(tmp_path / "worktree-feature-1")

        repo.create_worktree(branch, worktree_path)

        # Verify the worktree was created
        assert (tmp_path / "worktree-feature-1").exists()
        assert (tmp_path / "worktree-feature-1" / "file.txt").exists()


class TestPyGitHubRepositoryGetWorkingDir:
    def test_raises_value_error_when_no_git_repo(self) -> None:
        """PyGitHubRepository.get_working_dir() raises ValueError when _git_repo is None."""
        repo = _make_pygithub_repo(git_repo=None)

        with pytest.raises(ValueError, match="No local git repository"):
            repo.get_working_dir()

    def test_returns_working_directory_path(self, tmp_path) -> None:
        """Returns the working directory path of the git repo."""
        git_repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        git_repo.index.add(["file.txt"])
        git_repo.index.commit("Initial commit")
        repo = _make_pygithub_repo(git_repo=git_repo)

        result = repo.get_working_dir()

        assert result == str(tmp_path)


# Test helpers


def _make_repo(
    local_branches: list[MockBranch] | None,
) -> MockRepository:
    """Create a MockRepository with specified local branches."""
    return MockRepository(
        name="test-repo",
        full_name="test-user/test-repo",
        description="Test repository",
        private=False,
        url="https://github.com/test-user/test-repo",
        _local_branches=local_branches,
    )


def _make_pygithub_repo(
    git_repo: Repo | None,
) -> PyGitHubRepository:
    """Create a PyGitHubRepository with specified git repo."""
    return PyGitHubRepository(
        name="test-repo",
        full_name="test-user/test-repo",
        description="Test repository",
        private=False,
        url="https://github.com/test-user/test-repo",
        _git_repo=git_repo,
    )
