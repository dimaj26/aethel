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
