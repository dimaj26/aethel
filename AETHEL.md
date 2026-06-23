# Aethel Development Orchestrator & AI Protocol (AETHEL.md)

Welcome, AI Developer. This file is the official human-written orchestrator and rulebook. It defines your behavioral boundaries, decision routing, planning blueprints, and development standards.

---

## 1. Decision Routing Protocols

When the user issues a prompt, silently categorize the work into one of three routes:

### Route A: Immediate Execution
* **Criteria**: Simple bug fixes, style adjustments, single-file edits, comments, minor unit tests, or exploratory requests.
* **Protocol**: Implement directly. No plan is required. Explain what you did concisely.

### Route B: Plan-First Implementation (RNA-Blueprint)
* **Criteria**: New features, architectural changes, multi-file edits, database modifications, or complex refactorings.
* **Protocol**:
  1. **Start a session**: run `aethel start <slug>` to open a fresh per-session working
     directory `.aethel/sessions/<id>/` (it reconciles/archives the previous session first —
     a validated one to `.aethel/archive/<id>/`, an interrupted one to
     `.aethel/archive/_incomplete/<id>/`). Author `implementation_plan.md`, `task.md`, and
     `walkthrough.md` INSIDE that directory — it is the `<artifacts_directory>` the linter
     stages resolve to. `.aethel/` is gitignored (local scratch). To RESUME an unfinished task,
     keep working in the active session — do NOT re-run `aethel start` (that would archive it as
     `_incomplete`).
  2. Perform codebase research using search tools. Do NOT modify code yet.
  3. Create or update `implementation_plan.md` using the **RNA-Blueprint** format (see section 2).
  4. Specify any open questions or design decisions.
  5. **Plan Linting**: Right after generating/updating the plan, run:
     `.\venv\Scripts\python.exe prompt_linter.py --dir <artifacts_directory> --stage plan`
     Correct any errors before requesting user approval.
  6. Halt and wait for user approval before modifying code.
  7. Upon approval, author `task.md` as a complete ordered checklist derived from the plan's Proposed Changes, then execute it in 3–5 step chunks, re-checking and editing the checklist as reality dictates.
  8. **Checklist Linting**: Once all implementation steps are finished and all tasks in `task.md` are completed, run:
     `.\venv\Scripts\python.exe prompt_linter.py --dir <artifacts_directory> --stage checklist`
  9. **Walkthrough Report (MANDATORY)**: After the checklist is complete, author `walkthrough.md` — the session/task report — using the structure below, then validate it:
     `.\venv\Scripts\python.exe prompt_linter.py --dir <artifacts_directory> --stage report`
     A commit-time guard (`check_walkthrough_sync`) requires `walkthrough.md` whenever a Route B task stages code (escape hatch: `AETHEL_SKIP_SYNC=1`). `walkthrough.md` is a per-session local artifact (gitignored), not committed.
     * **Structure** (required sections): `## Summary` (what & why, 1 paragraph), `## Changes made` (by area, with file refs), `## What was tested` (commands/scenarios run), `## Validation results` (outcomes, key numbers). `## Notes / follow-ups` is optional.
  10. **Close the session**: run `aethel done`. It re-validates the active session's report
      (`check_report_file`) and, on success, marks the manifest `status=validated`; on failure it
      refuses and leaves the session `active`. The walkthrough guard stays PURE (enforce only) —
      marking a session done is `aethel done`'s job, never a commit side-effect.

### Route C: Docs Update (Markdown Knowledge Index) — MANDATORY post-step
* **Criteria**: Any changes to database schemas, API surfaces, module structures, business logic, or code patterns.
* **This is not an optional route.** Whenever a Route A or Route B change touches the items above, you MUST complete Route C in the SAME commit, BEFORE finishing. The pre-commit linter enforces this: its `[sync]` drift check flags a commit that stages code without updating a spec file (the knowledge index `CONTEXT.md`, a `knowledge/*.md` topic file, or `AETHEL.md`).
* **Protocol**:
  * Update the Markdown knowledge index ([CONTEXT.md](file:///c:/aethel/CONTEXT.md)) and the linked `knowledge/*.md` topic files so the spec moves with the code: extend (or add) the topic file for the layer you changed, and add or fix its link in the index.
  * Record notable design decisions as an ADR under `knowledge/decisions/NNNN-*.md`.
  * When refactoring or deleting structures, prune the stale topic files and remove their now-dead index links — keep the index curated (one line per link), not exhaustive.
  * For human-readable release changes, append to [CHANGELOG.md](file:///c:/aethel/CHANGELOG.md).
  * If a commit is genuinely spec-irrelevant (typo, formatting), bypass the guard explicitly with `AETHEL_SKIP_SYNC=1 git commit ...` — do not disable the check.

---

## 2. RNA-Blueprint Plan Template (RNA-1)
Every complex plan must be structured as follows:

```markdown
# [Feature/Goal Description]

## User Review Required
- Highlight critical design choices, breaking changes, or trade-offs.

## Base DNA
- OS, stack, runtime constraints.

## Task RNA
- Logic, risks, edge cases.

## Contextual Constraints (CC)
- Extract relevant rules from local configurations, the knowledge index (`CONTEXT.md`), and `knowledge/*.md`.

## Proposed Changes
### [Component/Module Name]
- [MODIFY/NEW/DELETE] [filename](file:///path/to/file)
  - Detail exact API and logic changes.

## Verification Plan & TDD Reproducer
### Automated Tests
- Command to run tests (e.g., `pytest`, `npm test`). Explicitly name the reproducing test file and test case name that reproduces the issue before code changes are applied.
### Manual Verification
- Visual inspection checklist or console output matches.
```

**Chunking rule**: Execute 3–5 steps → report → await approval → continue.

---

## 3. Debugging Philosophy (Bug Fixes)
* If a bug is reported, you MUST first write a failing unit or integration test that reproduces the bug, verify that it fails, and only then write the code changes to fix the bug. Fixing a bug without reproducing it with a test first is a process failure.

---

## 4. Git Commit & Workflow Protocol (GW-1)
* Commits must use imperative mood (e.g., `feat: add memory sync command`, NOT `added memory sync command`).
* Group commits by type prefix: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
* **Local milestone auto-commit (default ON)**: Upon completing a coherent milestone or refactor — NOT on every edit, and never mid-task while a Route B plan still awaits approval — commit locally without being asked, following these steps:
  1. Run the workspace linter and ensure it is green BEFORE committing. Never commit a red tree.
  2. Complete Route C in the SAME milestone: stage the matching spec updates (the knowledge index `CONTEXT.md` and/or the relevant `knowledge/*.md` topic file) together with the code, so the `[sync]` drift guard passes naturally. Do not bypass it with `AETHEL_SKIP_SYNC` to force an auto-commit.
  3. `git status` and review the diff for secrets, large files, or stray artifacts before staging. Stage intentionally; avoid blind `git add -A` when the tree is dirty with unrelated files.
  4. `git rm <deleted-files>` (if applicable), then `git add <paths>`.
  5. `git commit -m "<prefix>: <imperative message>"` — one logical change per commit; no `auto`/timestamp messages.
* `git push` is strictly forbidden from automatic execution. It must only be run if the user explicitly requests it.

---

## 5. Critical Coding Taboos (Hard Constraints)

1. **Sync Code and the Knowledge Index**: When modifying files or adding modules, immediately update the Markdown knowledge index (`CONTEXT.md`) and the relevant `knowledge/*.md` topic file to match.
2. **Database Facades Only**: Never query the raw database context from the UI or handler layers. Use service/domain facades.
3. **FSM State Hygiene**: Never transition state machines without validating pre-conditions and logging the transition event.
4. **No Placeholders in Prod**: Do not commit placeholders, dry-run mocks, or unhandled `TODO` comments to the main branch — this includes placeholder index links or topic files.
5. **No state.clear()**: Do not invoke global state clears without explicit backup and verification.
6. **Fail-Fast Error Handling**: Never catch exceptions silently. Always log with tracebacks and propagate where appropriate.
7. **Keep Context.md Under 150 Lines**: `CONTEXT.md` is a curated index — push detail down into `knowledge/*.md` topic files, do not dump it inline.
8. **Linter Compliance**: Do not ignore warnings from the `prompt_linter.py` script. Fix them before finishing.
9. **No Redundant Confirmation-Seeking**: If this file, a prior explicit instruction, or an established convention already answers a procedural question (commit granularity, formatting, which file something belongs in), act on it directly — do not ask the user to confirm that the documented rule should be followed. Reserve questions for genuine ambiguity: conflicting instructions, missing information needed to proceed, or an irreversible/destructive action. When unsure whether a question is redundant, check this file and recent conversation first; only ask if neither resolves it.

---

## 6. Response Rules
* **Be concise.** No preamble. No restating what the code does.
* **Token-efficient.** If you modified a file using tools — do NOT paste it in chat. Summary only.
* **Lossless.** Preserve all existing comments/docstrings not related to the change.
* **PowerShell only.** All terminal commands must use PowerShell syntax (Windows).
* **venv**: Call `.\venv\Scripts\python.exe` directly for all Python executions.
* **One thesis, one agent.** When delegating analysis to a sub-agent, spawn one agent per distinct question/thesis — never bundle multiple analyses into a single agent. Relay each result separately.
* **Delegate only when it pays.** A sub-agent starts cold and re-derives context you already hold — the expensive path. Spawn one only when the analysis needs broad or independent context you do not already have (large fan-out search, heavy cross-file review). When the relevant context is already loaded and the question is simple, analyze inline. If asked to use an agent for something already in context and trivial, say inline is cheaper and confirm before spawning.
* **Gitignored content is invisible to default search, not irrelevant.** This repo uses a `_nogit_*` naming convention (`_nogit_roadmap.md`, `_nogit_dev_fixtures/`) for files that are intentionally untracked but still meaningful working content — `.gitignore` hides them from `Glob`/`Grep` (ripgrep respects `.gitignore` regardless of whether a file is git-tracked; force-adding it does not change this). If a broad search returns a suspiciously filtered or truncated result, or you are hunting for something by topic ("roadmap", "philosophy", "notes") rather than an exact known path, explicitly check repo-root files and consider a `_nogit_*`-aware or ignore-bypassing follow-up before concluding something doesn't exist.

---

## 7. Specification Architecture (Markdown Knowledge Layer)
Structured knowledge is plain Markdown, provider-agnostic, with no server dependency:
* **Index → topics → decisions.** `CONTEXT.md` is an `llms.txt`-style index: an H1, a one-line summary, then H2 sections of annotated **inline** links (`[topic](knowledge/topic.md) — one-line note`). It is curated, not exhaustive, and stays ≈ one screen. Detail lives DOWN in `knowledge/*.md` atomic topic files; design decisions are append-only ADRs under `knowledge/decisions/NNNN-*.md`.
* **Granularity.** One topic file = one unit-of-change and unit-of-retrieval (a layer / subsystem / bounded context), ~50–200 lines, a single H1, with `name` + `description` frontmatter. If a topic is 2–3 lines, keep it in the index; if a file no longer reads in one sitting, split it.
* **Links are relative Markdown.** Index links resolve on disk relative to the index; the linter (`check_knowledge_index`) treats a dead link as an error and an unlinked topic file (orphan) as a warning. Use inline links only.

---

## 8. Core Consistency Contract (CC-1)
Deployed Aethel workspaces are governed by this repository's **core** (the `aethel-core` managed block and the library defaults). The relationship is directional and must be preserved:
* **No principled disagreement.** Nothing in a workspace — custom rules, `aethel.toml`, recipes, or knowledge files — may contradict or silently override a core rule. On conflict, **the core wins**.
* **Extend, do not fork.** A workspace must NOT edit inside the `AETHEL:MANAGED id=aethel-core` block; project-specific rules live BELOW it, stack tooling in recipes, policy in `aethel.toml`. The block is owned by `aethel update`.
* **Superset, not copy.** A workspace is a *superset* of the core (workspace ⊇ core). The core is the invariant subset and is intentionally NOT a copy of any workspace — project-specific detail does not belong in this repository's templates.
* **Enforced mechanically.** The linter (`check_core_consistency`) compares a workspace's core block against the installed library's core; divergence is resolved with `aethel update`, not by hand-editing the block. This repository is the source of the core and is therefore exempt from the check.
