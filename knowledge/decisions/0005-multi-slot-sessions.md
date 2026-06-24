---
name: adr-0005-multi-slot-sessions
description: Sessions are multi-slot; archival is an explicit verb (done/abandon), not a start side effect.
---

# ADR 0005 — Multi-slot Concurrent Sessions

- **Status:** Accepted
- **Date:** 2026-06-24

## Context
The per-session lifecycle was **single-slot by construction**: one global `CURRENT` pointer, and
`start_session` called `reconcile()` unconditionally, so opening a second Route B task forcibly
archived the first to `archive/_incomplete/<id>/`. Two parallel sessions were impossible — fatal for
a project whose stated operator is an AI agent (AETHEL.md §IMPORTANT) and whose intended mode is
multiple agents/chats working one workspace. Starting any new task silently destroyed an in-flight
one.

## Decision
Sessions are **multi-slot**: many live `sessions/<id>/` coexist, and the selected one is resolved by
precedence `--session <id>` flag > `AETHEL_SESSION` env > `CURRENT` pointer (`_active_run_id`).
`start` opens a NEW session and **never reconciles/archives the prior one**; archival moves out of
start into two explicit verbs:
- `aethel done` — validate the report, then archive to `archive/<id>/` **immediately** (completion
  is final and not resumable; owner decision).
- `aethel abandon` — archive to `archive/_incomplete/<id>/`, a recoverable move performed directly
  with **no interactive confirmation** (the operator is an AI agent; a `[y/N]` prompt is a step to
  stall on, not a safeguard, for a reversible move).

New read/selection verbs `aethel sessions` (list) and `aethel switch <id>` (repoint `CURRENT`)
round out the surface; `done`/`abandon`/`lint` accept `--session`. The legacy single-slot
`reconcile` is kept only for back-compat dangling-pointer cleanup and is no longer called by
`start`. `CORE_VERSION` 1.4.0 → 1.5.0 (the §1 Route B core-block text changed).

## Consequences
- Two agents pin `AETHEL_SESSION=<their-id>` and run truly parallel Route B tasks; the shared
  `CURRENT` is just the default selector.
- A selector pointing at a missing/archived id fails closed to the root-fallback (never crashes);
  unknown ids to `switch` fail fast (`[G-fail-fast-error-handling]`).
- Backward compatible: a single-session workflow with no env/flag behaves exactly as before
  (one `CURRENT`, root-fallback when absent) — fresh clone / CI stay inert and green.
- An interrupted session is no longer auto-swept by the next `start`; it stays live under
  `sessions/` until `done` or `abandon`. The `_incomplete/` bucket now fills via `abandon`.
