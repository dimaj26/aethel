"""`aethel eject` — sanctioned divergence for the managed `aethel-core` block (roadmap [10]).

Ejecting marks the block as intentionally hand-owned: `classify_core_state` reports a dedicated
`"ejected"` status (checked before the diverged/skew structural compare), so
`check_core_consistency`, `aethel doctor`, and `_update_aethel_md` all treat it as a deliberate
opt-out rather than a violation or something to silently overwrite.
"""

import argparse

import pytest

from aethel.linter import _installed_core_block, check_core_consistency, classify_core_state
from aethel.markers import eject_block, is_ejected, uneject_block


def _write_core(tmp_path, core_text):
    (tmp_path / "AETHEL.md").write_text(core_text, encoding="utf-8")


def _tampered_core():
    core = _installed_core_block()
    assert core is not None and "Decision Routing" in core
    return core.replace("Decision Routing", "Tampered Routing", 1)


# --- markers.py -------------------------------------------------------------

def test_eject_block_inserts_marker_and_is_idempotent():
    core = _installed_core_block()
    content = "# Project\n\n" + core + "\n"
    new_content, changed = eject_block(content, "aethel-core", "2026-06-23")
    assert changed
    assert is_ejected(new_content, "aethel-core")

    again, changed_again = eject_block(new_content, "aethel-core", "2026-06-23")
    assert not changed_again
    assert again == new_content


def test_eject_block_missing_block_is_noop():
    content = "# No managed block here\n"
    new_content, changed = eject_block(content, "aethel-core", "2026-06-23")
    assert not changed
    assert new_content == content


def test_uneject_restores_unmarked_block():
    core = _installed_core_block()
    content = "# Project\n\n" + core + "\n"
    ejected, _ = eject_block(content, "aethel-core", "2026-06-23")
    restored, changed = uneject_block(ejected, "aethel-core")
    assert changed
    assert not is_ejected(restored, "aethel-core")


def test_uneject_noop_when_not_ejected():
    core = _installed_core_block()
    content = "# Project\n\n" + core + "\n"
    restored, changed = uneject_block(content, "aethel-core")
    assert not changed
    assert restored == content


# --- linter.classify_core_state / check_core_consistency -------------------

def test_classify_ejected_overrides_diverged(tmp_path):
    tampered = _tampered_core()
    ejected, changed = eject_block(tampered, "aethel-core", "2026-06-23")
    assert changed
    _write_core(tmp_path, ejected + "\n")
    state = classify_core_state(str(tmp_path))
    assert state.status == "ejected"


def test_check_core_consistency_ejected_never_blocks(tmp_path):
    from aethel.config import AethelConfig

    tampered = _tampered_core()
    ejected, _ = eject_block(tampered, "aethel-core", "2026-06-23")
    _write_core(tmp_path, ejected + "\n")
    cfg = AethelConfig(consistency_enforce="error", version_skew_enforce="error")
    assert check_core_consistency(str(tmp_path), cfg) is True


def test_uneject_then_classify_restores_diverged(tmp_path):
    tampered = _tampered_core()
    ejected, _ = eject_block(tampered, "aethel-core", "2026-06-23")
    restored, _ = uneject_block(ejected, "aethel-core")
    _write_core(tmp_path, restored + "\n")
    assert classify_core_state(str(tmp_path)).status == "diverged"


# --- cli.py ------------------------------------------------------------------

def _ns(tmp_path, undo=False):
    return argparse.Namespace(path=str(tmp_path), undo=undo)


def test_cmd_eject_sets_marker(tmp_path, capsys):
    from aethel.cli import cmd_eject

    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    cmd_eject(_ns(tmp_path))
    state = classify_core_state(str(tmp_path))
    assert state.status == "ejected"
    assert "ejected" in capsys.readouterr().out.lower()


def test_cmd_eject_is_idempotent(tmp_path, capsys):
    from aethel.cli import cmd_eject

    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    cmd_eject(_ns(tmp_path))
    before = (tmp_path / "AETHEL.md").read_text(encoding="utf-8")
    cmd_eject(_ns(tmp_path))
    after = (tmp_path / "AETHEL.md").read_text(encoding="utf-8")
    assert before == after
    assert "already ejected" in capsys.readouterr().out.lower()


def test_cmd_eject_undo_restores_management(tmp_path, capsys):
    from aethel.cli import cmd_eject

    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    cmd_eject(_ns(tmp_path))
    capsys.readouterr()
    cmd_eject(_ns(tmp_path, undo=True))
    assert classify_core_state(str(tmp_path)).status == "consistent"
    assert "undo" in capsys.readouterr().out.lower() or "re-attach" in capsys.readouterr().out.lower()


def test_cmd_eject_undo_noop_when_not_ejected(tmp_path, capsys):
    from aethel.cli import cmd_eject

    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    cmd_eject(_ns(tmp_path, undo=True))
    assert "nothing to undo" in capsys.readouterr().out.lower()


def test_cmd_eject_no_aethel_md_exits_one(tmp_path):
    from aethel.cli import cmd_eject

    with pytest.raises(SystemExit) as exc:
        cmd_eject(_ns(tmp_path))
    assert exc.value.code == 1


# --- cli._update_aethel_md skip on ejected ----------------------------------

def test_update_skips_ejected_block(tmp_path, capsys):
    from aethel.cli import _update_aethel_md

    tampered = _tampered_core()
    ejected, _ = eject_block(tampered, "aethel-core", "2026-06-23")
    content = "# Project\n\n" + ejected + "\n"
    _write_core(tmp_path, content)

    _update_aethel_md(str(tmp_path))

    after = (tmp_path / "AETHEL.md").read_text(encoding="utf-8")
    assert after == content
    assert "ejected" in capsys.readouterr().out.lower()
    assert not list(tmp_path.glob("AETHEL.md.bak.*"))


# --- doctor ------------------------------------------------------------------

def test_doctor_ejected_exits_zero(tmp_path, monkeypatch, capsys):
    import aethel.cli as cli

    tampered = _tampered_core()
    ejected, _ = eject_block(tampered, "aethel-core", "2026-06-23")
    _write_core(tmp_path, "# Project\n\n" + ejected + "\n")

    monkeypatch.setattr(cli, "resolve_hook_python", lambda _p: "python")
    monkeypatch.setattr(cli, "probe_import", lambda _exe: (True, ""))

    with pytest.raises(SystemExit) as exc:
        cli.cmd_doctor(argparse.Namespace(path=str(tmp_path)))
    out = capsys.readouterr().out.lower()
    assert exc.value.code == 0
    assert "ejected" in out
