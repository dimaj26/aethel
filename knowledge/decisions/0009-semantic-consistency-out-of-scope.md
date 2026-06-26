---
name: adr-0009-semantic-consistency-out-of-scope
description: Semantic/meaning consistency is out of linter scope by design; reject fact-anchors, redirect duplicated scalars to single-sourcing.
---

# ADR 0009 — Semantic Consistency Is Out of Linter Scope (by Design)

- **Status:** Accepted
- **Date:** 2026-06-26

## Context
A field report (#9) flagged a false "All checks PASSED": one topic said schema "version 5" while
another said "version 8" — a flat contradiction the linter did not catch. The report proposed
**fact-anchors** (`<!-- aethel:fact key=value -->` + an echo-assertion) and, at minimum, documenting
that semantic agreement is out of scope. Route D audit (PA-1) scored "document-and-don't-build" 6/6.

## Decision
**The linter is mechanical/structural by design and does NOT check semantic agreement of values or
claims across files.** It validates links, headings, slug resolution, staged-file pairing, language —
none of which understand meaning. General semantic consistency requires understanding text, i.e. an
LLM, which is exactly the dependency §7 refuses (Markdown, provider-agnostic, no server, stdlib-only).
The semantic checker already exists: the AI agent that reads the spec, plus agent/human review.

**Fact-anchors are rejected.** They are not semantic checking — they are a manual string-echo over
values an author pre-annotates. They (a) catch only what was hand-marked, (b) create a false
"consistency check PASSED" over a tiny annotated subset — reproducing the very false-confidence #9 is
about (Taboo 4: no false signals; a check that yields false confidence is worse than none), and (c)
add a new syntax + subsystem for one narrow class.

**Redirect, don't ignore.** The real recurring class — one canonical scalar (a version, id, threshold)
duplicated across files — is solved by **single-sourcing by identity**, not by echo-checking a
duplicate. The `REQUIRED_PLAN_H2S` constant (linter.py) is the sanctioned pattern: define the value
once, reference it; if it cannot be a code constant, name one file as canonical and link to it rather
than restating the value.

## Consequences
- No new code, syntax, or check; `knowledge/linter-checks.md` gains a "What the linter does NOT check"
  note so "PASSED" is never read as "semantically consistent".
- Authors/agents own semantic agreement; reviewers and the reading agent are the check.
- Duplicated canonical scalars are a smell to single-source, not to echo-validate.
