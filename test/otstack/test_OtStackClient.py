from io import StringIO

from otstack.OtStackClient import OtStackClient
from otstack.PullRequest import PullRequest
from otstack.Repository import Repository

from .helpers.MockBranch import MockBranch
from .helpers.MockGitHubClient import MockGitHubClient
from .helpers.MockGitRepoDetector import MockGitRepoDetector
from .helpers.MockPullRequest import MockPullRequest
from .helpers.MockRepository import MockRepository


def test_otstack_client_uses_injected_github_client() -> None:
    mock_repos = [
        MockRepository(
            name="test-repo",
            full_name="test-user/test-repo",
            description="A test repository",
            private=False,
            url="https://github.com/test-user/test-repo",
        )
    ]
    mock_client = MockGitHubClient(repos=mock_repos)

    client = OtStackClient(github_client=mock_client)

    repos = client.github.get_user_repos()
    assert len(repos) == 1
    assert repos[0].name == "test-repo"


def test_get_repo_returns_repository_by_name() -> None:
    repo = MockRepository(
        name="test-repo",
        full_name="test-user/test-repo",
        description="A test repository",
        private=False,
        url="https://github.com/test-user/test-repo",
    )
    mock_client = MockGitHubClient(repos=[repo])
    client = OtStackClient(github_client=mock_client)

    result = client.get_repo("test-user/test-repo")

    assert result.name == "test-repo"


class TestDetectRepoName:
    def test_returns_repo_name_when_detected(self) -> None:
        mock_client = MockGitHubClient(repos=[])
        mock_detector = MockGitRepoDetector(repo_name="owner/repo")
        client = OtStackClient(
            github_client=mock_client, repo_detector=mock_detector
        )

        result = client.detect_repo_name()

        assert result == "owner/repo"

    def test_returns_none_when_not_in_git_repo(self) -> None:
        mock_client = MockGitHubClient(repos=[])
        mock_detector = MockGitRepoDetector(repo_name=None)
        client = OtStackClient(
            github_client=mock_client, repo_detector=mock_detector
        )

        result = client.detect_repo_name()

        assert result is None


class TestGetPrTree:
    def test_returns_tree_with_no_children_when_no_prs_target_branch(self) -> None:
        """When no PRs target the given branch, return a tree with empty children."""
        repo = _make_repo(pull_requests=[])
        client = _make_client(repos=[repo])

        tree = client.get_pr_tree(repo, "main")

        assert tree.branch_name == "main"
        assert tree.pull_request is None
        assert tree.children == []

    def test_returns_tree_with_child_for_pr_targeting_branch(self) -> None:
        """When a PR targets the given branch, return a tree with that PR as a child."""
        pr = _make_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr])
        client = _make_client(repos=[repo])

        tree = client.get_pr_tree(repo, "main")

        assert tree.branch_name == "main"
        assert tree.pull_request is None
        assert len(tree.children) == 1
        child = tree.children[0]
        assert child.branch_name == "feature-a"
        assert child.pull_request == pr
        assert child.children == []

    def test_returns_nested_tree_for_chained_prs(self) -> None:
        """When PRs are chained, return a nested tree structure."""
        pr_a = _make_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        pr_b = _make_pr(
            title="Add feature B",
            source_branch="feature-b",
            destination_branch="feature-a",
        )
        repo = _make_repo(pull_requests=[pr_a, pr_b])
        client = _make_client(repos=[repo])

        tree = client.get_pr_tree(repo, "main")

        # main -> feature-a -> feature-b
        assert tree.branch_name == "main"
        assert len(tree.children) == 1
        child_a = tree.children[0]
        assert child_a.branch_name == "feature-a"
        assert child_a.pull_request == pr_a
        assert len(child_a.children) == 1
        child_b = child_a.children[0]
        assert child_b.branch_name == "feature-b"
        assert child_b.pull_request == pr_b
        assert child_b.children == []

    def test_returns_multiple_children_for_multiple_prs_targeting_same_branch(
        self,
    ) -> None:
        """When multiple PRs target the same branch, all are included as children."""
        pr_a = _make_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        pr_b = _make_pr(
            title="Add feature B",
            source_branch="feature-b",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr_a, pr_b])
        client = _make_client(repos=[repo])

        tree = client.get_pr_tree(repo, "main")

        assert tree.branch_name == "main"
        assert len(tree.children) == 2
        branch_names = {child.branch_name for child in tree.children}
        assert branch_names == {"feature-a", "feature-b"}


class TestTree:
    def test_no_prs_returns_empty_output(self) -> None:
        repo = _make_repo(pull_requests=[])
        client, output = _make_client_with_output(repos=[repo])

        client.tree(repo)

        assert output.getvalue() == ""

    def test_single_pr_shows_horizontal_tree(self) -> None:
        pr = _make_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr])
        client, output = _make_client_with_output(repos=[repo], terminal_width=60)

        client.tree(repo)

        # Content centered in 60-char width
        # feature-a: 9 chars, padding = (60-9)//2 = 25
        # "Add feature A": 15 chars, padding = (60-15)//2 = 22
        # |: 1 char, padding = (60-1)//2 = 29
        # main: 4 chars, padding = (60-4)//2 = 28
        expected = """\
                         feature-a
                      "Add feature A"
                             |
                            main
"""
        assert output.getvalue() == expected

    def test_two_independent_prs_shows_two_columns(self) -> None:
        pr1 = _make_pr(
            title="Add A",
            source_branch="feature-a",
            destination_branch="main",
        )
        pr2 = _make_pr(
            title="Add B",
            source_branch="feature-b",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr1, pr2])
        client, output = _make_client_with_output(repos=[repo], terminal_width=60)

        client.tree(repo)

        # Two columns of 30 chars each
        # feature-a centered in 30: (30-9)//2 = 10 spaces
        # feature-b centered in 30: (30-9)//2 = 10 spaces
        # "Add A" centered in 30: (30-7)//2 = 11 spaces
        # "Add B" centered in 30: (30-7)//2 = 11 spaces
        # | centered in 30: (30-1)//2 = 14 spaces
        # Horizontal connector line with + at junction points
        expected = """\
          feature-a                     feature-b
           "Add A"                       "Add B"
              |                             |
              +-----------------------------+
                             |
                            main
"""
        assert output.getvalue() == expected

    def test_chained_prs_shows_vertical_stack_in_single_column(self) -> None:
        """PR feature-b depends on feature-a which depends on main."""
        pr1 = _make_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        pr2 = _make_pr(
            title="Add feature B",
            source_branch="feature-b",
            destination_branch="feature-a",
        )
        repo = _make_repo(pull_requests=[pr1, pr2])
        client, output = _make_client_with_output(repos=[repo], terminal_width=60)

        client.tree(repo)

        # Chained PRs appear stacked vertically in one column
        expected = """\
                         feature-b
                      "Add feature B"
                             |
                         feature-a
                      "Add feature A"
                             |
                            main
"""
        assert output.getvalue() == expected

    def test_complex_dag_with_chain_and_independent_pr(self) -> None:
        """
        Complex DAG structure:
        main <- feature-a <- feature-b
        main <- feature-c

        Should display as:
                  feature-b
               "Add feature B"
                      |
          feature-a                     feature-c
       "Add feature A"               "Add feature C"
              |                             |
              +-----------------------------+
                             |
                            main
        """
        pr_a = _make_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        pr_b = _make_pr(
            title="Add feature B",
            source_branch="feature-b",
            destination_branch="feature-a",
        )
        pr_c = _make_pr(
            title="Add feature C",
            source_branch="feature-c",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr_a, pr_b, pr_c])
        client, output = _make_client_with_output(repos=[repo], terminal_width=60)

        client.tree(repo)

        # Two columns: feature-a (with child feature-b above) and feature-c
        expected = """\
          feature-b
       "Add feature B"
              |
          feature-a                     feature-c
       "Add feature A"               "Add feature C"
              |                             |
              +-----------------------------+
                             |
                            main
"""
        assert output.getvalue() == expected

    def test_long_branch_name_is_truncated(self) -> None:
        """Branch names longer than column width - 2 are truncated with ..."""
        pr = _make_pr(
            title="Add A",
            source_branch="this-is-a-very-long-branch-name-that-exceeds-width",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr])
        # With width=40, the name has 50 chars, max is 38, so truncate at 35 + "..."
        client, output = _make_client_with_output(repos=[repo], terminal_width=40)

        client.tree(repo)

        # Branch name should be truncated to fit within width - 2 = 38 chars
        # "this-is-a-very-long-branch-name-tha..." (35 chars + 3 dots = 38)
        # centered in 40: (40 - 38) // 2 = 1 space
        expected = """\
 this-is-a-very-long-branch-name-tha...
                "Add A"
                   |
                  main
"""
        assert output.getvalue() == expected

    def test_long_pr_title_is_truncated(self) -> None:
        """PR titles longer than column width - 2 are truncated with ..."""
        pr = _make_pr(
            title="This is a very long PR title that definitely exceeds the width",
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr])
        # With width=40, max text width is 38
        client, output = _make_client_with_output(repos=[repo], terminal_width=40)

        client.tree(repo)

        # PR title (with quotes) should be truncated to 38 chars
        # Title with quotes: '"This is a very long PR title that definitely exceeds the width"' (64 chars)
        # Truncated to: '"This is a very long PR title that ...' (38 chars)
        # centered in 40: (40 - 38) // 2 = 1 space
        expected = """\
               feature-a
 "This is a very long PR title that ...
                   |
                  main
"""
        assert output.getvalue() == expected

    def test_truncation_in_multi_column_layout(self) -> None:
        """Long branch names and titles are truncated in multi-column layout."""
        pr1 = _make_pr(
            title="This is a very long title for A",
            source_branch="feature-a-with-long-name",
            destination_branch="main",
        )
        pr2 = _make_pr(
            title="Short B",
            source_branch="feature-b",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr1, pr2])
        # With width=50, each column is 25 chars, max text width is 23
        client, output = _make_client_with_output(repos=[repo], terminal_width=50)

        client.tree(repo)

        # Column width is 25, max text width is 23 (25-2)
        # "feature-a-with-long-name" (24 chars) -> "feature-a-with-long-..." (23 chars)
        # '"This is a very long title for A"' (33 chars) -> '"This is a very long...' (23 chars)
        expected = """\
 feature-a-with-long-...         feature-b
 "This is a very long...         "Short B"
            |                        |
            +------------------------+
                        |
                       main
"""
        assert output.getvalue() == expected


class TestSync:
    def test_sync_returns_true_when_no_prs(self) -> None:
        """sync() returns True when there are no PRs."""
        repo = _make_repo(pull_requests=[])
        client, output = _make_client_with_output(repos=[repo])

        result = client.sync(repo)

        assert result is True

    def test_sync_returns_true_when_all_local_prs_synced(self) -> None:
        """sync() returns True when all local PRs are synced successfully."""
        pr = _make_local_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr])
        client, output = _make_client_with_output(repos=[repo])

        result = client.sync(repo)

        assert result is True
        assert "Synced: feature-a" in output.getvalue()
        assert "main" in output.getvalue()

    def test_sync_returns_false_when_merge_conflicts(self) -> None:
        """sync() returns False when a merge would conflict."""
        pr = _make_local_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
            source_merge_will_conflict=True,
        )
        repo = _make_repo(pull_requests=[pr])
        client, output = _make_client_with_output(repos=[repo])

        result = client.sync(repo)

        assert result is False
        assert "Sync failed" in output.getvalue()
        assert "conflicts" in output.getvalue()

    def test_sync_skips_non_local_prs(self) -> None:
        """sync() skips PRs that are not local."""
        # Non-local PR (default MockBranch has _is_local=False)
        pr = _make_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        repo = _make_repo(pull_requests=[pr])
        client, output = _make_client_with_output(repos=[repo])

        result = client.sync(repo)

        assert result is True
        # No sync output for non-local PR
        assert "Synced:" not in output.getvalue()

    def test_sync_processes_prs_in_topdown_order(self) -> None:
        """sync() processes PRs from root (main) toward leaves."""
        # PR chain: main <- feature-a <- feature-b
        pr_a = _make_local_pr(
            title="Add feature A",
            source_branch="feature-a",
            destination_branch="main",
        )
        pr_b = _make_local_pr(
            title="Add feature B",
            source_branch="feature-b",
            destination_branch="feature-a",
        )
        repo = _make_repo(pull_requests=[pr_a, pr_b])
        client, output = _make_client_with_output(repos=[repo])

        result = client.sync(repo)

        assert result is True
        output_text = output.getvalue()
        # feature-a should be synced before feature-b (topdown order)
        assert output_text.index("feature-a") < output_text.index("feature-b")


# Test helpers


def _make_client(repos: list[Repository]) -> OtStackClient:
    """Create an OtStackClient with the given repos."""
    mock_client = MockGitHubClient(repos=repos)
    return OtStackClient(github_client=mock_client)


def _make_client_with_output(
    repos: list[Repository],
    terminal_width: int = 60,
) -> tuple[OtStackClient, StringIO]:
    """Create an OtStackClient with captured stdout."""
    mock_client = MockGitHubClient(repos=repos)
    output = StringIO()
    client = OtStackClient(
        github_client=mock_client, output=output, terminal_width=terminal_width
    )
    return client, output


def _make_repo(
    pull_requests: list[PullRequest],
    name: str = "test-repo",
) -> MockRepository:
    """Create a MockRepository with the given PRs."""
    return MockRepository(
        name=name,
        full_name=f"test-user/{name}",
        description="Test repository",
        private=False,
        url=f"https://github.com/test-user/{name}",
        _pull_requests=pull_requests,
    )


def _make_pr(
    title: str,
    source_branch: str,
    destination_branch: str,
) -> MockPullRequest:
    """Create a MockPullRequest with the given properties."""
    return MockPullRequest(
        title=title,
        description=None,
        source_branch=MockBranch(name=source_branch),
        destination_branch=MockBranch(name=destination_branch),
        url="https://github.com/test-user/test-repo/pull/1",
    )


def _make_local_pr(
    title: str,
    source_branch: str,
    destination_branch: str,
    source_merge_will_conflict: bool = False,
) -> MockPullRequest:
    """Create a MockPullRequest with local branches for sync testing."""
    return MockPullRequest(
        title=title,
        description=None,
        source_branch=MockBranch(
            name=source_branch,
            _is_local=True,
            _merge_will_conflict=source_merge_will_conflict,
        ),
        destination_branch=MockBranch(name=destination_branch, _is_local=True),
        url="https://github.com/test-user/test-repo/pull/1",
    )
