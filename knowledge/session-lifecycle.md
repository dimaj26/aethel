---
name: session-lifecycle
description: Per-session Route B working directory under .aethel/ — start, reconcile, archive, done.
---

# Session Lifecycle

Route B work happens in a **per-session working directory** under a gitignored `.aethel/` tree,
identified by a sortable run-id. This replaces the old fixed-name, root-level artifacts
(`implementation_plan.md` / `task.md` / `walkthrough.md` at the repo root), which had two failure
modes: mismatched fixed-name files from different tasks bundled together, and an interrupted
session polluting the next. A directory now *is* a session. Implemented in `aethel/session.py`
(stdlib only); the CLI verbs live in `aethel/cli.py`; the linter resolves artifacts through it.

## Layout (under the gitignored `aethel_dir`, default `.aethel`)
- `.aethel/CURRENT` — pointer file naming the active run-id (à la RocksDB `CURRENT` / git `HEAD`).
- `.aethel/sessions/<id>/` — the active working dir: `implementation_plan.md`, `task.md`,
  `walkthrough.md`, and `session.json` (the manifest).
- `.aethel/archive/<id>/` — sessions explicitly marked done.
- `.aethel/archive/_incomplete/<id>/` — sessions never marked done (interrupted).

The manifest `session.json` is `{id, slug, started_at, status, validated_at}` where
`status ∈ {active, validated}`.

## Run-id
`make_run_id(slug)` → `YYYYMMDDThhmmssZ` (UTC, fixed-width basic ISO-8601) optionally `-<slug>`,
where the slug is sanitized to kebab-case (from the `aethel start` argument). Lexicographic order
tracks chronological order. A same-second collision is resolved in `start_session` by appending
`-2`, `-3`, … (it sees the existing session dirs).

## Lifecycle — two explicit verbs + a pure guard
- **`aethel start [slug]`** — reconcile the previous session (see below), then open a fresh
  `sessions/<new-id>/` with an `active` manifest and rewrite `CURRENT`. Prints what it archived
  and the new session dir.
- **work** happens inside `sessions/<id>/`. The commit-time walkthrough guard
  (`check_walkthrough_sync`) blocks a code commit while that session's `walkthrough.md` is missing
  or malformed. The guard is **PURE**: it only enforces, it never writes the manifest.
- **`aethel done`** — the final Route B step. Re-validates the active session's report
  (`check_report_file`); on success writes `status=validated` (+ `validated_at`) to the manifest;
  on failure refuses (exit 1, session stays `active`). No active session is an error.

Completion is deliberately an explicit verb, not a guard side-effect: a guard that marked a
session done on every commit with a structurally-valid (even skeleton) report would undermine the
complete/`_incomplete` split and couple enforcement with lifecycle.

## Reconcile-on-start
`aethel start` reconciles a pre-existing `CURRENT` session before opening the new one: a
`validated` session moves to `archive/<id>/`, anything else (an `active`/interrupted session) to
`archive/_incomplete/<id>/`. The move is recoverable (a directory move, not a delete). With no
`CURRENT`, start just opens a new session.

## Artifact base resolution (backward-compatible)
`_artifact_base(workspace, cfg)` (in `aethel/linter.py`) = the active session dir when
`.aethel/CURRENT` resolves to an existing dir, else the workspace root. All artifact checks
(`check_plan_file` / `check_checklist_file` / `check_report_file` / `check_plan_stage`) and the
walkthrough guard read from that base. A workspace that never runs `aethel start` (fresh clone,
clean CI) has no `CURRENT`, so the base falls back to root and every session-aware check behaves
exactly as before — inert and green.

## Edge cases
- **Resume vs new task.** To RESUME an unfinished task, keep working in the active session — do
  NOT re-run `aethel start` (that would archive it as `_incomplete`).
- **Forgot `aethel done`.** The session stays `active` ⇒ the next `aethel start` archives it under
  `_incomplete/` (recoverable).
- **`.aethel/` is never scanned** as knowledge/recipes (a dot-dir; `check_knowledge_index` only
  walks the knowledge dir, and recipe discovery skips dot-dirs) and is gitignored by
  `ensure_aethel_gitignored` (called from `aethel init` / `aethel update`).

## Config
`[session] aethel_dir` (default `.aethel`) relocates the whole tree; see
[linter checks](linter-checks.md) for how the artifact base feeds the checks.
