"""Aethel workspace configuration.

The linter's ontology, required structure and language policy used to be
hard-coded. That made Aethel unusable as a multi-project library: a fixed set
of entity/relation types and exact Russian-numbered headings cannot fit every
stack. This module loads an optional ``aethel.toml`` from the workspace root and
falls back to sensible defaults, so behaviour stays backward-compatible when no
config is present.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field

# Default ontology. Intentionally broader than the original 7/8 sets so that
# common project structures (scripts, config, migrations, libraries, jobs) do
# not require a custom config just to pass the linter.
DEFAULT_ENTITY_TYPES = {
    "Framework", "Tool", "Layer", "Component", "DataModel", "ExternalService",
    "Route", "Script", "Config", "Job", "Migration", "Library",
}
DEFAULT_RELATION_TYPES = {
    "uses", "defines", "calls", "renders", "tests", "stores", "part_of",
    "depends_on", "configures", "extends", "implements",
}

# Structure checks match a heading line (starting with ##) that *contains* the
# keyword, case-insensitively. This is far less brittle than pinning the exact
# numbered title, while still catching a missing section.
DEFAULT_CONTEXT_HEADERS = [
    "Directory Structure", "Database Schema", "Coding Taboos", "Navigation Map",
]
DEFAULT_AETHEL_HEADERS = [
    "Decision Routing", "RNA-Blueprint", "Debugging", "Git Commit",
    "Coding Taboos", "Response Rules",
]

DEFAULT_PLACEHOLDER_MARKERS = ["[Insert", "[e.g.", "[your_", "[note_path]", "[vault_name]"]

# Spec-sync drift detection. At commit time the linter compares the staged file
# set: if code files are staged but no spec file is, it nudges (warn) or blocks
# (error). Globs are matched with fnmatch against the full POSIX path, where `*`
# spans directory separators (so "*.py" matches both "foo.py" and "src/foo.py").
DEFAULT_SYNC_WATCHED = [
    "*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs", "*.java", "*.rb",
    "*.php", "*.cs", "*.sql", "*.kt", "*.swift", "*.c", "*.cpp", "*.h", "*.hpp",
]
DEFAULT_SYNC_IGNORED = [
    "*test*", "*spec*", "*.md", "memory.json", "*.lock", "*.min.js",
    "*/node_modules/*", "*/__pycache__/*", "*/.venv/*", "venv/*", "*/dist/*", "*/build/*",
]
DEFAULT_SPEC_FILES = ["memory.json", "CONTEXT.md", "AETHEL.md"]

_VALID_ENFORCE = {"error", "warn", "off"}
_VALID_LANG = {"en", "ru", "any"}


@dataclass
class AethelConfig:
    entity_types: set[str] = field(default_factory=lambda: set(DEFAULT_ENTITY_TYPES))
    relation_types: set[str] = field(default_factory=lambda: set(DEFAULT_RELATION_TYPES))
    structure_enforce: str = "error"  # error | warn | off
    context_headers: list[str] = field(default_factory=lambda: list(DEFAULT_CONTEXT_HEADERS))
    aethel_headers: list[str] = field(default_factory=lambda: list(DEFAULT_AETHEL_HEADERS))
    artifact_lang: str = "en"  # language enforced for implementation_plan.md / task.md
    report_lang: str = "ru"  # language enforced for walkthrough.md
    placeholder_markers: list[str] = field(default_factory=lambda: list(DEFAULT_PLACEHOLDER_MARKERS))
    sync_enforce: str = "warn"  # error | warn | off (spec-sync drift at commit time)
    sync_watched: list[str] = field(default_factory=lambda: list(DEFAULT_SYNC_WATCHED))
    sync_ignored: list[str] = field(default_factory=lambda: list(DEFAULT_SYNC_IGNORED))
    spec_files: list[str] = field(default_factory=lambda: list(DEFAULT_SPEC_FILES))


def _coerce_enforce(value: object, fallback: str) -> str:
    return value if isinstance(value, str) and value in _VALID_ENFORCE else fallback


def _coerce_lang(value: object, fallback: str) -> str:
    return value if isinstance(value, str) and value in _VALID_LANG else fallback


def _coerce_str_list(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return list(value)
    return fallback


def load_config(workspace_path: str = ".") -> AethelConfig:
    """Load ``aethel.toml`` from the workspace root, merged over defaults.

    A missing or malformed file yields the default config (backward-compatible).
    Any key absent from the file keeps its default value.
    """
    cfg = AethelConfig()
    config_path = os.path.join(workspace_path, "aethel.toml")
    if not os.path.exists(config_path):
        return cfg

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        # Fail open: a broken config must not silently change validation rules.
        return cfg

    ontology = data.get("ontology", {})
    if isinstance(ontology, dict):
        ents = ontology.get("entity_types")
        if isinstance(ents, list) and all(isinstance(v, str) for v in ents):
            cfg.entity_types = set(ents)
        rels = ontology.get("relation_types")
        if isinstance(rels, list) and all(isinstance(v, str) for v in rels):
            cfg.relation_types = set(rels)

    structure = data.get("structure", {})
    if isinstance(structure, dict):
        cfg.structure_enforce = _coerce_enforce(structure.get("enforce"), cfg.structure_enforce)
        cfg.context_headers = _coerce_str_list(structure.get("context_headers"), cfg.context_headers)
        cfg.aethel_headers = _coerce_str_list(structure.get("aethel_headers"), cfg.aethel_headers)

    language = data.get("language", {})
    if isinstance(language, dict):
        cfg.artifact_lang = _coerce_lang(language.get("artifact_lang"), cfg.artifact_lang)
        cfg.report_lang = _coerce_lang(language.get("report_lang"), cfg.report_lang)

    sync = data.get("sync", {})
    if isinstance(sync, dict):
        cfg.sync_enforce = _coerce_enforce(sync.get("enforce"), cfg.sync_enforce)
        cfg.sync_watched = _coerce_str_list(sync.get("watched"), cfg.sync_watched)
        cfg.sync_ignored = _coerce_str_list(sync.get("ignored"), cfg.sync_ignored)
        cfg.spec_files = _coerce_str_list(sync.get("spec_files"), cfg.spec_files)

    return cfg
