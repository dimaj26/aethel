---
name: adr-0011-dedupe-session-mechanics-from-core
description: The verbose session mechanics are de-duplicated out of the managed core into the canonical session-lifecycle topic; CORE-REV 10→11.
---

# ADR 0011 — De-duplicate Session Mechanics Out of the Core Kernel

- **Status:** Accepted
- **Date:** 2026-06-26
- **Core:** `CORE-REV` 10 → 11 (Route B §1 prose trimmed)

## Context
Field report #8: the managed `aethel-core` block (~3,836 tokens, read on nearly every task) carried
verbose **session mechanics**. The fix was initially mis-designed as "move out + add a pointer link
inside AETHEL.md" — rejected by Route-D audit as a **dead pointer**: links live in `CONTEXT.md`, not
the rulebook, and the dead-link guard only scans `CONTEXT.md`, so a pointer in AETHEL.md is both
out-of-scope for the guard and broken in deployed workspaces.

The corrected finding: the mechanics are **already duplicated**. `knowledge/session-lifecycle.md`
holds the full canonical copy (multi-slot, the `--session`>`AETHEL_SESSION`>`CURRENT` precedence,
`switch`, `done`/`abandon`/archive paths, resume-vs-new) and is **already indexed in `CONTEXT.md`**
and dead-link-guarded. The two copies had already begun to drift — proof of the maintenance risk.

## Decision
**De-duplicate, don't relocate.** Remove the verbose session mechanics from the core block (§1
Route B steps 1 & 10), keeping the canonical topic as the single source of truth (Taboo 1 / §7
"one fact, one place"). **No pointer is added to AETHEL.md** — the agent discovers the topic via the
`CONTEXT.md` index as it does for every topic. `CORE-REV` 10 → 11; one block, no change to the
consistency machinery.

**Kept in the kernel** (operable happy-path for a deployed agent): the Route B step sequence, the
session verbs (`start`/`switch`/`done`/`abandon`), and TWO cautions that are behavioral invariants
NOT re-derivable from `aethel <cmd> --help`: (a) "`start` opens a NEW session, leaving any prior one
LIVE", and (b) **resume-vs-new** ("to resume, keep working in the session or `aethel switch <id>`;
do not re-run `start`"). **Moved out** (to the topic): the selection-precedence string, parallel
isolation, archive paths, and the pure-guard contract.

## Accepted CC-1 narrowing (audit condition, recorded so it is not silent)
`aethel init`/`update` do **not** ship `knowledge/session-lifecycle.md` to deployed workspaces, so a
deployed Route B agent relies on the **trimmed core's happy-path + the two retained cautions + the
CLI (`aethel <cmd> --help`)**, not on the topic. This is deliberate: the exhaustive mechanics are
*implementation documentation* re-derivable from the CLI, while the genuine *invariants* a cold agent
needs (the two cautions) stay in the propagated core. The behavior itself is shipped — it lives in
the `aethel` package, not in prose.

## Consequences
- The always-loaded core shrank (~15,344 → ~14,916 chars); more importantly, session mechanics now
  have ONE home and can no longer drift between core and topic.
- `knowledge/session-lifecycle.md` is the canonical reference (verified a strict superset of the
  trimmed prose before removal — no information lost).
- `tests/test_core_kernel.py` guards both directions: detail dropped, happy-path + both cautions kept.
