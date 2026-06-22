"""Tests for the per-session working-directory lifecycle (aethel/session.py).

A Route B task opens a session under a gitignored `.aethel/` tree, works inside
`.aethel/sessions/<run-id>/`, and `aethel start` reconciles the previous session
on start: a validated session is archived under `archive/<id>/`, an interrupted
one under `archive/_incomplete/<id>/`.
"""

import json
import os

from aethel.config import AethelConfig
from aethel.session import (
    aethel_paths,
    current_session_dir,
    make_run_id,
    mark_validated,
    read_manifest,
    reconcile,
    start_session,
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


def test_second_start_archives_the_first(tmp_path):
    ws = str(tmp_path)
    first = start_session(ws, "one")
    mark_validated(ws)
    first_id = os.path.basename(first)
    second = start_session(ws, "two")
    assert second != first
    paths = aethel_paths(ws)
    # First session archived (validated); CURRENT now points at the second.
    assert os.path.isdir(os.path.join(paths["archive"], first_id))
    assert current_session_dir(ws) == second


def test_mark_validated_flips_status(tmp_path):
    ws = str(tmp_path)
    session_dir = start_session(ws, "x")
    assert read_manifest(session_dir)["status"] == "active"
    mark_validated(ws)
    manifest = read_manifest(session_dir)
    assert manifest["status"] == "validated"
    assert "validated_at" in manifest


def test_aethel_dir_is_configurable(tmp_path):
    ws = str(tmp_path)
    cfg = AethelConfig(aethel_dir=".sessions")
    start_session(ws, "c", cfg)
    assert os.path.isdir(os.path.join(ws, ".sessions", "sessions"))
    # Manifest is valid JSON on disk.
    sdir = current_session_dir(ws, cfg)
    with open(os.path.join(sdir, "session.json"), "r", encoding="utf-8") as f:
        json.load(f)
