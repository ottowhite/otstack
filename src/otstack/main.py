import argparse
from pathlib import Path

from otstack.AboveDryRunResult import AboveDryRunResult
from otstack.BelowDryRunResult import BelowDryRunResult
from otstack.InteractivePrompter import InteractivePrompter
from otstack.OtStackClient import OtStackClient
from otstack.Repository import Repository


def _get_repo(
    client: OtStackClient, repo_arg: str | None, local_path: str
) -> Repository:
    """Get repository from argument or detect from git remote."""
    if repo_arg is not None:
        return client.get_repo(repo_arg, local_path)

    detected_repo = client.detect_repo(local_path)
    if detected_repo is None:
        print(
            "Could not detect repository. Please specify --repo or run "
            "from within a git repository with a GitHub remote."
        )
        raise SystemExit(-1)
    print(f"Detected repository: {detected_repo.full_name}")
    return detected_repo


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ots", description="OtStack - PR dependency management"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    tree_parser = subparsers.add_parser("tree", help="Show PR dependency tree")
    tree_parser.add_argument(
        "--repo",
        type=str,
        required=False,
        help="Repository name. If not provided, detects from git remote.",
    )
    tree_parser.add_argument(
        "--path",
        type=str,
        required=False,
        help="Path to local git repository. If not provided, uses current directory.",
    )

    sync_parser = subparsers.add_parser("sync", help="Sync all local PRs")
    sync_parser.add_argument(
        "--repo",
        type=str,
        required=False,
        help="Repository name. If not provided, detects from git remote.",
    )
    sync_parser.add_argument(
        "--path",
        type=str,
        required=False,
        help="Path to local git repository. If not provided, uses current directory.",
    )

    below_parser = subparsers.add_parser(
        "below", help="Insert a new PR below the current PR in the stack"
    )
    below_parser.add_argument(
        "--branch",
        "-b",
        type=str,
        required=False,
        help="Name for the new branch to create",
    )
    below_parser.add_argument(
        "--title",
        "-t",
        type=str,
        required=False,
        help="Title for the new PR",
    )
    below_parser.add_argument(
        "--worktree",
        "-w",
        type=str,
        required=False,
        help="Path where the new worktree will be created",
    )
    below_parser.add_argument(
        "--repo",
        "-r",
        type=str,
        required=False,
        help="Repository name (owner/repo). Auto-detected from git remote if omitted.",
    )
    below_parser.add_argument(
        "--path",
        "-p",
        type=str,
        required=False,
        help="Path to local git repository. Defaults to current directory.",
    )
    below_parser.add_argument(
        "--direnv",
        action="store_true",
        help="Run 'direnv allow' in the new worktree after creation",
    )
    below_parser.add_argument(
        "--copy",
        "-c",
        action="append",
        dest="copy_files",
        help="Copy a file from current to new worktree (can be repeated)",
    )
    below_parser.add_argument(
        "--draft",
        "-d",
        action="store_true",
        help="Create the new PR as a draft",
    )
    below_parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would happen without making any changes",
    )

    above_parser = subparsers.add_parser(
        "above", help="Insert a new PR above the current PR in the stack"
    )
    above_parser.add_argument(
        "--branch",
        "-b",
        type=str,
        required=False,
        help="Name for the new branch to create",
    )
    above_parser.add_argument(
        "--title",
        "-t",
        type=str,
        required=False,
        help="Title for the new PR",
    )
    above_parser.add_argument(
        "--worktree",
        "-w",
        type=str,
        required=False,
        help="Path where the new worktree will be created",
    )
    above_parser.add_argument(
        "--repo",
        "-r",
        type=str,
        required=False,
        help="Repository name (owner/repo). Auto-detected from git remote if omitted.",
    )
    above_parser.add_argument(
        "--path",
        "-p",
        type=str,
        required=False,
        help="Path to local git repository. Defaults to current directory.",
    )
    above_parser.add_argument(
        "--direnv",
        action="store_true",
        help="Run 'direnv allow' in the new worktree after creation",
    )
    above_parser.add_argument(
        "--copy",
        "-c",
        action="append",
        dest="copy_files",
        help=(
            "Copy a file from current worktree to new worktree "
            "(can be specified multiple times)"
        ),
    )
    above_parser.add_argument(
        "--draft",
        "-d",
        action="store_true",
        help="Create the new PR as a draft",
    )
    above_parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would happen without making any changes",
    )

    args = parser.parse_args()

    # Handle interactive prompts for below/above when required args are missing
    if args.command in ("below", "above"):
        # Auto-default worktree path from branch name
        if args.worktree is None and args.branch is not None:
            local_path = args.path or "."
            args.worktree = str(
                Path(local_path).resolve().parent / args.branch
            )

        if not all([args.branch, args.title, args.worktree]):
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
            repo = _get_repo(client, args.repo, local_path)

            if args.command == "tree":
                print(f"Repository: {repo.full_name}\n")
                client.tree(repo)
            elif args.command == "sync":
                print(f"Syncing repository: {repo.full_name}\n")
                if client.sync(repo):
                    print("All PRs synced successfully!")
                else:
                    exit(1)
            elif args.command == "below":
                result = client.below(
                    repo=repo,
                    new_branch_name=args.branch,
                    pr_title=args.title,
                    worktree_path=args.worktree,
                    copy_files=args.copy_files,
                    run_direnv=args.direnv,
                    dry_run=args.dry_run,
                    draft=args.draft,
                )
                if isinstance(result, BelowDryRunResult):
                    print(result.format_output())
                else:
                    print(
                        f"\nSuccessfully inserted '{args.branch}' "
                        "below your current PR!"
                    )
                    print(f"\nNew PR: {result.new_pr.url}")
                    print(f"Original PR (retargeted): {result.original_pr.url}")
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
                )
                if isinstance(result, AboveDryRunResult):
                    print(result.format_output())
                else:
                    print(
                        f"\nSuccessfully inserted '{args.branch}' "
                        "above your current PR!"
                    )
                    print(f"\nNew PR: {result.new_pr.url}")
                    print(f"Current PR: {result.current_pr.url}")
                    print(f"Worktree: {result.worktree_path}")
    except ValueError as e:
        print(e)
        exit(-1)


if __name__ == "__main__":
    main()
