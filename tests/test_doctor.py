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
    assert "core-rev" in out
    assert str(aethel.CORE_REVISION) in out


def test_classify_consistent(tmp_path):
    core = _installed_core_block()
    assert core is not None
    _write_core(tmp_path, "# Project\n\n" + core + "\n\n- custom rule\n")
    state = classify_core_state(str(tmp_path))
    assert state.status == "consistent"
    assert state.ws_rev == state.lib_rev


def test_classify_skew(tmp_path):
    from aethel.markers import parse_core_revision
    core = _installed_core_block()
    assert core is not None
    lib_rev = parse_core_revision(core)
    assert lib_rev is not None
    stale = core.replace(f"CORE-REV {lib_rev}", "CORE-REV 1", 1)
    _write_core(tmp_path, stale + "\n")
    state = classify_core_state(str(tmp_path))
    assert state.status == "skew"
    assert state.ws_rev == 1
    assert state.lib_rev == lib_rev


def test_classify_obsolete_stamp(tmp_path):
    """A block still carrying the superseded semver `CORE-VERSION` stamp is flagged distinctly,
    not as a silent unstamped skew."""
    from aethel.markers import parse_core_revision
    core = _installed_core_block()
    lib_rev = parse_core_revision(core)
    legacy = core.replace(f"AETHEL:CORE-REV {lib_rev}", "AETHEL:CORE-VERSION 1.5.0", 1)
    _write_core(tmp_path, legacy + "\n")
    state = classify_core_state(str(tmp_path))
    assert state.status == "obsolete_stamp"
    assert state.ws_rev is None


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


def _run_doctor(tmp_path, monkeypatch, *, importable=True, pypi=lambda _n: "9.9.9"):
    """Invoke cmd_doctor with the import probe AND the PyPI lookup stubbed (no network in
    unit tests); return its SystemExit code."""
    import aethel.cli as cli
    monkeypatch.setattr(cli, "resolve_hook_python", lambda _p: "python")
    monkeypatch.setattr(
        cli, "probe_import",
        lambda _exe: (importable, "" if importable else "ModuleNotFoundError: No module named 'aethel'"),
    )
    monkeypatch.setattr(cli, "_pypi_latest", pypi)
    import pytest
    with pytest.raises(SystemExit) as exc:
        cli.cmd_doctor(_ns(tmp_path))
    return exc.value.code


def _ns(tmp_path):
    import argparse
    return argparse.Namespace(path=str(tmp_path))


def test_doctor_skew_exits_zero(tmp_path, monkeypatch, capsys):
    from aethel.markers import parse_core_revision
    core = _installed_core_block()
    lib_rev = parse_core_revision(core)
    _write_core(tmp_path, core.replace(f"CORE-REV {lib_rev}", "CORE-REV 1", 1) + "\n")
    code = _run_doctor(tmp_path, monkeypatch)
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "skew" in out


def test_doctor_shows_three_axes(tmp_path, monkeypatch, capsys):
    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    _run_doctor(tmp_path, monkeypatch, pypi=lambda _n: "1.2.0")
    out = capsys.readouterr().out
    assert "package (dev)" in out and aethel.__version__ in out
    assert "package (PyPI)" in out and "1.2.0" in out
    assert "core-rev" in out and str(aethel.CORE_REVISION) in out


def test_doctor_pypi_offline_is_failsoft(tmp_path, monkeypatch, capsys):
    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    code = _run_doctor(tmp_path, monkeypatch, pypi=lambda _n: None)  # offline
    out = capsys.readouterr().out.lower()
    assert code == 0  # network miss never affects exit code
    assert "offline" in out


def test_doctor_pypi_malformed_not_masked_as_offline(tmp_path, monkeypatch, capsys):
    def boom(_n):
        raise KeyError("info")
    core = _installed_core_block()
    _write_core(tmp_path, "# Project\n\n" + core + "\n")
    code = _run_doctor(tmp_path, monkeypatch, pypi=boom)
    out = capsys.readouterr().out.lower()
    assert code == 0  # still fail-soft for the diagnostic
    assert "unexpected" in out and "offline" not in out  # distinct from offline


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
