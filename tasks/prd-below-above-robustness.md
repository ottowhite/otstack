# PRD: Below/Above Command Robustness & Missing Scenarios

## Introduction

The `ots below` and `ots above` commands are partially implemented but break in real-world usage. This PRD covers fixing bugs that cause failures in practice, adding missing scenarios (no existing PR, draft PRs), and adding end-to-end test coverage for every user journey. The goal is to make stacking PRs feel effortless — the user should never have to think about the steps involved.

## Goals

- Every real-world user journey for `below` and `above` works without errors
- Users can start stacking from any state (branch with PR, branch without PR, mid-stack, top of stack)
- Draft PR support so new stack entries don't trigger CI/reviews prematurely
- Smarter defaults that minimize required user input
- End-to-end integration tests that catch regressions against real git repos (local, no GitHub API)
- Clear error messages and recovery guidance when things go wrong

## User Stories

### US-001: Fix interactive mode overwriting provided CLI args
**Description:** As a user, I want to pass `--branch foo` and only be prompted for the missing args, so that I don't have to re-type values I already provided.

**Acceptance Criteria:**
- [ ] If `--branch` is provided but `--title` and `--worktree` are missing, interactive mode only prompts for title and worktree
- [ ] All combinations of partial args work (1 of 3, 2 of 3 provided)
- [ ] Existing CLI args are never discarded or overwritten by interactive prompts
- [ ] Unit tests cover all partial-arg combinations
- [ ] Typecheck/lint passes

### US-002: Auto-default worktree path from branch name
**Description:** As a user, I want the worktree path to default to `../<branch-name>` so I don't have to type it every time.

**Acceptance Criteria:**
- [ ] When `--worktree` is omitted and `--branch` is provided, worktree defaults to `../<branch-name>` relative to repo root
- [ ] Interactive mode shows the default and lets user accept or override
- [ ] `--worktree` flag still works to explicitly override
- [ ] Unit tests verify the default is applied correctly
- [ ] Typecheck/lint passes

### US-003: Fetch remote before creating branch in `below`
**Description:** As a user, I want `below` to fetch the latest remote state before creating the new branch, so that it branches from the up-to-date destination rather than a stale local ref.

**Acceptance Criteria:**
- [ ] `below` runs `git fetch origin <destination_branch>` before `create_branch`
- [ ] New branch is created from `origin/<destination>` (not the potentially-stale local ref)
- [ ] Dry-run output mentions the fetch step
- [ ] Unit tests verify fetch is called
- [ ] Typecheck/lint passes

### US-004: Check remote branch existence (not just local)
**Description:** As a user, I want the "branch already exists" check to also check remote branches, so I don't get a confusing push failure later.

**Acceptance Criteria:**
- [ ] Branch existence check queries both local refs and `origin/` remote refs
- [ ] Error message says "Branch 'foo' already exists (on remote)" when only remote exists
- [ ] Error message says "Branch 'foo' already exists" when local exists
- [ ] Unit tests cover both local-only and remote-only existence
- [ ] Typecheck/lint passes

### US-005: Support `below`/`above` when no PR exists on current branch
**Description:** As a user, I want to run `ots below` or `ots above` even when my current branch has no open PR, so that I can start building a stack from scratch.

**Acceptance Criteria:**
- [ ] When no PR exists for the current branch, the command prompts: "No PR found for branch 'X'. Create one now?"
- [ ] If user confirms, prompts for PR title (defaulting to the branch name humanized) and destination branch (defaulting to repo default branch)
- [ ] Creates the PR for the current branch first, then proceeds with the below/above operation
- [ ] `--dry-run` shows the PR creation as an additional step
- [ ] In non-interactive mode (all args provided), errors with a clear message explaining `--create-pr` flag is needed
- [ ] Add `--create-pr` flag to allow non-interactive PR creation (uses branch name as title, default branch as destination)
- [ ] Unit tests for: interactive create, non-interactive with flag, non-interactive without flag (error)
- [ ] Typecheck/lint passes

### US-006: Draft PR support
**Description:** As a user, I want to create new stack entries as draft PRs, so they don't trigger CI or review requests prematurely.

**Acceptance Criteria:**
- [ ] Add `--draft` / `-d` flag to both `below` and `above` commands
- [ ] When `--draft` is set, the newly created PR is a draft on GitHub
- [ ] Interactive mode asks "Create as draft PR?" (default: yes)
- [ ] Dry-run output shows "(draft)" when applicable
- [ ] `Repository.create_pr` protocol gains an optional `draft: bool = False` parameter
- [ ] `PyGitHubRepository.create_pr` passes `draft=True` to `self._gh_repo.create_pull()`
- [ ] Unit tests verify draft flag is passed through
- [ ] Typecheck/lint passes

### US-007: Handle git push failures gracefully
**Description:** As a user, I want clear error messages when push fails (network issues, auth problems), not raw subprocess tracebacks.

**Acceptance Criteria:**
- [ ] `git push` failures are caught and re-raised as `ValueError` with a human-readable message
- [ ] Message includes the branch name and suggests checking network/auth
- [ ] If push fails after branch+worktree creation, the error message tells the user what was already created and how to clean up
- [ ] Unit tests simulate push failure and verify error message
- [ ] Typecheck/lint passes

### US-008: Handle pre-commit hook failures on empty commit
**Description:** As a user, I want a clear error when my pre-commit hooks reject the initialization commit, rather than an opaque git error.

**Acceptance Criteria:**
- [ ] `git commit --allow-empty` failures are caught with a clear message
- [ ] Message suggests either fixing hooks or using `--no-verify` as escape hatch
- [ ] Add `--no-verify` flag that passes through to the git commit
- [ ] Unit tests simulate commit hook failure
- [ ] Typecheck/lint passes

### US-009: Partial failure cleanup and recovery guidance
**Description:** As a user, when the command fails midway through (e.g., push succeeds but PR creation fails), I want to know what was already done and how to recover.

**Acceptance Criteria:**
- [ ] On any failure after mutations have started, print a "Recovery" section listing what was already created
- [ ] Include exact commands to undo each completed step (e.g., `git worktree remove <path>`, `git branch -D <name>`)
- [ ] If the worktree was created but PR was not, suggest retrying just the PR creation
- [ ] Unit tests verify recovery messages for failures at each step
- [ ] Typecheck/lint passes

### US-010: End-to-end integration tests for all user journeys
**Description:** As a developer, I want integration tests that run real git operations (local repos, no GitHub API) to verify the full below/above flow works in practice.

**Acceptance Criteria:**
- [ ] Test fixture creates a real local git repo with branches, commits, and a mock GitHub client
- [ ] **Journey: `below` on a simple stack** — branch with PR targeting main, insert below, verify branch/worktree/retarget
- [ ] **Journey: `above` on a simple stack** — branch with PR targeting main, insert above, verify branch/worktree/PR target
- [ ] **Journey: `below` mid-stack** — PR targets another feature branch (not main), insert below, verify retarget to intermediate branch
- [ ] **Journey: `above` on top of stack** — PR at the tip of a 3-deep stack, insert above, verify PR targets current branch
- [ ] **Journey: `below` then `above` on same branch** — verify both can be chained
- [ ] **Journey: running from inside a worktree** — verify commands work when cwd is a worktree, not the main repo
- [ ] **Journey: file copying** — verify files are actually present in the new worktree after the command
- [ ] All journeys use real git commands (init, commit, branch, worktree) with a mock GitHub client for PR operations
- [ ] Typecheck/lint passes

### US-011: Fix `get_branches` to only check actual branches
**Description:** As a developer, I want `get_branches()` to only return real branches, not tags or other refs, so the "branch already exists" check doesn't produce false positives.

**Acceptance Criteria:**
- [ ] `get_branches()` in `PyGitHubRepository` only returns actual branch refs (from `self._git_repo.heads` or `self._git_repo.branches`), not from `self._git_repo.references`
- [ ] Tags, stash refs, and other non-branch refs are excluded
- [ ] Unit tests verify tags don't appear in branch list
- [ ] Typecheck/lint passes

## Functional Requirements

- FR-1: Interactive mode must merge provided CLI args with prompted inputs (never discard provided args)
- FR-2: Worktree path must default to `../<branch-name>` when omitted
- FR-3: `below` must fetch the remote destination branch before creating a new branch from it
- FR-4: Branch existence checks must query both local and remote refs
- FR-5: When no PR exists on the current branch, the command must offer to create one (interactive) or accept `--create-pr` (non-interactive)
- FR-6: `--draft` flag must create the new PR as a GitHub draft PR
- FR-7: Git push failures must produce human-readable error messages with the branch name
- FR-8: Pre-commit hook failures on the initialization commit must produce clear guidance
- FR-9: Partial failures must print recovery instructions listing completed steps and undo commands
- FR-10: `get_branches()` must only return actual git branches, not tags or other refs
- FR-11: All user journeys must have integration tests using real local git repos

## Non-Goals

- No GitHub API integration tests (mock GitHub client is sufficient)
- No automatic rollback on failure (just guidance — rollback is too complex and error-prone)
- No `ots remove` or `ots move` commands (separate PRD)
- No support for non-GitHub remotes (GitLab, Bitbucket)
- No changes to `tree` or `sync` commands
- No PR description/body templates (keep it simple for now)

## Technical Considerations

- Integration tests should use `tmp_path` pytest fixture for isolated git repos
- Mock GitHub client from existing test helpers can be reused for integration tests
- The `Repository.create_pr` protocol change (adding `draft` param) must use a default value to avoid breaking existing callers
- Fetch operations add network dependency — tests should mock `git fetch` via the `CommandRunner` protocol
- Recovery messages should be built incrementally as steps complete (track completed steps in a list)

## Success Metrics

- All 7 user journeys in US-010 pass in CI
- Zero raw subprocess tracebacks visible to users (all failures produce human-readable messages)
- A new user can run `ots below` with zero flags and successfully create a stack entry (interactive mode fills everything in)
- `ots below -b my-feature` works with only the branch name (worktree auto-defaults, interactive fills the rest)

## Open Questions

- Should `--create-pr` also support `--draft` for the initial PR it creates on the current branch?
- Should we warn when running `above` on a branch that already has child PRs targeting it?
- Should there be a `--no-worktree` option for users who just want the PR structure without a local worktree?
- What should the default for `--draft` be? (Currently proposed: interactive defaults to yes, non-interactive defaults to no)
