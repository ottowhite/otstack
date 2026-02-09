import pytest

from otstack.Branch import Branch
from otstack.LocalBranch import LocalBranch
from otstack.SimpleBranch import SimpleBranch

from .helpers.MockBranch import MockBranch


class TestBranchIsLocal:
    def test_branch_protocol_has_is_local_method(self) -> None:
        """Branch protocol defines is_local() method."""
        branch: Branch = MockBranch(name="test-branch", _is_local=True)

        result = branch.is_local()

        assert result is True

    def test_mock_branch_returns_configured_is_local_value(self) -> None:
        """MockBranch returns the configured _is_local value."""
        local_branch = MockBranch(name="local", _is_local=True)
        remote_branch = MockBranch(name="remote", _is_local=False)

        assert local_branch.is_local() is True
        assert remote_branch.is_local() is False


class TestSimpleBranchIsLocal:
    def test_simple_branch_is_local_returns_false(self) -> None:
        """SimpleBranch.is_local() always returns False."""
        branch = SimpleBranch(name="some-branch")

        result = branch.is_local()

        assert result is False


class TestLocalBranchIsLocal:
    def test_local_branch_is_local_returns_true(self, tmp_path) -> None:
        """LocalBranch.is_local() always returns True."""
        from git import Repo

        repo = Repo.init(tmp_path)
        branch = LocalBranch(name="main", _repo=repo)

        result = branch.is_local()

        assert result is True


class TestBranchPush:
    def test_branch_protocol_has_push_method(self) -> None:
        """Branch protocol defines push() method."""
        branch: Branch = MockBranch(name="test-branch", _push_will_succeed=True)

        result = branch.push()

        assert result is True

    def test_mock_branch_returns_configured_push_value(self) -> None:
        """MockBranch returns the configured _push_will_succeed value."""
        success_branch = MockBranch(name="success", _push_will_succeed=True)
        fail_branch = MockBranch(name="fail", _push_will_succeed=False)

        assert success_branch.push() is True
        assert fail_branch.push() is False


class TestSimpleBranchPush:
    def test_simple_branch_push_raises_not_implemented_error(self) -> None:
        """SimpleBranch.push() raises NotImplementedError."""
        branch = SimpleBranch(name="some-branch")

        with pytest.raises(NotImplementedError):
            branch.push()


class TestLocalBranchPush:
    def test_push_returns_true_on_success(self, tmp_path) -> None:
        """LocalBranch.push() returns True when push to origin succeeds."""
        from git import Repo

        # Setup: create a bare "origin" repo and a clone
        origin_path = tmp_path / "origin.git"
        clone_path = tmp_path / "clone"
        origin_repo = Repo.init(origin_path, bare=True)

        # Create clone with initial commit
        clone_repo = Repo.clone_from(str(origin_path), str(clone_path))
        (clone_path / "file.txt").write_text("content")
        clone_repo.index.add(["file.txt"])
        clone_repo.index.commit("Initial commit")
        clone_repo.git.push("origin", "master")

        # Create a new commit to push
        (clone_path / "file.txt").write_text("updated content")
        clone_repo.index.add(["file.txt"])
        clone_repo.index.commit("Update file")

        branch = LocalBranch(name="master", _repo=clone_repo)

        result = branch.push()

        assert result is True

    def test_push_returns_false_when_no_remote(self, tmp_path) -> None:
        """LocalBranch.push() returns False when push fails (no remote)."""
        from git import Repo

        # Setup: create a repo with no remote
        repo = Repo.init(tmp_path)
        (tmp_path / "file.txt").write_text("content")
        repo.index.add(["file.txt"])
        repo.index.commit("Initial commit")

        branch = LocalBranch(name="master", _repo=repo)

        result = branch.push()

        assert result is False
