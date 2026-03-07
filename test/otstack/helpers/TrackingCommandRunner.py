import subprocess
from dataclasses import dataclass, field

from otstack.CommandRunner import CommandRunner


@dataclass
class TrackingCommandRunner(CommandRunner):
    """A command runner that tracks all commands run for testing."""

    commands: list[tuple[list[str], str | None]] = field(default_factory=list)
    raise_file_not_found_for: list[str] | None = field(default=None)
    raise_called_process_error_for: list[str] | None = field(
        default=None
    )

    def run(self, command: list[str], cwd: str | None = None) -> None:
        """Run a command and track it."""
        cmds_to_raise_for = self.raise_file_not_found_for
        if cmds_to_raise_for and command[0] in cmds_to_raise_for:
            raise FileNotFoundError(f"Command not found: {command[0]}")
        cmds_to_error = self.raise_called_process_error_for
        if cmds_to_error and any(c in command for c in cmds_to_error):
            raise subprocess.CalledProcessError(
                returncode=1, cmd=command
            )
        self.commands.append((command, cwd))
