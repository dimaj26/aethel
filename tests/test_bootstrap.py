"""Bootstrap / install story (roadmap [3]).

The generated pre-commit wrapper must DEGRADE GRACEFULLY when `aethel` is not
installed for the interpreter the hook runs: warn and skip (exit 0) rather than
hard-fail a commit, unless `AETHEL_REQUIRE` is set (strict mode, mirrors
`AETHEL_SKIP_SYNC`). Real lint violations still fail. The hook prefers the
`aethel` console script (pipx), and `aethel init` diagnoses an un-importable
interpreter without forcing a dependency change.
"""

import argparse
import os
import subprocess
import sys

import pytest

from aethel.cli import PRE_COMMIT_HOOK, cmd_init, write_linter_wrapper


def _clean_env():
    # Strip PYTHONPATH so the subprocess cannot import aethel via the repo on path.
    return {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


def _aethel_importable_in_clean_subprocess(cwd):
    proc = subprocess.run(
        [sys.executable, "-c", "import aethel"],
        cwd=cwd, env=_clean_env(), capture_output=True, text=True,
    )
    return proc.returncode == 0


def _run_wrapper(tmp_path, env_extra=None):
    write_linter_wrapper(str(tmp_path))
    env = _clean_env()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "prompt_linter.py"],
        cwd=str(tmp_path), env=env, capture_output=True, text=True,
    )


def test_wrapper_skips_when_not_importable(tmp_path):
    if _aethel_importable_in_clean_subprocess(str(tmp_path)):
        pytest.skip("aethel is installed for this interpreter; cannot test the missing-install path")
    proc = _run_wrapper(tmp_path)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "WARNING" in (proc.stdout + proc.stderr).upper()


def test_wrapper_blocks_when_AETHEL_REQUIRE(tmp_path):
    if _aethel_importable_in_clean_subprocess(str(tmp_path)):
        pytest.skip("aethel is installed for this interpreter; cannot test the missing-install path")
    proc = _run_wrapper(tmp_path, env_extra={"AETHEL_REQUIRE": "1"})
    assert proc.returncode == 1, proc.stderr + proc.stdout


def test_hook_prefers_console_script():
    assert "command -v aethel" in PRE_COMMIT_HOOK
    assert "aethel lint" in PRE_COMMIT_HOOK


def test_init_warns_when_not_importable(tmp_path, monkeypatch, capsys):
    import aethel.cli as cli
    monkeypatch.setattr(cli, "resolve_hook_python", lambda _p: "python")
    monkeypatch.setattr(cli, "probe_import", lambda _exe: (False, "No module named 'aethel'"))
    cmd_init(argparse.Namespace(path=str(tmp_path), force=False, recipe=None))
    out = capsys.readouterr().out
    # Diagnoses + offers an install command, but never forces a dependency edit.
    assert "pipx install aethel" in out or "pip install" in out
    assert (tmp_path / "AETHEL.md").exists()  # init still completed
