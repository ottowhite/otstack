# PR Reflection Command

Conduct a learning reflection after completing a PR to identify concepts worth deeper study.

## Context

Users often use a coding agent to write code and may not have read relevant documentation for concepts introduced.

## Process

### Phase 1: Analyse the Diff

Launch parallel sub-agents to analyse `git diff main...HEAD`:

1. **Libraries/imports**: New dependencies, standard library modules, third-party features
2. **Python language features**: Protocols, async/await, type hints, decorators, generators, etc.
3. **Design patterns**: Composite, Strategy, dependency injection, caching patterns, etc.
4. **Testing patterns**: pytest features, test doubles, async testing, fixture patterns

### Phase 2: Interview (2-3 Rounds)

Use AskUserQuestion to assess familiarity with discovered concepts:

- Group related concepts (4 questions max per round)
- Offer: "Very familiar" / "Somewhat familiar" / "Not familiar"
- Allow free-text elaboration to capture nuance

### Phase 3: Research Resources (Most Important Phase)

**This is the highest-leverage part of the reflection.** Spend most effort here finding the best resources for each topic.

For each concept requiring a deep dive:

1. **Use WebSearch** to find current, high-quality resources (tutorials, official docs, conference talks, blog posts from respected authors)
2. **Use WebFetch** to verify all links are valid and the content is relevant
3. **Prioritise**:
   - Official documentation over third-party tutorials
   - Recent content (prefer 2025/2026)
   - Reputable sources with clear explanations and working examples
   - Video content for complex concepts (visual explanations often help)
4. **Reject** outdated resources, broken links, or low-quality content

### Phase 4: Generate Reflection

Create a structured markdown file with:

1. **Knowledge profile table**: Concept → Level → Notes from interview
2. **Prioritised deep dives**: Ordered by impact (🔥 high, 🟡 medium, 🟢 low)
   - Why this matters for the codebase
   - Specific study topics
   - **Curated resources** (verified links with brief descriptions of why each is valuable)
   - Relevant code locations in the PR
3. **Quick reference**: Concepts used correctly, no deep dive needed
4. **Suggested study order**: Weekly plan
5. **Action items**: Checkboxes for follow-up

## Output

Write the reflection to `~/projects/learning-reflections/{project-name}/` (create the directory if needed).

Filename format: `{branch-name}.md`

If the `~/projects/learning-reflections` repo doesn't exist, create it:
```bash
mkdir -p ~/projects/learning-reflections && cd ~/projects/learning-reflections && git init
```

After writing, commit the file and inform the user of the path.
