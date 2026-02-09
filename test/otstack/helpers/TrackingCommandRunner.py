from dataclasses import dataclass, field

from otstack.CommandRunner import CommandRunner


@dataclass
class TrackingCommandRunner(CommandRunner):
    """A command runner that tracks all commands run for testing."""

    commands: list[tuple[list[str], str | None]] = field(default_factory=list)
    raise_file_not_found_for: list[str] | None = field(default=None)

    def run(self, command: list[str], cwd: str | None = None) -> None:
        """Run a command and track it."""
        if self.raise_file_not_found_for and command[0] in self.raise_file_not_found_for:
            raise FileNotFoundError(f"Command not found: {command[0]}")
        self.commands.append((command, cwd))
