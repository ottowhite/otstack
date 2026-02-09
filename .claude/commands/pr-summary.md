# PR Summary Command

Generate a one-paragraph summary of the current branch's changes compared to `main`.

## Instructions

1. Run `git log main..HEAD --oneline` to see the commit history
2. Run `git diff main...HEAD --stat` to see the file changes summary
3. Synthesize the information into a **single paragraph** that describes:
   - The main feature/change introduced
   - Key architectural decisions or patterns used
   - Notable refactoring or deletions
   - Any new abstractions or protocols introduced

Keep the summary concise but comprehensive. Focus on the "what" and "why", not the "how".

## Style

- Write in **imperative mood** suitable for a squash commit message body (e.g., "Introduce...", "Add...", "Replace..."), not past tense ("This branch introduced...") or third person ("This PR adds...")
- Use **British English** spelling (e.g., "colour", "behaviour", "centralised", "organised")

## Output

Write the summary to `/tmp/pr-summary.txt` so it can be easily copied without terminal line-wrapping artifacts. After writing, inform the user of the file path.
