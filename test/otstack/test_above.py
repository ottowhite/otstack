import io

import pytest

from otstack.AboveDryRunResult import AboveDryRunResult
from otstack.AboveResult import AboveResult
from otstack.OtStackClient import OtStackClient

from .helpers.MockBranch import MockBranch
from .helpers.MockGitHubClient import MockGitHubClient
from .helpers.MockPullRequest import MockPullRequest
from .helpers.MockRepository import MockRepository
from .helpers.TrackingCommandRunner import TrackingCommandRunner


class TestAboveResult:
    def test_above_result_holds_new_branch_new_pr_current_pr_and_worktree_path(
        self,
    ) -> None:
        """AboveResult dataclass holds all result artifacts."""
        new_branch = MockBranch(name="feature-b")
        new_pr = _make_pr(source_branch="feature-b", destination_branch="feature-a")
        current_pr = _make_pr(source_branch="feature-a", destination_branch="main")

        result = AboveResult(
            new_branch=new_branch,
            new_pr=new_pr,
            current_pr=current_pr,
            worktree_path="/tmp/new-worktree",
        )

        assert result.new_branch.name == "feature-b"
        assert result.new_pr.source_branch.name == "feature-b"
        assert result.current_pr is not None
        assert result.current_pr.source_branch.name == "feature-a"
        assert result.worktree_path == "/tmp/new-worktree"


class TestAboveDryRunResult:
    def test_holds_all_planned_action_information(self) -> None:
        """AboveDryRunResult holds all information about planned actions."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=[".env"],
            run_direnv=True,
        )

        assert result.current_branch_name == "feature-a"
        assert result.current_pr is not None
        assert result.current_pr.title == "Feature A"
        assert result.new_branch_name == "feature-b"
        assert result.pr_title == "Feature B"
        assert result.worktree_path == "/tmp/new-worktree"
        assert result.copy_files == [".env"]
        assert result.run_direnv is True

    def test_format_output_includes_dry_run_header(self) -> None:
        """AboveDryRunResult.format_output() includes dry-run header."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=None,
            run_direnv=False,
        )

        output = result.format_output()
        assert "Dry run - no changes will be made" in output

    def test_format_output_includes_current_state(self) -> None:
        """AboveDryRunResult.format_output() includes current state section."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=None,
            run_direnv=False,
        )

        output = result.format_output()
        assert "Current state:" in output
        assert "Branch: feature-a" in output
        assert '"Feature A"' in output
        assert "main" in output

    def test_format_output_includes_planned_actions(self) -> None:
        """AboveDryRunResult.format_output() includes all planned actions."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=[".env", ".env.local"],
            run_direnv=True,
        )

        output = result.format_output()
        assert "Actions that would be performed:" in output
        # Key difference from below: branch is created from current, not destination
        assert "Create branch 'feature-b' from 'feature-a'" in output
        assert "Create worktree at /tmp/new-worktree" in output
        assert "Push 'feature-b' to origin" in output
        # Key difference: PR targets current branch, not destination
        assert "Create PR: 'feature-b' -> 'feature-a'" in output
        assert '"Feature B"' in output
        # Key difference: NO retargeting step
        assert "Retarget" not in output
        assert "Copy files:" in output
        assert ".env" in output
        assert ".env.local" in output
        assert "direnv allow" in output

    def test_format_output_shows_draft_label(self) -> None:
        """AboveDryRunResult shows '(draft)' when draft=True."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=None,
            run_direnv=False,
            draft=True,
        )

        output = result.format_output()
        assert "Create PR (draft):" in output

    def test_format_output_no_draft_label_when_not_draft(self) -> None:
        """AboveDryRunResult omits '(draft)' when draft=False."""
        current_pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )

        result = AboveDryRunResult(
            current_branch_name="feature-a",
            current_pr=current_pr,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/new-worktree",
            copy_files=None,
            run_direnv=False,
            draft=False,
        )

        output = result.format_output()
        assert "(draft)" not in output
        assert "Create PR:" in output


class TestAbove:
    def test_raises_error_when_in_detached_head_state(self) -> None:
        """above() raises ValueError when in detached HEAD state."""
        repo = _make_repo(current_branch=None)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You are in detached HEAD state"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_uncommitted_changes_exist(self) -> None:
        """above() raises ValueError when there are uncommitted changes."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(current_branch=current_branch, has_uncommitted_changes=True)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You have uncommitted changes"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_no_open_pr_for_current_branch(self) -> None:
        """above() raises ValueError when no open PR exists for current branch."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(current_branch=current_branch, pull_requests=[])
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="No open PR found for branch 'feature-a'"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_multiple_open_prs_for_current_branch(self) -> None:
        """above() raises ValueError when multiple open PRs exist for current branch."""
        current_branch = MockBranch(name="feature-a")
        pr1 = _make_pr(source_branch="feature-a", destination_branch="main")
        pr2 = _make_pr(source_branch="feature-a", destination_branch="develop")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr1, pr2])
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="Multiple open PRs found for branch 'feature-a'"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_new_branch_already_exists(self) -> None:
        """above() raises ValueError when new branch name already exists."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        existing_branch = MockBranch(name="feature-b")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[existing_branch],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="Branch 'feature-b' already exists"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_branch_exists_on_remote(self) -> None:
        """above() raises ValueError when branch exists on remote."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a", destination_branch="main"
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            remote_branches=["feature-b"],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError,
            match="Branch 'feature-b' already exists on remote",
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_raises_error_when_branch_exists_both_locally_and_remote(
        self,
    ) -> None:
        """above() raises ValueError when branch exists locally and remote."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a", destination_branch="main"
        )
        existing_branch = MockBranch(name="feature-b")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[existing_branch],
            remote_branches=["feature-b"],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="Branch 'feature-b' already exists"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_succeeds_when_branch_does_not_exist_anywhere(self) -> None:
        """above() proceeds when branch doesn't exist locally or remotely."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a", destination_branch="main"
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[],
            remote_branches=[],
            working_dir="/tmp/repo",
        )
        client = _make_client(repos=[repo])

        result = client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path="/tmp/project-feature-b",
            dry_run=True,
        )

        assert result is not None

    def test_raises_error_when_worktree_path_already_exists(self, tmp_path) -> None:
        """above() raises ValueError when worktree path already exists."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        existing_path = tmp_path / "existing-dir"
        existing_path.mkdir()

        with pytest.raises(ValueError, match="Path .* already exists"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=str(existing_path),
            )

    def test_creates_new_branch_from_current_branch(self, tmp_path) -> None:
        """above() creates new branch from current branch (not destination)."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
        )

        # Verify the new branch was created from current branch (feature-a)
        assert len(repo.created_branches) == 1
        branch_name, from_branch = repo.created_branches[0]
        assert branch_name == "feature-b"
        assert from_branch.name == "feature-a"

    def test_creates_worktree_for_new_branch(self, tmp_path) -> None:
        """above() creates a git worktree for the new branch."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
        )

        # Verify worktree was created
        assert len(repo.created_worktrees) == 1
        branch, path = repo.created_worktrees[0]
        assert branch.name == "feature-b"
        assert path == worktree_path

    def test_pushes_new_branch_to_origin(self, tmp_path) -> None:
        """above() pushes the new branch to origin."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
        )

        # Verify git push was called via command runner
        push_commands = [
            cmd for cmd, cwd in command_runner.commands if "push" in cmd
        ]
        assert len(push_commands) == 1
        assert push_commands[0] == ["git", "push", "-u", "origin", "feature-b"]

    def test_creates_pr_from_new_branch_to_current_branch(self, tmp_path) -> None:
        """above() creates a PR from new branch to current branch (not destination)."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
        )

        # Verify new PR was created targeting current branch
        assert len(repo.created_prs) == 1
        source, destination, title, draft = repo.created_prs[0]
        assert source.name == "feature-b"
        assert destination.name == "feature-a"  # Key difference from below
        assert title == "Feature B"

    def test_passes_draft_flag_to_create_pr(self, tmp_path) -> None:
        """above() passes draft=True to repo.create_pr()."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a", destination_branch="main"
        )
        repo = _make_repo(
            current_branch=current_branch, pull_requests=[pr]
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            draft=True,
        )

        assert len(repo.created_prs) == 1
        _, _, _, draft = repo.created_prs[0]
        assert draft is True

    def test_draft_defaults_to_false(self, tmp_path) -> None:
        """above() defaults draft=False in create_pr()."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a", destination_branch="main"
        )
        repo = _make_repo(
            current_branch=current_branch, pull_requests=[pr]
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
        )

        assert len(repo.created_prs) == 1
        _, _, _, draft = repo.created_prs[0]
        assert draft is False

    def test_does_not_retarget_current_pr(self, tmp_path) -> None:
        """above() does NOT change the current PR's destination (unlike below)."""
        current_branch = MockBranch(name="feature-a")
        main_branch = MockBranch(name="main")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            destination_branch_obj=main_branch,
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
        )

        # Key difference from below: current PR destination should still be 'main'
        assert pr.destination_branch.name == "main"

    def test_returns_above_result_with_all_artifacts(self, tmp_path) -> None:
        """above() returns AboveResult with new branch, PRs, and worktree path."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        result = client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
        )

        # Verify result contains all expected information
        assert isinstance(result, AboveResult)
        assert result.new_branch.name == "feature-b"
        assert result.new_pr.title == "Feature B"
        assert result.current_pr == pr
        assert result.worktree_path == worktree_path

    def test_copies_files_to_new_worktree(self, tmp_path) -> None:
        """above() copies specified files to the new worktree."""
        # Set up current worktree with a file
        current_worktree = tmp_path / "current"
        current_worktree.mkdir()
        env_file = current_worktree / ".env"
        env_file.write_text("SECRET=abc123")

        # Set up new worktree path
        new_worktree = tmp_path / "new-worktree"

        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir=str(current_worktree),
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=str(new_worktree),
            copy_files=[".env"],
        )

        # Verify file was copied
        new_env_file = new_worktree / ".env"
        assert new_env_file.exists()
        assert new_env_file.read_text() == "SECRET=abc123"

    def test_raises_error_when_copy_file_does_not_exist(self, tmp_path) -> None:
        """above() raises ValueError when file to copy doesn't exist."""
        current_worktree = tmp_path / "current"
        current_worktree.mkdir()
        new_worktree = tmp_path / "new-worktree"

        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir=str(current_worktree),
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)

        with pytest.raises(
            ValueError, match="Cannot copy '.env': file does not exist"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=str(new_worktree),
                copy_files=[".env"],
            )


class TestAboveCreatePr:
    def test_no_pr_without_create_pr_mentions_flag(
        self,
    ) -> None:
        """Error message mentions --create-pr flag."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(current_branch=current_branch)
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="--create-pr"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_create_pr_pushes_current_branch(
        self, tmp_path
    ) -> None:
        """create_pr=True pushes current branch first."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            create_pr=True,
        )

        push_cmds = [
            cmd
            for cmd, _ in command_runner.commands
            if "push" in cmd and "feature-a" in cmd
        ]
        assert len(push_cmds) == 1

    def test_create_pr_creates_pr_for_current_branch(
        self, tmp_path
    ) -> None:
        """create_pr=True creates PR for current branch."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            create_pr=True,
        )

        # First PR is the initial one, second is above
        assert len(repo.created_prs) == 2
        src, dest, title, _ = repo.created_prs[0]
        assert src.name == "feature-a"
        assert dest.name == "main"
        assert title == "Feature A"

    def test_create_pr_uses_default_branch(
        self, tmp_path
    ) -> None:
        """create_pr targets repo's default branch."""
        current_branch = MockBranch(name="feature-a")
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

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            create_pr=True,
        )

        _, dest, _, _ = repo.created_prs[0]
        assert dest.name == "develop"

    def test_create_pr_proceeds_with_above(
        self, tmp_path
    ) -> None:
        """After initial PR creation, above proceeds."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(
            current_branch=current_branch,
            working_dir="/tmp/repo",
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        result = client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            create_pr=True,
        )

        assert isinstance(result, AboveResult)
        assert result.new_branch.name == "feature-b"
        assert result.worktree_path == worktree_path

    def test_create_pr_dry_run_shows_initial_steps(
        self, tmp_path
    ) -> None:
        """Dry run with create_pr shows initial steps."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(
            current_branch=current_branch,
        )
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            dry_run=True,
            create_pr=True,
        )

        assert isinstance(result, AboveDryRunResult)
        assert result.create_initial_pr is True
        output = result.format_output()
        assert "Push 'feature-a' to origin" in output
        assert "Feature A" in output
        assert "PR: (none)" in output

    def test_create_pr_outputs_creation_message(
        self, tmp_path
    ) -> None:
        """create_pr=True outputs PR creation message."""
        current_branch = MockBranch(name="feature-a")
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

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            create_pr=True,
        )

        printed = output.getvalue()
        assert "Created PR for 'feature-a'" in printed


class TestAboveDefaultBranch:
    """Tests for above() when run from the default branch with no PR."""

    def test_above_on_default_branch_no_pr_succeeds(
        self, tmp_path
    ) -> None:
        """above() on default branch with no PR succeeds without --create-pr."""
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

        result = client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert isinstance(result, AboveResult)
        assert result.new_branch.name == "feature-a"

    def test_above_on_default_branch_creates_only_one_pr(
        self, tmp_path
    ) -> None:
        """above() on default branch creates only the new PR, no initial PR."""
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

        client.above(
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

    def test_above_on_default_branch_current_pr_is_none(
        self, tmp_path
    ) -> None:
        """above() on default branch returns None for current_pr."""
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

        result = client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert isinstance(result, AboveResult)
        assert result.current_pr is None

    def test_above_on_default_branch_with_create_pr_flag(
        self, tmp_path
    ) -> None:
        """--create-pr is silently accepted on default branch."""
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

        result = client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
            create_pr=True,
        )

        assert isinstance(result, AboveResult)
        # Still only one PR created (no initial PR)
        assert len(repo.created_prs) == 1

    def test_above_on_default_branch_does_not_push_default_branch(
        self, tmp_path
    ) -> None:
        """above() on default branch does not push the default branch itself."""
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

        client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        # Only push should be for the new branch
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
        """above() on non-default branch with no PR still errors without --create-pr."""
        current_branch = MockBranch(name="feature-a")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(
            ValueError, match="No open PR found"
        ):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
            )

    def test_above_on_default_branch_creates_branch_from_default(
        self, tmp_path
    ) -> None:
        """above() on default branch creates new branch from the default branch."""
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

        client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert len(repo.created_branches) == 1
        branch_name, from_branch = repo.created_branches[0]
        assert branch_name == "feature-a"
        assert from_branch.name == "main"

    def test_above_on_custom_default_branch(
        self, tmp_path
    ) -> None:
        """above() works when default branch is not 'main' (e.g. 'develop')."""
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

        result = client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path=worktree_path,
        )

        assert isinstance(result, AboveResult)
        assert len(repo.created_prs) == 1
        src, dest, _, _ = repo.created_prs[0]
        assert dest.name == "develop"

    def test_dry_run_on_default_branch_shows_simplified(
        self,
    ) -> None:
        """Dry-run on default branch shows simplified plan."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
        )
        client = _make_client(repos=[repo])

        result = client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path="/tmp/new-worktree",
            dry_run=True,
        )

        assert isinstance(result, AboveDryRunResult)
        output = result.format_output()
        assert "PR: (none)" in output
        assert "Create branch 'feature-a'" in output
        assert "Create worktree" in output
        assert "Push 'feature-a' to origin" in output
        assert (
            "Create PR: 'feature-a' -> 'main'" in output
        )
        # Should NOT mention creating initial PR
        assert "Push 'main' to origin" not in output
        assert "create_initial" not in output.lower()

    def test_dry_run_on_default_branch_no_initial_pr(
        self,
    ) -> None:
        """Dry-run on default branch has no initial PR."""
        current_branch = MockBranch(name="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[],
        )
        client = _make_client(repos=[repo])

        result = client.above(
            repo=repo,
            new_branch_name="feature-a",
            pr_title="Feature A",
            worktree_path="/tmp/new-worktree",
            dry_run=True,
        )

        assert isinstance(result, AboveDryRunResult)
        assert result.create_initial_pr is False


class TestAbovePushFailure:
    def test_push_failure_raises_value_error(self, tmp_path) -> None:
        """above() raises ValueError with clear message on push failure."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["push"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="Failed to push"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

    def test_push_failure_includes_branch_name(
        self, tmp_path
    ) -> None:
        """Push failure error includes the branch name."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["push"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="'feature-b'"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

    def test_push_failure_suggests_connectivity_check(
        self, tmp_path
    ) -> None:
        """Push failure error suggests checking connectivity."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
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
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

    def test_push_failure_auto_recovers(
        self, tmp_path
    ) -> None:
        """Push failure executes undo commands automatically."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
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
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

        undo_cmds = [
            cmd for cmd, _ in command_runner.commands
        ]
        assert (
            ["git", "worktree", "remove", worktree_path]
            in undo_cmds
        )
        assert (
            ["git", "branch", "-D", "feature-b"]
            in undo_cmds
        )
        printed = output.getvalue()
        assert "Undone:" in printed


class TestAboveCommitFailure:
    def test_commit_failure_raises_value_error(
        self, tmp_path
    ) -> None:
        """above() raises ValueError on commit failure."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
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
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

    def test_commit_failure_suggests_no_verify(
        self, tmp_path
    ) -> None:
        """Commit failure suggests --no-verify."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["commit"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="--no-verify"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

    def test_commit_failure_includes_branch_name(
        self, tmp_path
    ) -> None:
        """Commit failure includes the branch name."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
        )
        command_runner = TrackingCommandRunner(
            raise_called_process_error_for=["commit"],
        )
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        with pytest.raises(ValueError, match="'feature-b'"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

    def test_commit_failure_auto_recovers(
        self, tmp_path
    ) -> None:
        """Commit failure executes undo commands automatically."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
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
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

        undo_cmds = [
            cmd for cmd, _ in command_runner.commands
        ]
        assert (
            ["git", "worktree", "remove", worktree_path]
            in undo_cmds
        )
        assert (
            ["git", "branch", "-D", "feature-b"]
            in undo_cmds
        )
        printed = output.getvalue()
        assert "Undone:" in printed

    def test_no_verify_passes_flag_to_git_commit(
        self, tmp_path
    ) -> None:
        """above() passes --no-verify to git commit."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
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
        """above() omits --no-verify when no_verify=False."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
        )
        command_runner = TrackingCommandRunner()
        client = _make_client(
            repos=[repo], command_runner=command_runner
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
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


class TestAboveRecovery:
    def test_push_failure_recovery_undoes_in_reverse(
        self, tmp_path
    ) -> None:
        """Push failure undoes steps in reverse order."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
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
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

        undo_cmds = [
            cmd for cmd, _ in command_runner.commands
        ]
        # Worktree remove should come before branch delete
        # (reverse of creation order)
        wt_idx = undo_cmds.index(
            ["git", "worktree", "remove", worktree_path]
        )
        br_idx = undo_cmds.index(
            ["git", "branch", "-D", "feature-b"]
        )
        assert wt_idx < br_idx
        printed = output.getvalue()
        assert "Recovery:" in printed

    def test_pr_creation_failure_recovery_includes_push(
        self, tmp_path
    ) -> None:
        """PR creation failure recovery undoes push too."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
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
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path=worktree_path,
            )

        undo_cmds = [
            cmd for cmd, _ in command_runner.commands
        ]
        assert (
            [
                "git", "push", "origin", "--delete",
                "feature-b",
            ]
            in undo_cmds
        )
        assert (
            ["git", "worktree", "remove", worktree_path]
            in undo_cmds
        )
        assert (
            ["git", "branch", "-D", "feature-b"]
            in undo_cmds
        )


class TestAboveDirenv:
    def test_runs_direnv_allow_in_worktree_when_flag_is_set(self, tmp_path) -> None:
        """above() runs 'direnv allow' in the new worktree when run_direnv=True."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            run_direnv=True,
        )

        assert (["direnv", "allow"], worktree_path) in command_runner.commands

    def test_does_not_run_direnv_when_flag_is_not_set(self, tmp_path) -> None:
        """above() does NOT run 'direnv allow' when run_direnv=False (default)."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner()
        client = _make_client(repos=[repo], command_runner=command_runner)
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            run_direnv=False,
        )

        # Should not have direnv command (but will have git commands)
        direnv_commands = [
            cmd for cmd, _ in command_runner.commands if "direnv" in cmd
        ]
        assert direnv_commands == []

    def test_prints_warning_when_direnv_not_found(self, tmp_path) -> None:
        """above() prints a warning when 'direnv' command is not found."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        command_runner = TrackingCommandRunner(raise_file_not_found_for=["direnv"])
        output = io.StringIO()
        client = _make_client(
            repos=[repo], command_runner=command_runner, output=output
        )
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            run_direnv=True,
        )

        output_text = output.getvalue()
        assert "Warning: 'direnv' command not found" in output_text


class TestAboveDryRun:
    def test_dry_run_does_not_create_branch(self, tmp_path) -> None:
        """above() with dry_run=True does not create a branch."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert len(repo.created_branches) == 0

    def test_dry_run_does_not_create_worktree(self, tmp_path) -> None:
        """above() with dry_run=True does not create a worktree."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert len(repo.created_worktrees) == 0

    def test_dry_run_does_not_create_pr(self, tmp_path) -> None:
        """above() with dry_run=True does not create a PR."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert len(repo.created_prs) == 0

    def test_dry_run_does_not_copy_files(self, tmp_path) -> None:
        """above() with dry_run=True does not copy files."""
        current_worktree = tmp_path / "current"
        current_worktree.mkdir()
        env_file = current_worktree / ".env"
        env_file.write_text("SECRET=abc123")

        new_worktree = tmp_path / "new-worktree"

        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            working_dir=str(current_worktree),
        )
        client = _make_client(repos=[repo])

        client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=str(new_worktree),
            copy_files=[".env"],
            dry_run=True,
        )

        # Worktree directory should not exist (no files copied)
        assert not new_worktree.exists()

    def test_dry_run_returns_dry_run_result(self, tmp_path) -> None:
        """above() with dry_run=True returns an AboveDryRunResult."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            dry_run=True,
        )

        assert isinstance(result, AboveDryRunResult)

    def test_dry_run_result_contains_planned_actions(self, tmp_path) -> None:
        """AboveDryRunResult contains all information about planned actions."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(
            source_branch="feature-a",
            destination_branch="main",
            title="Feature A",
        )
        repo = _make_repo(current_branch=current_branch, pull_requests=[pr])
        client = _make_client(repos=[repo])
        worktree_path = str(tmp_path / "new-worktree")

        result = client.above(
            repo=repo,
            new_branch_name="feature-b",
            pr_title="Feature B",
            worktree_path=worktree_path,
            copy_files=[".env", ".env.local"],
            run_direnv=True,
            dry_run=True,
        )

        assert isinstance(result, AboveDryRunResult)
        assert result.current_branch_name == "feature-a"
        assert result.current_pr is not None
        assert result.current_pr.title == "Feature A"
        assert result.new_branch_name == "feature-b"
        assert result.pr_title == "Feature B"
        assert result.worktree_path == worktree_path
        assert result.copy_files == [".env", ".env.local"]
        assert result.run_direnv is True

    def test_dry_run_still_validates_detached_head(self) -> None:
        """dry_run=True still raises error when in detached HEAD state."""
        repo = _make_repo(current_branch=None)
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="You are in detached HEAD state"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
                dry_run=True,
            )

    def test_dry_run_still_validates_branch_exists(self) -> None:
        """dry_run=True still raises error when branch already exists."""
        current_branch = MockBranch(name="feature-a")
        pr = _make_pr(source_branch="feature-a", destination_branch="main")
        existing_branch = MockBranch(name="feature-b")
        repo = _make_repo(
            current_branch=current_branch,
            pull_requests=[pr],
            branches=[existing_branch],
        )
        client = _make_client(repos=[repo])

        with pytest.raises(ValueError, match="Branch 'feature-b' already exists"):
            client.above(
                repo=repo,
                new_branch_name="feature-b",
                pr_title="Feature B",
                worktree_path="/tmp/project-feature-b",
                dry_run=True,
            )


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
    working_dir: str | None = "/tmp/repo",
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
    return MockPullRequest(
        title=title,
        description=None,
        source_branch=MockBranch(name=source_branch),
        destination_branch=(
            destination_branch_obj or MockBranch(name=destination_branch)
        ),
        url="https://github.com/test-user/test-repo/pull/1",
    )
