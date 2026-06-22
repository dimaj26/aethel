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

## Version stamping & skew
The managed block carries a version stamp `<!-- AETHEL:CORE-VERSION X.Y.Z -->` right under the
BEGIN marker. It is the managed-core-block version (`aethel.CORE_VERSION`), bumped only when the
block's rules change — distinct from the pip package version `aethel.__version__` (a test keeps
each internally in sync: the template stamp == `CORE_VERSION`, and `__version__` ==
`pyproject [project].version`).

`check_core_consistency` strips the stamp from both sides (`markers.strip_core_version`) before
the structural compare, so two failure modes are told apart:
- **structure diverges** ⇒ the block was hand-edited / forked → severity `[consistency] enforce`.
- **structure matches, version differs** (incl. an unstamped older workspace) ⇒ the workspace is
  merely STALE → "run `aethel update`" at severity `[consistency] version_skew_enforce` (default
  `warn`, non-blocking). `aethel update` rewrites the block from the template, refreshing the
  stamp so the skew clears.
