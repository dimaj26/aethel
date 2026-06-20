# Changelog - Aethel Project

All notable changes to the Aethel boilerplate and tooling will be documented in this file.

## [Unreleased] - 2026-06-20
### Added
- Configurable workspace policy via optional `aethel.toml` (`[ontology]`, `[structure]`,
  `[language]`, `[sync]`): entity/relation types, required-header keywords with
  `enforce = error|warn|off`, per-artifact language policy, and spec-sync drift rules.
  Built-in defaults keep existing workspaces backward-compatible.
- Spec-sync drift guard: at commit time the pre-commit linter compares the staged file set and
  reminds (default `warn`) or blocks (`error`) when code is staged without updating a spec file
  (`memory.json`/`CONTEXT.md`/`AETHEL.md`). Inert outside a real commit (no repo / no HEAD /
  nothing staged); escape hatch `AETHEL_SKIP_SYNC=1`; also runnable as `--stage sync`. Route C in
  `AETHEL.md` is reworded as a mandatory post-step that this check enforces. Polygon scenario H.
- Core Consistency Contract (CC-1): a deployed workspace may EXTEND the Aethel core but must not
  contradict it (workspace ⊇ core; the core is not a copy of the workspace). Documented as a
  standard in `AETHEL.md` and enforced by `check_core_consistency`, which compares the workspace's
  `aethel-core` managed block against the installed library's core (`[consistency] enforce`,
  default `warn`; the source repo is exempt). Marker helpers moved to `aethel/markers.py`.
  Polygon scenario I.
- Pytest unit suite (`tests/test_config.py`, `tests/test_linter.py`, `tests/test_cli.py`) and a
  GitHub Actions CI workflow running ruff, mypy, pytest, the integration polygon, and a self-lint
  (dogfooding) on Python 3.11/3.12.
- Polygon scenarios F (custom `aethel.toml` ontology) and G (non-destructive update).

### Changed
- `aethel update` is now non-destructive: it refreshes only the managed block in `AETHEL.md`
  (delimited by `AETHEL:MANAGED` markers), merges `.agents` without deleting user-added files,
  and preserves recipe addenda and custom rules across upgrades.
- Required-header checks match heading keywords case-insensitively instead of pinning exact
  numbered titles, so workspaces may renumber/rename/localize sections.
- Default ontology broadened (added `Script`, `Config`, `Job`, `Migration`, `Library`, and
  relation types `configures`, `extends`, `implements`).
- Cycle detection rewritten as iterative DFS (no recursion limit on large graphs).

### Fixed
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
