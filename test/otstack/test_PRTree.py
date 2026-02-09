from otstack.PRTree import PRTree

from .helpers.MockBranch import MockBranch
from .helpers.MockPullRequest import MockPullRequest


class TestPRTree:
    def test_prtree_holds_branch_name_and_children(self) -> None:
        """PRTree dataclass holds branch_name, pull_request, and children."""
        pr = _make_pr(title="Test PR", source_branch="feature", destination_branch="main")

        tree = PRTree(
            branch_name="feature",
            pull_request=pr,
            children=[],
        )

        assert tree.branch_name == "feature"
        assert tree.pull_request == pr
        assert tree.children == []


# Test helpers


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
