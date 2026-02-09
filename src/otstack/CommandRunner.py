from typing import Protocol


class CommandRunner(Protocol):
    """Protocol for running shell commands."""

    def run(self, command: list[str], cwd: str | None = None) -> None:
        """
        Run a command.

        Args:
            command: Command and arguments as a list.
            cwd: Working directory to run the command in.

        Raises:
            FileNotFoundError: If the command is not found.
        """
        ...
