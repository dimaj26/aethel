"""Aethel workspace configuration.

The linter's required structure and language policy used to be hard-coded. That
made Aethel unusable as a multi-project library: rigid headings cannot fit every
stack. This module loads an optional ``aethel.toml`` from the workspace root and
falls back to language-neutral defaults, so behaviour stays backward-compatible
when no config is present.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field

# Structure checks match a heading line (starting with ##) that *contains* the
# keyword, case-insensitively. This is far less brittle than pinning the exact
# numbered title, while still catching a missing section. CONTEXT.md is now an
# `llms.txt`-style index whose section names are project-specific (CC-1), so the
# library ships no required CONTEXT headers — its integrity is enforced by the
# knowledge-index check instead. AETHEL.md still has a stable rulebook shape.
DEFAULT_CONTEXT_HEADERS: list[str] = []
DEFAULT_AETHEL_HEADERS = [
    "Decision Routing", "RNA-Blueprint", "Debugging", "Git Commit",
    "Coding Taboos", "Response Rules",
]

DEFAULT_PLACEHOLDER_MARKERS = ["[Insert", "[e.g.", "[your_", "[note_path]", "[vault_name]"]

# Walkthrough report (walkthrough.md) — the optimal section structure a session/task
# report must contain. Checked by check_report_file and the commit-time walkthrough guard.
DEFAULT_REPORT_SECTIONS = ["Summary", "Changes made", "What was tested", "Validation results"]

# Spec-sync drift detection. At commit time the linter compares the staged file
# set: if code files are staged but no spec file is, it nudges (warn) or blocks
# (error). Globs are matched with fnmatch against the full POSIX path, where `*`
# spans directory separators (so "*.py" matches both "foo.py" and "src/foo.py").
DEFAULT_SYNC_WATCHED = [
    "*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs", "*.java", "*.rb",
    "*.php", "*.cs", "*.sql", "*.kt", "*.swift", "*.c", "*.cpp", "*.h", "*.hpp",
]
DEFAULT_SYNC_IGNORED = [
    "*test*", "*spec*", "*.md", "*.lock", "*.min.js",
    "*/node_modules/*", "*/__pycache__/*", "*/.venv/*", "venv/*", "*/dist/*", "*/build/*",
]
# Spec = the Markdown knowledge layer: the index, the rulebook, and any topic
# file under the knowledge tree. Editing the index or ANY topic file satisfies
# Route C spec-sync (`*` spans `/` in this codebase's fnmatch, so "knowledge/*"
# matches nested topics too).
DEFAULT_SPEC_FILES = ["CONTEXT.md", "AETHEL.md", "knowledge/*"]

# Knowledge-index integrity defaults. The index is an `llms.txt`-style curated
# file (default CONTEXT.md) of inline links into a `knowledge/` topic tree.
DEFAULT_KNOWLEDGE_INDEX = "CONTEXT.md"
DEFAULT_KNOWLEDGE_DIR = "knowledge"

# Rule-change ⇒ changelog pairing. When a governance/rule file is staged, the
# human-readable history (CHANGELOG.md) is expected to move with it, so the
# release log does not silently lag behind a rule edit. Like the spec-sync guard
# this only checks the *pairing*, never what actually changed.
DEFAULT_RULE_FILES = ["AETHEL.md"]
DEFAULT_CHANGELOG_FILE = "CHANGELOG.md"

# Agent registry (Route D). Skill-agents live under a gitignored `.agents/` tree; the registry
# is a curated `knowledge/*.md` topic that names each one (so the index can surface them).
DEFAULT_AGENTS_DIR = ".agents"
DEFAULT_AGENTS_REGISTRY = "knowledge/agents.md"

_VALID_ENFORCE = {"error", "warn", "off"}
_VALID_LANG = {"en", "ru", "any"}

# User-level profile: a machine-local file in the caller's home dir that supplies
# personal defaults across ALL their projects. It is a LIVE overlay (re-read on
# every load_config), sitting between the library defaults and the per-workspace
# aethel.toml in precedence: workspace aethel.toml > ~/.aethel/profile.toml >
# library defaults. It lives in $HOME, never inside a repo, so it is private and
# per-machine by construction; a missing/malformed profile is fail-open (no-op).
DEFAULT_PROFILE_PATH = "~/.aethel/profile.toml"


@dataclass
class AethelConfig:
    structure_enforce: str = "error"  # error | warn | off
    context_headers: list[str] = field(default_factory=lambda: list(DEFAULT_CONTEXT_HEADERS))
    aethel_headers: list[str] = field(default_factory=lambda: list(DEFAULT_AETHEL_HEADERS))
    tag_reference_enforce: str = "warn"  # error | warn | off ([G-TabooN] tag resolves to a real taboo)
    artifact_lang: str = "any"  # "en" | "ru" | "any"; language check for plan/task (default: none)
    report_lang: str = "any"  # "en" | "ru" | "any"; language check for walkthrough.md (default: none)
    # Severity of the report-language check. Default "error" so a mandated language
    # actually BLOCKS (a mandated rule with no teeth is theatre). Gated behind
    # report_lang != "any", so workspaces that never set a language are unaffected.
    report_lang_enforce: str = "error"  # error | warn | off
    artifact_whitelist: list[str] = field(default_factory=list)  # words allowed when artifact_lang == "en"
    placeholder_markers: list[str] = field(default_factory=lambda: list(DEFAULT_PLACEHOLDER_MARKERS))
    sync_enforce: str = "warn"  # error | warn | off (spec-sync drift at commit time)
    sync_watched: list[str] = field(default_factory=lambda: list(DEFAULT_SYNC_WATCHED))
    sync_ignored: list[str] = field(default_factory=lambda: list(DEFAULT_SYNC_IGNORED))
    spec_files: list[str] = field(default_factory=lambda: list(DEFAULT_SPEC_FILES))
    require_changelog: str = "warn"  # error | warn | off (rule change ⇒ changelog at commit time)
    rule_files: list[str] = field(default_factory=lambda: list(DEFAULT_RULE_FILES))
    changelog_file: str = DEFAULT_CHANGELOG_FILE
    consistency_enforce: str = "warn"  # error | warn | off (workspace core block structure vs library)
    version_skew_enforce: str = "warn"  # error | warn | off (workspace core revision older than library)
    knowledge_index: str = DEFAULT_KNOWLEDGE_INDEX  # the llms.txt-style index file
    knowledge_dir: str = DEFAULT_KNOWLEDGE_DIR  # directory of atomic topic files
    dead_link_enforce: str = "error"  # error | warn | off (index link resolves on disk)
    orphan_enforce: str = "warn"  # error | warn | off (topic file unreachable from index)
    annotation_enforce: str = "warn"  # error | warn | off (index link to a knowledge file is annotated)
    # Context-bloat control: a knowledge topic over `max_topic_tokens` (char/4 proxy) is flagged.
    # ON by default as a WARNING (visibility into bloat without blocking a commit); 0 disables it.
    # The threshold maps to §7's "~200-line" topic ceiling. char/4 is too coarse to justify "error".
    max_topic_tokens: int = 2500  # 0 = off
    topic_size_enforce: str = "warn"  # error | warn | off
    require_walkthrough: str = "error"  # error | warn | off (commit-time Route-B report guard)
    report_sections: list[str] = field(default_factory=lambda: list(DEFAULT_REPORT_SECTIONS))
    aethel_dir: str = ".aethel"  # gitignored root of the per-session working-dir tree
    recipes_dir: str | None = None  # extra recipe base (personal recipes); None = none configured
    # Agent registry (Route D): the closed source-of-truth listing spawnable skill-agents that
    # live under a gitignored `.agents/` tree. The registry makes them discoverable from the index
    # ("not in the registry => does not exist"); the check keeps it honest in both directions.
    agents_dir: str = DEFAULT_AGENTS_DIR  # root of the gitignored agent (skill) tree
    agents_registry: str = DEFAULT_AGENTS_REGISTRY  # the registry topic file (a knowledge/*.md)
    agent_orphan_enforce: str = "warn"  # error | warn | off (a .agents SKILL.md absent from the registry)
    agent_dangling_enforce: str = "error"  # error | warn | off (a registry link to a missing SKILL.md)


def _coerce_enforce(value: object, fallback: str) -> str:
    return value if isinstance(value, str) and value in _VALID_ENFORCE else fallback


def _coerce_lang(value: object, fallback: str) -> str:
    return value if isinstance(value, str) and value in _VALID_LANG else fallback


def _coerce_str_list(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return list(value)
    return fallback


def _read_toml_file(path: str) -> dict:
    """Parse a TOML file into a dict, fail-open.

    Returns ``{}`` for a missing, unreadable, or malformed file so neither the
    workspace config nor the user profile can break validation by being broken.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def profile_path() -> str:
    """Resolve the user-profile path: ``AETHEL_PROFILE_PATH`` env (test seam +
    power-user override) else the expanded ``~/.aethel/profile.toml``."""
    return os.environ.get("AETHEL_PROFILE_PATH") or os.path.expanduser(DEFAULT_PROFILE_PATH)


def load_config(workspace_path: str = ".") -> AethelConfig:
    """Load config as a layered overlay over the library defaults.

    Precedence (last writer wins): library defaults < user profile
    (``~/.aethel/profile.toml``) < workspace ``aethel.toml``. The profile is a
    LIVE overlay, re-read on every call. Any missing/malformed file is a no-op
    (fail-open), so behaviour is backward-compatible when neither exists.
    """
    cfg = AethelConfig()
    _apply_overrides(cfg, _read_toml_file(profile_path()))
    _apply_overrides(cfg, _read_toml_file(os.path.join(workspace_path, "aethel.toml")))
    return cfg


def _apply_overrides(cfg: AethelConfig, data: dict) -> None:
    """Merge one parsed TOML mapping onto ``cfg`` in place. Absent keys are left
    untouched, so a later call only overrides what it actually sets."""
    structure = data.get("structure", {})
    if isinstance(structure, dict):
        cfg.structure_enforce = _coerce_enforce(structure.get("enforce"), cfg.structure_enforce)
        cfg.context_headers = _coerce_str_list(structure.get("context_headers"), cfg.context_headers)
        cfg.aethel_headers = _coerce_str_list(structure.get("aethel_headers"), cfg.aethel_headers)

    plan = data.get("plan", {})
    if isinstance(plan, dict):
        cfg.tag_reference_enforce = _coerce_enforce(plan.get("tag_reference_enforce"), cfg.tag_reference_enforce)

    language = data.get("language", {})
    if isinstance(language, dict):
        cfg.artifact_lang = _coerce_lang(language.get("artifact_lang"), cfg.artifact_lang)
        cfg.report_lang = _coerce_lang(language.get("report_lang"), cfg.report_lang)
        cfg.report_lang_enforce = _coerce_enforce(language.get("report_lang_enforce"), cfg.report_lang_enforce)
        cfg.artifact_whitelist = _coerce_str_list(language.get("whitelist"), cfg.artifact_whitelist)

    sync = data.get("sync", {})
    if isinstance(sync, dict):
        cfg.sync_enforce = _coerce_enforce(sync.get("enforce"), cfg.sync_enforce)
        cfg.sync_watched = _coerce_str_list(sync.get("watched"), cfg.sync_watched)
        cfg.sync_ignored = _coerce_str_list(sync.get("ignored"), cfg.sync_ignored)
        cfg.spec_files = _coerce_str_list(sync.get("spec_files"), cfg.spec_files)
        cfg.require_changelog = _coerce_enforce(sync.get("require_changelog"), cfg.require_changelog)
        cfg.rule_files = _coerce_str_list(sync.get("rule_files"), cfg.rule_files)
        changelog = sync.get("changelog_file")
        if isinstance(changelog, str):
            cfg.changelog_file = changelog

    consistency = data.get("consistency", {})
    if isinstance(consistency, dict):
        cfg.consistency_enforce = _coerce_enforce(consistency.get("enforce"), cfg.consistency_enforce)
        cfg.version_skew_enforce = _coerce_enforce(consistency.get("version_skew_enforce"), cfg.version_skew_enforce)

    knowledge = data.get("knowledge", {})
    if isinstance(knowledge, dict):
        index_file = knowledge.get("index_file")
        if isinstance(index_file, str):
            cfg.knowledge_index = index_file
        kdir = knowledge.get("dir")
        if isinstance(kdir, str):
            cfg.knowledge_dir = kdir
        cfg.dead_link_enforce = _coerce_enforce(knowledge.get("dead_link_enforce"), cfg.dead_link_enforce)
        cfg.orphan_enforce = _coerce_enforce(knowledge.get("orphan_enforce"), cfg.orphan_enforce)
        cfg.annotation_enforce = _coerce_enforce(knowledge.get("annotation_enforce"), cfg.annotation_enforce)
        mtt = knowledge.get("max_topic_tokens")
        if isinstance(mtt, int) and not isinstance(mtt, bool) and mtt >= 0:
            cfg.max_topic_tokens = mtt
        cfg.topic_size_enforce = _coerce_enforce(knowledge.get("topic_size_enforce"), cfg.topic_size_enforce)

    report = data.get("report", {})
    if isinstance(report, dict):
        cfg.require_walkthrough = _coerce_enforce(report.get("require_walkthrough"), cfg.require_walkthrough)
        cfg.report_sections = _coerce_str_list(report.get("sections"), cfg.report_sections)

    session = data.get("session", {})
    if isinstance(session, dict):
        aethel_dir = session.get("aethel_dir")
        if isinstance(aethel_dir, str) and aethel_dir:
            cfg.aethel_dir = aethel_dir

    recipes = data.get("recipes", {})
    if isinstance(recipes, dict):
        rdir = recipes.get("dir")
        if isinstance(rdir, str) and rdir:
            cfg.recipes_dir = rdir

    agents = data.get("agents", {})
    if isinstance(agents, dict):
        adir = agents.get("dir")
        if isinstance(adir, str) and adir:
            cfg.agents_dir = adir
        areg = agents.get("registry")
        if isinstance(areg, str) and areg:
            cfg.agents_registry = areg
        cfg.agent_orphan_enforce = _coerce_enforce(agents.get("orphan_enforce"), cfg.agent_orphan_enforce)
        cfg.agent_dangling_enforce = _coerce_enforce(agents.get("dangling_enforce"), cfg.agent_dangling_enforce)
