---
name: linter-checks-artifacts
description: Artifact-stage linter checks — plan/checklist/report, [G-]/[C-]/[K-] tag resolution, {#slug} anchors, topic size.
---

# Linter Checks — Artifacts & Tags

The authoring-time checks `aethel/linter.py` runs over Route B artifacts and the tag convention.
Severities come from `aethel.config` / `aethel.toml`. Part of [linter checks](linter-checks.md).

## Artifact checks
All artifact checks read from the **artifact base** — `_artifact_base(workspace, cfg)` resolves to
the active session dir when `.aethel/CURRENT` exists, else the workspace root (backward-compatible;
see [session lifecycle](session-lifecycle.md)).
- `check_plan_file` — `implementation_plan.md` has the required H2s (User Review Required,
  Open Questions, Proposed Changes, Verification Plan) + optional language policy. Also resolves
  `[G-]` reference tags (the "Contextual Constraints" namespace convention from AETHEL.md §2)
  against this workspace's own `AETHEL.md`. A tag is a **stable slug** matched by identity against
  the valid `[G-]` slug set — §5 taboo titles (`N. **Title**` → slug) plus heading rule codes
  (`(GW-1)` → `gw-1`), derived mechanically so there is no second list to drift. The legacy
  positional `[G-Taboo<N>]` still resolves (by §5 number) but is reported as a **deprecation
  warning**, since it silently re-points when §5 is reordered. `[C-<slug>]` resolves the same way
  against **CONTEXT.md** (inline-link text slugs, link target file stems, and section-heading
  slugs) and `[K-<slug>]` against **`knowledge/**/*.md`** (each topic-file stem plus every heading
  inside it) — no positional legacy form, so resolved/unresolved only, each source failing open if
  absent. An unresolved tag (bad slug, or a legacy `[G-]` number absent from §5) is routed by
  `[plan] tag_reference_enforce` (library default `warn`; this repo promotes it to `error`, since
  it defines the convention). An unresolved slug now carries a difflib "did you mean `<slug>`?"
  suggestion (non-blocking — the tag still fails). A heading / taboo title may pin a short stable
  slug with an explicit **`{#slug}` anchor** (`## Long heading {#facades}` → `[K-facades]`); the
  anchor SUPPRESSES the heading-derived slug (one identity per heading), decoupling human heading
  text from machine tag identity (the `_source_slug` rule shared by every resolver).
- `check_tag_anchors` — workspace-level companion to the tag resolution above: an explicit `{#slug}`
  that is not slug-shaped (unwritable) is warned and falls back to the derived slug; two distinct
  headings collapsing to one slug is an **ambiguous-identity** warning (rather than a silent `set`
  merge). Both routed by `[plan] tag_reference_enforce`. Inspect the full slug set with `aethel tags list`.
- `check_topic_size` — warns when a `knowledge/**/*.md` topic exceeds `[knowledge] max_topic_tokens`
  (char/4 estimate; default `2500`, `0` disables). ON by default as a WARNING (`topic_size_enforce`):
  it gives §7's "~50–200 lines per topic" an enforceable number so context bloat is visible, without
  ever blocking a commit (char/4 is too coarse to block). Deliberately separate from
  `check_knowledge_index` (reachability). See `aethel size` for the full per-file token report.
- `check_checklist_file` — `task.md` structure (well-formed items, last item runs the linter) is
  validated on every lint; **completeness** (no open `[ ]`/`[/]`) is enforced only at the explicit
  `--stage checklist` finalization step (§2.8), via `require_complete`. The default/pre-commit lint
  passes `require_complete=False` so open items do not block incremental commits during a multi-chunk
  Route B task (§2 chunking, §4 milestone auto-commit); it surfaces the remaining count as a note.
- `check_report_file` — `walkthrough.md` has Changes made / What was tested / Validation results.
