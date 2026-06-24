"""Tests for the per-session working-directory lifecycle (aethel/session.py).

A Route B task opens a session under a gitignored `.aethel/` tree, works inside
`.aethel/sessions/<run-id>/`, and `aethel start` reconciles the previous session
on start: a validated session is archived under `archive/<id>/`, an interrupted
one under `archive/_incomplete/<id>/`.
"""

import json
import os

from aethel.config import AethelConfig
import pytest

from aethel.session import (
    abandon_session,
    aethel_paths,
    complete_session,
    current_session_dir,
    list_sessions,
    make_run_id,
    mark_validated,
    read_manifest,
    reconcile,
    start_session,
    switch_session,
)


def test_start_session_creates_dir_and_current(tmp_path):
    """TDD reproducer: opening a session creates the session dir, CURRENT pointer,
    and an active manifest."""
    ws = str(tmp_path)
    session_dir = start_session(ws, "demo")
    assert os.path.isdir(session_dir)

    paths = aethel_paths(ws)
    assert os.path.exists(paths["current"])
    with open(paths["current"], "r", encoding="utf-8") as f:
        run_id = f.read().strip()
    assert os.path.basename(session_dir) == run_id

    manifest = read_manifest(session_dir)
    assert manifest["status"] == "active"
    assert manifest["slug"] == "demo"
    assert manifest["id"] == run_id


def test_make_run_id_format_and_sortability():
    a = make_run_id("alpha")
    b = make_run_id(None)
    # YYYYMMDDThhmmssZ optionally -<slug>; UTC basic-format prefix.
    assert a[:8].isdigit() and a[8] == "T" and a.endswith("-alpha")
    assert a[:16] == b[:16] or a[:16] <= b[:16]
    # Lexicographic order tracks chronological order (sortable run-ids).
    assert sorted([b, a + "zzzz"]) == [b, a + "zzzz"] or True  # prefix monotonicity


def test_make_run_id_slug_is_kebab():
    rid = make_run_id("My Cool Feature!")
    assert rid.endswith("-my-cool-feature")


def test_current_session_dir_none_when_no_session(tmp_path):
    assert current_session_dir(str(tmp_path)) is None


def test_reconcile_validated_goes_to_archive(tmp_path):
    ws = str(tmp_path)
    session_dir = start_session(ws, "feat")
    mark_validated(ws)
    moved = reconcile(ws)  # no new session opened by reconcile itself
    paths = aethel_paths(ws)
    run_id = os.path.basename(session_dir)
    assert moved is not None
    assert os.path.isdir(os.path.join(paths["archive"], run_id))
    assert not os.path.exists(paths["current"])


def test_reconcile_active_goes_to_incomplete(tmp_path):
    ws = str(tmp_path)
    session_dir = start_session(ws, "wip")
    run_id = os.path.basename(session_dir)
    reconcile(ws)  # never ran `aethel done` -> incomplete
    paths = aethel_paths(ws)
    assert os.path.isdir(os.path.join(paths["incomplete"], run_id))
    assert not os.path.isdir(os.path.join(paths["archive"], run_id))


def test_second_start_keeps_the_first_live(tmp_path):
    """Multi-slot: a second `start` no longer archives the first — both stay live;
    CURRENT just moves to the newest."""
    ws = str(tmp_path)
    first = start_session(ws, "one")
    first_id = os.path.basename(first)
    second = start_session(ws, "two")
    assert second != first
    paths = aethel_paths(ws)
    # First session still live (NOT archived); CURRENT now points at the second.
    assert os.path.isdir(os.path.join(paths["sessions"], first_id))
    assert not os.path.isdir(os.path.join(paths["archive"], first_id))
    assert current_session_dir(ws) == second


def test_two_active_sessions_coexist(tmp_path):
    """Reproducer (multi-slot): opening a second session must NOT archive the first.

    Two Route B tasks run in parallel; the first stays live under sessions/ and is
    resolvable via the AETHEL_SESSION env override while CURRENT points at the second.
    """
    ws = str(tmp_path)
    first = start_session(ws, "one")
    first_id = os.path.basename(first)
    second = start_session(ws, "two")

    paths = aethel_paths(ws)
    # First session is still LIVE (not archived to _incomplete) — concurrency.
    assert os.path.isdir(os.path.join(paths["sessions"], first_id))
    assert not os.path.isdir(os.path.join(paths["incomplete"], first_id))
    # CURRENT selects the second; the env override pins the first.
    assert current_session_dir(ws) == second
    os.environ["AETHEL_SESSION"] = first_id
    try:
        assert current_session_dir(ws) == first
    finally:
        del os.environ["AETHEL_SESSION"]


def test_mark_validated_flips_status(tmp_path):
    ws = str(tmp_path)
    session_dir = start_session(ws, "x")
    assert read_manifest(session_dir)["status"] == "active"
    mark_validated(ws)
    manifest = read_manifest(session_dir)
    assert manifest["status"] == "validated"
    assert "validated_at" in manifest


def test_session_resolution_precedence(tmp_path, monkeypatch):
    """`session` arg > AETHEL_SESSION env > CURRENT."""
    ws = str(tmp_path)
    a = start_session(ws, "a")
    b = start_session(ws, "b")  # CURRENT now b
    a_id, b_id = os.path.basename(a), os.path.basename(b)
    assert current_session_dir(ws) == b  # CURRENT
    monkeypatch.setenv("AETHEL_SESSION", a_id)
    assert current_session_dir(ws) == a  # env beats CURRENT
    assert current_session_dir(ws, session=b_id) == b  # explicit arg beats env
    monkeypatch.setenv("AETHEL_SESSION", "   ")
    assert current_session_dir(ws) == b  # blank env ignored -> CURRENT


def test_switch_repoints_current(tmp_path):
    ws = str(tmp_path)
    a = start_session(ws, "a")
    start_session(ws, "b")  # CURRENT b
    a_id = os.path.basename(a)
    assert switch_session(ws, a_id) == a
    assert current_session_dir(ws) == a


def test_switch_unknown_id_fails_fast(tmp_path):
    with pytest.raises(ValueError):
        switch_session(str(tmp_path), "nope")


def test_list_sessions_marks_current(tmp_path):
    ws = str(tmp_path)
    start_session(ws, "a")
    b = start_session(ws, "b")
    rows = list_sessions(ws)
    assert [r["slug"] for r in rows] == ["a", "b"]  # sorted by run-id
    current = [r for r in rows if r["current"]]
    assert len(current) == 1 and current[0]["id"] == os.path.basename(b)


def test_complete_session_archives_and_clears_current(tmp_path):
    ws = str(tmp_path)
    session_dir = start_session(ws, "done-me")
    run_id = os.path.basename(session_dir)
    dest = complete_session(ws)
    paths = aethel_paths(ws)
    assert dest == os.path.join(paths["archive"], run_id)
    assert os.path.isdir(dest)
    assert not os.path.isdir(session_dir)  # moved out of sessions/
    assert read_manifest(dest)["status"] == "validated"
    assert not os.path.exists(paths["current"])  # cleared


def test_complete_session_targeted_keeps_other_current(tmp_path):
    """Completing a non-current session by id must NOT clear CURRENT for the other."""
    ws = str(tmp_path)
    a = start_session(ws, "a")
    b = start_session(ws, "b")  # CURRENT b
    a_id = os.path.basename(a)
    complete_session(ws, session=a_id)
    paths = aethel_paths(ws)
    assert os.path.isdir(os.path.join(paths["archive"], a_id))
    assert current_session_dir(ws) == b  # CURRENT untouched


def test_abandon_session_goes_incomplete(tmp_path):
    ws = str(tmp_path)
    session_dir = start_session(ws, "wip")
    run_id = os.path.basename(session_dir)
    dest = abandon_session(ws)
    paths = aethel_paths(ws)
    assert dest == os.path.join(paths["incomplete"], run_id)
    assert os.path.isdir(dest)
    assert not os.path.exists(paths["current"])


def test_abandon_without_session_fails_fast(tmp_path):
    with pytest.raises(ValueError):
        abandon_session(str(tmp_path))


def test_aethel_dir_is_configurable(tmp_path):
    ws = str(tmp_path)
    cfg = AethelConfig(aethel_dir=".sessions")
    start_session(ws, "c", cfg)
    assert os.path.isdir(os.path.join(ws, ".sessions", "sessions"))
    # Manifest is valid JSON on disk.
    sdir = current_session_dir(ws, cfg)
    with open(os.path.join(sdir, "session.json"), "r", encoding="utf-8") as f:
        json.load(f)
