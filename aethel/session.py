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


def _active_run_id(
    workspace_path: str, cfg: AethelConfig, session: str | None = None
) -> str | None:
    """The selected run-id under multi-slot resolution.

    Precedence: an explicit ``session`` argument > the ``AETHEL_SESSION`` env
    override (per-agent pinning) > the shared ``CURRENT`` pointer. An empty or
    whitespace-only selector at any tier is ignored and falls through, so a
    blank ``AETHEL_SESSION`` never masks ``CURRENT``.
    """
    for candidate in (session, os.environ.get("AETHEL_SESSION")):
        if candidate and candidate.strip():
            return candidate.strip()
    return _read_current_id(workspace_path, cfg)


def current_session_dir(
    workspace_path: str, cfg: AethelConfig | None = None, session: str | None = None
) -> str | None:
    """The selected session directory, or ``None`` when none resolves.

    Resolves the selector (see ``_active_run_id``) to ``sessions/<id>/`` and
    returns it only if that directory actually exists — a dangling ``CURRENT``,
    a stale ``AETHEL_SESSION``, or an already-archived id all read as "no
    session" (fail closed to the root-fallback in the linter).
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    run_id = _active_run_id(workspace_path, cfg, session)
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

    validated = read_manifest(session_dir).get("status") == "validated"
    return archive_session(workspace_path, run_id, incomplete=not validated, cfg=cfg)


def archive_session(
    workspace_path: str, run_id: str, *, incomplete: bool, cfg: AethelConfig | None = None
) -> str:
    """Move ``sessions/<run_id>/`` into the archive (a recoverable directory move).

    ``incomplete=False`` → ``archive/<id>/`` (a completed/validated session);
    ``incomplete=True`` → ``archive/_incomplete/<id>/`` (abandoned/interrupted).
    Clears ``CURRENT`` iff it pointed at this id, so the selector never dangles.
    Raises ``ValueError`` for an unknown session id (fail-fast).
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    paths = aethel_paths(workspace_path, cfg)
    session_dir = os.path.join(paths["sessions"], run_id)
    if not os.path.isdir(session_dir):
        raise ValueError(f"No such session: {run_id}")

    dest_parent = paths["incomplete"] if incomplete else paths["archive"]
    os.makedirs(dest_parent, exist_ok=True)
    dest = os.path.join(dest_parent, run_id)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.move(session_dir, dest)
    if _read_current_id(workspace_path, cfg) == run_id:
        _clear_current(paths)
    return dest


def list_sessions(workspace_path: str, cfg: AethelConfig | None = None) -> list[dict[str, Any]]:
    """Every live session under ``sessions/``, sorted by run-id (chronological).

    Each entry merges the manifest with ``current=True`` for the one ``CURRENT``
    selects, so a caller can render the active marker without re-reading the
    pointer. Archived sessions are intentionally excluded.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    sessions_dir = aethel_paths(workspace_path, cfg)["sessions"]
    if not os.path.isdir(sessions_dir):
        return []
    current = _read_current_id(workspace_path, cfg)
    out: list[dict[str, Any]] = []
    for run_id in sorted(os.listdir(sessions_dir)):
        session_dir = os.path.join(sessions_dir, run_id)
        if not os.path.isdir(session_dir):
            continue
        manifest = read_manifest(session_dir)
        manifest.setdefault("id", run_id)
        manifest["current"] = run_id == current
        out.append(manifest)
    return out


def switch_session(workspace_path: str, run_id: str, cfg: AethelConfig | None = None) -> str:
    """Point ``CURRENT`` at an existing live session. Returns its directory.

    Resolves by exact run-id only; an unknown id raises ``ValueError`` (no
    fuzzy guessing — fail-fast).
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    paths = aethel_paths(workspace_path, cfg)
    session_dir = os.path.join(paths["sessions"], run_id)
    if not os.path.isdir(session_dir):
        raise ValueError(f"No such session: {run_id}")
    with open(paths["current"], "w", encoding="utf-8") as f:
        f.write(run_id + "\n")
    return session_dir


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
    CURRENT to point at it. Multi-slot: the prior session is left LIVE under
    ``sessions/`` (resolvable via ``AETHEL_SESSION``), not reconciled/archived —
    archival is now an explicit verb (``aethel done`` / ``aethel abandon``).
    Returns the new session directory.
    """
    cfg = _resolve_cfg(workspace_path, cfg)

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


def mark_validated(
    workspace_path: str, cfg: AethelConfig | None = None, session: str | None = None
) -> str:
    """Flip the selected session's manifest to ``status=validated`` (PURE).

    Stays a pure status flip — it never archives — so it composes under both
    ``complete_session`` (done) and the legacy ``reconcile`` path. Raises
    ``ValueError`` when no session resolves (fail-fast). Returns the session dir.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    session_dir = current_session_dir(workspace_path, cfg, session)
    if session_dir is None:
        raise ValueError("No active Aethel session to validate (run `aethel start` first).")
    manifest = read_manifest(session_dir)
    manifest["status"] = "validated"
    manifest["validated_at"] = _utc_now()
    write_manifest(session_dir, manifest)
    return session_dir


def complete_session(
    workspace_path: str, cfg: AethelConfig | None = None, session: str | None = None
) -> str:
    """``aethel done``: validate the selected session, then archive it immediately.

    Owner decision (2026-06-24): completion archives at once — a validated
    session is finished and not resumable. Returns the ``archive/<id>/`` dest.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    session_dir = mark_validated(workspace_path, cfg, session)
    run_id = os.path.basename(session_dir)
    return archive_session(workspace_path, run_id, incomplete=False, cfg=cfg)


def abandon_session(
    workspace_path: str, cfg: AethelConfig | None = None, session: str | None = None
) -> str:
    """``aethel abandon``: archive the selected session to ``_incomplete/``.

    A recoverable directory move (not a delete), so it acts directly with no
    interactive confirmation. Raises ``ValueError`` when none resolves.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    session_dir = current_session_dir(workspace_path, cfg, session)
    if session_dir is None:
        raise ValueError("No active Aethel session to abandon (run `aethel start` first).")
    run_id = os.path.basename(session_dir)
    return archive_session(workspace_path, run_id, incomplete=True, cfg=cfg)
