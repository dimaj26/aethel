---
name: session-lifecycle
description: Per-session Route B working directory under .aethel/ — multi-slot start, select, switch, done, abandon.
---

# Session Lifecycle

Route B work happens in a **per-session working directory** under a gitignored `.aethel/` tree,
identified by a sortable run-id. This replaces the old fixed-name, root-level artifacts
(`implementation_plan.md` / `task.md` / `walkthrough.md` at the repo root), which had two failure
modes: mismatched fixed-name files from different tasks bundled together, and an interrupted
session polluting the next. A directory now *is* a session.

Sessions are **multi-slot**: many can be live at once, so two agents/chats can run parallel Route B
tasks in one workspace without stomping each other. Implemented in `aethel/session.py` (stdlib
only); the CLI verbs live in `aethel/cli.py`; the linter resolves artifacts through it.

## Layout (under the gitignored `aethel_dir`, default `.aethel`)
- `.aethel/CURRENT` — pointer file naming the **default** selected run-id (one of possibly many).
- `.aethel/sessions/<id>/` — a live working dir: `implementation_plan.md`, `task.md`,
  `walkthrough.md`, and `session.json` (the manifest). Multiple live sessions coexist here.
- `.aethel/archive/<id>/` — sessions explicitly completed (`aethel done`).
- `.aethel/archive/_incomplete/<id>/` — sessions explicitly abandoned (`aethel abandon`) or, via the
  legacy `reconcile`, an interrupted one.

The manifest `session.json` is `{id, slug, started_at, status, validated_at}` where
`status ∈ {active, validated}`.

## Run-id
`make_run_id(slug)` → `YYYYMMDDThhmmssZ` (UTC, fixed-width basic ISO-8601) optionally `-<slug>`,
where the slug is sanitized to kebab-case (from the `aethel start` argument). Lexicographic order
tracks chronological order. A same-second collision is resolved in `start_session` by appending
`-2`, `-3`, … (it sees the existing session dirs).

## Selecting a session (resolution precedence)
A command operates on **one** selected session, resolved by `_active_run_id`:
`--session <id>` flag  >  `AETHEL_SESSION` env var  >  the `CURRENT` pointer. An empty/whitespace
selector at any tier is ignored and falls through, so a blank env never masks `CURRENT`. Per-agent
isolation uses the env (each parallel agent pins its own id without touching the shared `CURRENT`);
interactive switching uses `CURRENT` via `aethel switch`. A selector that resolves to a missing or
already-archived dir reads as "no session" (fail closed to the root-fallback below) — it never
crashes.

## Lifecycle — verbs
- **`aethel start [slug]`** — open a fresh `sessions/<new-id>/` with an `active` manifest and point
  `CURRENT` at it. **Multi-slot: it does NOT reconcile/archive the prior session** — that one stays
  live and is reachable via `AETHEL_SESSION`/`switch`.
- **`aethel sessions`** — list every live session (id, status, slug), `*` marking the one `CURRENT`
  selects.
- **`aethel switch <id>`** — repoint `CURRENT` at an existing live session (exact run-id only; an
  unknown id fails fast).
- **work** happens inside `sessions/<id>/`. The commit-time walkthrough guard
  (`check_walkthrough_sync`) blocks a code commit while the SELECTED session's `walkthrough.md` is
  missing or malformed. The guard is **PURE**: it only enforces, it never writes the manifest or
  archives.
- **`aethel done`** — the final Route B step. Re-validates the selected session's report
  (`check_report_file`); on success marks `status=validated` AND archives it to `archive/<id>/`
  immediately (completion is final, not resumable); on failure refuses (exit 1, session stays
  `active`). Clears `CURRENT` iff it pointed at the archived id.
- **`aethel abandon`** — archive the selected session to `archive/_incomplete/<id>/`. A recoverable
  directory move (not a delete), so it acts directly with no interactive confirmation (the operator
  is an AI agent; a `[y/N]` prompt would only add a step to stall on). Clears `CURRENT` iff it
  pointed there.

Archival is deliberately an explicit verb, never a side effect of `start`: that is what lets
parallel sessions coexist. The single-slot `reconcile` (archive-on-start) is retained only for
back-compat dangling-pointer cleanup and is no longer called by `start`.

## Artifact base resolution (backward-compatible)
`_artifact_base(workspace, cfg)` (in `aethel/linter.py`) = the selected session dir when one
resolves (see precedence above), else the workspace root. All artifact checks (`check_plan_file` /
`check_checklist_file` / `check_report_file` / `check_plan_stage`) and the walkthrough guard read
from that base. A workspace that never runs `aethel start` (fresh clone, clean CI) has no selector,
so the base falls back to root and every session-aware check behaves exactly as before — inert and
green. `aethel lint --session <id>` pins the base to a specific session.

## Edge cases
- **Parallel tasks.** Two agents each `aethel start` their own session; each pins
  `AETHEL_SESSION=<its-id>` so its `lint`/`done` resolve its own artifacts while the shared
  `CURRENT` may point at either.
- **Resume vs new task.** To RESUME a task, keep working in its session (or `aethel switch <id>`) —
  do NOT re-run `aethel start` for the same task (that just opens a second parallel session).
- **Forgot to close.** A live session simply stays under `sessions/` until `aethel done`
  (complete) or `aethel abandon` (drop) — `start` no longer sweeps it away.
- **`.aethel/` is never scanned** as knowledge/recipes (a dot-dir; `check_knowledge_index` only
  walks the knowledge dir, and recipe discovery skips dot-dirs) and is gitignored by
  `ensure_aethel_gitignored` (called from `aethel init` / `aethel update`).

## Config
`[session] aethel_dir` (default `.aethel`) relocates the whole tree; see
[linter checks](linter-checks.md) for how the artifact base feeds the checks.
