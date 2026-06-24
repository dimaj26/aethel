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


def test_multi_slot_sessions_coexist_and_abandon_to_incomplete(installed_aethel_cli, tmp_path):
    """Multi-slot: a second `aethel start` leaves the first LIVE (concurrent Route B tasks);
    sending a session to `_incomplete/` is now the explicit `aethel abandon` verb, not a
    side effect of the next start."""
    target = tmp_path / "proj_multi"
    target.mkdir()
    installed_aethel_cli.run("init", str(target))
    sessions_dir = target / ".aethel" / "sessions"
    incomplete_dir = target / ".aethel" / "archive" / "_incomplete"

    first = installed_aethel_cli.run("start", "task-a", "--path", str(target))
    assert first.returncode == 0, first.stdout + first.stderr
    second = installed_aethel_cli.run("start", "task-b", "--path", str(target))
    assert second.returncode == 0, second.stdout + second.stderr

    # Both sessions are live; nothing was forced into _incomplete by the second start.
    assert len(list(sessions_dir.iterdir())) == 2, "second start did not keep the first session live"
    assert not (incomplete_dir.exists() and list(incomplete_dir.iterdir())), (
        "a start must not archive a prior session under multi-slot"
    )

    # `aethel sessions` lists both; `aethel abandon` moves the selected (CURRENT=task-b) out.
    listed = installed_aethel_cli.run("sessions", str(target))
    assert listed.returncode == 0 and "task-a" in listed.stdout and "task-b" in listed.stdout

    abandoned = installed_aethel_cli.run("abandon", "--path", str(target))
    assert abandoned.returncode == 0, abandoned.stdout + abandoned.stderr
    assert incomplete_dir.exists() and list(incomplete_dir.iterdir()), (
        "abandon did not archive the session as incomplete"
    )
    assert len(list(sessions_dir.iterdir())) == 1, "abandon should leave the other session live"


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
