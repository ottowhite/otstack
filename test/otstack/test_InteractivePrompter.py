from unittest.mock import patch

from otstack.InteractivePrompter import InteractivePrompter

_MOD = "otstack.InteractivePrompter.questionary"


class TestPromptBelowAboveInputsPrefilledValues:
    """Tests that pre-filled values skip prompts."""

    def _mock_ask(self, return_value):
        """Create a mock questionary question that returns a value."""

        class MockQuestion:
            def ask(self):
                return return_value

        return MockQuestion()

    def test_branch_provided_skips_branch_prompt(self) -> None:
        """When branch is pre-filled, only title and worktree are prompted."""
        prompter = InteractivePrompter()
        calls: list[str] = []

        def fake_text(prompt, **kwargs):
            calls.append(prompt)
            if "title" in prompt.lower():
                return self._mock_ask("My PR title")
            return self._mock_ask("/path/to/worktree")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm",
                side_effect=fake_confirm,
            ),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "below", branch="my-branch"
            )

        assert inputs.branch == "my-branch"
        assert inputs.title == "My PR title"
        assert inputs.worktree == "/path/to/worktree"
        assert "Branch name:" not in calls
        assert "PR title:" in calls
        assert "Worktree path:" in calls

    def test_title_provided_skips_title_prompt(self) -> None:
        """When title is pre-filled, only branch and worktree are prompted."""
        prompter = InteractivePrompter()
        calls: list[str] = []

        def fake_text(prompt, **kwargs):
            calls.append(prompt)
            if "branch" in prompt.lower():
                return self._mock_ask("my-branch")
            if "worktree" in prompt.lower():
                return self._mock_ask("/path/to/worktree")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm",
                side_effect=fake_confirm,
            ),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "below", title="My Title"
            )

        assert inputs.branch == "my-branch"
        assert inputs.title == "My Title"
        assert inputs.worktree == "/path/to/worktree"
        assert "Branch name:" in calls
        assert "PR title:" not in calls
        assert "Worktree path:" in calls

    def test_worktree_provided_skips_worktree_prompt(self) -> None:
        """When worktree is pre-filled, only branch and title are prompted."""
        prompter = InteractivePrompter()
        calls: list[str] = []

        def fake_text(prompt, **kwargs):
            calls.append(prompt)
            if "branch" in prompt.lower():
                return self._mock_ask("my-branch")
            if "title" in prompt.lower():
                return self._mock_ask("My Title")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm",
                side_effect=fake_confirm,
            ),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "above", worktree="/my/worktree"
            )

        assert inputs.branch == "my-branch"
        assert inputs.title == "My Title"
        assert inputs.worktree == "/my/worktree"
        assert "Branch name:" in calls
        assert "PR title:" in calls
        assert "Worktree path:" not in calls

    def test_branch_and_title_provided_only_prompts_worktree(self) -> None:
        """When branch and title are pre-filled, only worktree is prompted."""
        prompter = InteractivePrompter()
        calls: list[str] = []

        def fake_text(prompt, **kwargs):
            calls.append(prompt)
            if "worktree" in prompt.lower():
                return self._mock_ask("/path/to/wt")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm",
                side_effect=fake_confirm,
            ),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "below", branch="feat", title="Feature"
            )

        assert inputs.branch == "feat"
        assert inputs.title == "Feature"
        assert inputs.worktree == "/path/to/wt"
        assert "Branch name:" not in calls
        assert "PR title:" not in calls
        assert "Worktree path:" in calls

    def test_branch_and_worktree_provided_only_prompts_title(self) -> None:
        """When branch and worktree are pre-filled, only title is prompted."""
        prompter = InteractivePrompter()
        calls: list[str] = []

        def fake_text(prompt, **kwargs):
            calls.append(prompt)
            if "title" in prompt.lower():
                return self._mock_ask("My Title")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm",
                side_effect=fake_confirm,
            ),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "above", branch="feat", worktree="/wt"
            )

        assert inputs.branch == "feat"
        assert inputs.title == "My Title"
        assert inputs.worktree == "/wt"
        assert "Branch name:" not in calls
        assert "PR title:" in calls
        assert "Worktree path:" not in calls

    def test_no_prefilled_values_prompts_all(self) -> None:
        """When no values are pre-filled, all three are prompted."""
        prompter = InteractivePrompter()
        calls: list[str] = []

        def fake_text(prompt, **kwargs):
            calls.append(prompt)
            if "branch" in prompt.lower():
                return self._mock_ask("my-branch")
            if "title" in prompt.lower():
                return self._mock_ask("My Title")
            if "worktree" in prompt.lower():
                return self._mock_ask("/wt/path")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm",
                side_effect=fake_confirm,
            ),
        ):
            inputs = prompter.prompt_below_above_inputs("below")

        assert inputs.branch == "my-branch"
        assert inputs.title == "My Title"
        assert inputs.worktree == "/wt/path"
        assert "Branch name:" in calls
        assert "PR title:" in calls
        assert "Worktree path:" in calls


class TestDraftPrompt:
    """Tests for draft PR prompt in interactive mode."""

    def _mock_ask(self, return_value):
        class MockQuestion:
            def ask(self):
                return return_value

        return MockQuestion()

    def test_draft_prompt_is_asked_with_default_true(self) -> None:
        """Interactive mode asks 'Create as draft PR?' default yes."""
        prompter = InteractivePrompter()
        confirm_calls: list[tuple[str, bool | None]] = []

        def fake_text(prompt: str, **kwargs) -> object:
            if "branch" in prompt.lower():
                return self._mock_ask("my-branch")
            if "title" in prompt.lower():
                return self._mock_ask("Title")
            if "worktree" in prompt.lower():
                return self._mock_ask("../wt")
            return self._mock_ask("")

        def fake_confirm(prompt: str, **kwargs) -> object:
            default: bool | None = kwargs.get("default", None)
            confirm_calls.append((prompt, default))
            return self._mock_ask(True)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm", side_effect=fake_confirm
            ),
        ):
            inputs = prompter.prompt_below_above_inputs("below")

        # Draft prompt should be asked with default=True
        draft_calls = [
            (p, d)
            for p, d in confirm_calls
            if "draft" in p.lower()
        ]
        assert len(draft_calls) == 1
        assert draft_calls[0][1] is True
        assert inputs.draft is True

    def test_draft_false_when_user_declines(self) -> None:
        """Draft is False when user declines the prompt."""
        prompter = InteractivePrompter()

        def fake_text(prompt, **kwargs):
            if "branch" in prompt.lower():
                return self._mock_ask("my-branch")
            if "title" in prompt.lower():
                return self._mock_ask("Title")
            if "worktree" in prompt.lower():
                return self._mock_ask("../wt")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            if "draft" in prompt.lower():
                return self._mock_ask(False)
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(
                f"{_MOD}.confirm", side_effect=fake_confirm
            ),
        ):
            inputs = prompter.prompt_below_above_inputs("below")

        assert inputs.draft is False


class TestWorktreeDefaultFromBranch:
    """Tests that worktree prompt shows default path from branch."""

    def _mock_ask(self, return_value):
        class MockQuestion:
            def ask(self):
                return return_value

        return MockQuestion()

    def test_worktree_default_from_prefilled_branch(self) -> None:
        """Worktree prompt shows ../branch as default when branch
        is pre-filled."""
        prompter = InteractivePrompter()
        defaults: dict[str, str] = {}

        def fake_text(prompt, **kwargs):
            if "default" in kwargs:
                defaults[prompt] = kwargs["default"]
            if "title" in prompt.lower():
                return self._mock_ask("Title")
            if "worktree" in prompt.lower():
                return self._mock_ask(kwargs.get("default", ""))
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(f"{_MOD}.confirm", side_effect=fake_confirm),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "below", branch="my-feature"
            )

        assert defaults["Worktree path:"] == "../my-feature"
        assert inputs.worktree == "../my-feature"

    def test_worktree_default_from_prompted_branch(self) -> None:
        """Worktree prompt shows ../branch as default when branch
        was entered interactively."""
        prompter = InteractivePrompter()
        defaults: dict[str, str] = {}

        def fake_text(prompt, **kwargs):
            if "default" in kwargs:
                defaults[prompt] = kwargs["default"]
            if "branch" in prompt.lower():
                return self._mock_ask("new-feat")
            if "title" in prompt.lower():
                return self._mock_ask("Title")
            if "worktree" in prompt.lower():
                return self._mock_ask(kwargs.get("default", ""))
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(f"{_MOD}.confirm", side_effect=fake_confirm),
        ):
            inputs = prompter.prompt_below_above_inputs("above")

        assert defaults["Worktree path:"] == "../new-feat"
        assert inputs.worktree == "../new-feat"

    def test_worktree_default_can_be_overridden(self) -> None:
        """User can type a custom path instead of accepting default."""
        prompter = InteractivePrompter()

        def fake_text(prompt, **kwargs):
            if "title" in prompt.lower():
                return self._mock_ask("Title")
            if "worktree" in prompt.lower():
                return self._mock_ask("/custom/path")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(f"{_MOD}.confirm", side_effect=fake_confirm),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "below", branch="my-feat"
            )

        assert inputs.worktree == "/custom/path"

    def test_prefilled_worktree_skips_default(self) -> None:
        """When worktree is pre-filled, no default is computed."""
        prompter = InteractivePrompter()
        defaults: dict[str, str] = {}

        def fake_text(prompt, **kwargs):
            if "default" in kwargs:
                defaults[prompt] = kwargs["default"]
            if "title" in prompt.lower():
                return self._mock_ask("Title")
            return self._mock_ask("")

        def fake_confirm(prompt, **kwargs):
            return self._mock_ask(False)

        with (
            patch(f"{_MOD}.text", side_effect=fake_text),
            patch(f"{_MOD}.confirm", side_effect=fake_confirm),
        ):
            inputs = prompter.prompt_below_above_inputs(
                "below",
                branch="feat",
                worktree="/explicit/path",
            )

        assert "Worktree path:" not in defaults
        assert inputs.worktree == "/explicit/path"
