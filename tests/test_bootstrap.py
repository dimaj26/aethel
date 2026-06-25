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


def test_hook_has_windows_venv_probe():
    """#3: the Windows venv interpreter is `python.exe`; the hook must probe it
    BEFORE the extension-less POSIX name, else it falls through to bare `python`
    (usually without aethel) and silently skips the guard."""
    assert "./venv/Scripts/python.exe" in PRE_COMMIT_HOOK
    win = PRE_COMMIT_HOOK.index("./venv/Scripts/python.exe")
    posix = PRE_COMMIT_HOOK.index("./venv/bin/python")
    assert win < posix, "Windows .exe probe must come before the POSIX venv probe"


def test_hook_is_fail_closed():
    """#2: a missing install must BLOCK the commit in hook context, not warn-skip.
    The generated hook bakes AETHEL_REQUIRE=1 so the wrapper's degrade path fails
    closed (manual `python prompt_linter.py` outside the hook stays lenient)."""
    assert "AETHEL_REQUIRE=1" in PRE_COMMIT_HOOK


def _init_git_dir(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)


def test_write_hook_instructs_under_hooksPath(tmp_path, monkeypatch, capsys):
    """#1: when a manager owns hooks (core.hooksPath set), Aethel must NOT write a
    dead `.git/hooks/pre-commit`; it prints an instruction and writes nothing."""
    import aethel.cli as cli
    _init_git_dir(tmp_path)
    monkeypatch.setattr(cli, "_git_config", lambda _ws, _key: ".husky/_")
    cli.write_pre_commit_hook(str(tmp_path), "Configured")
    out = capsys.readouterr().out.lower()
    assert "core.hookspath" in out or "hooks are managed" in out
    assert "aethel lint" in out
    assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()


def test_write_hook_default_when_no_hooksPath(tmp_path, monkeypatch):
    """#1 regression guard: with no core.hooksPath, behavior is unchanged — the
    hook is written to `.git/hooks/pre-commit`."""
    import aethel.cli as cli
    _init_git_dir(tmp_path)
    monkeypatch.setattr(cli, "_git_config", lambda _ws, _key: None)
    cli.write_pre_commit_hook(str(tmp_path), "Configured")
    assert (tmp_path / ".git" / "hooks" / "pre-commit").exists()


def test_init_warns_when_not_importable(tmp_path, monkeypatch, capsys):
    import aethel.cli as cli
    monkeypatch.setattr(cli, "resolve_hook_python", lambda _p: "python")
    monkeypatch.setattr(cli, "probe_import", lambda _exe: (False, "No module named 'aethel'"))
    cmd_init(argparse.Namespace(path=str(tmp_path), force=False, recipe=None))
    out = capsys.readouterr().out
    # Diagnoses + offers an install command, but never forces a dependency edit.
    assert "pipx install aethel-cli" in out or "pip install" in out
    assert (tmp_path / "AETHEL.md").exists()  # init still completed
