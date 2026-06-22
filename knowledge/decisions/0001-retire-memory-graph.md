---
name: adr-0001-retire-memory-graph
description: Retire the Memory MCP graph (memory.json) for a Markdown knowledge layer.
---

# ADR 0001 — Retire the Memory MCP Graph for a Markdown Knowledge Layer

- **Status:** Accepted
- **Date:** 2026-06-22

## Context
Aethel's structured-knowledge layer was a Memory MCP server backing a `memory.json`
JSON-Lines graph (entities/relations, an ontology, and `check_memory_integrity`). This tied
the boilerplate to one provider's server, required MCP wiring during onboarding, and masked
`memory.json` as a git-binary. The graph's relational value was latent: `check_memory_integrity`
only validated structure (JSON-Lines well-formedness, type enums, broken-relation/orphan/cycle
checks), and the relational querying lived in the external server, which Aethel shipped rules
about but never invoked.

## Decision
Replace the graph with a provider-agnostic Markdown architecture: a curated `llms.txt`-style
index (`CONTEXT.md`) linking a `knowledge/` tree of atomic topic files, a universal `AGENTS.md`
entry point (with `CLAUDE.md`/`GEMINI.md` as stubs), and a Markdown-native integrity check
(`check_knowledge_index`) replacing `check_memory_integrity`. Remove `memory.json`, the
ontology config, Taboos #1/#7, and all MCP/graph prose. This repository migrates itself
(dogfood). See [spec architecture](../spec-architecture.md).

## Consequences
- No server/runtime dependency for the knowledge layer; any agent reads it as plain Markdown.
- The linter enforces index *integrity* (links resolve, no orphans, no placeholders), not a
  fixed set of topic files — topic structure is project-specific (CC-1).
- `.gitattributes` drops `memory.json binary` in favour of `* text=auto`.
- No deployed Aethel projects existed, so there is no migration window or legacy-handling code.
