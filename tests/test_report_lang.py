"""Report-language enforcement has teeth.

Regression for the 2026-06-23 miss: a project-mandated `report_lang` was the lone
policy without a severity lever — hardcoded to `warn`, so `aethel done` and the
commit guard (both escalate only on `errors`) could never enforce it. The fix adds
`report_lang_enforce` (default `error` in core) and routes the language finding by
severity in `check_report_file`.
"""

import os

from aethel.config import AethelConfig
from aethel.linter import check_report_file

_SECTIONS = (
    "## Summary\nx\n## Changes made\nx\n## What was tested\nx\n## Validation results\nx\n"
)


def _write_walkthrough(tmp_path, body):
    (tmp_path / "walkthrough.md").write_text(body, encoding="utf-8")


def test_report_lang_warn_does_not_block(tmp_path):
    _write_walkthrough(tmp_path, "# Report (English only)\n" + _SECTIONS)
    cfg = AethelConfig(report_lang="ru", report_lang_enforce="warn")
    errors, warnings = check_report_file(str(tmp_path), cfg)
    assert errors == []
    assert any("Russian" in w for w in warnings)


def test_report_lang_error_blocks(tmp_path):
    _write_walkthrough(tmp_path, "# Report (English only)\n" + _SECTIONS)
    cfg = AethelConfig(report_lang="ru", report_lang_enforce="error")
    errors, warnings = check_report_file(str(tmp_path), cfg)
    assert any("Russian" in e for e in errors)
    assert all("Russian" not in w for w in warnings)


def test_report_lang_off_silent(tmp_path):
    _write_walkthrough(tmp_path, "# Report (English only)\n" + _SECTIONS)
    cfg = AethelConfig(report_lang="ru", report_lang_enforce="off")
    errors, warnings = check_report_file(str(tmp_path), cfg)
    assert all("Russian" not in m for m in errors + warnings)


def test_report_lang_ok_when_cyrillic_present(tmp_path):
    _write_walkthrough(tmp_path, "# Отчёт по-русски\n" + _SECTIONS)
    cfg = AethelConfig(report_lang="ru", report_lang_enforce="error")
    errors, warnings = check_report_file(str(tmp_path), cfg)
    assert all("Russian" not in m for m in errors + warnings)


def test_report_lang_error_blocks_done(tmp_path, monkeypatch):
    """End-to-end: `aethel done` must refuse an English report under report_lang=ru
    (default core severity = error) and leave the session active."""
    import pytest

    from aethel import session
    from aethel.cli import cmd_done

    ws = str(tmp_path)
    (tmp_path / "aethel.toml").write_text(
        '[language]\nreport_lang = "ru"\n', encoding="utf-8"
    )
    session_dir = session.start_session(ws, "demo")
    _write_walkthrough_in(session_dir, "# Report (English only)\n" + _SECTIONS)

    import argparse
    with pytest.raises(SystemExit) as exc:
        cmd_done(argparse.Namespace(path=ws))
    assert exc.value.code == 1
    assert session.read_manifest(session_dir)["status"] == "active"


def _write_walkthrough_in(session_dir, body):
    with open(os.path.join(session_dir, "walkthrough.md"), "w", encoding="utf-8") as f:
        f.write(body)
