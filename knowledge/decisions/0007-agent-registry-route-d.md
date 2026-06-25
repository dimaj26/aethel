---
name: adr-0007-agent-registry-route-d
description: Route D delegates analysis to a registered agent; a closed knowledge/agents.md registry is the only mechanical teeth. [A-] tags, Route-D sessions, and prelude enforcement were considered and dropped.
---

# ADR 0007 — Agent Layer as a First-Class Protocol (Route D + registry)

- **Status:** Accepted
- **Date:** 2026-06-24

## Context
The `proposal-analysis` audit engine (a `SKILL.md` under the gitignored `.agents/` tree) **existed
but was unreachable from the protocol**: no route told a chat *when* to use an agent, and default
(`.gitignore`-respecting) search could not even find it. The observed failure: asked to "analyse via
an agent", a chat **invents a non-existent agent** and spawns it with no protocol context. The
problem is three-faced — (a) discoverability (agents invisible under gitignore), (b) routing (no
protocol entry point), (c) cold-start context (a spawned agent inherits nothing).

## Decision
Add **Route D: Analysis** to AETHEL.md §1, opt-in (fires only when the user asks to *evaluate /
review / critique / audit* — disjoint from Route B, which implements). Back it with a single
mechanical guarantee: a **closed registry** `knowledge/agents.md` ("not in the registry ⇒ does not
exist") whose integrity is enforced by `check_agent_registry` (see [linter-checks](../linter-checks.md)).
A §6 **spawn-prelude contract** requires every delegation prompt to name a registered agent and to
inject AETHEL.md + the task's CC tags + the data + a result contract.

Face-by-face: **(a) + (b) are mechanized** (registry + the check; Route D in core). **(c) is prose**
— the §6 prelude rule, with no linter teeth, because a spawn prompt is not a file the linter sees.

## Alternatives considered and dropped
- **An `[A-]` reference-tag namespace** (mirror of `[G-]/[C-]/[K-]`, resolved in
  `implementation_plan.md`). Dropped: a **false analogy**. `[G-/C-/K-]` are *plan-internal*
  Contextual-Constraint tags, but Route B (plan) and Route D (analysis) are **disjoint stages** — an
  agent is essentially never cited inside a plan, so the tag would resolve over the empty
  intersection. It also leaked a concrete slug into the managed core block (CC-1 §8). The registry +
  ordinary inline links already give identity and integrity.
- **A dedicated Route-D lifecycle** (`aethel analyze`, an `analysis.md` artifact, a `--stage
  analysis`) to give face (c) mechanical teeth. Dropped as over-engineering: Route D only needs to
  ensure the AI hands data to a *registered* agent; that is the registry's job, and a Route D run may
  not even open a session. Owner accepts prose-only enforcement for the prelude.

## Consequences
- The core block changes (Route D + §6), so `CORE_REVISION` 7 → 8.
- Route D text in core is **generic** ("route to a registered agent in `knowledge/agents.md`"); the
  concrete `proposal-analysis` entry lives in the workspace registry, not in core — CC-1 §8 stays clean.
- Registry scope is **skill-agents under `.agents/`**. Ad-hoc framework agents selected by
  `subagent_type` (Explore/Plan/general-purpose) are host-spawned and intentionally out of scope —
  noted, not solved, so a future reader does not mistake the registry for an exhaustive agent list.
- Face (c) has no mechanical guarantee by design; a future ADR may revisit if prose proves insufficient.
