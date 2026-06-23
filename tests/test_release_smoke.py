"""End-to-end smoke tests against the ACTUAL installed `aethel-cli` console-script entry point
(via the `installed_aethel_cli` fixture in conftest.py) - never `python -m aethel.cli` from the
source checkout. That distinction is the point: every other test in this repo (unit tests,
`tests/run_polygon.py`) runs from source, which is exactly the blind spot that let the
templates-missing-from-wheel packaging bug ship unnoticed. This file is the regression guard for
that root cause, exercising the full command surface a real `pip install aethel-cli` user gets.
"""



def test_version_runs(installed_aethel_cli):
    proc = installed_aethel_cli.run("version")
    assert proc.returncode == 0, proc.stderr
    assert "aethel" in proc.stdout.lower()


def test_init_then_lint_clean(installed_aethel_cli, tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    init = installed_aethel_cli.run("init", str(target))
    assert init.returncode == 0, init.stdout + init.stderr
    for f in ("AETHEL.md", "AGENTS.md", "CONTEXT.md", "aethel.toml", ".gitattributes"):
        assert (target / f).exists(), f"{f} missing after init"
    assert (target / ".agents" / "plugins" / "aethel-plugin" / "plugin.json").exists(), (
        "the hidden .agents plugin tree (the second packaging bug) did not survive install"
    )

    # `aethel init` intentionally leaves AETHEL_ONBOARDING.md as a hard lint-blocking gate until
    # onboarding is completed and the file manually removed - simulate that completion.
    (target / "AETHEL_ONBOARDING.md").unlink()

    lint = installed_aethel_cli.run("lint", str(target))
    assert lint.returncode == 0, lint.stdout + lint.stderr
    assert "PASS" in lint.stdout


def test_init_recipe_python_includes_hidden_dotfiles(installed_aethel_cli, tmp_path):
    target = tmp_path / "proj_py"
    target.mkdir()
    init = installed_aethel_cli.run("init", str(target), "--recipe", "python")
    assert init.returncode == 0, init.stdout + init.stderr
    assert (target / ".ruff.toml").exists(), ".ruff.toml recipe file did not survive install"


def test_doctor_on_initialized_workspace(installed_aethel_cli, tmp_path):
    target = tmp_path / "proj_doctor"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))
    doctor = installed_aethel_cli.run("doctor", str(target))
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "core block" in doctor.stdout.lower()


def test_lint_on_uninitialized_directory_does_not_crash(installed_aethel_cli, tmp_path):
    target = tmp_path / "empty"
    target.mkdir()
    lint = installed_aethel_cli.run("lint", str(target))
    assert "Traceback" not in lint.stderr, lint.stderr


def test_eject_then_undo_round_trip(installed_aethel_cli, tmp_path):
    target = tmp_path / "proj_eject"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))

    eject = installed_aethel_cli.run("eject", str(target))
    assert eject.returncode == 0, eject.stdout + eject.stderr
    assert "ejected" in eject.stdout.lower()

    doctor = installed_aethel_cli.run("doctor", str(target))
    assert "ejected" in doctor.stdout.lower(), doctor.stdout

    undo = installed_aethel_cli.run("eject", str(target), "--undo")
    assert undo.returncode == 0, undo.stdout + undo.stderr
    doctor_after = installed_aethel_cli.run("doctor", str(target))
    assert "ejected" not in doctor_after.stdout.lower(), doctor_after.stdout


def test_start_then_done_session_lifecycle(installed_aethel_cli, tmp_path):
    target = tmp_path / "proj_session"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))

    start = installed_aethel_cli.run("start", "my-feature", "--path", str(target))
    assert start.returncode == 0, start.stdout + start.stderr
    sessions_dir = target / ".aethel" / "sessions"
    assert sessions_dir.exists() and list(sessions_dir.iterdir()), "no session directory created"
    session_dir = next(sessions_dir.iterdir())

    # `aethel done` without a valid report must refuse, not silently succeed.
    done_without_report = installed_aethel_cli.run("done", "--path", str(target))
    assert done_without_report.returncode == 1, done_without_report.stdout

    (session_dir / "implementation_plan.md").write_text(
        "# Plan\n\n## User Review Required\n- x\n\n## Open Questions\n- x\n\n"
        "## Proposed Changes\n### x\n- [NEW] x\n\n## Verification Plan & TDD Reproducer\n"
        "### Automated Tests\n- x\n",
        encoding="utf-8",
    )
    (session_dir / "task.md").write_text("# Task Checklist\n- [x] done\n", encoding="utf-8")
    (session_dir / "walkthrough.md").write_text(
        "# Report\n\n## Summary\nx\n\n## Changes made\nx\n\n## What was tested\nx\n\n"
        "## Validation results\nx\n",
        encoding="utf-8",
    )
    done = installed_aethel_cli.run("done", "--path", str(target))
    assert done.returncode == 0, done.stdout + done.stderr


def test_update_is_non_destructive_to_custom_rules(installed_aethel_cli, tmp_path):
    target = tmp_path / "proj_update"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))
    aethel_md = target / "AETHEL.md"
    custom_marker = "\n## My Custom Project Rule\n- never delete the cat\n"
    aethel_md.write_text(aethel_md.read_text(encoding="utf-8") + custom_marker, encoding="utf-8")

    update = installed_aethel_cli.run("update", str(target))
    assert update.returncode == 0, update.stdout + update.stderr
    assert "never delete the cat" in aethel_md.read_text(encoding="utf-8"), (
        "aethel update destroyed a user's custom rule below the managed block"
    )


