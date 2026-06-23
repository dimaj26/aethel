# Aethel Context & Memory CLI Package

# The pip package version (kept in sync with pyproject [project].version by a test).
__version__ = "1.2.0"

# The managed `aethel-core` block version. Stamped into the shipped template and
# compared by `check_core_consistency` to tell a stale workspace ("run aethel
# update") from a hand-edited one. Bumped only when the core block's rules change,
# independently of package patch releases — so it is a separate constant.
CORE_VERSION = "1.4.0"
