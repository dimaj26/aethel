from aethel.config import AethelConfig
from aethel.linter import (
    _artifact_base,
    _artifact_language_warning,
    _changelog_drift,
    _check_required_headers,
    _classify_staged,
    _heading_present,
    _installed_core_block,
    check_changelog_sync,
    check_core_consistency,
    check_knowledge_index,
    check_plan_file,
    check_report_file,
    check_spec_sync,
)
from aethel.session import read_manifest, start_session

_VALID_REPORT = (
    "# Walkthrough\n\n## Summary\nDid the thing.\n\n## Changes made\n- a\n\n"
    "## What was tested\n- pytest\n\n## Validation results\n- green\n"
)


def test_report_file_missing_is_error(tmp_path):
    errs, _ = check_report_file(str(tmp_path))
    assert errs and "not found" in errs[0]


def test_report_file_valid_passes(tmp_path):
    (tmp_path / "walkthrough.md").write_text(_VALID_REPORT, encoding="utf-8")
    errs, warns = check_report_file(str(tmp_path))
    assert errs == [] and warns == []


def test_report_file_missing_summary_section_errors(tmp_path):
    # 'Summary' is now a required section.
    body = _VALID_REPORT.replace("## Summary\nDid the thing.\n\n", "")
    (tmp_path / "walkthrough.md").write_text(body, encoding="utf-8")
    errs, _ = check_report_file(str(tmp_path))
    assert any("Summary" in e for e in errs)


def test_report_file_ru_language_blocks_by_default(tmp_path):
    """report_lang has teeth now: the default severity is 'error', so an English
    body under report_lang='ru' is a blocking error, not a soft warning."""
    (tmp_path / "walkthrough.md").write_text(_VALID_REPORT, encoding="utf-8")
    errs, _warns = check_report_file(str(tmp_path), AethelConfig(report_lang="ru"))
    assert any("Russian" in e for e in errs)
    # Explicitly downgrading to warn keeps the old non-blocking behaviour.
    _e, warns = check_report_file(
        str(tmp_path), AethelConfig(report_lang="ru", report_lang_enforce="warn")
    )
    assert any("Russian" in w for w in warns)


def test_heading_present_is_lenient():
    content = "## 2. Core Database Schema (DDL reference)\n"
    assert _heading_present(content, "Database Schema") is True
    assert _heading_present(content, "database schema") is True  # case-insensitive
    assert _heading_present(content, "Routing") is False


def test_required_headers_enforce_modes():
    cfg_error = AethelConfig(structure_enforce="error", aethel_headers=["Routing"])
    cfg_warn = AethelConfig(structure_enforce="warn", aethel_headers=["Routing"])
    cfg_off = AethelConfig(structure_enforce="off", aethel_headers=["Routing"])
    content = "## No matching heading here\n"
    assert _check_required_headers("AETHEL.md", content, cfg_error.aethel_headers, cfg_error) is True
    assert _check_required_headers("AETHEL.md", content, cfg_warn.aethel_headers, cfg_warn) is False
    assert _check_required_headers("AETHEL.md", content, cfg_off.aethel_headers, cfg_off) is False


def test_artifact_language_policy():
    en = AethelConfig(artifact_lang="en")
    ru = AethelConfig(artifact_lang="ru")
    any_ = AethelConfig(artifact_lang="any")
    assert _artifact_language_warning("привет мир", en, "plan") is not None  # cyrillic flagged
    assert _artifact_language_warning("hello world", en, "plan") is None
    assert _artifact_language_warning("hello world", ru, "plan") is not None  # missing cyrillic flagged
    assert _artifact_language_warning("привет", ru, "plan") is None
    assert _artifact_language_warning("привет", any_, "plan") is None  # disabled


def test_classify_staged_drift():
    cfg = AethelConfig()
    assert _classify_staged(["src/module.py"], cfg) == (True, False)  # code only -> drift
    assert _classify_staged(["CONTEXT.md"], cfg) == (False, True)  # spec only
    assert _classify_staged(["src/module.py", "CONTEXT.md"], cfg) == (True, True)  # both
    assert _classify_staged(["app.py", "knowledge/arch.md"], cfg) == (True, True)  # topic file is a spec
    assert _classify_staged(["tests/test_x.py"], cfg) == (False, False)  # ignored test file
    assert _classify_staged(["README.md"], cfg) == (False, False)  # doc, not watched


def test_check_spec_sync_disabled_is_noop(tmp_path):
    # 'off' short-circuits before any git inspection; tmp_path need not be a repo.
    assert check_spec_sync(str(tmp_path), AethelConfig(sync_enforce="off")) is True


def test_check_spec_sync_skip_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEL_SKIP_SYNC", "1")
    assert check_spec_sync(str(tmp_path), AethelConfig(sync_enforce="error")) is True


def test_changelog_drift():
    cfg = AethelConfig()
    assert _changelog_drift(["AETHEL.md"], cfg) is True  # rule edited, no changelog -> drift
    assert _changelog_drift(["AETHEL.md", "CHANGELOG.md"], cfg) is False  # paired
    assert _changelog_drift(["CHANGELOG.md"], cfg) is False  # changelog only
    assert _changelog_drift(["src/module.py"], cfg) is False  # non-rule change
    # rule_files matching is path-aware via fnmatch as well as basename.
    cfg2 = AethelConfig(rule_files=["docs/RULES.md"])
    assert _changelog_drift(["docs/RULES.md"], cfg2) is True
    assert _changelog_drift(["docs/RULES.md", "CHANGELOG.md"], cfg2) is False


def test_walkthrough_sync_disabled_is_noop(tmp_path):
    # 'off' short-circuits before any git inspection; tmp_path need not be a repo.
    from aethel.linter import check_walkthrough_sync
    assert check_walkthrough_sync(str(tmp_path), AethelConfig(require_walkthrough="off")) is True


def test_walkthrough_sync_skip_env(tmp_path, monkeypatch):
    from aethel.linter import check_walkthrough_sync
    monkeypatch.setenv("AETHEL_SKIP_SYNC", "1")
    assert check_walkthrough_sync(str(tmp_path), AethelConfig(require_walkthrough="error")) is True


def test_check_changelog_sync_disabled_is_noop(tmp_path):
    # 'off' short-circuits before any git inspection; tmp_path need not be a repo.
    assert check_changelog_sync(str(tmp_path), AethelConfig(require_changelog="off")) is True


def test_check_changelog_sync_skip_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEL_SKIP_SYNC", "1")
    assert check_changelog_sync(str(tmp_path), AethelConfig(require_changelog="error")) is True


def test_core_consistency_matches_and_allows_extension(tmp_path):
    core = _installed_core_block()
    assert core is not None
    # Workspace core block identical to the library core, plus a custom rule below it.
    (tmp_path / "AETHEL.md").write_text(
        "# Project AETHEL\n\n" + core + "\n\n- [G-1]: project-specific rule\n",
        encoding="utf-8",
    )
    assert check_core_consistency(str(tmp_path), AethelConfig(consistency_enforce="error")) is True


def test_core_consistency_flags_in_block_edit(tmp_path):
    core = _installed_core_block()
    assert core is not None and "Decision Routing" in core
    tampered = core.replace("Decision Routing", "Tampered Routing", 1)
    (tmp_path / "AETHEL.md").write_text(tampered, encoding="utf-8")
    assert check_core_consistency(str(tmp_path), AethelConfig(consistency_enforce="error")) is False
    assert check_core_consistency(str(tmp_path), AethelConfig(consistency_enforce="warn")) is True
    assert check_core_consistency(str(tmp_path), AethelConfig(consistency_enforce="off")) is True


def test_core_consistency_flags_missing_block(tmp_path):
    (tmp_path / "AETHEL.md").write_text("# Forked file with no managed markers\n", encoding="utf-8")
    assert check_core_consistency(str(tmp_path), AethelConfig(consistency_enforce="error")) is False


def test_core_consistency_reports_version_skew(tmp_path, capsys):
    """A workspace whose core block matches structurally but carries an older (or
    absent) version stamp is *stale*, not forked: warn 'run aethel update', do not
    block, and do not report structural divergence."""
    from aethel.markers import parse_core_version, strip_core_version
    core = _installed_core_block()
    assert core is not None
    lib_version = parse_core_version(core)
    assert lib_version is not None, "library core block must carry a version stamp"

    # Downgrade the stamp to an older version; structure is otherwise identical.
    stale = core.replace(lib_version, "0.0.1", 1)
    assert parse_core_version(stale) == "0.0.1"
    assert strip_core_version(stale) == strip_core_version(core)  # same structure
    (tmp_path / "AETHEL.md").write_text(stale + "\n", encoding="utf-8")

    # Skew is non-blocking even when structural consistency is 'error'...
    ok = check_core_consistency(str(tmp_path), AethelConfig(consistency_enforce="error"))
    out = capsys.readouterr().out
    assert ok is True, "version skew must not block (it is an upgrade nudge)"
    assert "update" in out.lower(), "skew message should tell the user to run aethel update"
    assert "diverge" not in out.lower(), "skew must not be reported as divergence"

    # ...but can be promoted to a hard error via version_skew_enforce.
    assert check_core_consistency(
        str(tmp_path), AethelConfig(version_skew_enforce="error")
    ) is False


def _write_index(tmp_path, body):
    (tmp_path / "CONTEXT.md").write_text(body, encoding="utf-8")


def test_knowledge_index_flags_dead_link_and_orphan(tmp_path, capsys):
    """TDD reproducer: a dead index link is an error; an unlinked knowledge file
    is an orphan warning."""
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "real.md").write_text("# Real topic\n", encoding="utf-8")
    (kn / "orphan.md").write_text("# Orphan topic\n", encoding="utf-8")
    # Index links one real file and one missing file; never links orphan.md.
    (tmp_path / "CONTEXT.md").write_text(
        "# Index\n\n> summary\n\n"
        "## Topics\n"
        "- [Real](knowledge/real.md) — present\n"
        "- [Missing](knowledge/ghost.md) — dead link\n",
        encoding="utf-8",
    )
    ok = check_knowledge_index(str(tmp_path))
    out = capsys.readouterr().out
    assert ok is False  # dead link is an error
    assert "ghost.md" in out  # the dead link is named
    assert "orphan.md" in out  # the orphan is warned about


def test_knowledge_index_passes_when_links_resolve(tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "arch.md").write_text("# Arch\n", encoding="utf-8")
    (kn / "decisions").mkdir()
    (kn / "decisions" / "0001-x.md").write_text("# ADR\n", encoding="utf-8")
    _write_index(
        tmp_path,
        "# Index\n\n> summary\n\n## Topics\n"
        "- [Arch](knowledge/arch.md) — present\n"
        "- [ADR 1](knowledge/decisions/0001-x.md) — present\n"
        "- [Anthropic](https://www.anthropic.com) — external, ignored\n"
        "- [Self](#topics) — in-page anchor, ignored\n",
    )
    assert check_knowledge_index(str(tmp_path)) is True


def test_knowledge_index_dead_link_severity_configurable(tmp_path):
    _write_index(tmp_path, "# Index\n\n- [Gone](knowledge/missing.md)\n")
    # Default: dead link is an error.
    assert check_knowledge_index(str(tmp_path)) is False
    # Downgraded to a warning via config.
    assert check_knowledge_index(str(tmp_path), AethelConfig(dead_link_enforce="warn")) is True


def test_knowledge_index_orphan_can_be_promoted_to_error(tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "lonely.md").write_text("# Lonely\n", encoding="utf-8")
    _write_index(tmp_path, "# Index\n\n> summary\n\n## Topics\n- nothing linked\n")
    # Orphan defaults to a warning (non-blocking)...
    assert check_knowledge_index(str(tmp_path)) is True
    # ...but can be promoted to an error.
    assert check_knowledge_index(str(tmp_path), AethelConfig(orphan_enforce="error")) is False


def test_knowledge_index_missing_is_error(tmp_path):
    assert check_knowledge_index(str(tmp_path)) is False


def test_knowledge_index_placeholder_warns(tmp_path, capsys):
    _write_index(tmp_path, "# Index\n\n> [Insert summary here]\n")
    check_knowledge_index(str(tmp_path))
    assert "placeholder" in capsys.readouterr().out.lower()


def test_artifact_base_falls_back_to_root_without_session(tmp_path):
    # No `.aethel/CURRENT` -> base is the workspace root (backward-compatible).
    assert _artifact_base(str(tmp_path), AethelConfig()) == str(tmp_path)


def test_artifact_base_resolves_active_session(tmp_path):
    session_dir = start_session(str(tmp_path), "demo")
    assert _artifact_base(str(tmp_path), AethelConfig()) == session_dir


def test_report_check_reads_from_active_session(tmp_path):
    # A report at the root is invisible once a session is open; the session's own
    # report is what the check validates.
    (tmp_path / "walkthrough.md").write_text(_VALID_REPORT, encoding="utf-8")
    session_dir = start_session(str(tmp_path), "demo")
    errs, _ = check_report_file(str(tmp_path))
    assert errs and "not found" in errs[0]  # root report ignored; session has none yet

    import os
    with open(os.path.join(session_dir, "walkthrough.md"), "w", encoding="utf-8") as f:
        f.write(_VALID_REPORT)
    errs, _ = check_report_file(str(tmp_path))
    assert errs == []


def test_walkthrough_sync_stays_pure(tmp_path):
    # The guard must never mutate the session manifest (marking done is `aethel done`'s job).
    import os

    from aethel.linter import check_walkthrough_sync
    session_dir = start_session(str(tmp_path), "demo")
    with open(os.path.join(session_dir, "task.md"), "w", encoding="utf-8") as f:
        f.write("- [x] done\n- [x] run prompt-linter\n")
    with open(os.path.join(session_dir, "walkthrough.md"), "w", encoding="utf-8") as f:
        f.write(_VALID_REPORT)
    # 'off' short-circuits without git; the point is the manifest is untouched.
    check_walkthrough_sync(str(tmp_path), AethelConfig(require_walkthrough="off"))
    assert read_manifest(session_dir)["status"] == "active"


def test_plan_language_respects_config(tmp_path):
    (tmp_path / "implementation_plan.md").write_text(
        "# Цель\n\n## User Review Required\n\n## Open Questions\n\n"
        "## Proposed Changes\n\n## Verification Plan\n",
        encoding="utf-8",
    )
    # English policy flags Cyrillic words.
    errs, warns = check_plan_file(str(tmp_path), AethelConfig(artifact_lang="en"))
    assert errs == [] and any("Cyrillic" in w for w in warns)
    # "any" disables the language warning.
    errs, warns = check_plan_file(str(tmp_path), AethelConfig(artifact_lang="any"))
    assert warns == []
