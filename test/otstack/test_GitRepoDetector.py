from otstack.GitRepoDetector import GitPythonRepoDetector


class TestGitPythonRepoDetector:
    """Tests for GitPythonRepoDetector."""

    class TestParseGitHubUrl:
        """Tests for _parse_github_url method."""

        def test_parses_https_url_with_git_extension(self) -> None:
            detector = GitPythonRepoDetector()
            result = detector._parse_github_url(
                "https://github.com/owner/repo.git"
            )
            assert result == "owner/repo"

        def test_parses_https_url_without_git_extension(self) -> None:
            detector = GitPythonRepoDetector()
            result = detector._parse_github_url("https://github.com/owner/repo")
            assert result == "owner/repo"

        def test_parses_ssh_url_with_git_extension(self) -> None:
            detector = GitPythonRepoDetector()
            result = detector._parse_github_url("git@github.com:owner/repo.git")
            assert result == "owner/repo"

        def test_parses_ssh_url_without_git_extension(self) -> None:
            detector = GitPythonRepoDetector()
            result = detector._parse_github_url("git@github.com:owner/repo")
            assert result == "owner/repo"

        def test_returns_none_for_non_github_https_url(self) -> None:
            detector = GitPythonRepoDetector()
            result = detector._parse_github_url(
                "https://gitlab.com/owner/repo.git"
            )
            assert result is None

        def test_returns_none_for_non_github_ssh_url(self) -> None:
            detector = GitPythonRepoDetector()
            result = detector._parse_github_url("git@gitlab.com:owner/repo.git")
            assert result is None

        def test_returns_none_for_invalid_url(self) -> None:
            detector = GitPythonRepoDetector()
            result = detector._parse_github_url("not-a-url")
            assert result is None

    class TestGetRepoName:
        """Tests for get_repo_name method."""

        def test_returns_none_for_non_git_directory(self, tmp_path) -> None:
            detector = GitPythonRepoDetector(str(tmp_path))
            result = detector.get_repo_name()
            assert result is None
