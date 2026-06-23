---
name: project-overview
description: What Aethel is, its stack, and the repository layout.
---

# Project Overview

Aethel is a lightweight, provider-agnostic context & prompt management boilerplate for AI
agents in solo-developer projects. It separates human-authored rules (Markdown) from an
AI-maintained Markdown knowledge layer (the `CONTEXT.md` index + `knowledge/` topic tree),
and ships a CLI + linter that scaffold, update, and validate a workspace.

## Stack
- **Python 3.11+**, standard library only (`os`, `re`, `pathlib`, `tomllib`); no runtime deps.
- Dev tooling: `ruff`, `mypy`, `pytest`; CI on Linux + Windows, Python 3.11/3.12.

## Directory Layout
```text
├── AETHEL.md          # Canonical human-written orchestrator & rulebook
├── AGENTS.md          # Universal cross-agent entry point (→ AETHEL.md)
├── GEMINI.md/CLAUDE.md# Thin redirect stubs (→ AGENTS.md / AETHEL.md)
├── CONTEXT.md         # llms.txt-style index into knowledge/
├── knowledge/         # Atomic topic files (+ decisions/ ADRs)
├── CHANGELOG.md       # Human-readable release history
├── aethel.toml        # Optional linter policy
├── aethel/            # CLI package: cli.py, linter.py, config.py, markers.py, templates/
│                      #   recipes discovered at runtime from templates/recipes/*
└── prompt_linter.py   # Wrapper around aethel.linter
```

## How It Fits Together
`aethel init` scaffolds a workspace from `aethel/templates`; `aethel update` refreshes the
managed core block non-destructively; `aethel lint` runs the checks. `aethel version` prints the
package + core versions; `aethel doctor` diagnoses a workspace — version skew, core-block
consistency (shared `classify_core_state`, see [core consistency](core-consistency.md)), and
whether `aethel` is importable by the pre-commit hook's interpreter (exit 1 on a hard problem).
See [linter checks](linter-checks.md), [recipe discovery](recipes.md), and
[spec architecture](spec-architecture.md).
