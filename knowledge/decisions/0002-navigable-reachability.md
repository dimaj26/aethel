---
name: adr-0002-navigable-reachability
description: Orphan = reachable by navigation (transitive); ADRs surfaced via a ledger.
---

# ADR 0002 — Navigable Reachability for the Knowledge Index

- **Status:** Accepted
- **Date:** 2026-06-23

## Context
An AI agent only *proactively* sees an `.md` if it is reachable by navigation from the entry point
(`CLAUDE.md → AGENTS.md → AETHEL.md → CONTEXT.md`) with an annotation telling it when to open the
file. An unlinked file is not invisible (grep finds it) but it is *unsurfaced* — effectively dead
knowledge for proactive use. The orphan check is the mechanism that prevents that.

The previous `check_knowledge_index` computed orphan reachability at **depth-1 from the index
only** — the reachable set was built solely from `CONTEXT.md`'s own inline links. A topic linked
from another topic (but not directly from the index) was a false orphan. That forced an impossible
choice: either a flat, exhaustive index (attention dilution; violates AETHEL.md §7 "curated, not
exhaustive" and Taboo #7's ≤150-line index) or per-directory exemptions that make files invisible.
The append-only ADR ledger is the canonical case: requiring every ADR be linked directly from the
index turns the index into an exhaustive decision log.

## Decision
Orphan means **not reachable by navigation from the index, transitively** (`index → topic → topic
→ ADR`), modelled by a cycle-safe breadth-first walk of inline links (`_reachable_md`). Links
resolve relative to the *linking* file's directory, so a topic can surface its own children.
ADRs are surfaced through `knowledge/decisions/README.md` (a ledger linked once from the index),
not one link per ADR in the top index. The change is strictly additive — it can only *reduce*
orphans — so no previously valid workspace regresses. With every file now reachable from the entry
point, this repo promotes `[knowledge] orphan_enforce` to `error`.

## Consequences
- The index stays a short, curated map; structure can nest without tripping the orphan check.
- The library default for `orphan_enforce` stays `warn` (CC-1: defaults are the lenient invariant);
  strictness is a per-workspace `aethel.toml` choice.
- The dead-link contract is unchanged: the index's own curated links must still resolve.
- Deeper-than-index dead links are out of scope here (a broken link in a topic simply fails to make
  its target reachable, surfacing as an orphan).
