---
name: linter-checks
description: The checks aethel.linter runs and how they are wired into stages.
---

# Linter Checks

`aethel/linter.py` validates a workspace. Severities are driven by `aethel.config` /
`aethel.toml`. The pre-commit hook runs the parameterless default; `--stage` selects one.

**Console-encoding resilience.** Both CLI entry points (`linter.main()`, `cli.main()`) call
`ensure_resilient_stdio()` first, reconfiguring stdout/stderr with `errors="replace"`. The linter
re-prints arbitrary AUTHORED Markdown (task-checklist text, plan errors) back to the user, which
will eventually contain a character outside whatever codepage a non-UTF-8 console uses (e.g. a
plain `cp1251`/`cp1252` Windows terminal) — this degrades legibility instead of crashing the
process. See `tests/test_console_encoding.py`.

**Hook degradation.** The hook prefers the installed `aethel` console script (`command -v aethel` →
`aethel lint .`), falling back to a venv interpreter running the `prompt_linter.py` wrapper. The
generated hook bakes `export AETHEL_REQUIRE=1`, so inside the hook a missing install is **fail-closed**
(hard `exit 1` with the install command) — a silent skip of a process guard is the wrong default. The
wrapper run MANUALLY outside the hook keeps the lenient default (warns and skips, exit 0; a missing
install is not a rule violation). Real lint violations always exit 1. See
[ADR 0003](decisions/0003-hook-degradation.md) and [ADR 0008](decisions/0008-hook-fail-closed.md).

## Checks
The individual checks are grouped into two atomic topics (this hub stays curated, §7):
- [Artifacts & tags](linter-checks-artifacts.md) — the Route B artifact-stage checks (plan / checklist
  / report), `[G-]/[C-]/[K-]` tag resolution, `{#slug}` anchors, and topic-size.
- [Integrity & commit guards](linter-checks-integrity.md) — knowledge-index, agent registry, workspace
  hygiene / core-consistency, the commit-time drift guards, and what the linter does NOT check.
