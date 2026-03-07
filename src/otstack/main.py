import argparse
from pathlib import Path

from otstack.AboveDryRunResult import AboveDryRunResult
from otstack.BelowDryRunResult import BelowDryRunResult
from otstack.InteractivePrompter import InteractivePrompter
from otstack.OtStackClient import OtStackClient
from otstack.Repository import Repository


def _get_repo(
    client: OtStackClient,
    repo_arg: str | None,
    local_path: str,
) -> Repository:
    """Get repository from argument or detect from git remote."""
    if repo_arg is not None:
        return client.get_repo(repo_arg, local_path)

    detected_repo = client.detect_repo(local_path)
    if detected_repo is None:
        print(
            "Could not detect repository."
            " Please specify --repo or run"
            " from within a git repository"
            " with a GitHub remote."
        )
        raise SystemExit(-1)
    print(f"Detected repository: {detected_repo.full_name}")
    return detected_repo


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ots",
        description="OtStack - PR dependency management",
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True
    )

    tree_parser = subparsers.add_parser(
        "tree", help="Show PR dependency tree"
    )
    tree_parser.add_argument(
        "--repo",
        type=str,
        required=False,
        help=(
            "Repository name. If not provided,"
            " detects from git remote."
        ),
    )
    tree_parser.add_argument(
        "--path",
        type=str,
        required=False,
        help=(
            "Path to local git repository."
            " If not provided, uses current directory."
        ),
    )

    sync_parser = subparsers.add_parser(
        "sync", help="Sync all local PRs"
    )
    sync_parser.add_argument(
        "--repo",
        type=str,
        required=False,
        help=(
            "Repository name. If not provided,"
            " detects from git remote."
        ),
    )
    sync_parser.add_argument(
        "--path",
        type=str,
        required=False,
        help=(
            "Path to local git repository."
            " If not provided, uses current directory."
        ),
    )

    below_parser = subparsers.add_parser(
        "below",
        help="Insert a new PR below the current PR"
        " in the stack",
    )
    _add_below_above_args(below_parser)

    above_parser = subparsers.add_parser(
        "above",
        help="Insert a new PR above the current PR"
        " in the stack",
    )
    _add_below_above_args(above_parser)

    args = parser.parse_args()

    # Handle interactive prompts for below/above
    is_interactive = False
    if args.command in ("below", "above"):
        # Auto-default worktree path from branch name
        if (
            args.worktree is None
            and args.branch is not None
        ):
            local_path = args.path or "."
            args.worktree = str(
                Path(local_path).resolve().parent
                / args.branch
            )

        if not all([args.branch, args.title, args.worktree]):
            is_interactive = True
            prompter = InteractivePrompter()
            inputs = prompter.prompt_below_above_inputs(
                args.command,
                branch=args.branch,
                title=args.title,
                worktree=args.worktree,
            )
            args.branch = inputs.branch
            args.title = inputs.title
            args.worktree = inputs.worktree
            args.direnv = inputs.direnv
            args.copy_files = inputs.copy_files
            args.dry_run = inputs.dry_run
            args.draft = inputs.draft

    try:
        local_path = getattr(args, "path", None) or "."
        with OtStackClient() as client:
            repo = _get_repo(
                client, args.repo, local_path
            )

            if args.command == "tree":
                print(f"Repository: {repo.full_name}\n")
                client.tree(repo)
            elif args.command == "sync":
                print(
                    "Syncing repository:"
                    f" {repo.full_name}\n"
                )
                if client.sync(repo):
                    print("All PRs synced successfully!")
                else:
                    exit(1)
            elif args.command in ("below", "above"):
                _handle_below_above(
                    client,
                    repo,
                    args,
                    is_interactive,
                )
    except ValueError as e:
        print(e)
        exit(-1)


def _add_below_above_args(
    parser: argparse.ArgumentParser,
) -> None:
    """Add common args for below and above commands."""
    parser.add_argument(
        "--branch",
        "-b",
        type=str,
        required=False,
        help="Name for the new branch to create",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        required=False,
        help="Title for the new PR",
    )
    parser.add_argument(
        "--worktree",
        "-w",
        type=str,
        required=False,
        help=(
            "Path where the new worktree"
            " will be created"
        ),
    )
    parser.add_argument(
        "--repo",
        "-r",
        type=str,
        required=False,
        help=(
            "Repository name (owner/repo)."
            " Auto-detected from git remote"
            " if omitted."
        ),
    )
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        required=False,
        help=(
            "Path to local git repository."
            " Defaults to current directory."
        ),
    )
    parser.add_argument(
        "--direnv",
        action="store_true",
        help=(
            "Run 'direnv allow' in the new"
            " worktree after creation"
        ),
    )
    parser.add_argument(
        "--copy",
        "-c",
        action="append",
        dest="copy_files",
        help=(
            "Copy a file from current to new"
            " worktree (can be repeated)"
        ),
    )
    parser.add_argument(
        "--draft",
        "-d",
        action="store_true",
        help="Create the new PR as a draft",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help=(
            "Skip pre-commit hooks on the"
            " initialization commit"
        ),
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help=(
            "Create a PR for the current branch"
            " if one doesn't exist"
        ),
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help=(
            "Show what would happen without"
            " making any changes"
        ),
    )


def _handle_below_above(
    client: OtStackClient,
    repo: Repository,
    args: argparse.Namespace,
    is_interactive: bool,
) -> None:
    """Handle below and above commands."""
    create_pr = getattr(args, "create_pr", False)

    # In interactive mode, check if PR exists and prompt
    # (skip on default branch — no PR needed there)
    if is_interactive and not create_pr:
        cur = repo.get_current_branch()
        if cur is not None:
            default_branch = repo.get_default_branch()
            is_default = cur.name == default_branch
            if not is_default:
                prs = repo.get_open_pull_requests()
                has_pr = any(
                    pr.source_branch.name == cur.name
                    for pr in prs
                )
                if not has_pr:
                    import questionary

                    answer = questionary.confirm(
                        "No PR found for branch"
                        f" '{cur.name}'."
                        " Create one now?",
                        default=True,
                    ).ask()
                    if answer is None:
                        raise KeyboardInterrupt()
                    if answer:
                        create_pr = True
                    else:
                        print(
                            "No open PR for"
                            f" '{cur.name}'."
                            " Aborting."
                        )
                        raise SystemExit(-1)

    if args.command == "below":
        result = client.below(
            repo=repo,
            new_branch_name=args.branch,
            pr_title=args.title,
            worktree_path=args.worktree,
            copy_files=args.copy_files,
            run_direnv=args.direnv,
            dry_run=args.dry_run,
            draft=args.draft,
            no_verify=args.no_verify,
            create_pr=create_pr,
        )
        if isinstance(result, BelowDryRunResult):
            print(result.format_output())
        else:
            print(
                f"\nSuccessfully inserted"
                f" '{args.branch}'"
                " below your current PR!"
            )
            print(f"\nNew PR: {result.new_pr.url}")
            if result.original_pr is not None:
                print(
                    "Original PR (retargeted):"
                    f" {result.original_pr.url}"
                )
            print(f"Worktree: {result.worktree_path}")
    elif args.command == "above":
        result = client.above(
            repo=repo,
            new_branch_name=args.branch,
            pr_title=args.title,
            worktree_path=args.worktree,
            copy_files=args.copy_files,
            run_direnv=args.direnv,
            dry_run=args.dry_run,
            draft=args.draft,
            no_verify=args.no_verify,
            create_pr=create_pr,
        )
        if isinstance(result, AboveDryRunResult):
            print(result.format_output())
        else:
            print(
                f"\nSuccessfully inserted"
                f" '{args.branch}'"
                " above your current PR!"
            )
            print(f"\nNew PR: {result.new_pr.url}")
            if result.current_pr is not None:
                print(
                    "Current PR:"
                    f" {result.current_pr.url}"
                )
            print(f"Worktree: {result.worktree_path}")


if __name__ == "__main__":
    main()
