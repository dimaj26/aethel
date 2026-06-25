---
name: agents
description: Closed registry of spawnable skill-agents — the single source of truth for Route D delegation ("not listed here = does not exist").
---

# Agent Registry

Skill-agents live under the gitignored `.agents/` tree, so they are invisible to default
(`.gitignore`-respecting) search and to a chat picking an agent to spawn. This file is the
**closed source of truth**: Route D (Analysis) delegates only to an agent listed here. *Not in this
registry ⇒ it does not exist* — a chat must never invent or spawn an unlisted agent.

`check_agent_registry` ([linter-checks](linter-checks.md)) keeps the list honest in both directions:
a registry reference to a missing skill file is a dangling reference (error), and a skill file
discovered under `.agents/` but absent here is an orphan (warn) — promoted to error in this repo's
`aethel.toml`. **Register a skill-agent** with an inline Markdown link — or a backticked path —
pointing at its skill file under `.agents/`; both resolve on disk identically (exact form in
[linter-checks](linter-checks.md)). The live registration below is the worked example.

> **Scope.** The registry covers *skill-agents* (a `SKILL.md` under `.agents/`). Ad-hoc framework
> agents selected by `subagent_type` (Explore, Plan, general-purpose, …) are spawned by the host and
> are intentionally out of registry scope.

## proposal-analysis

- **Skill:** [proposal-analysis SKILL.md](../.agents/plugins/aethel-plugin/skills/proposal-analysis/SKILL.md)
- **What it is:** the architectural audit / design-evaluation engine (Ruthless System Architect).
  Optimality Scale (0–6 over Compliance / Value / Footprint), Triple Dialectic
  (Thesis → Antithesis → Synthesis), four verdict patterns with anti-perfectionism + auto-reject.
- **Invocation modes:**
  - **PA-1 (Project Mode, default)** — reference frame is the knowledge index (`CONTEXT.md`) +
    `knowledge/*.md` + Core Philosophy; recorded patterns are ground truth.
  - **APA-1 (Abstract Mode)** — only on an unambiguous abstract signal ("evaluate in the abstract",
    "independent of this project", "re-evaluate the recorded decision"); local rules suspended.
- **When to route here:** the user asks to *evaluate / review / critique* a proposal, plan, or
  design (Route D). Ordinary feature/architecture implementation stays Route B.
