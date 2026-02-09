# PR Review Loop Skill

You are assisting with a live PR review session. Your job is to continuously monitor and resolve PR comments from the PR author until the PR is in a mergeable state.

**CRITICAL: You only action comments from the human who created the PR.** Comments from other humans or AIs are only actioned if the PR author has responded in agreement with an action plan.

## Workflow

Execute this workflow in a loop until there are no more unresolved PR comments (or 5 minutes pass with no new comments):

### Step 1: Get PR Information

Get the PR number, owner, repo, and **PR author** for the current branch:

```bash
gh pr view --json number,url,title,headRepository,author --jq '{number: .number, owner: .headRepository.owner.login, repo: .headRepository.name, pr_author: .author.login}'
```

If no PR exists for the current branch, inform the user and stop.

**Store the `pr_author` value—you will use it to filter comments.**

### Step 2: Fetch Unresolved Review Threads

Query the PR's review threads to get unresolved comments with their thread IDs and **comment authors**:

```bash
gh api graphql -f query='
  query {
    repository(owner: "{owner}", name: "{repo}") {
      pullRequest(number: {pr_number}) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            comments(first: 20) {
              nodes {
                body
                path
                line
                author {
                  login
                }
                createdAt
              }
            }
          }
        }
      }
    }
  }
'
```

### Step 3: Filter Comments by Authorship

For each unresolved thread, determine if it should be actioned:

1. **Direct PR author comment**: If the most recent actionable comment is from the PR author → **action it**

2. **Third-party comment with PR author approval**: If someone else made a suggestion AND the PR author subsequently replied in agreement (e.g., acknowledged the point, proposed an action plan, or indicated they want the change made) → **action the PR author's response/plan**

3. **Third-party comment without PR author approval**: If someone else (human or AI) made a comment and the PR author has NOT responded in agreement → **skip it** (do not action)

To determine "agreement", look at the PR author's response in the thread. Signs of agreement include:
- Explicit acknowledgment ("good point", "agreed", "yes", "will do")
- Proposing how to address it ("I'll change this to...", "let's do X instead")
- Any response that indicates acceptance of the feedback

If the PR author's response is ambiguous, treat it as agreement if they propose any action.

### Step 4: Process Actionable Comments

If there are actionable threads (per Step 3), spawn a general-purpose subagent using the Task tool with `subagent_type="general-purpose"`.

**The subagent prompt MUST include:**

1. **The list of actionable threads** with this structure for each:
   - Thread ID (the GraphQL node ID, e.g., `PRRT_kwDON...`)
   - File path
   - Line number
   - Comment body (the actionable comment—either from PR author or their agreed action plan)
   - Original suggestion (if this was a third-party comment that PR author approved)

2. **The subagent system prompt** (copy this exactly):

---

You are resolving PR review comments. For each comment provided:

**IMPORTANT: You may decline to action a comment** if:
- The rationale doesn't make sense after reviewing the code context
- The suggestion contradicts established patterns in the codebase
- The documentation/guidance is unclear or ambiguous about the right approach

**Before actioning each comment:**
1. Read and understand the comment and surrounding code context
2. Review relevant AI guidance files (CLAUDE.md, CODE_STANDARDS.md, agent definitions in `.claude/agents/`) if the comment relates to coding standards or practices
3. Verify you understand WHY the change is an improvement

**If the comment doesn't make sense or you're uncertain:**
- Do NOT make the change
- Do NOT resolve the thread
- Instead, reply to the comment on GitHub asking for clarification:

```bash
gh api graphql -f query='
  mutation {
    addPullRequestReviewComment(input: {
      pullRequestReviewId: "REVIEW_ID",
      body: "YOUR_QUESTION_HERE",
      inReplyTo: "COMMENT_ID"
    }) {
      comment { id }
    }
  }
'
```

Or use the simpler PR comment reply:
```bash
gh pr comment {pr_number} --body "Regarding the comment on {file}:{line} - {YOUR_QUESTION}"
```

**If the comment makes sense and you're confident:**
1. Make the necessary code changes to address the feedback
2. Create an atomic commit (one per logical change - may combine related comments)
3. Push immediately after each commit so the reviewer sees changes instantly
4. Resolve the thread on GitHub using this GraphQL mutation:

```bash
gh api graphql -f query='
  mutation {
    resolveReviewThread(input: {threadId: "THREAD_ID_HERE"}) {
      thread {
        isResolved
      }
    }
  }
'
```

Replace `THREAD_ID_HERE` with the actual thread ID provided for each comment.

**Important:**
- Create focused commits that address specific feedback
- Push after EVERY commit
- Resolve threads AFTER the fix is pushed

---

## Reflection Phase (CRITICAL - DO NOT SKIP)

**This phase is HIGH IMPORTANCE and must be executed after addressing all comments above.**

After all comments have been addressed, reflect on why the AI guidance allowed these mistakes to happen in the first place.

**For each comment that was actioned, ask:**
1. Why did the original code have this issue?
2. What systemic improvements could prevent this? Consider:
   - AI guidance (CLAUDE.md, CODE_STANDARDS.md, agent definitions, command definitions)
   - Project infrastructure (linting rules, type checking, pre-commit hooks, CI checks)
   - Note: Improvements may involve simplifying, clarifying, or removing noisy/contradictory guidance—not just adding more.
3. Is there a pattern across multiple comments suggesting a systemic gap?

**Actions to take:**
1. Review the relevant project components:
   - AI guidance: `CLAUDE.md`, `CODE_STANDARDS.md`, `.claude/agents/*.md`, `.claude/commands/*.md`
   - Project infrastructure: linting configs (`pyproject.toml`), CI workflows, pre-commit hooks, type checking

2. If you identify improvements that would prevent similar mistakes:
   - **Guidance improvements**: Make targeted edits to documentation
     - Be specific and actionable (not vague platitudes)
     - Add examples where helpful
     - **Consider simplifying**: Remove contradictory/noisy guidance, consolidate redundant sections
     - Commit message: `docs: improve AI guidance to prevent [specific issue type]`
   - **Infrastructure improvements**: Update linting rules, add CI checks, enhance type checking
     - Commit message: `chore: add [check/rule] to prevent [specific issue type]`
   - Push immediately after each commit

3. If the guidance was already sufficient but wasn't followed:
   - Consider if the guidance needs to be more prominent or clearer
   - Consider if the guidance is buried and should be elevated
   - Consider if there's conflicting guidance elsewhere that should be removed

**Reflection quality criteria:**
- Changes must be based on understanding the rationale behind the improvement
- Don't add guidance for one-off issues—focus on patterns
- Guidance should be concise and actionable
- Test the guidance mentally: "Would this have prevented the issue?"

---

3. **Instruction to return** a summary of:
   - Changes made for each thread (including any declined with questions)
   - Guidance improvements made during reflection

### Step 5: Check for New Comments (with Exponential Backoff)

After the subagent returns (or if there were no actionable threads):

1. Fetch review threads again from the PR (repeat Step 2)
2. If there are new unresolved actionable threads, reset the backoff timer and go back to Step 4
3. If there are no actionable threads, wait using exponential backoff before checking again:
   - First wait: 15 seconds
   - Second wait: 30 seconds
   - Third wait: 60 seconds
   - Fourth wait: 120 seconds
   - Fifth wait and beyond: 300 seconds (5 minutes, capped)
4. After waiting 5 minutes with no new comments, proceed to Step 6 (completion)

**Backoff implementation:**
```python
wait_times = [15, 30, 60, 120, 300]  # seconds
current_wait_index = 0

# After finding no new comments:
wait_time = wait_times[min(current_wait_index, len(wait_times) - 1)]
sleep(wait_time)
current_wait_index += 1

# If we've waited 300 seconds (5 min cap) and still no comments, exit the loop

# When new comments arrive:
current_wait_index = 0  # Reset backoff
```

### Step 6: Completion

When the loop exits:
- Inform the user that all PR comments have been addressed (or that the session timed out)
- Provide a summary of:
  - Changes made across all iterations
  - Comments declined and questions asked
  - Guidance improvements made during reflection

## Now Execute

Begin executing this workflow now. Start by getting the PR information for the current branch.
