---
name: spec-architecture
description: The Markdown knowledge layer — index, topic tree, ADRs — that replaced the MCP graph.
---

# Specification Architecture (Markdown Knowledge Layer)

Structured knowledge is plain, provider-agnostic Markdown. The earlier design (a Memory MCP
server backing a `memory.json` JSON-Lines graph) was retired in favour of this layer; see
[ADR 0001](decisions/0001-retire-memory-graph.md).

## Shape
- **`CONTEXT.md`** — an `llms.txt`-style index: H1 + one-line summary + H2 sections of
  annotated **inline** links into the topic tree. Curated, not exhaustive; ≈ one screen,
  under 150 lines.
- **`knowledge/*.md`** — atomic topic files: one layer / subsystem / bounded context each,
  ~50–200 lines, a single H1, with `name` + `description` frontmatter.
- **`knowledge/decisions/NNNN-*.md`** — append-only ADRs for design decisions.

## Why
A curated link index is a DAG, so the graph's cycle/typed-relation modelling was unneeded;
`check_memory_integrity` only did structural validation, and the graph's relational querying
(in the external MCP server) was never invoked programmatically. The guarantees that matter —
no dead references, no orphan docs, no placeholders, spec moves with code (Route C) — are kept
by `check_knowledge_index` (see [linter checks](linter-checks.md)).

## Granularity
One file = one unit-of-change AND unit-of-retrieval. If a topic is 2–3 lines, keep it in the
index; if a file no longer reads in one sitting or changes piecemeal, split it. Topic-file
structure is project-specific and is NOT hard-coded into the core (per
[core consistency](core-consistency.md)); only index-integrity rules live in the core/linter.
