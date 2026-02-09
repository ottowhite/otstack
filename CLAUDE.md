- Always keep this CLAUDE.md up to date as you make changes
- Perform atomic git commits with standard git tags and descriptions as you work, and always push directly after committing

## Coding Practices

### File Organization
- Each class should be in its own file named exactly the same as the class (e.g., `OtStackClient` class in `OtStackClient.py`)
- Use Protocol classes for interfaces that need to be mocked in tests
- Concrete implementations should be prefixed with the library/implementation name (e.g., `PyGitHubClient` for PyGithub implementation)
- Never maintain `__init__.py` exports or `__all__` lists - this is an internal project and we are the only consumers, so we don't care about breaking compatibility. Less to keep in sync is better.

### Protocols and Interfaces
- We use Protocols extensively to completely mock out external interactions (like GitHub) for testing, and to define exact interfaces without coupling to implementation details
- Define Protocol classes for abstractions that will have multiple implementations or need to be mocked
- Protocol methods should have `...` as the body
- For data-holding protocols intended for dataclass implementations, use attribute annotations (e.g., `name: str`) rather than `@property` decorators
- Concrete implementations can use dataclasses for simple data-holding classes that implement protocols
- All protocol implementations should explicitly inherit from the protocol definition for clarity (e.g., `class PyGitHubClient(GitHubClient):`)

### Type Checking
- Never use `if TYPE_CHECKING:` guards - we always type check, so these are unnecessary indirection

### Git Worktree Support
- All commands work correctly from within git worktrees
- When opening a git repo, use `Repo(path)` which correctly detects worktree context
- The `get_current_branch()` method returns the worktree's checked-out branch, not the main repo's branch
- PyGitHubRepository implements all Repository protocol methods for worktree compatibility

## Commands

### below
Insert a new PR "below" the current PR in a stack. Creates a new branch and PR that becomes the new base for the current PR, with a git worktree for parallel development.

**Usage:** `otstack below --branch <name> --title <title> --worktree <path> [options]`

**Required arguments:**
- `--branch, -b` - Name for the new branch
- `--title, -t` - Title for the new PR
- `--worktree, -w` - Path where the new worktree will be created

**Optional arguments:**
- `--repo, -r` - Repository name (owner/repo), auto-detected if omitted
- `--path, -p` - Path to local git repository (defaults to `.`)
- `--direnv` - Run `direnv allow` in new worktree after creation
- `--copy, -c` - Copy file from current worktree to new (repeatable)
- `--dry-run, -n` - Show what would happen without making any changes

**Dry run behavior:**
When `--dry-run` is passed, the command performs all validation checks (which are read-only and safe) and then prints what would happen instead of executing. The output includes:
- Current state (branch and PR info)
- Numbered list of actions that would be performed (create branch, worktree, push, create PR, retarget, copy files, run direnv)

### tree
Show PR dependency tree for a repository.

### sync
Sync all local PRs by pulling destination and merging into source.
