---
name: adr-0001-record-architecture-decisions
description: We record architecture decisions as append-only ADR files.
---

# ADR 0001 — Record Architecture Decisions

- **Status:** Accepted
- **Date:** 2026-01-01

## Context
Design decisions need a durable, reviewable home. Inlining them into the index bloats it;
losing them to chat history loses the rationale.

## Decision
Record each notable decision as an atomic, append-only Markdown file under
`knowledge/decisions/NNNN-title.md`, numbered sequentially. ADRs are immutable once
accepted; a later decision that overrides an earlier one is a new ADR that supersedes it.

## Consequences
- The index links to ADRs like any other topic file; the rationale survives refactors.
- Superseded ADRs are kept (marked superseded), not deleted, so history stays auditable.
