---
name: core-consistency
description: CC-1 — the directional contract between the core and a workspace.
---

# Core Consistency Contract (CC-1)

Deployed Aethel workspaces are governed by this repository's **core**: the
`AETHEL:MANAGED id=aethel-core` block in `aethel/templates/AETHEL.md.template` plus the
library defaults. The relationship is directional and must be preserved.

- **No principled disagreement.** Nothing in a workspace (custom rules, `aethel.toml`,
  recipes, knowledge files) may contradict or silently override a core rule. On conflict,
  **the core wins**.
- **Extend, do not fork.** A workspace must NOT edit inside the managed block;
  project-specific rules live BELOW it. The block is owned by `aethel update`.
- **Superset, not copy.** A workspace is a superset of the core (workspace ⊇ core). The core
  is the invariant subset and intentionally NOT a copy of any workspace.
- **Enforced mechanically.** `check_core_consistency` compares a workspace's core block
  against the installed library's core (via `aethel/markers.py`); divergence is resolved with
  `aethel update`, not hand-editing. This source repo *defines* the core and is exempt
  (`_is_aethel_source_repo`). Severity: `[consistency] enforce` (default `warn`).
- **This repo's own exemption leaves a gap `check_core_consistency` cannot close**: nothing
  mechanically verifies that THIS repo's own `AETHEL.md` (the dev environment) itself meets every
  standard the shipped template declares — the directional rule (dev-env ⊇ core) applies here
  too, just unchecked by the linter. `tests/test_dev_env_core_sync.py` closes that specific gap
  for the Critical Coding Taboos list (the template's taboos must all appear in this repo's own
  `AETHEL.md`; the reverse asymmetry — dev-only taboos the template doesn't need — is allowed).

## Version stamping & skew
The managed block carries a version stamp `<!-- AETHEL:CORE-VERSION X.Y.Z -->` right under the
BEGIN marker. It is the managed-core-block version (`aethel.CORE_VERSION`), bumped only when the
block's rules change — distinct from the pip package version `aethel.__version__` (a test keeps
each internally in sync: the template stamp == `CORE_VERSION`, and `__version__` ==
`pyproject [project].version`).

The classification is a pure seam — `classify_core_state(workspace_path) -> CoreState` (status:
`source` / `no_template` / `no_workspace` / `no_block` / `consistent` / `skew` / `diverged`, plus
`ws_version` / `lib_version`). It strips the stamp from both sides (`markers.strip_core_version`)
before the structural compare, so two failure modes are told apart:
- **structure diverges** ⇒ the block was hand-edited / forked → severity `[consistency] enforce`.
- **structure matches, version differs** (incl. an unstamped older workspace) ⇒ the workspace is
  merely STALE → "run `aethel update`" at severity `[consistency] version_skew_enforce` (default
  `warn`, non-blocking). `aethel update` rewrites the block from the template, refreshing the
  stamp so the skew clears.

`check_core_consistency` consumes that classification and applies the config severity. `aethel
doctor` consumes the SAME `classify_core_state` to print the state for humans (see
[project overview](README.md)), so the linter and the doctor never disagree on what the core's
state is.

## Eject (sanctioned divergence)
`aethel eject [path]` stamps the block with `<!-- AETHEL:EJECTED id=aethel-core date=... -->`
(right after the BEGIN marker, written by `aethel/markers.py`'s `eject_block`). Once present,
`classify_core_state` returns status `"ejected"` BEFORE the structural compare — hand-edits stop
being `"diverged"`, `check_core_consistency` treats it as non-blocking like `"source"`, and
`_update_aethel_md` skips refreshing the block entirely (no backup, no overwrite) instead of
clobbering the workspace's intentional content. `aethel eject --undo` removes the stamp
(`uneject_block`), restoring both managed updates and divergence detection. This is the one
sanctioned exception to CC-1's "no principled disagreement": it must be an explicit, per-workspace
opt-in — never a library default.
