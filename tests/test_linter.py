from aethel.config import AethelConfig
from aethel.linter import (
    _artifact_language_warning,
    _check_required_headers,
    _classify_staged,
    _has_cycle,
    _heading_present,
    check_memory_integrity,
    check_plan_file,
    check_spec_sync,
)


def _write_memory(path, lines):
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def test_valid_ontology_passes(tmp_path):
    _write_memory(
        tmp_path / "memory.json",
        [
            '{"type":"entity","name":"A","entityType":"Component","observations":[]}',
            '{"type":"entity","name":"B","entityType":"Layer","observations":[]}',
            '{"type":"relation","from":"A","to":"B","relationType":"uses"}',
        ],
    )
    assert check_memory_integrity(str(tmp_path)) is True


def test_invalid_entity_type_fails(tmp_path):
    _write_memory(
        tmp_path / "memory.json",
        [
            '{"type":"entity","name":"A","entityType":"bogus","observations":[]}',
            '{"type":"entity","name":"B","entityType":"Layer","observations":[]}',
            '{"type":"relation","from":"A","to":"B","relationType":"uses"}',
        ],
    )
    assert check_memory_integrity(str(tmp_path)) is False


def test_invalid_relation_type_fails(tmp_path):
    _write_memory(
        tmp_path / "memory.json",
        [
            '{"type":"entity","name":"A","entityType":"Component","observations":[]}',
            '{"type":"entity","name":"B","entityType":"Layer","observations":[]}',
            '{"type":"relation","from":"A","to":"B","relationType":"bogus"}',
        ],
    )
    assert check_memory_integrity(str(tmp_path)) is False


def test_custom_ontology_via_config(tmp_path):
    cfg = AethelConfig(entity_types={"Widget"}, relation_types={"binds"})
    _write_memory(
        tmp_path / "memory.json",
        [
            '{"type":"entity","name":"A","entityType":"Widget","observations":[]}',
            '{"type":"entity","name":"B","entityType":"Widget","observations":[]}',
            '{"type":"relation","from":"A","to":"B","relationType":"binds"}',
        ],
    )
    assert check_memory_integrity(str(tmp_path), cfg) is True


def test_cycle_detection():
    assert _has_cycle({"A": ["B"], "B": ["A"]}) is True
    assert _has_cycle({"A": ["B"], "B": ["C"], "C": []}) is False


def test_cycle_detection_deep_chain_no_recursion_error():
    # Linear chain far beyond the default recursion limit must not raise.
    n = 5000
    adj = {f"N{i}": [f"N{i+1}"] for i in range(n)}
    adj[f"N{n}"] = []
    assert _has_cycle(adj) is False


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
    assert _classify_staged(["src/module.py", "memory.json"], cfg) == (True, True)  # both
    assert _classify_staged(["tests/test_x.py"], cfg) == (False, False)  # ignored test file
    assert _classify_staged(["README.md"], cfg) == (False, False)  # doc, not watched


def test_check_spec_sync_disabled_is_noop(tmp_path):
    # 'off' short-circuits before any git inspection; tmp_path need not be a repo.
    assert check_spec_sync(str(tmp_path), AethelConfig(sync_enforce="off")) is True


def test_check_spec_sync_skip_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEL_SKIP_SYNC", "1")
    assert check_spec_sync(str(tmp_path), AethelConfig(sync_enforce="error")) is True


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
