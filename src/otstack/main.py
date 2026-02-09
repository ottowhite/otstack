import argparse

from otstack.BelowDryRunResult import BelowDryRunResult
from otstack.OtStackClient import OtStackClient


def main() -> None:
    parser = argparse.ArgumentParser(description="OtStack - PR dependency management")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tree_parser = subparsers.add_parser("tree", help="Show PR dependency tree")
    tree_parser.add_argument(
        "--repo",
        type=str,
        required=False,
        help="Repository name (e.g., 'repo-name'). If not provided, detects from git remote.",
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
        help="Repository name (e.g., 'repo-name'). If not provided, detects from git remote.",
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
        required=True,
        help="Name for the new branch to create",
    )
    below_parser.add_argument(
        "--title",
        "-t",
        type=str,
        required=True,
        help="Title for the new PR",
    )
    below_parser.add_argument(
        "--worktree",
        "-w",
        type=str,
        required=True,
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
        help="Copy a file from current worktree to new worktree (can be specified multiple times)",
    )
    below_parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would happen without making any changes",
    )

    args = parser.parse_args()

    try:
        local_path = getattr(args, "path", None) or "."
        with OtStackClient() as client:
            if args.repo is None:
                repo = client.detect_repo(local_path)
                if repo is None:
                    print(
                        "Could not detect repository. Please specify --repo or run "
                        "from within a git repository with a GitHub remote."
                    )
                    exit(-1)
                print(f"Detected repository: {repo.full_name}")
            else:
                repo = client.get_repo(args.repo, local_path)

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
                )
                if isinstance(result, BelowDryRunResult):
                    print(result.format_output())
                else:
                    print(
                        f"\nSuccessfully inserted '{args.branch}' below your current PR!"
                    )
                    print(f"\nNew PR: {result.new_pr.url}")
                    print(f"Original PR (retargeted): {result.original_pr.url}")
                    print(f"Worktree: {result.worktree_path}")
    except ValueError as e:
        print(e)
        exit(-1)


if __name__ == "__main__":
    main()
