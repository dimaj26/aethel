# Changelog - Aethel Project

All notable changes to the Aethel boilerplate and tooling will be documented in this file.

## [Unreleased] - 2026-06-23
### Changed
- **Report-language policy now has teeth (it can BLOCK).** Previously `[language] report_lang`
  produced only a warning, so a project-mandated report language (e.g. `report_lang = "ru"`) could
  never stop `aethel done` or a commit — both escalate only on errors. It was the lone policy
  without a severity lever. Added `[language] report_lang_enforce` (`error|warn|off`), **default
  `error` in core** (gated behind `report_lang != "any"`, so workspaces that set no language are
  unaffected); `check_report_file` now routes the language finding by that severity, and the message
  cites its source. As a result an English `walkthrough.md` under `report_lang = "ru"` is a blocking
  error at `aethel done` and at the commit-time `check_walkthrough_sync` guard. This repo's
  `aethel.toml` also promotes `[sync] enforce` and `require_changelog` to `error` (it is the
  canonical protocol source). New `tests/test_report_lang.py`.
### Added
- **`aethel version` / `aethel doctor` commands.** `aethel version` prints the package + managed-core
  versions. `aethel doctor` diagnoses a workspace — package/library/workspace core versions, the
  core-block state (consistent / skew / diverged / no-block / source), and whether `aethel` is
  importable by the pre-commit hook's interpreter (resolved the same way the hook picks it). It
  exits `1` on a hard problem (core block diverged/forked, or `aethel` not importable), `0`
  otherwise (a version skew is a warn). The skew/divergence classification is now a pure seam,
  `classify_core_state() -> CoreState`, shared by `check_core_consistency` and `doctor` so they
  never disagree. New `tests/test_doctor.py`.
- **Core version stamping + version-skew detection.** The managed `aethel-core` block now carries
  a `<!-- AETHEL:CORE-VERSION X.Y.Z -->` stamp (shipped in the template, owned by `aethel update`).
  `check_core_consistency` strips it before the structural compare, so it distinguishes a
  hand-edited block (divergence, `[consistency] enforce`) from a merely stale one (version skew →
  "run `aethel update`", new `[consistency] version_skew_enforce`, default `warn`/non-blocking).
  New `aethel.CORE_VERSION` (the managed-block version, distinct from the pip package
  `__version__`) with `markers.parse_core_version`/`strip_core_version`. Both version pairs are
  guarded by `tests/test_version.py` (template stamp == `CORE_VERSION`; `__version__` ==
  `pyproject [project].version`). Package + core bumped 1.0.0 → 1.1.0. Polygon scenario I extended
  with the skew sub-case (downgrade stamp → warn; `aethel update` → clean). Unblocks the
  version-skew messaging in the install-story and `aethel doctor` roadmap items.
- **Per-session Route B working directory + reconcile-on-start lifecycle.** Route B artifacts
  (`implementation_plan.md` / `task.md` / `walkthrough.md`) now live in a per-session directory
  under a gitignored `.aethel/` tree (`.aethel/sessions/<run-id>/`), not at the repo root, removing
  the mismatched-fixed-name and interrupted-session-pollution failure modes. New `aethel/session.py`
  (stdlib only): sortable UTC run-ids, `start_session` (reconcile prior + open new), `reconcile`
  (validated → `.aethel/archive/<id>/`, interrupted → `.aethel/archive/_incomplete/<id>/`),
  `mark_validated`, and a `session.json` manifest (`status ∈ active|validated`). New CLI verbs
  `aethel start [slug]` (opens a session, reconciles/archives the previous) and `aethel done`
  (re-validates the report via `check_report_file`, then marks `status=validated`; refuses on a
  bad/absent report). Completion is an explicit verb, not a guard side-effect — the walkthrough
  guard stays PURE. The linter gains `_artifact_base` (active session dir if `.aethel/CURRENT`
  resolves, else workspace root); `check_plan_file` / `check_checklist_file` / `check_report_file`
  / `check_plan_stage` and `check_walkthrough_sync` all read from that base, so workspaces that
  never run `aethel start` (fresh clone, clean CI) behave exactly as before. `aethel init` /
  `aethel update` gitignore `.aethel/` (`ensure_aethel_gitignored`); `[session] aethel_dir` config
  relocates the tree. Route B in the core block gains step 1 (`aethel start`) and step 10
  (`aethel done`); new `knowledge/session-lifecycle.md`. Polygon scenario M.
- **Mandatory walkthrough report (`walkthrough.md`) + commit-time guard.** A Route B task now
  must produce a session report with a defined structure (`Summary` / `Changes made` /
  `What was tested` / `Validation results`). New `check_walkthrough_sync` is a sibling of the
  spec-sync / changelog-sync guards: inert outside a real commit, it fires only when a Route B
  task is active (`task.md` present) AND the commit stages code, then requires a well-formed
  `walkthrough.md` at `[report] require_walkthrough` (default `error`); same `AETHEL_SKIP_SYNC=1`
  escape hatch. Added `[report]` config (`require_walkthrough`, `sections`); `check_report_file`
  now drives required sections from config (incl. `Summary`) and runs in the default lint +
  `--stage sync`. The rule is in the managed core block (Route B step 8 + a structure note);
  `walkthrough.md` is a per-session local artifact (gitignored). This repo sets
  `report_lang = "ru"` (warn) in its own `aethel.toml` as a dev-env preference (not core).
  Polygon scenario L.

### Changed
- **Specification architecture migrated from the Memory MCP graph to a provider-agnostic
  Markdown layer.** Retired `memory.json`, the Memory MCP server wiring, the ontology
  (`[ontology]` entity/relation types), and `check_memory_integrity`. Structured knowledge is
  now a curated `llms.txt`-style index (`CONTEXT.md`: H1 + summary + annotated inline links)
  pointing at a `knowledge/` tree of atomic topic files, with decisions as append-only ADRs
  under `knowledge/decisions/`. A new universal `AGENTS.md` entry point is shipped (with
  `CLAUDE.md`/`GEMINI.md` as thin stubs that name it); all redirect to `AETHEL.md`.
- **Linter:** `check_memory_integrity` (+ `_has_cycle`) replaced by `check_knowledge_index` —
  the index must exist and be non-placeholder, every relative inline link must resolve on disk
  (dead link = error), and every `knowledge/*.md` topic file must be reachable from the index
  (orphan = warn). Anchors stripped, `\`→`/` normalized, `http(s)`/`mailto` skipped; inline
  links only. Severities configurable via `[knowledge] dead_link_enforce`/`orphan_enforce`.
  Workspace hygiene drops the `memory.json binary` `.gitattributes` rule and checks the
  knowledge dir; spec-sync `spec_files` default is now `CONTEXT.md`/`AETHEL.md`/`knowledge/*`.
- **CLI:** `init` scaffolds `AGENTS.md`, the index, and a `knowledge/` seed (no `memory.json`);
  `update` ships `AGENTS.md`; `ensure_gitattributes` writes `* text=auto`.
- **Route C / Taboos** reworded to the knowledge index: Route C now updates `CONTEXT.md` +
  `knowledge/*.md` (+ ADRs); Taboos #1 (no manual `memory.json` edits) and #7 (binary masking)
  removed, #2 repointed to the index, renumbered; added an AETHEL.md "Specification
  Architecture" section. The repo migrated ITSELF (dogfood): `memory.json` removed,
  `knowledge/` + `CONTEXT.md` index added, `.gitattributes` → `* text=auto`.
- **Templates/onboarding/skill:** removed `memory.json.template`; rewrote the onboarding guide
  and the proposal-analysis skill to reference the knowledge index instead of the MCP graph.
- **Tests:** removed memory-integrity/cycle/ontology tests; added knowledge-index unit tests,
  `[knowledge]` config tests, and an init-scaffolding test. Polygon: dropped the graph from
  Scenario C, repurposed Scenario D as a 150-topic index scale test, made Scenario F
  structure-only, and added **Scenario K** (dead link = error, orphan = warn, promote-to-error).

### Added (earlier this cycle)
- Configurable workspace policy via optional `aethel.toml` (`[ontology]`, `[structure]`,
  `[language]`, `[sync]`): entity/relation types, required-header keywords with
  `enforce = error|warn|off`, per-artifact language policy, and spec-sync drift rules.
  Built-in defaults keep existing workspaces backward-compatible.
- Spec-sync drift guard: at commit time the pre-commit linter compares the staged file set and
  reminds (default `warn`) or blocks (`error`) when code is staged without updating a spec file
  (`memory.json`/`CONTEXT.md`/`AETHEL.md`). Inert outside a real commit (no repo / no HEAD /
  nothing staged); escape hatch `AETHEL_SKIP_SYNC=1`; also runnable as `--stage sync`. Route C in
  `AETHEL.md` is reworded as a mandatory post-step that this check enforces. Polygon scenario H.
- Changelog-sync drift guard (`check_changelog_sync`): a scoped sibling of the spec-sync guard that
  pairs rule changes with the release log. When a `[sync] rule_files` path (default `AETHEL.md`) is
  staged but `[sync] changelog_file` (default `CHANGELOG.md`) is not, the linter reminds
  (default `require_changelog = "warn"`) or blocks (`"error"`). Closes the gap where editing a
  governance rule and staging only `AETHEL.md` satisfied spec-sync while the changelog silently
  lagged. Same inert-outside-a-commit behavior and `AETHEL_SKIP_SYNC=1` escape hatch; runs in the
  default lint and `--stage sync`. Polygon scenario J.
- Core Consistency Contract (CC-1): a deployed workspace may EXTEND the Aethel core but must not
  contradict it (workspace ⊇ core; the core is not a copy of the workspace). Enforced by
  `check_core_consistency`, which compares the workspace's `aethel-core` managed block against the
  installed library's core (`[consistency] enforce`, default `warn`; the source repo is exempt).
  The deployed template carries only the operational guidance (don't edit the block; rules go
  below it; on conflict the core wins; run `aethel update` on divergence) folded into the
  managed-block note — it is not a maintainer essay. The full directional/maintainer framing of
  CC-1 lives only in the root `AETHEL.md`. Marker helpers moved to `aethel/markers.py`.
  Polygon scenario I.
- Orchestrator rules in `AETHEL.md`: GW-1 local milestone auto-commit is now the default behavior
  (commit at coherent milestones only, lint green first, code + specs staged together, imperative
  message, no auto-push); and a "one thesis, one agent" rule (delegate one sub-agent per distinct
  question/analysis, never bundle). Both live in the managed `aethel-core` block.
- Pytest unit suite (`tests/test_config.py`, `tests/test_linter.py`, `tests/test_cli.py`) and a
  GitHub Actions CI workflow running ruff, mypy, pytest, the integration polygon, and a self-lint
  (dogfooding) on Python 3.11/3.12.
- Polygon scenarios F (custom `aethel.toml` ontology) and G (non-destructive update).

### Changed (earlier this cycle)
- Added a "Delegate only when it pays" rule to Response Rules in the `aethel-core` block: a
  sub-agent starts cold and re-derives context already held, so spawn one only for broad or
  independent analysis (large fan-out, heavy cross-file review) and analyze inline when the
  context is already loaded and the question is simple. Complements "one thesis, one agent".
- Route B step 6 in the `aethel-core` block now states that `task.md` is authored up front
  as a complete ordered checklist derived from the plan's Proposed Changes (then executed in
  3–5 step chunks and edited as reality dictates), rather than created and filled lazily —
  codifying the intended plan (WHAT/WHY) vs checklist (ordered HOW) split.
- Recipes are now discovered dynamically by `discover_recipes()` scanning
  `aethel/templates/recipes/*` instead of a hard-coded `RECIPES` dict + argparse `choices`.
  A recipe is any sub-directory with an `AETHEL_RECIPE_ADDENDUM.md` whose managed-block marker
  yields the sentinel (parsed via the shared `parse_block_id` helper); `configs` are its
  top-level files. Adding a recipe needs no Python edit. An unknown `--recipe` is validated at
  runtime (`exit 2`, lists discovered recipes); a malformed recipe folder (missing or
  marker-less addendum) raises `RecipeError` (fail-fast); an empty folder warns and is skipped.
  `_installed_recipes` is re-based on sentinel presence in `AETHEL.md` (not config-file
  existence), and the `aethel update` legacy-rewrite path reads that sentinel from the original
  content before rewriting. Removed the committed `templates/recipes/python/.ruff_cache/` and
  excluded cache dirs from git and the sdist/wheel (`MANIFEST.in`). Polygon scenario A extended.
- De-projected the library: removed the hard-coded Teñir-Too Cyrillic whitelist and Russian
  phrases from the linter, and the "respond in Russian" / Russian verdict labels from the shipped
  proposal-analysis skill. Language defaults are now neutral (`artifact_lang`/`report_lang` default
  to `"any"` — no check unless configured); allowed words for `"en"` mode move to a configurable
  `[language] whitelist` (default empty).
- `aethel update` is now non-destructive: it refreshes only the managed block in `AETHEL.md`
  (delimited by `AETHEL:MANAGED` markers), merges `.agents` without deleting user-added files,
  and preserves recipe addenda and custom rules across upgrades.
- Required-header checks match heading keywords case-insensitively instead of pinning exact
  numbered titles, so workspaces may renumber/rename/localize sections.
- Default ontology broadened (added `Script`, `Config`, `Job`, `Migration`, `Library`, and
  relation types `configures`, `extends`, `implements`).
- Cycle detection rewritten as iterative DFS (no recursion limit on large graphs).

### Fixed (earlier this cycle)
- `.gitattributes` append path now writes `memory.json binary` (implies `-diff`) instead of
  `merge=binary`, which did not suppress diffs.
- Declared `requires-python = ">=3.11"` (was a false `>=3.8`); consolidated packaging into
  `pyproject.toml` and removed the duplicate `setup.py`.
- Repository now passes its own linter (added root `AETHEL.md`; `GEMINI.md`/`CLAUDE.md` are
  redirect stubs).

## [1.0.0] - 2026-06-19
### Added
- Core workspace configuration: `.gitattributes` to mask database diffs.
- Orchestrator rulebook: `GEMINI.md` defining decision routing and critical coding taboos.
- Compact technical context: `CONTEXT.md` providing references and database schemas.
- Starter database: `memory.json` in JSON Lines format with starting framework entities.
- Integrations guide: `README.md` containing detailed setup configs for Cursor and Claude Desktop.
- Integrity tooling: `prompt_linter.py` script for local validation of plan files and knowledge graph integrity.
