---
name: linter-checks
description: The checks aethel.linter runs and how they are wired into stages.
---

# Linter Checks

`aethel/linter.py` validates a workspace. Severities are driven by `aethel.config` /
`aethel.toml`. The pre-commit hook runs the parameterless default; `--stage` selects one.

## Artifact checks
All artifact checks read from the **artifact base** — `_artifact_base(workspace, cfg)` resolves to
the active session dir when `.aethel/CURRENT` exists, else the workspace root (backward-compatible;
see [session lifecycle](session-lifecycle.md)).
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
core-consistency (see [core consistency](core-consistency.md)). `check_core_consistency` strips
the `AETHEL:CORE-VERSION` stamp before comparing structure, so it distinguishes a hand-edited
block (divergence, `[consistency] enforce`) from a merely stale one (version skew → "run `aethel
update`", `[consistency] version_skew_enforce`, default warn/non-blocking).

## Commit-time drift guards
All three are inert outside a real commit (no repo / no HEAD / nothing staged) and share the
`AETHEL_SKIP_SYNC=1` escape hatch; each checks only the *pairing*, never the content.
- `check_spec_sync` — code staged without a spec file (`CONTEXT.md` / `AETHEL.md` /
  `knowledge/*`) warns or blocks (Route C).
- `check_changelog_sync` — a staged rule file (`AETHEL.md`) without `CHANGELOG.md` warns/blocks.
- `check_walkthrough_sync` — when a Route B task is active (`task.md` present in the artifact base)
  AND the commit stages code, the base's session report `walkthrough.md` must exist and carry the
  required sections (`Summary` / `Changes made` / `What was tested` / `Validation results`, from
  `[report] sections`); missing/malformed → `[report] require_walkthrough` (default `error`).
  `walkthrough.md` is a per-session local artifact (gitignored). The guard stays **PURE** — it
  never writes the session manifest; marking a session done is `aethel done`'s job (see
  [session lifecycle](session-lifecycle.md)). Report language is governed by `[language]
  report_lang` and routed by severity `[language] report_lang_enforce` (**default `error`** in
  core — a mandated language must BLOCK, not merely warn; gated behind `report_lang != "any"`, so
  workspaces that set no language are unaffected). An `error`-level language mismatch goes into
  `check_report_file`'s `errors`, so it blocks both `aethel done` and the commit-time
  `check_walkthrough_sync` guard, which escalate only on errors. Structure validation also lives in
  `check_report_file` (reachable via `--stage report`).
