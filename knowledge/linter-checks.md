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
`aethel lint .`), falling back to a venv interpreter running the `prompt_linter.py` wrapper. If
`aethel` is not importable, the wrapper **warns and skips (exit 0)** instead of blocking the commit —
a missing install is not a rule violation. Strict mode `AETHEL_REQUIRE=1` makes it a hard `exit 1`
(mirror of `AETHEL_SKIP_SYNC`). Real lint violations always exit 1. See
[ADR 0003](decisions/0003-hook-degradation.md).

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
  it defines the convention).
- `check_checklist_file` — `task.md` items are all complete and the last item runs the linter.
- `check_report_file` — `walkthrough.md` has Changes made / What was tested / Validation results.

## Knowledge-index integrity (`check_knowledge_index`)
Replaces the retired `memory.json` graph check. The index (default `CONTEXT.md`) must exist
and not be a placeholder; every relative **inline** link in the index must resolve on disk
(dead link = error by default). Every `*.md` under the knowledge dir must be **reachable by
navigation from the index — transitively** (`index → topic → topic → ADR`), computed by a
cycle-safe walk (`_reachable_md`) that follows inline links in every reachable file, resolving
each relative to the *linking* file's directory. An unreachable file is unsurfaced (dead
knowledge), flagged at `[knowledge] orphan_enforce` (warn by default). Transitive reachability
keeps the index curated (AETHEL.md §7): ADRs are surfaced via the ledger
[knowledge/decisions/README.md](decisions/README.md), not one link per ADR in the top index
(see [ADR 0002](decisions/0002-navigable-reachability.md)). Anchors are stripped, `\`→`/`
normalized, `http(s)`/`mailto` skipped; reference-style links/autolinks are NOT parsed, so use
inline links only. Each index link to a knowledge file should also carry an **annotation**
(`[text](target) — note`) — reachability surfaces a file, the note is what makes an agent open the
*right* one; an unannotated knowledge link is flagged at `[knowledge] annotation_enforce` (warn by
default; only index links whose target resolves under the knowledge dir are checked, so prose and
external links are never flagged). Severities: `[knowledge] dead_link_enforce` / `orphan_enforce` /
`annotation_enforce`.

## Agent registry integrity (`check_agent_registry`)
Backs **Route D** (AETHEL.md §1): analysis is delegated only to an agent listed in the closed
registry (default `knowledge/agents.md`, `[agents] registry`). Skill-agents live under a gitignored
`.agents/` tree (`[agents] dir`), so discovery walks that tree **directly** (`_discover_skill_files`,
`os.walk` — not a git-tracked listing), keeping gitignored agents visible (the [discovery-discipline]
lesson, roadmap [18]). Bidirectional:
- a registry inline link naming a `SKILL.md` that does not resolve on disk → dangling link,
  `[agents] dangling_enforce` (library default **error**);
- a `SKILL.md` discovered under `.agents/` but absent from the registry → orphan, `[agents]
  orphan_enforce` (library default **warn**; this repo promotes both to **error**).

Fails **open**: with neither a registry nor any agent there is nothing to validate (a fresh
workspace stays green). Runs in `run_linter` and the parameterless `main` path, next to
`check_knowledge_index`. The registry itself is a `knowledge/*.md` topic, so it is also subject to
the knowledge-index reachability/annotation checks. See [ADR 0007](decisions/0007-agent-registry-route-d.md).

## Workspace hygiene (`check_workspace_hygiene`)
Core files present (`AETHEL.md`, `CONTEXT.md`, `.gitattributes`), knowledge dir present,
required AETHEL/CONTEXT headers, no `LEGACY_*` or `AETHEL_ONBOARDING.md` left behind, and
core-consistency (see [core consistency](core-consistency.md)). `check_core_consistency` strips
the integer `AETHEL:CORE-REV` stamp before comparing structure, so it distinguishes a hand-edited
block (divergence, `[consistency] enforce`) from a merely stale one (revision skew, or the obsolete
semver stamp → "run `aethel update`", `[consistency] version_skew_enforce`, default warn/non-blocking).

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
