import io

import pytest

from otstack.OtStackClient import OtStackClient

from .helpers.MockBranch import MockBranch
from .helpers.MockGitHubClient import MockGitHubClient
from .helpers.MockPullRequest import MockPullRequest
from .helpers.MockRepository import MockRepository
from .helpers.TrackingCommandRunner import TrackingCommandRunner


class TestBelow:
    def test_raises_error_when_in_detached_head_state(self) -> None:
        """below() raises ValueError when in detached HEAD state."""
        repo = _make_repo(current_branch=None)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You are in detached HEAD state"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_raises_error_when_uncommitted_changes_exist(self) -> None:
        """below() raises ValueError when there are uncommitted changes."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(current_branch=current_branch, has_uncommitted_changes=True)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You have uncommitted changes"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_raises_error_when_no_open_pr_for_current_branch(self) -> None:
        """below() raises ValueError when no open PR exists for current branch."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(current_branch=current_branch, pull_requests=[])
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="No open PR found for branch 'feature-branch'"
        ):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_raises_error_when_multiple_open_prs_for_current_branch(self) -> None:
        """below() raises ValueError when multiple open PRs exist for current branch."""
        current_branch = MockBranch(name="feature-branch")
        pr1 = _make_pr(source_branch="feature-branch", destination_branch="main")
        pr2 = _make_pr(source_branch="feature-branch", destination_branch="develop")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr1, pr2])
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="Multiple open PRs found for branch 'feature-branch'"
        ):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_raises_error_when_new_branch_already_exists(self) -> None:
        """below() raises ValueError when new branch name already exists."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        existing_branch = MockBranch(name="prep-work")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[existing_branch],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="Branch 'prep-work' already exists"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_raises_error_when_branch_exists_on_remote(self) -> None:
        """below() raises ValueError when branch exists on remote."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch", destination_branch="main"
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            remote_branches=["prep-work"],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError,
            match="Branch 'prep-work' already exists on remote",
        ):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_raises_error_when_branch_exists_both_locally_and_remote(
        self,
    ) -> None:
        """below() raises ValueError when branch exists locally and on remote."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch", destination_branch="main"
        )
        existing_branch = MockBranch(name="prep-work")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[existing_branch],
            remote_branches=["prep-work"],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="Branch 'prep-work' already exists"
        ):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_succeeds_when_branch_does_not_exist_anywhere(self) -> None:
        """below() proceeds when branch doesn't exist locally or remotely."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch", destination_branch="main"
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[],
            remote_branches=[],
            working_dir="/tmp/repo",
        )
        client = _make_client(repos=[repo])

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path="/tmp/project-prep-work",
            dry_run=True,
        )

        assert result is not None

    def test_raises_error_when_worktree_path_already_exists(self, tmp_path) -> None:
        """below() raises ValueError when worktree path already exists."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        existing_path = tmp_path / "existing-dir"
        existing_path.mkdir()

        with pytest.raises(ValueError, match="Path .* already exists"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=str(existing_path),
            )

    def test_fetches_remote_before_creating_branch(self, tmp_path) -> None:
        """below() fetches the destination branch from origin before creating."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        # Verify fetch was called before other commands
        fetch_commands = [
            (cmd, cwd)
            for cmd, cwd in command_runner.commands
            if "fetch" in cmd
        ]
        assert len(fetch_commands) == 1
        assert fetch_commands[0] == (
            ["git", "fetch", "origin", "main"],
            "/tmp/repo",
        )

        # Verify fetch comes before push in command order
        cmd_names = [cmd[1] for cmd, _ in command_runner.commands]
        fetch_idx = cmd_names.index("fetch")
        push_idx = cmd_names.index("push")
        assert fetch_idx < push_idx

    def test_creates_new_branch_from_origin_destination(self, tmp_path) -> None:
        """below() creates new branch from origin/<dest>, not local ref."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        # Verify the new branch was created from origin/main
        assert len(repo.created_branches) == 1
        branch_name, from_branch = repo.created_branches[0]
        assert branch_name == "prep-work"
        assert from_branch.name == "origin/main"

    def test_creates_worktree_for_new_branch(self, tmp_path) -> None:
        """below() creates a git worktree for the new branch."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        # Verify worktree was created
        assert len(repo.created_worktrees) == 1
        branch, path = repo.created_worktrees[0]
        assert branch.name == "prep-work"
        assert path == worktree_path

    def test_pushes_new_branch_to_origin(self, tmp_path) -> None:
        """below() pushes the new branch to origin."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        # Verify git push was called via command runner
        push_commands = [
            cmd for cmd, cwd in command_runner.commands if "push" in cmd
        ]
        assert len(push_commands) == 1
        assert push_commands[0] == ["git", "push", "-u", "origin", "prep-work"]

    def test_creates_pr_from_new_branch_to_original_destination(self, tmp_path) -> None:
        """below() creates a PR from new branch to original destination."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        # Verify new PR was created
        assert len(repo.created_prs) == 1
        source, destination, title, draft = repo.created_prs[0]
        assert source.name == "prep-work"
        assert destination.name == "main"
        assert title == "Preparatory refactor"

    def test_passes_draft_flag_to_create_pr(self, tmp_path) -> None:
        """below() passes draft=True to repo.create_pr()."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            draft=True,
        )

        assert len(repo.created_prs) == 1
        _, _, _, draft = repo.created_prs[0]
        assert draft is True

    def test_draft_defaults_to_false(self, tmp_path) -> None:
        """below() defaults draft=False in create_pr()."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        assert len(repo.created_prs) == 1
        _, _, _, draft = repo.created_prs[0]
        assert draft is False

    def test_retargets_original_pr_to_new_branch(self, tmp_path) -> None:
        """below() changes original PR's destination to the new branch."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        # Verify original PR was retargeted
        assert pr.destination_branch.name == "prep-work"

    def test_returns_below_result_with_all_artifacts(self, tmp_path) -> None:
        """below() returns BelowResult with new branch, PRs, and worktree path."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
        )

        # Verify result contains all expected information
        from otstack.BelowResult import BelowResult

        assert isinstance(result, BelowResult)
        assert result.new_branch.name == "prep-work"
        assert result.new_pr.title == "Preparatory refactor"
        assert result.original_pr == pr
        assert result.worktree_path == worktree_path

    def test_copies_files_to_new_worktree(self, tmp_path) -> None:
        """below() copies specified files to the new worktree."""
        # Set up current worktree with a file
        current_worktree = tmp_path / "current"
        current_worktree.mkdir()
        env_file = current_worktree / ".env"
        env_file.write_text("SECRET=abc123")

        # Set up new worktree path
        new_worktree = tmp_path / "new-worktree"

        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir=str(current_worktree),
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=str(new_worktree),
            copy_files=[".env"],
        )

        # Verify file was copied
        new_env_file = new_worktree / ".env"
        assert new_env_file.exists()
        assert new_env_file.read_text() == "SECRET=abc123"

    def test_raises_error_when_copy_file_does_not_exist(self, tmp_path) -> None:
        """below() raises ValueError when file to copy doesn't exist."""
        current_worktree = tmp_path / "current"
        current_worktree.mkdir()
        new_worktree = tmp_path / "new-worktree"

        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir=str(current_worktree),
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)

        with pytest.raises(ValueError, match="Cannot copy '.env': file does not exist"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=str(new_worktree),
                copy_files=[".env"],
            )


class TestBelowDryRun:
    def test_dry_run_does_not_create_branch(self, tmp_path) -> None:
        """below() with dry_run=True does not create a branch."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert len(repo.created_branches) == 0

    def test_dry_run_does_not_create_worktree(self, tmp_path) -> None:
        """below() with dry_run=True does not create a worktree."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert len(repo.created_worktrees) == 0

    def test_dry_run_does_not_create_pr(self, tmp_path) -> None:
        """below() with dry_run=True does not create a PR."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert len(repo.created_prs) == 0

    def test_dry_run_does_not_retarget_original_pr(self, tmp_path) -> None:
        """below() with dry_run=True does not change original PR's destination."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
        )

        # Original PR destination should still be 'main', not 'prep-work'
        assert pr.destination_branch.name == "main"

    def test_dry_run_does_not_copy_files(self, tmp_path) -> None:
        """below() with dry_run=True does not copy files."""
        current_worktree = tmp_path / "current"
        current_worktree.mkdir()
        env_file = current_worktree / ".env"
        env_file.write_text("SECRET=abc123")

        new_worktree = tmp_path / "new-worktree"

        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir=str(current_worktree),
        )
        client = _make_client(repos=[repo])

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=str(new_worktree),
            copy_files=[".env"],
            dry_run=True,
        )

        # Worktree directory should not exist (no files copied)
        assert not new_worktree.exists()

    def test_dry_run_returns_dry_run_result(self, tmp_path) -> None:
        """below() with dry_run=True returns a BelowDryRunResult."""
        from otstack.BelowDryRunResult import BelowDryRunResult

        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert isinstance(result, BelowDryRunResult)

    def test_dry_run_result_contains_planned_actions(self, tmp_path) -> None:
        """BelowDryRunResult contains all information about planned actions."""
        from otstack.BelowDryRunResult import BelowDryRunResult

        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
            title="Add user authentication",
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="auth-refactor",
            pr_title="Extract auth utilities",
            worktree_path=worktree_path,
            copy_files=[".env", ".env.local"],
            run_direnv=True,
            dry_run=True,
        )

        assert isinstance(result, BelowDryRunResult)
        assert result.current_branch_name == "feature-branch"
        assert result.current_pr is not None
        assert result.current_pr.title == "Add user authentication"
        assert result.new_branch_name == "auth-refactor"
        assert result.pr_title == "Extract auth utilities"
        assert result.worktree_path == worktree_path
        assert result.original_destination_name == "main"
        assert result.copy_files == [".env", ".env.local"]
        assert result.run_direnv is True

    def test_dry_run_result_format_output_includes_header(self, tmp_path) -> None:
        """BelowDryRunResult.format_output() includes dry-run header."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
        )

        from otstack.BelowDryRunResult import BelowDryRunResult

        assert isinstance(result, BelowDryRunResult)
        output = result.format_output()
        assert "Dry run - no changes will be made" in output

    def test_dry_run_result_format_output_has_current_state(self, tmp_path) -> None:
        """BelowDryRunResult.format_output() includes current state section."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
            title="Add user authentication",
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
        )

        from otstack.BelowDryRunResult import BelowDryRunResult

        assert isinstance(result, BelowDryRunResult)
        output = result.format_output()
        assert "Current state:" in output
        assert "Branch: feature-branch" in output
        assert '"Add user authentication"' in output
        assert "main" in output

    def test_dry_run_result_format_output_includes_planned_actions(
        self, tmp_path
    ) -> None:
        """BelowDryRunResult.format_output() includes all planned actions."""
        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
            title="Add user authentication",
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="auth-refactor",
            pr_title="Extract auth utilities",
            worktree_path=worktree_path,
            copy_files=[".env", ".env.local"],
            run_direnv=True,
            dry_run=True,
        )

        from otstack.BelowDryRunResult import BelowDryRunResult

        assert isinstance(result, BelowDryRunResult)
        output = result.format_output()
        assert "Actions that would be performed:" in output
        assert "Fetch latest 'main' from origin" in output
        assert "Create branch 'auth-refactor'" in output
        assert "origin/main" in output
        assert "Create worktree at" in output
        assert "Push 'auth-refactor' to origin" in output
        assert "Create PR:" in output
        assert "'auth-refactor'" in output
        assert "'main'" in output
        assert '"Extract auth utilities"' in output
        assert "Retarget" in output
        assert "'feature-branch'" in output
        assert "Copy files:" in output
        assert ".env" in output
        assert ".env.local" in output
        assert "direnv allow" in output

    def test_dry_run_draft_shows_draft_label(self, tmp_path) -> None:
        """BelowDryRunResult shows '(draft)' when draft=True."""
        from otstack.BelowDryRunResult import BelowDryRunResult

        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(
            current_branch=current_branch, pull_requests=[pr]
        )
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
            draft=True,
        )

        assert isinstance(result, BelowDryRunResult)
        output = result.format_output()
        assert "Create PR (draft):" in output

    def test_dry_run_no_draft_label_when_not_draft(
        self, tmp_path
    ) -> None:
        """BelowDryRunResult omits '(draft)' when draft=False."""
        from otstack.BelowDryRunResult import BelowDryRunResult

        current_branch = MockBranch(name="feature-branch")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(
            current_branch=current_branch, pull_requests=[pr]
        )
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
            draft=False,
        )

        assert isinstance(result, BelowDryRunResult)
        output = result.format_output()
        assert "(draft)" not in output
        assert "Create PR:" in output

    def test_dry_run_still_validates_detached_head(self) -> None:
        """dry_run=True still raises error when in detached HEAD state."""
        repo = _make_repo(current_branch=None)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You are in detached HEAD state"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
                dry_run=True,
            )

    def test_dry_run_still_validates_branch_exists(self) -> None:
        """dry_run=True still raises error when branch already exists."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        existing_branch = MockBranch(name="prep-work")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[existing_branch],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="Branch 'prep-work' already exists"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
                dry_run=True,
            )


class TestBelowCreatePr:
    def test_no_pr_without_create_pr_mentions_flag(
        self,
    ) -> None:
        """Error message mentions --create-pr flag."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(current_branch=current_branch)
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="--create-pr"
        ):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path="/tmp/project-prep-work",
            )

    def test_create_pr_pushes_current_branch(
        self, tmp_path
    ) -> None:
        """create_pr=True pushes current branch first."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            create_pr=True,
        )

        push_cmds = [
            cmd
            for cmd, _ in command_runner.commands
            if "push" in cmd
            and "feature-branch" in cmd
        ]
        assert len(push_cmds) == 1

    def test_create_pr_creates_pr_for_current_branch(
        self, tmp_path
    ) -> None:
        """create_pr=True creates PR for current branch."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            create_pr=True,
        )

        # First created PR is the initial one
        assert len(repo.created_prs) == 2
        src, dest, title, _ = repo.created_prs[0]
        assert src.name == "feature-branch"
        assert dest.name == "main"
        assert title == "Feature Branch"

    def test_create_pr_uses_default_branch(
        self, tmp_path
    ) -> None:
        """create_pr targets repo's default branch."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        repo._default_branch = "develop"
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            create_pr=True,
        )

        src, dest, _, _ = repo.created_prs[0]
        assert dest.name == "develop"

    def test_create_pr_proceeds_with_below(
        self, tmp_path
    ) -> None:
        """After initial PR creation, below proceeds."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            create_pr=True,
        )

        from otstack.BelowResult import BelowResult

        assert isinstance(result, BelowResult)
        assert result.new_branch.name == "prep-work"
        assert result.worktree_path == worktree_path

    def test_create_pr_dry_run_shows_initial_steps(
        self, tmp_path
    ) -> None:
        """Dry run with create_pr shows initial PR steps."""
        from otstack.BelowDryRunResult import (
            BelowDryRunResult,
        )

        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(
            current_branch=current_branch,
        )
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
            create_pr=True,
        )

        assert isinstance(result, BelowDryRunResult)
        assert result.create_initial_pr is True
        output = result.format_output()
        assert "Push 'feature-branch' to origin" in output
        assert "Feature Branch" in output
        assert "PR: (none)" in output

    def test_create_pr_dry_run_has_correct_destination(
        self, tmp_path
    ) -> None:
        """Dry run with create_pr uses default branch."""
        from otstack.BelowDryRunResult import (
            BelowDryRunResult,
        )

        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(
            current_branch=current_branch,
        )
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            dry_run=True,
            create_pr=True,
        )

        assert isinstance(result, BelowDryRunResult)
        assert result.initial_pr_destination == "main"
        assert result.original_destination_name == "main"

    def test_create_pr_outputs_creation_message(
        self, tmp_path
    ) -> None:
        """create_pr=True outputs PR creation message."""
        current_branch = MockBranch(name="feature-branch")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        output = io.StringIO()
        client = _make_client(
            repos=[repo],
            command_runner=command_runner,
            output=output,
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            create_pr=True,
        )

        printed = output.getvalue()
        assert "Created PR for 'feature-branch'" in printed


class TestBelowDefaultBranch:
    """Tests for below() when run from the default branch."""

    def test_below_on_default_branch_no_pr_succeeds(
        self, tmp_path
    ) -> None:
        """below() on default branch with no PR succeeds."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        from otstack.BelowResult import BelowResult

        result = client.below(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert isinstance(result, BelowResult)
        assert result.new_branch.name == "feature-a"

    def test_below_on_default_branch_creates_only_one_pr(
        self, tmp_path
    ) -> None:
        """below() on default branch creates only one PR."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert len(repo.created_prs) == 1
        src, dest, title, _ = repo.created_prs[0]
        assert src.name == "feature-a"
        assert dest.name == "main"
        assert title == "Feature A"

    def test_below_on_default_branch_no_retarget(
        self, tmp_path
    ) -> None:
        """below() on default branch does not retarget any PR."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        from otstack.BelowResult import BelowResult

        result = client.below(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert isinstance(result, BelowResult)
        assert result.original_pr is None

    def test_below_on_default_branch_with_create_pr_flag(
        self, tmp_path
    ) -> None:
        """--create-pr silently accepted on default branch."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        from otstack.BelowResult import BelowResult

        result = client.below(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
            create_pr=True,
        )

        assert isinstance(result, BelowResult)
        assert len(repo.created_prs) == 1

    def test_below_on_default_branch_does_not_push_default(
        self, tmp_path
    ) -> None:
        """below() on default branch does not push default."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        push_cmds = [
            cmd
            for cmd, _ in command_runner.commands
            if "push" in cmd
        ]
        assert len(push_cmds) == 1
        assert "feature-a" in push_cmds[0]

    def test_non_default_branch_no_pr_still_errors(
        self,
    ) -> None:
        """below() on non-default branch still errors."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="No open PR found"
        ):
            client.below(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_below_on_default_branch_fetches_default(
        self, tmp_path
    ) -> None:
        """below() on default branch fetches origin/default."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        fetch_cmds = [
            cmd
            for cmd, _ in command_runner.commands
            if "fetch" in cmd
        ]
        assert len(fetch_cmds) == 1
        assert "main" in fetch_cmds[0]

    def test_below_on_custom_default_branch(
        self, tmp_path
    ) -> None:
        """below() works with non-main default branch."""
        current_branch = MockBranch(name="develop")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
            working_dir="/tmp/repo",
        )
        repo._default_branch = "develop"
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        from otstack.BelowResult import BelowResult

        result = client.below(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert isinstance(result, BelowResult)
        assert len(repo.created_prs) == 1
        src, dest, _, _ = repo.created_prs[0]
        assert dest.name == "develop"


class TestBelowPushFailure:
    def test_push_failure_raises_value_error(self, tmp_path) -> None:
        """below() raises ValueError with clear message on push failure."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["push"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="Failed to push"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

    def test_push_failure_includes_branch_name(
        self, tmp_path
    ) -> None:
        """Push failure error includes the branch name."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["push"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="'prep-work'"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

    def test_push_failure_suggests_connectivity_check(
        self, tmp_path
    ) -> None:
        """Push failure error suggests checking connectivity."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["push"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(
            ValueError, match="network connectivity"
        ):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

    def test_push_failure_prints_recovery_message(
        self, tmp_path
    ) -> None:
        """Push failure prints recovery with undo commands."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["push"],
        )
        output = io.StringIO()
        client = _make_client(
            repos=[repo],
            command_runner=command_runner,
            output=output,
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

        printed = output.getvalue()
        assert "git branch -D prep-work" in printed
        assert (
            f"git worktree remove {worktree_path}"
            in printed
        )


class TestBelowCommitFailure:
    def test_commit_failure_raises_value_error(
        self, tmp_path
    ) -> None:
        """below() raises ValueError on commit failure."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["commit"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(
            ValueError, match="Pre-commit hooks rejected"
        ):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

    def test_commit_failure_suggests_no_verify(
        self, tmp_path
    ) -> None:
        """Commit failure suggests --no-verify."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["commit"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="--no-verify"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

    def test_commit_failure_includes_branch_name(
        self, tmp_path
    ) -> None:
        """Commit failure includes the branch name."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["commit"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="'prep-work'"):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

    def test_commit_failure_prints_recovery_message(
        self, tmp_path
    ) -> None:
        """Commit failure prints recovery with undo commands."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["commit"],
        )
        output = io.StringIO()
        client = _make_client(
            repos=[repo],
            command_runner=command_runner,
            output=output,
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

        printed = output.getvalue()
        assert "git branch -D prep-work" in printed
        assert (
            f"git worktree remove {worktree_path}"
            in printed
        )

    def test_no_verify_passes_flag_to_git_commit(
        self, tmp_path
    ) -> None:
        """below() passes --no-verify to git commit."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            no_verify=True,
        )

        commit_cmds = [
            cmd
            for cmd, _ in command_runner.commands
            if "commit" in cmd
        ]
        assert len(commit_cmds) == 1
        assert "--no-verify" in commit_cmds[0]

    def test_no_verify_false_omits_flag(
        self, tmp_path
    ) -> None:
        """below() omits --no-verify when no_verify=False."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            no_verify=False,
        )

        commit_cmds = [
            cmd
            for cmd, _ in command_runner.commands
            if "commit" in cmd
        ]
        assert len(commit_cmds) == 1
        assert "--no-verify" not in commit_cmds[0]


class TestBelowRecovery:
    def test_push_failure_recovery_lists_undo_commands(
        self, tmp_path
    ) -> None:
        """Push failure recovery lists branch and worktree undo."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["push"],
        )
        output = io.StringIO()
        client = _make_client(
            repos=[repo],
            command_runner=command_runner,
            output=output,
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

        printed = output.getvalue()
        assert "Recovery:" in printed
        assert "git branch -D prep-work" in printed
        assert (
            f"git worktree remove {worktree_path}"
            in printed
        )

    def test_pr_creation_failure_recovery_includes_push(
        self, tmp_path
    ) -> None:
        """PR creation failure recovery includes push undo."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(
            source_branch="feature-branch",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
            raise_on_create_pr=True,
        )
        command_runner = TrackingCommandRunner()
        output = io.StringIO()
        client = _make_client(
            repos=[repo],
            command_runner=command_runner,
            output=output,
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(RuntimeError):
            client.below(
                repo=repo,
                new_branch_name="prep-work",
                pr_title="Preparatory refactor",
                worktree_path=worktree_path,
            )

        printed = output.getvalue()
        assert "Recovery:" in printed
        assert "git branch -D prep-work" in printed
        assert (
            f"git worktree remove {worktree_path}"
            in printed
        )
        assert (
            "git push origin --delete prep-work"
            in printed
        )


class TestBelowDirenv:
    def test_runs_direnv_allow_in_worktree_when_flag_is_set(self, tmp_path) -> None:
        """below() runs 'direnv allow' in the new worktree when run_direnv=True."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            run_direnv=True,
        )

        assert (["direnv", "allow"], worktree_path) in command_runner.commands

    def test_does_not_run_direnv_when_flag_is_not_set(self, tmp_path) -> None:
        """below() does NOT run 'direnv allow' when run_direnv=False (default)."""
        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            run_direnv=False,
        )

        # Should not have direnv command (but will have git commands)
        direnv_commands = [cmd for cmd, _ in command_runner.commands if "direnv" in cmd]
        assert direnv_commands == []

    def test_prints_warning_when_direnv_not_found(self, tmp_path) -> None:
        """below() prints a warning when 'direnv' command is not found."""
        import io

        current_branch = MockBranch(name="feature-branch")
        pr = _make_pr(source_branch="feature-branch", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner(raise_file_not_found_for=["direnv"])
        output = io.StringIO()
        client = _make_client(
            repos=[repo], command_runner=command_runner, output=output
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.below(
            repo=repo,
            new_branch_name="prep-work",
            pr_title="Preparatory refactor",
            worktree_path=worktree_path,
            run_direnv=True,
        )

        output_text = output.getvalue()
        assert "Warning: 'direnv' command not found" in output_text


# Test helpers


def _make_client(
    repos: list[MockRepository],
    command_runner: TrackingCommandRunner | None = None,
    output: "io.StringIO | None" = None,
) -> OtStackClient:
    """Create an OtStackClient with the given repos."""
    mock_client = MockGitHubClient(repos=repos)
    return OtStackClient(
        github_client=mock_client, command_runner=command_runner, output=output
    )


def _make_repo(
    current_branch: MockBranch | None = None,
    pull_requests: list[MockPullRequest] | None = None,
    has_uncommitted_changes: bool = False,
    branches: list[MockBranch] | None = None,
    remote_branches: list[str] | None = None,
    working_dir: str | None = None,
    name: str = "test-repo",
    raise_on_create_pr: bool = False,
) -> MockRepository:
    """Create a MockRepository with configurable current branch."""
    prs: list[MockPullRequest] = pull_requests or []
    branch_list: list[MockBranch] = branches or []
    remote_list: list[str] = remote_branches or []
    return MockRepository(
        name=name,
        full_name=f"test-user/{name}",
        description="Test repository",
        private=False,
        url=f"https://github.com/test-user/{name}",
        _pull_requests=prs,
        _current_branch=current_branch,
        _has_uncommitted_changes=has_uncommitted_changes,
        _branches=branch_list,
        _remote_branches=remote_list,
        _working_dir=working_dir,
        _raise_on_create_pr=raise_on_create_pr,
    )


def _make_pr(
    source_branch: str,
    destination_branch: str,
    title: str = "Test PR",
    destination_branch_obj: MockBranch | None = None,
) -> MockPullRequest:
    """Create a MockPullRequest with the given branches."""
    dest = destination_branch_obj or MockBranch(name=destination_branch)
    return MockPullRequest(
        title=title,
        description=None,
        source_branch=MockBranch(name=source_branch),
        destination_branch=dest,
        url="https://github.com/test-user/test-repo/pull/1",
    )
