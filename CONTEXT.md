# Aethel Context Index (CONTEXT.md)

> Curated `llms.txt`-style index for the Aethel repository. One H1, a short summary, then
> annotated **inline** links into the `knowledge/` topic tree. Detail lives DOWN in
> `knowledge/*.md`; keep this index under 150 lines and ≈ one screen.

Aethel is a CLI + linter that scaffolds, updates, and validates a Markdown-based AI context
workspace. This file maps the project's structured knowledge — each link points at an atomic
topic file; design decisions are append-only ADRs under `knowledge/decisions/`.

---

## Architecture & Layout
- [Project overview](knowledge/README.md) — what Aethel is, the stack, and the repo layout.
- [Specification architecture](knowledge/spec-architecture.md) — the Markdown knowledge layer (index → topics → ADRs) that replaced the MCP graph.

## Tooling & Rules
- [Configuration loading](knowledge/config.md) — `aethel.toml` layered over a personal `~/.aethel/profile.toml` and library defaults.
- [Linter checks](knowledge/linter-checks.md) — every check `aethel.linter` runs and its stage wiring.
- [Session lifecycle](knowledge/session-lifecycle.md) — per-session `.aethel/` working dir: start, reconcile, archive, `aethel done`.
- [Core consistency (CC-1)](knowledge/core-consistency.md) — the directional core ⊇ workspace contract.
- [Recipe discovery](knowledge/recipes.md) — runtime discovery of stack-specific config recipes.

## Decisions (ADRs)
- [Decision records (ADR ledger)](knowledge/decisions/README.md) — append-only index of ADRs; each record reachable from here (keeps this index curated).

<!--
Add one inline link per topic file under knowledge/. Every relative link here must resolve on
disk (the linter errors on dead links); every knowledge/*.md must be reachable from this index
(an unlinked file warns as an orphan). External links and #anchors are ignored by the checker.
-->
