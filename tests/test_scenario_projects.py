"""Cognitive/functional scenarios not already covered by `tests/run_polygon.py` (A-M) or
`tests/test_release_smoke.py`'s straight-line command coverage - each represents a realistic way
a real user's workspace can be in a non-trivial state. Run against the installed console script
(see `installed_aethel_cli` in conftest.py), same rationale as test_release_smoke.py.

Scenarios are constructed at runtime (via `aethel init`/normal CLI use) rather than checked-in
static fixture files, so they can't go stale when templates change.
"""



def test_non_ascii_authored_content_round_trips(installed_aethel_cli, tmp_path):
    """Cyrillic + emoji in a knowledge topic must survive init -> edit -> lint without
    mangling or crashing, on any console encoding (ties into the cp1251/1252 fix)."""
    target = tmp_path / "proj_non_ascii"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))
    (target / "AETHEL_ONBOARDING.md").unlink()

    topic = target / "knowledge" / "auth.md"
    topic.write_text(
        "---\nname: auth\ndescription: Аутентификация и авторизация 🔐\n---\n\n"
        "# Аутентификация\n\nКороткое описание на русском с эмодзи 🚀 и стрелкой →.\n",
        encoding="utf-8",
    )
    context_md = target / "CONTEXT.md"
    context_md.write_text(
        context_md.read_text(encoding="utf-8").rstrip()
        + "\n\n## Auth\n- [auth](knowledge/auth.md) — Аутентификация и авторизация заметка\n",
        encoding="utf-8",
    )

    lint = installed_aethel_cli.run("lint", str(target))
    assert "Traceback" not in lint.stderr, lint.stderr
    assert lint.returncode == 0, lint.stdout + lint.stderr
    assert "Аутентификация" in topic.read_text(encoding="utf-8")


def test_interrupted_session_is_archived_as_incomplete(installed_aethel_cli, tmp_path):
    """A session left active without `aethel done` (e.g. a crashed agent) must be archived under
    `_incomplete/` on the next `aethel start`, not silently lost or treated as validated."""
    target = tmp_path / "proj_interrupted"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))

    first = installed_aethel_cli.run("start", "crashed-task", "--path", str(target))
    assert first.returncode == 0, first.stdout + first.stderr
    # No `aethel done` here - simulates a crashed/abandoned agent mid-task.

    second = installed_aethel_cli.run("start", "recovery-task", "--path", str(target))
    assert second.returncode == 0, second.stdout + second.stderr
    incomplete_dir = target / ".aethel" / "archive" / "_incomplete"
    assert incomplete_dir.exists() and list(incomplete_dir.iterdir()), (
        "interrupted session was not archived as incomplete"
    )


def test_eject_survives_further_hand_edits(installed_aethel_cli, tmp_path):
    """Once ejected, further hand-edits to the managed block must stay classified 'ejected' (not
    re-flagged as 'diverged'); `--undo` must then correctly restore divergence detection."""
    target = tmp_path / "proj_eject_then_edit"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))
    installed_aethel_cli.run("eject", str(target))

    aethel_md = target / "AETHEL.md"
    text = aethel_md.read_text(encoding="utf-8")
    aethel_md.write_text(text.replace("Decision Routing Protocols", "Custom Routing Rules"), encoding="utf-8")

    doctor = installed_aethel_cli.run("doctor", str(target))
    assert "ejected" in doctor.stdout.lower(), doctor.stdout
    assert "diverged" not in doctor.stdout.lower(), doctor.stdout

    installed_aethel_cli.run("eject", str(target), "--undo")
    doctor_after = installed_aethel_cli.run("doctor", str(target))
    assert "diverged" in doctor_after.stdout.lower(), (
        "undo should restore divergence detection for the still hand-edited block"
    )


def test_js_recipe_full_cycle(installed_aethel_cli, tmp_path):
    """First full init -> lint -> update cycle for the JS recipe (existing recipe tests are
    unit-level only)."""
    target = tmp_path / "proj_js"
    target.mkdir()
    init = installed_aethel_cli.run("init", str(target), "--recipe", "javascript")
    assert init.returncode == 0, init.stdout + init.stderr
    assert (target / ".eslintrc.json").exists(), ".eslintrc.json recipe file missing after init"
    (target / "AETHEL_ONBOARDING.md").unlink()

    lint = installed_aethel_cli.run("lint", str(target))
    assert lint.returncode == 0, lint.stdout + lint.stderr

    update = installed_aethel_cli.run("update", str(target))
    assert update.returncode == 0, update.stdout + update.stderr
    assert (target / ".eslintrc.json").exists(), "update removed the JS recipe file"
