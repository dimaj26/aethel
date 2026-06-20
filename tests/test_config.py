from aethel.config import (
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATION_TYPES,
    load_config,
)


def test_defaults_when_no_file(tmp_path):
    cfg = load_config(str(tmp_path))
    assert cfg.entity_types == set(DEFAULT_ENTITY_TYPES)
    assert cfg.relation_types == set(DEFAULT_RELATION_TYPES)
    assert cfg.structure_enforce == "error"
    assert cfg.artifact_lang == "en"
    assert cfg.report_lang == "ru"


def test_custom_ontology_replaces_defaults(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[ontology]\n'
        'entity_types = ["Widget", "Gadget"]\n'
        'relation_types = ["binds"]\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.entity_types == {"Widget", "Gadget"}
    assert cfg.relation_types == {"binds"}


def test_structure_and_language_overrides(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[structure]\n'
        'enforce = "warn"\n'
        'context_headers = ["Only One"]\n\n'
        '[language]\n'
        'artifact_lang = "any"\n'
        'report_lang = "en"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.structure_enforce == "warn"
    assert cfg.context_headers == ["Only One"]
    assert cfg.artifact_lang == "any"
    assert cfg.report_lang == "en"


def test_invalid_values_fall_back_to_defaults(tmp_path):
    (tmp_path / "aethel.toml").write_text(
        '[structure]\nenforce = "nonsense"\n\n'
        '[language]\nartifact_lang = "klingon"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(tmp_path))
    assert cfg.structure_enforce == "error"  # invalid -> default
    assert cfg.artifact_lang == "en"  # invalid -> default


def test_malformed_toml_is_safe(tmp_path):
    (tmp_path / "aethel.toml").write_text("this is = = not valid toml [[", encoding="utf-8")
    cfg = load_config(str(tmp_path))
    # Fail open: defaults are used rather than crashing or relaxing rules.
    assert cfg.entity_types == set(DEFAULT_ENTITY_TYPES)
