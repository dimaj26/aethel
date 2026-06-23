"""`aethel version` / `aethel doctor` and the shared core-state classifier.

`doctor` reuses the linter's core-consistency classification (roadmap [7]); these
tests pin both the pure `classify_core_state` seam and the two CLI commands. The
workspace fixtures mirror `tests/test_linter.py`: an `AETHEL.md` whose `aethel-core`
block is identical to / tampered from / absent vs the installed library core.
"""

import aethel
from aethel.linter import _installed_core_block, classify_core_state


def _write_core(tmp_path, core_text):
    (tmp_path / "AETHEL.md").write_text(core_text, encoding="utf-8")


def test_version_command_prints_versions(capsys):
    from aethel.cli import cmd_version
    cmd_version(None)
    out = capsys.readouterr().out
    assert aethel.__version__ in out
    assert aethel.CORE_VERSION in out


def test_classify_consistent(tmp_path):
    core = _installed_core_block()
    assert core is not None
    _write_core(tmp_path, "# Project\n\n" + core + "\n\n- custom rule\n")
    state = classify_core_state(str(tmp_path))
    assert state.status == "consistent"
    assert state.ws_version == state.lib_version


def test_classify_skew(tmp_path):
    from aethel.markers import parse_core_version
    core = _installed_core_block()
    assert core is not None
    lib_version = parse_core_version(core)
    assert lib_version is not None
    stale = core.replace(lib_version, "0.0.1", 1)
    _write_core(tmp_path, stale + "\n")
    state = classify_core_state(str(tmp_path))
    assert state.status == "skew"
    assert state.ws_version == "0.0.1"
    assert state.lib_version == lib_version


def test_classify_diverged(tmp_path):
    core = _installed_core_block()
    assert core is not None and "Decision Routing" in core
    _write_core(tmp_path, core.replace("Decision Routing", "Tampered Routing", 1))
    assert classify_core_state(str(tmp_path)).status == "diverged"


def test_classify_no_block(tmp_path):
    _write_core(tmp_path, "# Forked file, no managed markers\n")
    assert classify_core_state(str(tmp_path)).status == "no_block"


def test_classify_no_workspace(tmp_path):
    assert classify_core_state(str(tmp_path)).status == "no_workspace"


def _run_doctor(tmp_path, monkeypatch, *, importable=True):
    """Invoke cmd_doctor with the import probe stubbed; return its SystemExit code."""
    import aethel.cli as cli
    monkeypatch.setattr(cli, "resolve_hook_python", lambda _p: "python")
    monkeypatch.setattr(
        cli, "probe_import",
        lambda _exe: (importable, "" if importable else "ModuleNotFoundError: No module named 'aethel'"),
    )
    import pytest
    with pytest.raises(SystemExit) as exc:
        cli.cmd_doctor(_ns(tmp_path))
    return exc.value.code


def _ns(tmp_path):
    import argparse
    return argparse.Namespace(path=str(tmp_path))


def test_doctor_skew_exits_zero(tmp_path, monkeypatch, capsys):
    from aethel.markers import parse_core_version
    core = _installed_core_block()
    lib_version = parse_core_version(core)
    _write_core(tmp_path, core.replace(lib_version, "0.0.1", 1) + "\n")
    code = _run_doctor(tmp_path, monkeypatch)
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "skew" in out


def test_doctor_diverged_exits_one(tmp_path, monkeypatch):
    core = _installed_core_block()
    _write_core(tmp_path, core.replace("Decision Routing", "Tampered Routing", 1))
    assert _run_doctor(tmp_path, monkeypatch) == 1


def test_doctor_consistent_exits_zero(tmp_path, monkeypatch):
    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    assert _run_doctor(tmp_path, monkeypatch) == 0


def test_doctor_import_failure_exits_one(tmp_path, monkeypatch):
    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    assert _run_doctor(tmp_path, monkeypatch, importable=False) == 1
