---
name: adr-0008-hook-fail-closed
description: The generated git hook is fail-closed (bakes AETHEL_REQUIRE=1); Aethel never edits a manager-owned hook.
---

# ADR 0008 — Pre-commit Hook Is Fail-Closed; Foreign Hooks Are Never Edited

- **Status:** Accepted
- **Date:** 2026-06-26
- **Amends:** [ADR 0003](0003-hook-degradation.md)

## Context
A field report (an agent onboarding a real husky-managed Windows repo) found three compounding
defects that let a "hardened" Aethel hook be completely inert with no warning:

1. **Dead hook under a manager.** `init` wrote `.git/hooks/pre-commit` without checking
   `core.hooksPath`. With husky (`core.hooksPath=.husky/_`) git never reads that path, so the
   spec-sync/consistency guards silently never fired.
2. **Fail-open on missing install.** ADR 0003 made the wrapper warn-and-skip (exit 0) on a missing
   install unless `AETHEL_REQUIRE=1`. In any clone/CI without the exact venv, every guard silently
   no-opped — the "blocking" enforcement was illusory off the author's machine.
3. **Windows-broken venv probe.** The hook tested `[ -f "./venv/Scripts/python" ]`; on Windows the
   file is `python.exe`, so the test failed and it fell through to a bare `python` (usually without
   aethel) — combined with #2, another silent skip.

ADR 0003's leniency was the right call for *manual* invocation (a fresh clone shouldn't be unable to
commit), but the wrong default *inside the hook*, whose entire purpose is to enforce.

## Decision
- **The generated hook is fail-closed.** `PRE_COMMIT_HOOK` bakes `export AETHEL_REQUIRE=1`, so the
  wrapper's degrade path becomes a hard error *in hook context*. A missing install blocks the commit
  with the install command. `AETHEL_REQUIRE` scopes this to the hook only: the wrapper run manually
  keeps ADR 0003's warn-and-skip default, so a bare clone can still commit non-spec work. Escape
  hatches are unchanged (`AETHEL_SKIP_SYNC=1` for a spec-irrelevant commit; install to enable guards).
- **Windows venv probe fixed.** The hook probes `./venv/Scripts/python.exe` before the extension-less
  `./venv/Scripts/python`, matching `resolve_hook_python`'s pick order.
- **Foreign hooks are never edited.** When `core.hooksPath` is set, `write_pre_commit_hook` writes
  nothing and prints a manager-specific instruction (husky/lefthook/pre-commit-fw, else generic) to
  register `aethel lint .`. A shell-append is only correct for husky; lefthook (`lefthook.yml`) and
  pre-commit-fw (generated from `.pre-commit-config.yaml`) need format-specific edits a generic
  appender would corrupt or that get clobbered on the manager's next reinstall. So the only honest
  universal behavior is detect-and-instruct.
- **`aethel doctor` reports hook liveness.** `_hook_liveness` returns `live`/`dead`/`foreign`/`absent`/
  `n/a`; a `core.hooksPath` whose pre-commit lacks the Aethel invocation is `DEAD`, keeping the gap
  visible (it also checks husky's parent `.husky/pre-commit` when hooksPath ends in `_`).

## Consequences
- A deployed hardened workspace can no longer silently no-op its guards: a missing install blocks,
  a manager-owned hook is announced and surfaced by `doctor`, and the Windows interpreter is found.
- The leniency ADR 0003 introduced survives where it belongs (manual/CI invocation of the wrapper),
  scoped off in the hook via the env var rather than removed.
- This is a wrapper/CLI/diagnostic change only — no managed-core-block edit, no `CORE-REV` bump.
