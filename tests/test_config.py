from aethel.config import (
    DEFAULT_SPEC_FILES,
    load_config,
)


def test_defaults_when_no_file(tmp_path):
    cfg = load_config(str(tmp_path))
    assert cfg.structure_enforce == "error"
    assert cfg.artifact_lang == "any"
    assert cfg.report_lang == "any"
    # A mandated report language must block by default (teeth in core, not opt-in).
    assert cfg.report_lang_enforce == "error"
    assert cfg.artifact_whitelist == []
    # Spec = the Markdown knowledge layer (memory.json retired).
    assert cfg.spec_files == list(DEFAULT_SPEC_FILES)
    assert "memory.json" not in cfg.spec_files
    assert "knowledge/*" in cfg.spec_files


def test_knowledge_defaults(tmp_path):
    cfg = load_config(str(tmp_path))
    assert cfg.knowledge_index == "CONTEXT.md"
    assert cfg.knowledge_dir == "knowledge"
    assert cfg.dead_link_enforce == "error"
    assert cfg.orphan_enforce == "warn"
    assert cfg.annotation_enforce == "warn"


def test_knowledge_overrides(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[knowledge]\n'
        'index_file = "INDEX.md"\n'
        'dir = "docs"\n'
        'dead_link_enforce = "warn"\n'
        'orphan_enforce = "error"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.knowledge_index == "INDEX.md"
    assert cfg.knowledge_dir == "docs"
    assert cfg.dead_link_enforce == "warn"
    assert cfg.orphan_enforce == "error"


def test_invalid_knowledge_enforce_falls_back(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[knowledge]\ndead_link_enforce = "nonsense"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.dead_link_enforce == "error"  # invalid -> default


def test_report_defaults(tmp_path):
    cfg = load_config(str(tmp_path))
    assert cfg.require_walkthrough == "error"
    assert cfg.report_sections == ["Summary", "Changes made", "What was tested", "Validation results"]


def test_report_overrides(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[report]\n'
        'require_walkthrough = "warn"\n'
        'sections = ["Итог", "Что тестировалось"]\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.require_walkthrough == "warn"
    assert cfg.report_sections == ["Итог", "Что тестировалось"]


def test_invalid_require_walkthrough_falls_back(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[report]\nrequire_walkthrough = "nonsense"\n', encoding="utf-8",
    )
    assert load_config(str(tmp_path)).require_walkthrough == "error"  # invalid -> default


def test_session_aethel_dir_default(tmp_path):
    assert load_config(str(tmp_path)).aethel_dir == ".aethel"


def test_session_aethel_dir_override(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[session]\naethel_dir = ".sessions"\n', encoding="utf-8",
    )
    assert load_config(str(tmp_path)).aethel_dir == ".sessions"


def test_session_aethel_dir_empty_falls_back(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[session]\naethel_dir = ""\n', encoding="utf-8",
    )
    assert load_config(str(tmp_path)).aethel_dir == ".aethel"  # empty -> default


def test_structure_and_language_overrides(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[structure]\n'
        'enforce = "warn"\n'
        'context_headers = ["Only One"]\n\n'
        '[language]\n'
        'artifact_lang = "any"\n'
        'report_lang = "en"\n'
        'report_lang_enforce = "warn"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.structure_enforce == "warn"
    assert cfg.context_headers == ["Only One"]
    assert cfg.artifact_lang == "any"
    assert cfg.report_lang == "en"
    assert cfg.report_lang_enforce == "warn"


def test_invalid_values_fall_back_to_defaults(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[structure]\nenforce = "nonsense"\n\n'
        '[language]\nartifact_lang = "klingon"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.structure_enforce == "error"  # invalid -> default
    assert cfg.artifact_lang == "any"  # invalid -> default


def test_changelog_sync_defaults(tmp_path):
    cfg = load_config(str(tmp_path))
    assert cfg.require_changelog == "warn"
    assert cfg.rule_files == ["AETHEL.md"]
    assert cfg.changelog_file == "CHANGELOG.md"


def test_changelog_sync_overrides(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[sync]\n'
        'require_changelog = "error"\n'
        'rule_files = ["AETHEL.md", "docs/RULES.md"]\n'
        'changelog_file = "HISTORY.md"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.require_changelog == "error"
    assert cfg.rule_files == ["AETHEL.md", "docs/RULES.md"]
    assert cfg.changelog_file == "HISTORY.md"


def test_consistency_defaults(tmp_path):
    cfg = load_config(str(tmp_path))
    assert cfg.consistency_enforce == "warn"
    assert cfg.version_skew_enforce == "warn"


def test_version_skew_enforce_override(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[consistency]\nenforce = "error"\nversion_skew_enforce = "error"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.consistency_enforce == "error"
    assert cfg.version_skew_enforce == "error"


def test_invalid_version_skew_enforce_falls_back(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[consistency]\nversion_skew_enforce = "nonsense"\n', encoding="utf-8",
    )
    assert load_config(str(tmp_path)).version_skew_enforce == "warn"  # invalid -> default


def test_malformed_toml_is_safe(tmp_path):
    (tmp_path / "aethel.toml").write_text("this is = = not valid toml [[", encoding="utf-8")
    cfg = load_config(str(tmp_path))
    # Fail open: defaults are used rather than crashing or relaxing rules.
    assert cfg.spec_files == list(DEFAULT_SPEC_FILES)
    assert cfg.dead_link_enforce == "error"
