# OtStack Development Guide

- Always keep this CLAUDE.md and README.md up to date as you make changes
- Perform atomic git commits with standard git tags and descriptions as you work, and always push directly after committing

## Project Overview

OtStack (`ots`) is a CLI tool for managing stacked pull requests on GitHub. It helps developers work with chains of dependent PRs by providing commands to visualize PR trees, sync branches, and insert new PRs into existing stacks.

## Architecture

### File Organization
- Each class should be in its own file named exactly the same as the class (e.g., `OtStackClient` class in `OtStackClient.py`)
- Use Protocol classes for interfaces that need to be mocked in tests
- Concrete implementations should be prefixed with the library/implementation name (e.g., `PyGitHubClient` for PyGithub implementation)
- Never maintain `__init__.py` exports or `__all__` lists - this is an internal project and we are the only consumers, so we don't care about breaking compatibility

### Protocols and Interfaces
- We use Protocols extensively to completely mock out external interactions (like GitHub) for testing, and to define exact interfaces without coupling to implementation details
- Define Protocol classes for abstractions that will have multiple implementations or need to be mocked
- Protocol methods should have `...` as the body
- For data-holding protocols intended for dataclass implementations, use attribute annotations (e.g., `name: str`) rather than `@property` decorators
- Concrete implementations can use dataclasses for simple data-holding classes that implement protocols
- All protocol implementations should explicitly inherit from the protocol definition for clarity (e.g., `class PyGitHubClient(GitHubClient):`)

### Key Classes
- `OtStackClient` - Main orchestration client, coordinates all operations
- `GitHubClient` (Protocol) / `PyGitHubClient` - GitHub API interactions
- `Repository` (Protocol) / `PyGitHubRepository` - Git repository operations
- `PullRequest` (Protocol) / `PyGitHubPullRequest` - PR data and operations
- `Branch` (Protocol) / `LocalBranch`, `SimpleBranch` - Branch abstractions
- `GitRepoDetector` - Detects repository from git remotes
- `CommandRunner` (Protocol) / `SubprocessCommandRunner` - Shell command execution
- `InteractivePrompter` - Handles interactive prompts for CLI commands using questionary

### Type Checking
- Never use `if TYPE_CHECKING:` guards - we always type check, so these are unnecessary indirection

### Git Worktree Support
- All commands work correctly from within git worktrees
- When opening a git repo, use `Repo(path)` which correctly detects worktree context
- The `get_current_branch()` method returns the worktree's checked-out branch, not the main repo's branch
- PyGitHubRepository implements all Repository protocol methods for worktree compatibility

## Commands

### tree
Show PR dependency tree for a repository. Visualizes which PRs depend on other PRs.

**Usage:** `ots tree [--repo owner/repo] [--path /path/to/repo]`

### sync
Sync all local PRs by pulling the destination branch and merging into the source branch.

**Usage:** `ots sync [--repo owner/repo] [--path /path/to/repo]`

### below
Insert a new PR "below" the current PR in a stack. Creates a new branch and PR that becomes the new base for the current PR, with a git worktree for parallel development.

**Usage:** `ots below [--branch <name>] [--title <title>] [--worktree <path>] [options]`

**Interactive mode:** If any required arguments are omitted, the command enters interactive mode and prompts for all inputs (including optional ones like direnv and copy files).

**Arguments (prompted interactively if missing):**
- `--branch, -b` - Name for the new branch
- `--title, -t` - Title for the new PR
- `--worktree, -w` - Path where the new worktree will be created

**Optional arguments:**
- `--repo, -r` - Repository name (owner/repo), auto-detected if omitted
- `--path, -p` - Path to local git repository (defaults to `.`)
- `--draft, -d` - Create the new PR as a draft
- `--no-verify` - Skip pre-commit hooks on the initialization commit
- `--create-pr` - Create a PR for the current branch if one doesn't exist (uses branch name as title, targets default branch)
- `--direnv` - Run `direnv allow` in new worktree after creation
- `--copy, -c` - Copy file from current worktree to new (repeatable)
- `--dry-run, -n` - Show what would happen without making any changes

**No PR behavior:**
When on the default branch with no open PR, below/above skip the initial PR creation entirely and just create the new branch + PR targeting the default branch directly. No `--create-pr` flag is needed (it is silently accepted). When on a non-default branch with no open PR, below/above will error with a message suggesting `--create-pr`. In interactive mode on a non-default branch, the user is prompted to create one. With `--create-pr`, a PR is automatically created using the humanized branch name as title and the repo's default branch as destination.

**Dry run behavior:**
When `--dry-run` is passed, the command performs all validation checks (which are read-only and safe) and then prints what would happen instead of executing. The output includes:
- Current state (branch and PR info)
- Numbered list of actions that would be performed (create branch, worktree, push, create PR, retarget, copy files, run direnv)

### above
Insert a new PR "above" the current PR in a stack. Creates a new branch from the current branch and a PR targeting the current branch, with a git worktree for parallel development.

**Usage:** `ots above [--branch <name>] [--title <title>] [--worktree <path>] [options]`

**Interactive mode:** If any required arguments are omitted, the command enters interactive mode and prompts for all inputs (including optional ones like direnv and copy files).

**Arguments (prompted interactively if missing):**
- `--branch, -b` - Name for the new branch
- `--title, -t` - Title for the new PR
- `--worktree, -w` - Path where the new worktree will be created

**Optional arguments:**
- `--repo, -r` - Repository name (owner/repo), auto-detected if omitted
- `--path, -p` - Path to local git repository (defaults to `.`)
- `--draft, -d` - Create the new PR as a draft
- `--no-verify` - Skip pre-commit hooks on the initialization commit
- `--create-pr` - Create a PR for the current branch if one doesn't exist (uses branch name as title, targets default branch)
- `--direnv` - Run `direnv allow` in new worktree after creation
- `--copy, -c` - Copy file from current worktree to new (repeatable)
- `--dry-run, -n` - Show what would happen without making any changes

**Key difference from `below`:** The `above` command creates a branch from the current branch and the new PR targets the current branch. No PR retargeting is needed - the new PR simply becomes a child of the current PR in the stack.

**Dry run behavior:**
When `--dry-run` is passed, the command performs all validation checks and then prints what would happen:
- Current state (branch and PR info)
- Numbered list of actions (create branch, worktree, push, create PR, copy files, run direnv)

## Nix Flake

The project provides a Nix flake for installation via URL from other flakes.

**Supported systems:** `x86_64-linux`, `x86_64-darwin`, `aarch64-darwin`

**Usage from another flake:**
```nix
{
  inputs.otstack.url = "github:ottowhite/otstack";
  # Then use: inputs.otstack.packages.${system}.default
}
```

**Local commands:**
- `nix build .#` - Build the package
- `nix run .# -- <command>` - Run ots directly

**Remote usage:**
- `nix run github:ottowhite/otstack -- <command>` - Run from remote without cloning

**CLI binary:** The installed binary is named `ots`. It auto-detects the repository from the current directory's git remote.

## Development

**Setup:**
```bash
nix-shell  # Enter development environment
```

**Run tests:**
```bash
make test      # or: uv run pytest
```

**Lint and type check:**
```bash
make check     # runs both lint and typecheck
make lint      # ruff only
make typecheck # ty only
```

**Run locally during development:**
```bash
uv run ots tree
```
