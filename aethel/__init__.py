# Aethel Context & Memory CLI Package

# The pip package version (kept in sync with pyproject [project].version by a test).
__version__ = "1.6.0"

# The managed `aethel-core` block revision: a MONOTONIC INTEGER, not a semver string.
# The block is a schema replaced wholesale by `aethel update`, so it needs ordering
# only — and an integer can never be confused with the semver package `__version__`
# (the conflation this scheme exists to prevent). Stamped into the shipped template as
# `AETHEL:CORE-REV N` and compared by `check_core_consistency` to tell a stale workspace
# ("run aethel update") from a hand-edited one. Bumped whenever the core block changes,
# independently of package releases. See knowledge/versioning.md and ADR 0006.
CORE_REVISION: int = 9
