---
name: linter-checks
description: The checks aethel.linter runs and how they are wired into stages.
---

# Linter Checks

`aethel/linter.py` validates a workspace. Severities are driven by `aethel.config` /
`aethel.toml`. The pre-commit hook runs the parameterless default; `--stage` selects one.

## Artifact checks
- `check_plan_file` — `implementation_plan.md` has the required H2s (User Review Required,
  Open Questions, Proposed Changes, Verification Plan) + optional language policy.
- `check_checklist_file` — `task.md` items are all complete and the last item runs the linter.
- `check_report_file` — `walkthrough.md` has Changes made / What was tested / Validation results.

## Knowledge-index integrity (`check_knowledge_index`)
Replaces the retired `memory.json` graph check. The index (default `CONTEXT.md`) must exist
and not be a placeholder; every relative **inline** link must resolve on disk (dead link =
error by default); every `*.md` under the knowledge dir must be reachable from the index
(orphan = warn by default). Anchors are stripped, `\`→`/` normalized, `http(s)`/`mailto`
skipped. Reference-style links/autolinks are intentionally NOT parsed, so the index must use
inline links only. Severities: `[knowledge] dead_link_enforce` / `orphan_enforce`.

## Workspace hygiene (`check_workspace_hygiene`)
Core files present (`AETHEL.md`, `CONTEXT.md`, `.gitattributes`), knowledge dir present,
required AETHEL/CONTEXT headers, no `LEGACY_*` or `AETHEL_ONBOARDING.md` left behind, and
core-consistency (see [core consistency](core-consistency.md)).

## Commit-time drift guards
- `check_spec_sync` — code staged without a spec file (`CONTEXT.md` / `AETHEL.md` /
  `knowledge/*`) warns or blocks (Route C). Inert outside a real commit; `AETHEL_SKIP_SYNC=1` escapes.
- `check_changelog_sync` — a staged rule file (`AETHEL.md`) without `CHANGELOG.md` warns/blocks.
