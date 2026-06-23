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

## Testing strategy
Unit tests (`tests/test_*.py`) and `tests/run_polygon.py`'s 13 end-to-end scenarios (A–M) run
against the SOURCE checkout (editable install / `python -m aethel.cli`). That is a structural
blind spot for packaging bugs: an editable install never goes through `package_data`/
`MANIFEST.in` resolution, so a config bug there (e.g. `aethel/templates/` silently dropped from
the wheel) is invisible to every test that runs from source. `tests/conftest.py`'s
session-scoped `installed_aethel_cli` fixture closes that gap: it builds the wheel once and
installs it into one throwaway venv, and `tests/test_release_smoke.py` /
`tests/test_scenario_projects.py` exercise the full command surface against that REAL installed
console script. `tests/test_packaging.py` guards the packaging config itself (the two root
causes of the templates-missing bug — a wildcard in `packages.find` and an unanchored `*` in
`MANIFEST.in`).

## Install & bootstrap
Recommended install is **pipx** (`pipx install aethel-cli`) — a global CLI the pre-commit hook finds via
`command -v aethel`, independent of any project venv; for development, `pip install -e .` inside the
venv. The generated hook **degrades gracefully** when `aethel` is not importable: it warns and skips
(exit 0) rather than blocking the commit, unless `AETHEL_REQUIRE` is set (strict mode, mirror of
`AETHEL_SKIP_SYNC`); real lint violations still fail. `aethel init` probes the hook interpreter and
prints the install command when the package is missing, without editing dependencies. See
[ADR 0003](decisions/0003-hook-degradation.md).
