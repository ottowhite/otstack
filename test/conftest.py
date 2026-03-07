import pytest

# Git environment variables set during hooks (pre-commit, etc.)
# that interfere with git operations on other repos in tests.
_GIT_HOOK_ENV_VARS = [
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_WORK_TREE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_PREFIX",
]


@pytest.fixture(autouse=True)
def _clean_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove git hook environment variables so tests can run git commands
    against their own temporary repos without interference."""
    for var in _GIT_HOOK_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
