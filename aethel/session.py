"""Per-session working-directory lifecycle for Route B tasks.

A Route B task runs inside a per-session working directory under a gitignored
``.aethel/`` tree, identified by a sortable UTC run-id. ``aethel start`` opens a
NEW session and *reconciles* the previous one on start (industry
"reconcile-on-startup"): a session explicitly marked done (``status=validated``,
written by ``aethel done``) is archived to ``.aethel/archive/<id>/``; an
interrupted one (still ``active``) to ``.aethel/archive/_incomplete/<id>/``.

Layout (all under the gitignored ``aethel_dir``, default ``.aethel``)::

    .aethel/CURRENT                  -> pointer file naming the active run-id
    .aethel/sessions/<id>/           -> active working dir (plan/task/walkthrough/session.json)
    .aethel/archive/<id>/            -> sessions marked done
    .aethel/archive/_incomplete/<id> -> sessions never marked done

Stdlib only; this is the single seam for session paths so the linter and CLI
never hand-roll them.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
from typing import Any

from aethel.config import AethelConfig, load_config

CURRENT_FILE = "CURRENT"
SESSIONS_DIRNAME = "sessions"
ARCHIVE_DIRNAME = "archive"
INCOMPLETE_DIRNAME = "_incomplete"
MANIFEST_NAME = "session.json"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _resolve_cfg(workspace_path: str, cfg: AethelConfig | None) -> AethelConfig:
    return cfg if cfg is not None else load_config(workspace_path)


def _kebab(slug: str) -> str:
    """Sanitize an arbitrary string into a lowercase kebab-case slug."""
    return _SLUG_RE.sub("-", slug.strip().lower()).strip("-")


def make_run_id(slug: str | None) -> str:
    """A sortable UTC run-id: ``YYYYMMDDThhmmssZ`` optionally ``-<kebab-slug>``.

    Lexicographic order tracks chronological order (the timestamp prefix is
    fixed-width basic ISO-8601). Collision handling (same second) lives in
    ``start_session``, which sees the existing session dirs.
    """
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if slug:
        kebab = _kebab(slug)
        if kebab:
            return f"{stamp}-{kebab}"
    return stamp


def aethel_paths(workspace_path: str, cfg: AethelConfig | None = None) -> dict[str, str]:
    """The canonical filesystem locations of the session tree.

    Returns absolute-or-workspace-relative paths (joined onto ``workspace_path``)
    for the ``.aethel`` root, the CURRENT pointer, the sessions dir, the archive
    dir, and the ``_incomplete`` sub-archive.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    root = os.path.join(workspace_path, cfg.aethel_dir)
    archive = os.path.join(root, ARCHIVE_DIRNAME)
    return {
        "root": root,
        "current": os.path.join(root, CURRENT_FILE),
        "sessions": os.path.join(root, SESSIONS_DIRNAME),
        "archive": archive,
        "incomplete": os.path.join(archive, INCOMPLETE_DIRNAME),
    }


def _read_current_id(workspace_path: str, cfg: AethelConfig) -> str | None:
    current = aethel_paths(workspace_path, cfg)["current"]
    if not os.path.exists(current):
        return None
    try:
        with open(current, "r", encoding="utf-8") as f:
            run_id = f.read().strip()
    except OSError:
        return None
    return run_id or None


def current_session_dir(workspace_path: str, cfg: AethelConfig | None = None) -> str | None:
    """The active session directory, or ``None`` when no session is open.

    Resolves CURRENT to ``sessions/<id>/`` and returns it only if that directory
    actually exists (a dangling pointer reads as "no session").
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    run_id = _read_current_id(workspace_path, cfg)
    if run_id is None:
        return None
    session_dir = os.path.join(aethel_paths(workspace_path, cfg)["sessions"], run_id)
    return session_dir if os.path.isdir(session_dir) else None


def read_manifest(session_dir: str) -> dict[str, Any]:
    """Load a session's ``session.json`` manifest (``{}`` if absent/malformed)."""
    manifest_path = os.path.join(session_dir, MANIFEST_NAME)
    if not os.path.exists(manifest_path):
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_manifest(session_dir: str, manifest: dict[str, Any]) -> None:
    """Persist a session manifest as pretty JSON."""
    os.makedirs(session_dir, exist_ok=True)
    with open(os.path.join(session_dir, MANIFEST_NAME), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reconcile(workspace_path: str, cfg: AethelConfig | None = None) -> str | None:
    """Archive the CURRENT session by its status, then clear the pointer.

    A ``validated`` session moves to ``archive/<id>/``; anything else (an
    interrupted/``active`` session) moves to ``archive/_incomplete/<id>/``. The
    move is recoverable (a directory move, not a delete). Returns the destination
    path, or ``None`` when there is no session to reconcile.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    paths = aethel_paths(workspace_path, cfg)
    run_id = _read_current_id(workspace_path, cfg)
    if run_id is None:
        return None

    session_dir = os.path.join(paths["sessions"], run_id)
    if not os.path.isdir(session_dir):
        # Dangling CURRENT: drop the stale pointer so a fresh start is clean.
        _clear_current(paths)
        return None

    status = read_manifest(session_dir).get("status")
    dest_parent = paths["archive"] if status == "validated" else paths["incomplete"]
    os.makedirs(dest_parent, exist_ok=True)
    dest = os.path.join(dest_parent, run_id)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.move(session_dir, dest)
    _clear_current(paths)
    return dest


def _clear_current(paths: dict[str, str]) -> None:
    if os.path.exists(paths["current"]):
        os.remove(paths["current"])


def _unique_run_id(sessions_dir: str, base_id: str) -> str:
    """Append ``-2``, ``-3`` … if a same-second run-id already exists on disk."""
    if not os.path.exists(os.path.join(sessions_dir, base_id)):
        return base_id
    n = 2
    while os.path.exists(os.path.join(sessions_dir, f"{base_id}-{n}")):
        n += 1
    return f"{base_id}-{n}"


def start_session(
    workspace_path: str, slug: str | None = None, cfg: AethelConfig | None = None
) -> str:
    """Reconcile the prior session (if any) and open a fresh one.

    Creates ``sessions/<new-id>/`` with an ``active`` manifest and rewrites
    CURRENT to point at it. Returns the new session directory.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    reconcile(workspace_path, cfg)

    paths = aethel_paths(workspace_path, cfg)
    os.makedirs(paths["sessions"], exist_ok=True)
    run_id = _unique_run_id(paths["sessions"], make_run_id(slug))
    session_dir = os.path.join(paths["sessions"], run_id)
    os.makedirs(session_dir)

    write_manifest(
        session_dir,
        {
            "id": run_id,
            "slug": _kebab(slug) if slug else "",
            "started_at": _utc_now(),
            "status": "active",
            "validated_at": None,
        },
    )
    with open(paths["current"], "w", encoding="utf-8") as f:
        f.write(run_id + "\n")
    return session_dir


def mark_validated(workspace_path: str, cfg: AethelConfig | None = None) -> str:
    """Flip the active session's manifest to ``status=validated``.

    Raises ``ValueError`` when no session is open (fail-fast: ``aethel done``
    has nothing to mark). Returns the session directory.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    session_dir = current_session_dir(workspace_path, cfg)
    if session_dir is None:
        raise ValueError("No active Aethel session to validate (run `aethel start` first).")
    manifest = read_manifest(session_dir)
    manifest["status"] = "validated"
    manifest["validated_at"] = _utc_now()
    write_manifest(session_dir, manifest)
    return session_dir
