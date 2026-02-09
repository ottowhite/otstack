# Refine TDD Guide from PR Feedback

Refines the TDD Feature Implementer guide and fixes tests based on PR review feedback. Uses a validation loop to ensure the guide captures generalizable rules and the tests comply with PR comments.

## Agents

| Agent | Purpose | Inputs | Outputs |
|-------|---------|--------|---------|
| **GuideUpdater** | Extract generalizable rules from PR feedback | PR comments, fail context | Updated TDD guide |
| **BlindAnalyzer** | Analyze tests with NO PR visibility | TDD guide only | Notes file |
| **AlignmentValidator** | Check if blind analysis matches PR feedback | PR comments + notes | PASS/FAIL + reason |
| **TestFixer** | Apply guide to fix tests in place | TDD guide, notes, focus areas | Fixed tests (committed) |
| **ComplianceValidator** | Check if PR comments are addressed | PR comments, notes, test diffs | PASS/FAIL + unserviced list |

## Constants

```
MAX_RETRIES = 2
TDD_GUIDE = ".claude/agents/tdd-feature-implementer.md"
NOTES_FILE = "notes/test-review-against-tdd-guide.md"  # ephemeral - deleted on success
```

## Workflow

### Step 0: Verify PR Exists

```bash
gh pr view --json number,url,title --jq '{number: .number, url: .url, title: .title}'
```

If no PR exists for the current branch, inform the user and stop.

### Step 1: Main Loop

```
attempt = 0
unserviced_comments = null
fail_reason = null

while attempt <= MAX_RETRIES:
    attempt += 1

    # ─── GuideUpdater (SKIP on first attempt - guide might be sufficient) ───
    if attempt > 1:
        Run GuideUpdater with fail_reason context
        Commit TDD_GUIDE only: "docs: refine TDD guide (attempt {attempt})"

    # ─── BlindAnalyzer ───
    Run BlindAnalyzer → writes NOTES_FILE

    # ─── AlignmentValidator (SKIP on first attempt) ───
    if attempt > 1:
        Run AlignmentValidator
        if FAIL:
            fail_reason = alignment failure reason
            continue  # Guide still not capturing PR feedback, retry

    # ─── TestFixer ───
    Run TestFixer with focus on unserviced_comments
    TestFixer commits its own changes (atomic commits per fix)

    # ─── Run Tests ───
    Run: make test
    if tests fail:
        🙋 HUMAN INTERVENTION POINT
        "Tests failing after fixes. Options: [1] Retry [2] Fix manually [3] Abort"
        Handle based on user choice

    # ─── ComplianceValidator ───
    Run ComplianceValidator
    if PASS:
        BREAK  # Success!
    else:
        unserviced_comments = list of unserviced PR comments
        fail_reason = compliance failure reason

        if attempt >= MAX_RETRIES:
            🙋 HUMAN INTERVENTION POINT
            "PR comments unserviced after max retries. Options:
             [1] Continue anyway [2] Fix manually [3] Abort"
```

### Step 2: Cleanup

On success:
- Delete NOTES_FILE (ephemeral)
- Report summary to user

---

## Agent Prompts

### GuideUpdater

Spawn a `general-purpose` subagent with this prompt:

---

Update the TDD Feature Implementer guide based on PR review feedback.

**Context from previous failure** (if any):
{fail_reason}

**Unserviced PR comments** (if any):
{unserviced_comments}

1. Get PR comments using:
   - `gh pr view --json reviews,comments`
   - `gh api repos/{owner}/{repo}/pulls/{pr_number}/comments`

2. If no PR or no comments: return `EARLY_EXIT: [reason]`

3. Read `.claude/agents/tdd-feature-implementer.md`

4. Update the guide with GENERALIZABLE rules that would help catch the issues the reviewer raised. Focus especially on any unserviced comments from previous attempts.

5. Return: `SUCCESS: [summary of changes]`

**Important**: Extract patterns, not specific fixes. Rules should help future code, not just this PR.

---

### BlindAnalyzer

Spawn a `general-purpose` subagent with this prompt:

---

Analyze tests in this branch against the TDD Feature Implementer guidance.

**IMPORTANT**: You do NOT have access to PR comments. Analyze ONLY based on the TDD guide.

1. Read `.claude/agents/tdd-feature-implementer.md`

2. Find test files changed in this branch:
   ```bash
   git diff main --name-only -- 'tests/'
   ```

3. Read and analyze those test files thoroughly

4. Write findings to `notes/test-review-against-tdd-guide.md`:
   - List specific issues with file:line references
   - Cite which TDD guide section each issue violates
   - Suggest fixes for each issue

Be thorough but fair - only flag genuine violations of the TDD guide.

---

### AlignmentValidator

Spawn a `general-purpose` subagent with this prompt:

---

Validate whether the TDD guide successfully captures PR reviewer feedback.

You have access to BOTH:
1. PR comments (use `gh` CLI for current branch)
2. Blind analysis notes at `notes/test-review-against-tdd-guide.md`

Compare them:
- Do the notes identify the SAME issues as the PR reviewer?
- Are there PR comments the notes MISSED?
- Are there issues that seem like OVERFITTING?

Return:
```
VERDICT: [PASS/FAIL]

## Coverage Summary
- PR comments captured: X/Y

## Reason
[Brief explanation]
```

Be fair - minor misses are acceptable. The goal is useful guidance, not perfection.

---

### TestFixer

Spawn a `general-purpose` subagent with this prompt:

---

Fix the tests in this branch based on the TDD Feature Implementer guide.

1. Read `.claude/agents/tdd-feature-implementer.md`

2. Read the analysis notes at `notes/test-review-against-tdd-guide.md`

3. **Focus areas** (if any - prioritize these):
   {unserviced_comments}

4. Find and read test files changed in this branch:
   ```bash
   git diff main --name-only -- 'tests/'
   ```

5. Fix each issue identified in the notes:
   - Make the code change
   - Create an atomic commit for each logical fix
   - Use commit message format: `test: [description of fix]`

6. Return a summary of all fixes made.

**Important**:
- Only commit test files you changed
- Ensure tests still pass after each fix
- Don't fix issues not mentioned in the notes or guide

---

### ComplianceValidator

Spawn a `general-purpose` subagent with this prompt:

---

Validate whether the PR review comments have been addressed by the test fixes.

You have access to:
1. PR comments (use `gh` CLI for current branch)
2. Analysis notes at `notes/test-review-against-tdd-guide.md`
3. Git diff of test changes since fixes began

Steps:
1. Get all PR review comments
2. For each comment, check if the test fixes address it
3. Consider both direct fixes AND fixes that address the underlying pattern

Return:
```
VERDICT: [PASS/FAIL]

## PR Comment Status
| Comment | File:Line | Status | Notes |
|---------|-----------|--------|-------|
| [summary] | path:line | SERVICED/UNSERVICED | [how it was addressed or why not] |

## Unserviced Comments (if any)
[List comments that still need attention]

## Reason
[Brief explanation of verdict]
```

Be fair - if a comment's intent is addressed even if not literally, count it as serviced.

---

## Human Intervention Points

| Point | Trigger | Options |
|-------|---------|---------|
| **#1** | Tests failing after fixes | Retry / Fix manually / Abort |
| **#2** | Max retries exceeded | Continue anyway / Fix manually / Abort |
| **#3** | Workflow complete | Push / Review first / Squash commits |

## Now Execute

Begin executing this workflow. Start by checking if a PR exists for the current branch.
