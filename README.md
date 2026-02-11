# OtStack

A CLI tool for managing stacked pull requests on GitHub.

## What is OtStack?

OtStack helps you work with **stacked PRs** - chains of dependent pull requests where each PR builds on the previous one. Instead of having one massive PR, you can break your work into smaller, reviewable chunks while maintaining the dependency chain.

## Installation

### Via Nix Flake (Recommended)

Add to your flake inputs:

```nix
{
  inputs.otstack.url = "github:ottowhite/otstack";
}
```

Then add `inputs.otstack.packages.${system}.default` to your packages.

### Run without installing

```bash
nix run github:ottowhite/otstack -- --help
```

## Configuration

OtStack requires a GitHub Personal Access Token with `repo` scope.

Set the `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
```

Or create a `~/.env` file (if your shell sources it):

```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
```

## Usage

The CLI binary is called `ots`. It auto-detects the repository from the current directory's git remote.

### View PR Tree

Visualize the dependency tree of all open PRs:

```bash
cd your-repo
ots tree
```

### Sync PRs

Sync all local PRs by merging their destination branches into their source branches:

```bash
ots sync
```

### Insert PR Below Current

Create a new PR that becomes the base of your current PR. This is useful when you realize your current PR needs some preparatory work that should be reviewed separately.

```bash
ots below -b prep-work -t "Preparatory refactoring" -w ../prep-work-worktree
```

This will:
1. Create a new branch `prep-work` from your current PR's base
2. Create a git worktree at `../prep-work-worktree`
3. Push and create a new PR
4. Retarget your current PR to point to the new branch

#### Options

```
-b, --branch     Name for the new branch (required)
-t, --title      Title for the new PR (required)
-w, --worktree   Path for the new git worktree (required)
-r, --repo       Repository (owner/repo), auto-detected if omitted
-p, --path       Path to local git repo, defaults to current directory
    --direnv     Run 'direnv allow' in new worktree
-c, --copy       Copy a file to new worktree (can repeat)
-n, --dry-run    Show what would happen without making changes
```

#### Example with all options

```bash
ots below \
  -b feature-prep \
  -t "Add utility functions for feature X" \
  -w ../feature-prep \
  --direnv \
  -c .env \
  -c config.local.json \
  --dry-run
```

### Insert PR Above Current

Create a new PR that depends on your current PR. This is useful when you want to start work that builds on your current PR before it's merged.

```bash
ots above -b next-feature -t "Build on current work" -w ../next-feature-worktree
```

This will:
1. Create a new branch `next-feature` from your current branch
2. Create a git worktree at `../next-feature-worktree`
3. Push and create a new PR targeting your current branch

The new PR becomes a child of your current PR in the stack - when your current PR merges, the new PR will automatically retarget to your current PR's base.

#### Options

Same options as `below`:

```
-b, --branch     Name for the new branch (required)
-t, --title      Title for the new PR (required)
-w, --worktree   Path for the new git worktree (required)
-r, --repo       Repository (owner/repo), auto-detected if omitted
-p, --path       Path to local git repo, defaults to current directory
    --direnv     Run 'direnv allow' in new worktree
-c, --copy       Copy a file to new worktree (can repeat)
-n, --dry-run    Show what would happen without making changes
```

## Specifying Repository

By default, `ots` detects the repository from the git remote of your current directory. You can override this:

```bash
# Specify repo explicitly
ots tree --repo owner/repo-name

# Specify a different local path
ots tree --path /path/to/repo
```

## License

MIT
