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
