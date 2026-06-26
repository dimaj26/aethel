"""#8: the managed core block is a KERNEL — the verbose session mechanics are de-duplicated out
(they live canonically in knowledge/session-lifecycle.md, already indexed in CONTEXT.md). The
kernel keeps the Route B happy-path, the session verbs, and the two behavioral cautions a deployed
agent cannot re-derive from `--help`; it drops the selection-precedence and archive-path internals.
"""

import os

from aethel.markers import extract_managed_block

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_TEMPLATE = os.path.join(_REPO_ROOT, "aethel", "templates", "AETHEL.md.template")


def _core_block() -> str:
    with open(_TEMPLATE, "r", encoding="utf-8") as f:
        block = extract_managed_block(f.read(), "aethel-core")
    assert block is not None
    return block


def test_core_drops_session_detail():
    """The moved-to-topic internals are gone from the kernel: the selection-precedence string
    and the _incomplete archive path now live only in session-lifecycle.md."""
    block = _core_block()
    assert "AETHEL_SESSION" not in block, "selection-precedence detail should move to the topic"
    assert "_incomplete" not in block, "abandon archive-path detail should move to the topic"


def test_core_keeps_happy_path_and_cautions():
    """Over-trim guard: the kernel must still let a deployed agent run Route B correctly — the
    verbs plus BOTH cautions (start opens a NEW session; resume-vs-new via switch)."""
    block = _core_block()
    for verb in ("aethel start", "aethel done", "aethel abandon"):
        assert verb in block, f"kernel lost the Route B verb: {verb}"
    assert "aethel switch" in block, "kernel lost the resume-vs-new caution (CC-1 invariant)"
    # wrap-insensitive: the "start opens a NEW session, prior stays LIVE" caution.
    assert "NEW" in block and "LIVE" in block, "kernel lost the 'start opens a NEW session' caution"


def test_core_block_shrank_below_prior_size():
    """De-dup must actually reduce the always-loaded surface (prior block was ~15,344 chars)."""
    assert len(_core_block()) < 15000
