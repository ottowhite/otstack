import subprocess

from .CommandRunner import CommandRunner


class SubprocessCommandRunner(CommandRunner):
    """Default command runner using subprocess."""

    def run(self, command: list[str], cwd: str | None = None) -> None:
        """
        Run a command using subprocess.

        Args:
            command: Command and arguments as a list.
            cwd: Working directory to run the command in.

        Raises:
            FileNotFoundError: If the command is not found.
        """
        subprocess.run(command, cwd=cwd, check=True)
