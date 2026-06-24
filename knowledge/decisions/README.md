---
name: adr-ledger
description: Append-only index of Architecture Decision Records (ADRs).
---

# Decision Records (ADR Ledger)

Append-only index of Aethel's Architecture Decision Records. The curated knowledge index
([CONTEXT.md](../../CONTEXT.md)) links **this ledger** (one line), and the ledger links each ADR —
so the index stays curated (AETHEL.md §7, "curated, not exhaustive") while every ADR remains
reachable by navigation. Add a new line here when you add an ADR; never delete entries (records are
historical).

## Records
- [ADR 0001 — Retire the Memory MCP graph](0001-retire-memory-graph.md) — why structured knowledge is Markdown, not a `memory.json` graph.
- [ADR 0002 — Navigable reachability + ADR ledger](0002-navigable-reachability.md) — orphan = reachable by navigation (transitive); ADRs surfaced via this ledger.
- [ADR 0003 — Hook degrades on a missing install](0003-hook-degradation.md) — missing install → warn-skip (exit 0); strict mode via `AETHEL_REQUIRE`.
- [ADR 0004 — Personal profile is a live overlay](0004-personal-profile-live-overlay.md) — `~/.aethel/` config + recipes merged live; precedence defaults < profile < workspace; fail-open.
- [ADR 0005 — Multi-slot concurrent sessions](0005-multi-slot-sessions.md) — many live sessions; selector `--session` > `AETHEL_SESSION` > `CURRENT`; archival is explicit `done`/`abandon`, not a `start` side effect.
- [ADR 0006 — Core block uses an integer revision, not semver](0006-core-revision-not-semver.md) — `CORE-REV N` unconfusable with the semver package version; PyPI axis surfaced live by `aethel doctor`.
