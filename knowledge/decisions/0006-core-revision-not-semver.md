---
name: adr-0006-core-revision-not-semver
description: The managed core block is versioned by an integer revision, not semver, to make it unconfusable with the package version.
---

# ADR 0006 — Core Block Uses an Integer Revision, Not Semver

- **Status:** Accepted
- **Date:** 2026-06-24

## Context
The managed `aethel-core` block carried a semver stamp `AETHEL:CORE-VERSION X.Y.Z`
(`aethel.CORE_VERSION`), introduced in ADR-adjacent work [1]. It was *intentionally* decoupled from
the pip package version (`aethel.__version__`), but shared its `X.Y.Z` shape — so the two were
visually indistinguishable. An AI operator conflated them (read core `1.5.0` as a package version
above what PyPI ships) — the exact "version chaos" this record resolves. A third axis, the
**published** package version on PyPI, had no representation in the repo at all, so the operator
guessed it.

## Decision
Version the core block by a **monotonic integer revision** `aethel.CORE_REVISION` (stamp
`<!-- AETHEL:CORE-REV N -->`), not semver. The block is a schema replaced wholesale by `aethel
update`, so it needs ordering only — and an integer can never be mistaken for the semver package
version. The package axes are untouched (`__version__` / `pyproject.version` stay semver). The
**PyPI/published** axis is surfaced live by `aethel doctor` (stdlib `urllib`, fail-soft to "unknown
(offline)"), not stored as a number that would go stale. The package was **not yet deployed to any
consumer workspace**, so this is a clean break with no dual-format reader — except a read-only
`has_legacy_core_version_stamp` guard so a stray old stamp is reported as "obsolete stamp", not a
silent skew.

The starting revision is **7**, the count of *declared* `CORE_VERSION` values across the project's
history (1.0.0 → 1.5.0 = 6 states) plus this change. Note the stamp physically existed only from
package **1.1.0** ([1]); the integer is a count of declared core states, NOT a claim that 1.0.0 was
stamped — the migration ledger (roadmap [9]) must not read "rev 1" as a stamped 1.0.0.

## Consequences
- Package semver and core revision are different shapes (`aethel-cli 1.4.0` vs `core-rev 7`) →
  conflation is structurally impossible; the core revision exceeding the package number is no longer
  alarming because they are different namespaces.
- `aethel doctor` is the single source of truth for all three axes; the AI reads it instead of
  guessing what is on PyPI.
- The migration ledger [9] keys naturally on integer revision transitions.
- Network in `doctor` is fail-soft and never affects the exit code; a malformed PyPI response is
  surfaced distinctly, not masked as offline (taboo 6).
- See [versioning](../versioning.md). Supersedes the semver stamp scheme from [1] / ADR 0005's
  `CORE_VERSION` bump.
