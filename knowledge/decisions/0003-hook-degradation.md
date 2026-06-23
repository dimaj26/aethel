---
name: adr-0003-hook-degradation
description: Missing-install degrades to warn-skip (exit 0); strict mode via AETHEL_REQUIRE.
---

# ADR 0003 — Pre-commit Hook Degrades on a Missing Install

- **Status:** Accepted
- **Date:** 2026-06-23

## Context
The Aethel pre-commit hook runs the generated `prompt_linter.py` wrapper, which imports
`aethel.linter`. Previously a failed import (`aethel` not installed for the interpreter the hook
picked) printed an error and exited `1`, **hard-blocking the commit**. That punishes a state that
is not a rule violation: a fresh clone, a CI runner, or a contributor who has not yet installed the
package cannot commit at all — even for changes the linter never got to inspect. It also conflates
"the checker could not run" with "the checked content is bad".

## Decision
A **missing install degrades to warn-and-skip (exit 0)**, not a hard failure. The wrapper prints a
loud warning naming the interpreter (`sys.executable`) and the exact install commands
(`pipx install aethel` / `pip install -e .`), then exits `0`. A **strict mode** is available behind
`AETHEL_REQUIRE` (any non-empty value), which restores the blocking `exit 1` — the mirror of
`AETHEL_SKIP_SYNC` on the leniency side. Real lint violations are unaffected: `main()` runs only
when the import succeeds, so genuine findings still exit `1`.

The hook also prefers the installed `aethel` console script (`command -v aethel` → `aethel lint .`)
before falling back to a venv interpreter running the wrapper, so a globally installed CLI (pipx)
is found even when a project venv lacks the package. `aethel init` surfaces the same gap early: it
probes `import aethel` against the hook interpreter and prints the install command, but never edits
the project's dependencies (offer, not force).

## Consequences
- Onboarding and CI without a local install are not blocked; the gap is visible, not silent
  (Taboo #6: fail-soft with a loud signal, not a silent catch).
- Strict environments opt in with `AETHEL_REQUIRE=1` (e.g. a CI lane that must guarantee the linter
  actually ran).
- The leniency is scoped to *import failure only*; it never weakens any real check.
