import argparse
import fnmatch
import os
import re
import subprocess
import sys
from typing import NamedTuple

from aethel import CORE_REVISION
from aethel.config import AethelConfig, load_config
from aethel.markers import (
    extract_managed_block,
    has_legacy_core_version_stamp,
    is_ejected,
    normalize_block,
    parse_core_revision,
    strip_core_revision,
)
from aethel.session import current_session_dir

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

CYRILLIC_WORD_RE = re.compile(r"\b[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ\-]+\b")
CYRILLIC_CHAR_RE = re.compile(r"[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ]")


def print_success(msg: str) -> None:
    print(f"{GREEN}[PASS] {msg}{RESET}")


def print_warning(msg: str) -> None:
    print(f"{YELLOW}[WARN] {msg}{RESET}")


def print_error(msg: str) -> None:
    print(f"{RED}[FAIL] {msg}{RESET}")


def _resolve_cfg(workspace_path: str, cfg: AethelConfig | None) -> AethelConfig:
    return cfg if cfg is not None else load_config(workspace_path)


def _artifact_base(workspace_path: str, cfg: AethelConfig) -> str:
    """The directory Route B artifacts (plan/task/walkthrough) live in.

    Resolves to the active session dir when ``.aethel/CURRENT`` points at one,
    else the workspace root. This keeps workspaces/tests that never call
    ``aethel start`` behaving exactly as before (root-fallback)."""
    return current_session_dir(workspace_path, cfg) or workspace_path


def _heading_present(content: str, keyword: str) -> bool:
    """True if any Markdown heading line contains the keyword (case-insensitive).

    Intentionally lenient: it does not pin the section number or exact title, so
    a workspace may renumber, rename or localize headings without failing the
    linter, as long as the conceptual section is still there.
    """
    pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(keyword), re.MULTILINE | re.IGNORECASE)
    return bool(pattern.search(content))


def _cyrillic_violations(content: str, whitelist: list[str]) -> list[str]:
    words = CYRILLIC_WORD_RE.findall(content)
    allowed = {w.lower() for w in whitelist}
    return [w for w in words if w.lower() not in allowed]


def _artifact_language_warning(content: str, cfg: AethelConfig, artifact_name: str) -> str | None:
    """Return a language warning for plan/checklist artifacts, honoring config."""
    if cfg.artifact_lang == "any":
        return None
    if cfg.artifact_lang == "en":
        violators = _cyrillic_violations(content, cfg.artifact_whitelist)
        if violators:
            unique = sorted(set(violators))
            display = ", ".join(unique[:10]) + ("..." if len(unique) > 10 else "")
            return f"Cyrillic words found in {artifact_name}: {display}. {artifact_name} should be in English."
        return None
    if cfg.artifact_lang == "ru":
        if not CYRILLIC_CHAR_RE.search(content):
            return f"No Cyrillic characters found in {artifact_name}. {artifact_name} should be in Russian."
    return None


# Legacy positional form `[G-Taboo4]` (CamelCase): the number indexes §5's list position, so it
# silently re-points when the list is reordered. Kept resolving for backward compatibility but
# deprecated in favour of the slug form below.
_TABOO_LEGACY_RE = re.compile(r"\[G-Taboo(\d+)\]")
_TABOO_NUMBER_RE = re.compile(r"^(\d+)\.\s+\*\*", re.MULTILINE)
# Slug form `[G-no-placeholders-in-prod]` (lowercase): a stable slug naming the rule by identity,
# immune to §5 reordering. The capital `T` in the legacy form means the two regexes never overlap.
_G_SLUG_TAG_RE = re.compile(r"\[G-([a-z0-9][a-z0-9-]*)\]")
# Valid `[G-]` slugs are derived from AETHEL.md so there is no second hand-maintained list:
#   - §5 taboo titles:           `N. **No Placeholders in Prod**` -> no-placeholders-in-prod
#   - heading rule codes:        `(GW-1)`, `(CC-1)`               -> gw-1, cc-1
_TABOO_TITLE_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)
_RULE_CODE_RE = re.compile(r"\(([A-Za-z]+-\d+)\)")


def _slugify(text: str) -> str:
    """Lowercase, non-alphanumeric runs -> single hyphen, trimmed. The exact rule plan authors
    follow when writing a `[G-<slug>]` tag (documented in AETHEL.md §2)."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _valid_g_slugs(aethel_text: str) -> set[str]:
    slugs = {_slugify(t) for t in _TABOO_TITLE_RE.findall(aethel_text)}
    slugs |= {_slugify(c) for c in _RULE_CODE_RE.findall(aethel_text)}
    return slugs


def _unresolved_taboo_tags(content: str, workspace_path: str) -> tuple[list[str], list[str]]:
    """Resolve `[G-]` reference tags against this workspace's AETHEL.md, returning
    ``(unresolved, deprecated)``:

    - ``unresolved`` — tags that do not resolve: a legacy ``[G-Taboo<N>]`` whose number is absent
      from §5, or a slug ``[G-<slug>]`` not among the valid `[G-]` slugs. This is the actual risk
      the convention's "prevents line-shift errors" claim names.
    - ``deprecated`` — every legacy ``[G-Taboo<N>]`` tag (positional, identity-blind); callers
      surface these as warnings nudging the slug form.

    Fails OPEN (empty lists) if AETHEL.md is unreadable - that absence is reported by workspace
    hygiene, not duplicated here.
    """
    legacy = _TABOO_LEGACY_RE.findall(content)
    slugs = _G_SLUG_TAG_RE.findall(content)
    if not legacy and not slugs:
        return [], []
    aethel_path = os.path.join(workspace_path, "AETHEL.md")
    try:
        with open(aethel_path, "r", encoding="utf-8") as f:
            aethel_text = f.read()
    except OSError:
        return [], []
    valid_numbers = set(_TABOO_NUMBER_RE.findall(aethel_text))
    valid_slugs = _valid_g_slugs(aethel_text)
    unresolved = [f"[G-Taboo{n}]" for n in legacy if n not in valid_numbers]
    unresolved += [f"[G-{s}]" for s in slugs if s not in valid_slugs]
    deprecated = [f"[G-Taboo{n}]" for n in legacy]
    return unresolved, deprecated


# `[C-<slug>]` (CONTEXT.md index entries) and `[K-<slug>]` (knowledge/*.md domain rules) mirror the
# `[G-]` slug form: a stable slug naming the target by identity, validated against the source-of-truth
# so there is no second hand-maintained list to drift. No positional legacy form ever existed for
# these, so there is no deprecation path — only resolved/unresolved.
_C_SLUG_TAG_RE = re.compile(r"\[C-([a-z0-9][a-z0-9-]*)\]")
_K_SLUG_TAG_RE = re.compile(r"\[K-([a-z0-9][a-z0-9-]*)\]")
# Inline markdown link `[text](target)` — both the text and the target stem identify an index entry.
# (Distinct from `_INLINE_LINK_RE` below, which captures only the target for dead-link checks.)
_CK_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_CK_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def _valid_c_slugs(context_text: str) -> set[str]:
    """Valid `[C-]` slugs from CONTEXT.md: slugified inline-link text, link target file stems, and
    section-heading text (the "link slugs/anchors" an index entry can be named by)."""
    slugs: set[str] = set()
    for text, target in _CK_LINK_RE.findall(context_text):
        slugs.add(_slugify(text))
        stem = os.path.splitext(os.path.basename(target.split("#", 1)[0]))[0]
        if stem:
            slugs.add(_slugify(stem))
    slugs |= {_slugify(h) for h in _CK_HEADING_RE.findall(context_text)}
    slugs.discard("")
    return slugs


def _valid_k_slugs(workspace_path: str) -> set[str]:
    """Valid `[K-]` slugs: every `knowledge/**/*.md` topic-file stem plus every heading inside it."""
    knowledge_dir = os.path.join(workspace_path, "knowledge")
    slugs: set[str] = set()
    for root, _dirs, files in os.walk(knowledge_dir):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            slugs.add(_slugify(os.path.splitext(fn)[0]))
            try:
                with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                    slugs |= {_slugify(h) for h in _CK_HEADING_RE.findall(f.read())}
            except OSError:
                continue
    slugs.discard("")
    return slugs


def _unresolved_ck_tags(content: str, workspace_path: str) -> list[str]:
    """Resolve `[C-]`/`[K-]` reference tags against CONTEXT.md and `knowledge/**/*.md`, returning the
    unresolved tag strings. Fails OPEN per source: a missing/unreadable CONTEXT.md skips `[C-]`
    resolution and a missing `knowledge/` dir skips `[K-]` (those absences are reported by
    `check_knowledge_index`, not duplicated here)."""
    c_tags = _C_SLUG_TAG_RE.findall(content)
    k_tags = _K_SLUG_TAG_RE.findall(content)
    unresolved: list[str] = []
    if c_tags:
        try:
            with open(os.path.join(workspace_path, "CONTEXT.md"), "r", encoding="utf-8") as f:
                valid_c = _valid_c_slugs(f.read())
            unresolved += [f"[C-{s}]" for s in c_tags if s not in valid_c]
        except OSError:
            pass
    if k_tags and os.path.isdir(os.path.join(workspace_path, "knowledge")):
        valid_k = _valid_k_slugs(workspace_path)
        unresolved += [f"[K-{s}]" for s in k_tags if s not in valid_k]
    return unresolved


# The plan sections the linter REQUIRES, single-sourced so the documented RNA template
# (AETHEL.md §2 / AETHEL.md.template) cannot silently drift from what `check_plan_file`
# enforces. `tests/test_plan_template_sync.py` asserts both carry every entry.
REQUIRED_PLAN_H2S = ["User Review Required", "Open Questions", "Proposed Changes", "Verification Plan"]


def check_plan_file(workspace_path: str, cfg: AethelConfig | None = None) -> tuple[list[str], list[str]]:
    """Validates implementation_plan.md format and language."""
    cfg = _resolve_cfg(workspace_path, cfg)
    errors: list[str] = []
    warnings: list[str] = []
    plan_path = os.path.join(_artifact_base(workspace_path, cfg), "implementation_plan.md")

    if not os.path.exists(plan_path):
        return [f"Implementation plan file '{plan_path}' not found."], []

    with open(plan_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not re.search(r"^#\s+\S+", content, re.MULTILINE):
        errors.append("Missing H1 Goal Description header (e.g., '# Goal Description').")

    for h2 in REQUIRED_PLAN_H2S:
        if not re.search(r"^##\s+" + re.escape(h2), content, re.MULTILINE):
            errors.append(f"Missing required H2 section: '## {h2}'.")

    unresolved, deprecated = _unresolved_taboo_tags(content, workspace_path)
    if unresolved:
        msg = (
            f"Unresolved `[G-]` tag(s) in implementation_plan.md: {', '.join(unresolved)} - "
            f"no taboo/rule with that slug or number exists in this workspace's AETHEL.md (stale "
            f"after a rename, or never existed)."
        )
        if cfg.tag_reference_enforce == "error":
            errors.append(msg)
        elif cfg.tag_reference_enforce == "warn":
            warnings.append(msg)
    unresolved_ck = _unresolved_ck_tags(content, workspace_path)
    if unresolved_ck:
        msg = (
            f"Unresolved `[C-]`/`[K-]` tag(s) in implementation_plan.md: {', '.join(unresolved_ck)} "
            f"- no CONTEXT.md index entry / `knowledge/` topic with that slug exists in this "
            f"workspace (stale after a rename, or never existed)."
        )
        if cfg.tag_reference_enforce == "error":
            errors.append(msg)
        elif cfg.tag_reference_enforce == "warn":
            warnings.append(msg)
    if deprecated and cfg.tag_reference_enforce != "off":
        warnings.append(
            f"Deprecated positional tag(s) in implementation_plan.md: "
            f"{', '.join(sorted(set(deprecated)))} - use the stable slug form "
            f"(e.g. `[G-no-placeholders-in-prod]`) instead of `[G-TabooN]`."
        )

    warn = _artifact_language_warning(content, cfg, "plan")
    if warn:
        warnings.append(warn)
    return errors, warnings


def check_checklist_file(
    workspace_path: str, cfg: AethelConfig | None = None, require_complete: bool = True
) -> tuple[list[str], list[str]]:
    """Validates task.md format and language.

    ``require_complete`` separates STRUCTURE validation (always run: well-formed items,
    a final 'run checklist-linter' item) from COMPLETENESS (open ``[ ]``/``[/]`` items).
    The default/pre-commit path passes ``False`` so an in-progress checklist does not
    block every commit during a multi-chunk Route B task (AETHEL.md §2 chunking, §4
    milestone auto-commit); completeness is enforced only at the explicit ``--stage
    checklist`` finalization step (§2.8), where ``require_complete`` stays ``True``."""
    cfg = _resolve_cfg(workspace_path, cfg)
    errors: list[str] = []
    warnings: list[str] = []
    task_path = os.path.join(_artifact_base(workspace_path, cfg), "task.md")

    if not os.path.exists(task_path):
        return [f"Task checklist file '{task_path}' not found."], []

    with open(task_path, "r", encoding="utf-8") as f:
        content = f.read()

    checklist_pattern = re.compile(r"^\s*-\s*`?\[([ x/])\]`?\s*(.*)$")
    tasks = []
    for line in content.splitlines():
        match = checklist_pattern.match(line)
        if match:
            tasks.append((match.group(1), match.group(2).strip()))

    if not tasks:
        errors.append("No task checklist items found in task.md.")
        return errors, warnings

    open_items = [(s, t) for s, t in tasks if s in (" ", "/")]
    if require_complete:
        for status, text in open_items:
            errors.append(f"Incomplete task: [{status}] {text}")
    elif open_items:
        # Lenient (per-commit) mode: surface remaining work, do not block.
        warnings.append(f"{len(open_items)} checklist item(s) still open (not blocking; "
                        f"completeness is enforced at `--stage checklist`).")

    # Last task check
    last_status, last_text = tasks[-1]
    cleaned_last_text = re.sub(r"[`_*]", "", last_text).lower()
    valid_last_items = ["run checklist-linter", "run prompt-linter", "run prompt linter"]
    if not any(item in cleaned_last_text for item in valid_last_items):
        errors.append("Error: Last item must be 'run checklist-linter' (or 'run prompt-linter').")

    warn = _artifact_language_warning(content, cfg, "checklist")
    if warn:
        warnings.append(warn)
    return errors, warnings


def check_report_file(workspace_path: str, cfg: AethelConfig | None = None) -> tuple[list[str], list[str]]:
    """Validates walkthrough.md format and language."""
    cfg = _resolve_cfg(workspace_path, cfg)
    errors: list[str] = []
    warnings: list[str] = []
    walkthrough_path = os.path.join(_artifact_base(workspace_path, cfg), "walkthrough.md")

    if not os.path.exists(walkthrough_path):
        return [f"Walkthrough report file '{walkthrough_path}' not found."], []

    with open(walkthrough_path, "r", encoding="utf-8") as f:
        content = f.read()

    for sec in cfg.report_sections:
        pattern = re.compile(r"(?:^##?\s+|^\s*\*\*\s*)" + re.escape(sec), re.MULTILINE | re.IGNORECASE)
        if not pattern.search(content):
            errors.append(f"Missing required section or heading: '{sec}'.")

    has_cyrillic = bool(CYRILLIC_CHAR_RE.search(content))
    lang_msg: str | None = None
    if cfg.report_lang == "ru" and not has_cyrillic:
        lang_msg = ("No Cyrillic characters found in report. Walkthrough should be in Russian "
                    "(aethel.toml [language] report_lang).")
    elif cfg.report_lang == "en" and has_cyrillic:
        lang_msg = ("Cyrillic characters found in report. Walkthrough should be in English "
                    "(aethel.toml [language] report_lang).")
    # Route the language finding by its configured severity, like every other
    # policy: a mandated language must be able to BLOCK, not only warn.
    if lang_msg is not None:
        if cfg.report_lang_enforce == "error":
            errors.append(lang_msg)
        elif cfg.report_lang_enforce == "warn":
            warnings.append(lang_msg)
        # "off" → suppressed entirely.

    return errors, warnings


def check_plan_stage(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Validates plan and task formats if they exist."""
    cfg = _resolve_cfg(workspace_path, cfg)
    print("--- Running Plan Stage Validation ---")
    base = _artifact_base(workspace_path, cfg)
    plan_path = os.path.join(base, "implementation_plan.md")
    task_path = os.path.join(base, "task.md")

    plan_ok = True
    if os.path.exists(plan_path):
        errs, warns = check_plan_file(workspace_path, cfg)
        for w in warns:
            print_warning(w)
        for e in errs:
            print_error(e)
            plan_ok = False
        if plan_ok:
            print_success(f"'{plan_path}' structure is valid.")
    else:
        print_warning(f"No '{plan_path}' found in workspace. Skipping.")

    task_ok = True
    if os.path.exists(task_path):
        # Default/pre-commit lint validates checklist STRUCTURE only — open items must
        # not block incremental commits (#4); completeness is the `--stage checklist` gate.
        errs, warns = check_checklist_file(workspace_path, cfg, require_complete=False)
        for w in warns:
            print_warning(w)
        for e in errs:
            print_error(e)
            task_ok = False
        if task_ok:
            print_success(f"'{task_path}' format is valid.")
    else:
        print_warning(f"No '{task_path}' found in workspace. Skipping.")

    return plan_ok and task_ok


_INLINE_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# Same link, plus whatever trails it on the line — used to check for an annotation
# (`[text](target) — note`). An annotation starts with a dash/colon then text.
_INLINE_LINK_TRAIL_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)([^\n]*)")
_ANNOTATION_RE = re.compile(r"\s*[-—–:]\s*\S")


def _emit(severity: str, msg: str) -> bool:
    """Print msg at the configured severity. Returns True iff it blocks (error)."""
    if severity == "off":
        return False
    if severity == "warn":
        print_warning(msg)
        return False
    print_error(msg)
    return True


def _extract_inline_links(content: str) -> list[str]:
    """Inline Markdown link targets (``[text](target)``) only.

    An ``llms.txt``-style index is inline-heavy; reference-style links
    (``[ref]: path``) and autolinks (``<path>``) are intentionally out of scope so
    orphan detection cannot false-positive a file that *is* linked by a form this
    does not parse. The template index must therefore use inline links exclusively.
    """
    return _INLINE_LINK_RE.findall(content)


def _is_external_link(target: str) -> bool:
    return target.strip().lower().startswith(("http://", "https://", "mailto:"))


def _unannotated_index_links(content: str, index_dir: str, knowledge_root: str) -> list[str]:
    """Index links to a knowledge file that carry no annotation.

    Reachability surfaces a file; the one-line note (`[text](target) — note`) is
    what makes the agent open the *right* one. Scoped to links whose target
    resolves under the knowledge dir, so prose/external links are never flagged."""
    kn_prefix = os.path.normcase(knowledge_root) + os.sep
    findings: list[str] = []
    for match in _INLINE_LINK_TRAIL_RE.finditer(content):
        target, trailing = match.group(1), match.group(2)
        resolved = _local_link_target(target, index_dir)
        if resolved is None:
            continue
        if not os.path.normcase(resolved).startswith(kn_prefix):
            continue  # only the curated topic/ledger/ADR links carry annotations
        if not _ANNOTATION_RE.match(trailing):
            findings.append(target)
    return findings


def _local_link_target(target: str, base_dir: str) -> str | None:
    """Resolve an inline-link target to an on-disk path, or None.

    Skips external links and pure in-page anchors; strips ``#fragment``; resolves
    relative to ``base_dir`` (the directory of the linking file). Returns the
    normalized path only when it exists on disk."""
    if _is_external_link(target):
        return None
    rel = target.split("#", 1)[0].strip().replace("\\", "/")
    if not rel:
        return None  # pure in-page anchor (#section)
    resolved = os.path.normpath(os.path.join(base_dir, rel))
    return resolved if os.path.exists(resolved) else None


def _reachable_md(index_path: str) -> set[str]:
    """Files reachable by navigation from the index, following inline links
    transitively (index -> topic -> topic -> ADR). Returns normcase paths.

    This models how an agent actually discovers files — it walks the link graph,
    not just the index's first level. Cycle-safe (a visited set), and only ``.md``
    files are *traversed* (a linked binary/dir is recorded as reachable but never
    opened). Links resolve relative to the *linking* file's directory, so a topic
    can surface its own children."""
    reachable: set[str] = set()
    visited: set[str] = set()
    queue: list[str] = [index_path]
    while queue:
        current = queue.pop()
        key = os.path.normcase(os.path.normpath(current))
        if key in visited:
            continue
        visited.add(key)
        try:
            with open(current, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        base_dir = os.path.dirname(current)
        for target in _extract_inline_links(content):
            resolved = _local_link_target(target, base_dir)
            if resolved is None:
                continue
            reachable.add(os.path.normcase(resolved))
            if resolved.lower().endswith(".md") and os.path.normcase(resolved) not in visited:
                queue.append(resolved)
    return reachable


def check_knowledge_index(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Validate the Markdown knowledge index and its ``knowledge/`` topic tree.

    Replaces the retired ``memory.json`` graph integrity check. It keeps the
    guarantees that matter for a curated link index (a DAG, so no cycle/typed-
    relation modelling is needed):

    * the index file (default ``CONTEXT.md``) exists and is not a bare placeholder;
    * every relative inline link in the index resolves on disk (dead link is an
      error by default) — anchors stripped, ``\\``→``/`` normalized, resolved
      relative to the index file, ``http(s)``/``mailto`` skipped;
    * every ``*.md`` topic file under the knowledge dir is reachable from the index
      (an orphan is a warning by default). The index itself and the entry stubs
      live outside the knowledge dir and are thus naturally exempt.

    Severities come from config. Returns False only on an error-severity problem.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    print("--- Running Knowledge Index Integrity Validation ---")
    index_path = os.path.join(workspace_path, cfg.knowledge_index)
    has_errors = False

    if not os.path.exists(index_path):
        print_error(f"Knowledge index '{cfg.knowledge_index}' not found.")
        return False

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    for ph in cfg.placeholder_markers:
        if ph in content:
            print_warning(f"Knowledge index '{cfg.knowledge_index}' contains placeholder: '{ph}'.")

    # Dead-link check: the index's own curated links must resolve on disk.
    index_dir = os.path.dirname(index_path)
    for target in _extract_inline_links(content):
        if _is_external_link(target):
            continue
        rel = target.split("#", 1)[0].strip().replace("\\", "/")
        if not rel:
            continue  # pure in-page anchor (#section)
        if _local_link_target(target, index_dir) is None and _emit(
            cfg.dead_link_enforce, f"Knowledge index dead link: '{target}' does not resolve on disk."
        ):
            has_errors = True

    # Orphan check: every topic .md under the knowledge dir must be REACHABLE by
    # navigation from the index (transitively), not merely linked from it directly.
    # That matches how an agent surfaces files and lets the index stay curated.
    reachable = _reachable_md(index_path)
    knowledge_root = os.path.join(workspace_path, cfg.knowledge_dir)
    if os.path.isdir(knowledge_root):
        for root, _dirs, files in os.walk(knowledge_root):
            for fname in files:
                if not fname.lower().endswith(".md"):
                    continue
                topic = os.path.normpath(os.path.join(root, fname))
                if os.path.normcase(topic) not in reachable:
                    topic_rel = os.path.relpath(topic, workspace_path).replace("\\", "/")
                    if _emit(cfg.orphan_enforce, f"Orphan knowledge file: '{topic_rel}' is not reachable from the index."):
                        has_errors = True

    # Annotation check: each index link to a knowledge file should carry a note —
    # the annotation is what makes an agent open the right surfaced file.
    for target in _unannotated_index_links(content, index_dir, os.path.normpath(knowledge_root)):
        if _emit(
            cfg.annotation_enforce,
            f"Index link to '{target}' has no annotation (expected '[text]({target}) - note').",
        ):
            has_errors = True

    if has_errors:
        return False
    print_success("Knowledge index integrity check passed successfully.")
    return True


_SKILL_FILENAME = "SKILL.md"
# A backticked *path* naming a SKILL.md, e.g. `../.agents/plugins/p/skills/demo/SKILL.md`.
# Accepted as a registration form alongside inline links (both resolved on disk identically).
# Requires a real path separator and path-only chars, so a bare `SKILL.md` or a `<placeholder>/
# SKILL.md` used illustratively in prose does NOT count as a registration (avoids false danglers).
_BACKTICK_SKILL_RE = re.compile(r"`([\w./\\-]+/SKILL\.md)`")


def _discover_skill_files(agents_root: str) -> list[str]:
    """Every ``SKILL.md`` under the agents tree, as real (display-case) paths.

    Walks the directory tree DIRECTLY (``os.walk``) rather than any git-tracked
    listing, so an agent under a gitignored ``.agents/`` is still discovered — the
    discipline lesson from roadmap [18] (a gitignore-filtered search hides agents
    that very much exist). A missing tree yields an empty list (fail open).
    Matching is case-folded by the caller (``os.path.normcase``); the real path is
    kept here so a Windows finding prints ``SKILL.md``, not a lower-cased path."""
    discovered: list[str] = []
    if not os.path.isdir(agents_root):
        return discovered
    for root, _dirs, files in os.walk(agents_root):
        for fname in files:
            if fname == _SKILL_FILENAME:
                discovered.append(os.path.normpath(os.path.join(root, fname)))
    return discovered


def check_agent_registry(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Validate the closed agent registry against the on-disk ``.agents/`` tree.

    Route D delegates analysis to a REGISTERED agent ("not in the registry => does
    not exist"), so the registry (a curated ``knowledge/*.md`` topic) must stay
    honest in both directions:

    * every registry inline link naming a ``SKILL.md`` resolves on disk — a
      dangling link is an error by default (``agent_dangling_enforce``);
    * every ``SKILL.md`` discovered under the agents tree is registered — an
      unlisted one is an orphan warning by default (``agent_orphan_enforce``).

    Fails OPEN: with neither a registry nor any agent there is nothing to validate.
    Returns False only on an error-severity problem.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    print("--- Running Agent Registry Integrity Validation ---")
    agents_root = os.path.join(workspace_path, cfg.agents_dir)
    registry_path = os.path.join(workspace_path, cfg.agents_registry)
    discovered = _discover_skill_files(agents_root)
    has_registry = os.path.exists(registry_path)

    if not discovered and not has_registry:
        print_success("No agents and no registry; nothing to validate.")
        return True

    has_errors = False
    registered: set[str] = set()

    if has_registry:
        with open(registry_path, "r", encoding="utf-8") as f:
            content = f.read()
        registry_dir = os.path.dirname(registry_path)
        # A skill-agent is registered by an inline link OR a backticked path naming a
        # SKILL.md (authors reach for either). Both forms resolve through the SAME
        # on-disk check, so a backtick path to a missing file is a dangling ERROR, not a
        # silent "registered" — the closed-registry contract stays honest (Route D §1).
        inline = [
            t for t in _extract_inline_links(content)
            if os.path.basename(t.split("#", 1)[0].strip().replace("\\", "/")) == _SKILL_FILENAME
        ]
        backticked = _BACKTICK_SKILL_RE.findall(content)
        for target in dict.fromkeys(inline + backticked):  # dedupe, preserve order
            resolved = _local_link_target(target, registry_dir)
            if resolved is None:
                if _emit(
                    cfg.agent_dangling_enforce,
                    f"Agent registry dangling reference: '{target}' does not resolve to a "
                    f"SKILL.md on disk (register a skill-agent with an inline link or backticked "
                    f"path to an existing SKILL.md).",
                ):
                    has_errors = True
                continue
            registered.add(os.path.normcase(os.path.normpath(resolved)))
    elif discovered and _emit(
        cfg.agent_orphan_enforce,
        f"Agent registry '{cfg.agents_registry}' not found, but "
        f"{len(discovered)} skill-agent(s) exist under '{cfg.agents_dir}'.",
    ):
        has_errors = True

    for skill in sorted(discovered):
        if os.path.normcase(skill) not in registered:
            rel = os.path.relpath(skill, workspace_path).replace("\\", "/")
            name = os.path.basename(os.path.dirname(skill)) or "agent"
            rel_from_registry = os.path.relpath(
                skill, os.path.dirname(registry_path)
            ).replace("\\", "/")
            if _emit(
                cfg.agent_orphan_enforce,
                f"Orphan skill-agent: '{rel}' is not registered in '{cfg.agents_registry}'. "
                f"Register it with an inline link (or backticked path) to its SKILL.md, e.g. "
                f"[{name}]({rel_from_registry}).",
            ):
                has_errors = True

    if has_errors:
        return False
    print_success("Agent registry integrity check passed successfully.")
    return True


def _check_required_headers(
    file_label: str, content: str, keywords: list[str], cfg: AethelConfig
) -> bool:
    """Check that each required heading keyword is present. Returns True if a
    hard error was raised (only when structure_enforce == 'error')."""
    if cfg.structure_enforce == "off":
        return False
    raised_error = False
    for keyword in keywords:
        if not _heading_present(content, keyword):
            msg = f"{file_label} is missing required section heading containing: '{keyword}'"
            if cfg.structure_enforce == "warn":
                print_warning(msg)
            else:
                print_error(msg)
                raised_error = True
    return raised_error


def check_workspace_hygiene(
    workspace_path: str, other_checks_passed: bool = True, cfg: AethelConfig | None = None
) -> bool:
    """Validates workspace core files, Git configuration, and cleans up onboarding files."""
    cfg = _resolve_cfg(workspace_path, cfg)
    print("--- Running Workspace Hygiene Validation ---")
    has_errors = False

    # 1. Verify core files presence (memory.json retired in favour of the Markdown
    # knowledge layer; the index file and knowledge dir are checked below + by
    # check_knowledge_index).
    core_files = ["AETHEL.md", "CONTEXT.md", ".gitattributes"]
    for core_file in core_files:
        fpath = os.path.join(workspace_path, core_file)
        if not os.path.exists(fpath):
            print_error(f"Core Aethel file '{core_file}' is missing from the workspace root.")
            has_errors = True
        else:
            print_success(f"Core file present: {core_file}")

    # 1.1 Verify CONTEXT.md required headers (placeholder/link integrity is enforced
    # by check_knowledge_index). With the default index format the library ships no
    # required CONTEXT headers, so this is a no-op unless a project configures some.
    context_path = os.path.join(workspace_path, "CONTEXT.md")
    if os.path.exists(context_path):
        try:
            with open(context_path, "r", encoding="utf-8") as fh:
                ctx_content = fh.read()
            if _check_required_headers("CONTEXT.md", ctx_content, cfg.context_headers, cfg):
                has_errors = True
        except Exception as e:
            print_error(f"Failed to read CONTEXT.md for structural checks: {e}")
            has_errors = True

    # 1.05 Verify the knowledge topic tree exists (the index links into it).
    knowledge_root = os.path.join(workspace_path, cfg.knowledge_dir)
    if os.path.isdir(knowledge_root):
        print_success(f"Knowledge directory present: {cfg.knowledge_dir}")
    else:
        print_warning(f"Knowledge directory '{cfg.knowledge_dir}' is absent; topic detail should live there.")

    # 1.2 Verify AETHEL.md required headers presence
    aethel_path = os.path.join(workspace_path, "AETHEL.md")
    if os.path.exists(aethel_path):
        try:
            with open(aethel_path, "r", encoding="utf-8") as fh:
                aethel_content = fh.read()
            if _check_required_headers("AETHEL.md", aethel_content, cfg.aethel_headers, cfg):
                has_errors = True
        except Exception as e:
            print_error(f"Failed to read AETHEL.md for structural checks: {e}")
            has_errors = True

    # 1.3 Verify the workspace core does not diverge from the installed Aethel core
    if not check_core_consistency(workspace_path, cfg):
        has_errors = True

    # 2. Verify .gitattributes is present and readable. The old `memory.json binary`
    # merge rule is retired (the graph is gone); the shipped template now declares
    # `* text=auto` for consistent line endings. Presence is already covered by the
    # core-files loop above; here we just confirm it reads.
    gitattrib_path = os.path.join(workspace_path, ".gitattributes")
    if os.path.exists(gitattrib_path):
        try:
            with open(gitattrib_path, "r", encoding="utf-8"):
                pass
            print_success("Git attributes file present and readable.")
        except Exception as e:
            print_error(f"Failed to read '.gitattributes': {e}")
            has_errors = True

    # 3. Check for LEGACY_* files in the workspace
    try:
        files = os.listdir(workspace_path)
        legacy_files = [f for f in files if f.startswith("LEGACY_")]
        if legacy_files:
            for lf in legacy_files:
                print_error(f"Legacy file '{lf}' is still present. Please migrate its contents and delete it.")
                has_errors = True
    except Exception as e:
        print_error(f"Failed to list directory contents to check for legacy files: {e}")
        has_errors = True

    # 4. Check for AETHEL_ONBOARDING.md (must be manually deleted by developer)
    onboarding_path = os.path.join(workspace_path, "AETHEL_ONBOARDING.md")
    if os.path.exists(onboarding_path):
        print_error("Temporary onboarding/migration file 'AETHEL_ONBOARDING.md' is present. Complete onboarding, merge rules, and manually delete this file to unblock.")
        has_errors = True

    # 5. Warn if aethel is missing from dependencies
    dep_found = False
    dep_files = ["requirements.txt", "requirements-dev.txt", "setup.py", "pyproject.toml", "setup.cfg"]
    for df in dep_files:
        dfpath = os.path.join(workspace_path, df)
        if os.path.exists(dfpath):
            try:
                with open(dfpath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                if "aethel" in content.lower():
                    dep_found = True
                    break
            except Exception:
                pass
    if not dep_found:
        print_warning("Package 'aethel-cli' (the PyPI distribution; `import aethel` at runtime) is not declared as a dependency in requirements.txt, setup.py, or pyproject.toml.")

    return not has_errors


def _git(workspace_path: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=workspace_path,
        capture_output=True,
        text=True,
    )


def _in_git_repo(workspace_path: str) -> bool:
    try:
        res = _git(workspace_path, "rev-parse", "--is-inside-work-tree")
    except (OSError, ValueError):
        return False
    return res.returncode == 0 and res.stdout.strip() == "true"


def _has_head(workspace_path: str) -> bool:
    try:
        return _git(workspace_path, "rev-parse", "--verify", "-q", "HEAD").returncode == 0
    except (OSError, ValueError):
        return False


def _staged_files(workspace_path: str) -> list[str]:
    try:
        res = _git(workspace_path, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    except (OSError, ValueError):
        return []
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def _classify_staged(staged: list[str], cfg: AethelConfig) -> tuple[bool, bool]:
    """Return (code_changed, spec_changed) for the staged file set."""
    spec_basenames = set(cfg.spec_files)
    code_changed = False
    spec_changed = False
    for f in staged:
        posix = f.replace("\\", "/")
        if os.path.basename(posix) in spec_basenames or _matches_any(posix, cfg.spec_files):
            spec_changed = True
        if _matches_any(posix, cfg.sync_watched) and not _matches_any(posix, cfg.sync_ignored):
            code_changed = True
    return code_changed, spec_changed


def check_spec_sync(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Pre-commit drift guard: warn/block when code is staged without a spec update.

    Detects only the *presence* of a spec change in the same commit, never its
    correctness. Stays inert outside a real commit (no git repo, no HEAD/initial
    commit, nothing staged) so `aethel lint` and the first commit are unaffected.
    Returns True (non-blocking) unless drift is found and enforce == 'error'.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    if cfg.sync_enforce == "off":
        return True
    if os.environ.get("AETHEL_SKIP_SYNC"):
        return True
    if not _in_git_repo(workspace_path) or not _has_head(workspace_path):
        return True
    staged = _staged_files(workspace_path)
    if not staged:
        return True

    code_changed, spec_changed = _classify_staged(staged, cfg)
    if not (code_changed and not spec_changed):
        return True

    print("--- Running Spec-Sync Drift Validation ---")
    msg = (
        "Spec drift: code files are staged but no spec file "
        f"({', '.join(cfg.spec_files)}) was updated in this commit. "
        "Update the knowledge index (CONTEXT.md) or a knowledge/ topic file "
        "(Route C), or set AETHEL_SKIP_SYNC=1 for an intentionally spec-irrelevant commit."
    )
    if cfg.sync_enforce == "error":
        print_error(msg)
        return False
    print_warning(msg)
    return True


def _changelog_drift(staged: list[str], cfg: AethelConfig) -> bool:
    """Return True if a rule file is staged but the changelog is not."""
    rule_staged = False
    changelog_staged = False
    for f in staged:
        posix = f.replace("\\", "/")
        base = os.path.basename(posix)
        if base in cfg.rule_files or _matches_any(posix, cfg.rule_files):
            rule_staged = True
        if base == cfg.changelog_file or _matches_any(posix, [cfg.changelog_file]):
            changelog_staged = True
    return rule_staged and not changelog_staged


def check_changelog_sync(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Pre-commit guard: warn/block when a rule file changes without a CHANGELOG entry.

    A scoped sibling of `check_spec_sync`: the spec-sync guard treats a commit as
    "specs updated" if ANY spec file is staged, so editing a governance rule in
    AETHEL.md and staging only AETHEL.md passes while CHANGELOG.md silently lags.
    This pairs rule changes with the human-readable history. Like the spec guard
    it checks only the *pairing*, never what changed, and stays inert outside a
    real commit. Returns True (non-blocking) unless drift is found and
    require_changelog == 'error'.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    if cfg.require_changelog == "off":
        return True
    if os.environ.get("AETHEL_SKIP_SYNC"):
        return True
    if not _in_git_repo(workspace_path) or not _has_head(workspace_path):
        return True
    staged = _staged_files(workspace_path)
    if not staged:
        return True
    if not _changelog_drift(staged, cfg):
        return True

    print("--- Running Changelog-Sync Drift Validation ---")
    msg = (
        f"Changelog drift: a rule file ({', '.join(cfg.rule_files)}) is staged but "
        f"{cfg.changelog_file} was not updated in this commit. Record the rule change "
        f"in {cfg.changelog_file} (Route C), or set AETHEL_SKIP_SYNC=1 for an "
        "intentionally history-irrelevant commit."
    )
    if cfg.require_changelog == "error":
        print_error(msg)
        return False
    print_warning(msg)
    return True


def check_walkthrough_sync(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Pre-commit guard: require walkthrough.md when a Route B task commits code.

    A sibling of `check_spec_sync` / `check_changelog_sync`. A Route B task is
    signalled by a `task.md` in the artifact base (the active session dir if
    `.aethel/CURRENT` resolves, else the workspace root); when such a task stages
    CODE for a commit, the base's session report (`walkthrough.md`) must exist and
    be well-formed. Like the other guards it is inert outside a real commit (no
    repo / no HEAD / nothing staged), honors `AETHEL_SKIP_SYNC`, and checks only at
    the configured severity. It stays PURE: it never writes the session manifest
    (marking a session done is `aethel done`'s job). Returns True (non-blocking)
    unless drift is found and require_walkthrough == 'error'.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    if cfg.require_walkthrough == "off":
        return True
    if os.environ.get("AETHEL_SKIP_SYNC"):
        return True
    if not _in_git_repo(workspace_path) or not _has_head(workspace_path):
        return True
    staged = _staged_files(workspace_path)
    if not staged:
        return True
    code_changed, _spec_changed = _classify_staged(staged, cfg)
    if not code_changed:
        return True
    # Route B signal: an execution checklist (task.md) is present in the artifact
    # base (the active session dir if one is open, else the workspace root).
    if not os.path.exists(os.path.join(_artifact_base(workspace_path, cfg), "task.md")):
        return True

    print("--- Running Walkthrough-Report Drift Validation ---")
    errors, warnings = check_report_file(workspace_path, cfg)
    for w in warnings:
        print_warning(w)
    if not errors:
        return True
    msg = (
        "Walkthrough drift: a Route B task (task.md present) is committing code but "
        "walkthrough.md is missing or malformed: " + "; ".join(errors) + " "
        "Author the session report (Summary / Changes made / What was tested / "
        "Validation results), or set AETHEL_SKIP_SYNC=1 for an intentionally "
        "report-irrelevant commit."
    )
    return not _emit(cfg.require_walkthrough, msg)


def _installed_core_block() -> str | None:
    """The `aethel-core` managed block shipped by the installed Aethel library."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "AETHEL.md.template")
    if not os.path.exists(template_path):
        return None
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return extract_managed_block(f.read(), "aethel-core")
    except OSError:
        return None


def _installed_core_revision() -> int:
    """The core revision the installed library ships (authoritative; the template
    stamp is asserted equal to it by a test)."""
    return CORE_REVISION


def _is_aethel_source_repo(workspace_path: str) -> bool:
    """True when the workspace IS the Aethel library source (it *defines* the
    core, so it cannot meaningfully 'diverge' from itself)."""
    return os.path.exists(os.path.join(workspace_path, "aethel", "templates", "AETHEL.md.template"))


class CoreState(NamedTuple):
    """The state of a workspace's managed core block vs the installed library.

    ``status`` is one of:
    * ``"source"`` — the workspace IS the Aethel source repo (defines the core).
    * ``"no_template"`` — the installed library ships no core template to compare.
    * ``"no_workspace"`` — the workspace has no readable ``AETHEL.md``.
    * ``"no_block"`` — ``AETHEL.md`` exists but has no ``aethel-core`` managed block.
    * ``"ejected"`` — the block carries an ``AETHEL:EJECTED`` stamp (`aethel eject`):
      sanctioned divergence, structure is never compared.
    * ``"consistent"`` — block matches structure AND revision.
    * ``"skew"`` — block matches structure but the revision stamp differs (stale).
    * ``"obsolete_stamp"`` — the block carries the superseded semver ``AETHEL:CORE-VERSION``
      stamp instead of an integer ``AETHEL:CORE-REV`` (needs `aethel update`).
    * ``"diverged"`` — block structure differs from the library (hand-edited / forked).

    ``ws_rev`` is the workspace's stamped core revision (``None`` if unstamped / absent /
    obsolete-format); ``lib_rev`` is the integer revision the installed library ships.
    """

    status: str
    ws_rev: int | None
    lib_rev: int


def classify_core_state(workspace_path: str) -> CoreState:
    """Classify a workspace's core block against the installed library core.

    Config-independent: it computes *what the state is*, never *how severe* — the
    enforce/severity mapping lives in ``check_core_consistency``. It is the single
    source of truth shared by the linter check and ``aethel doctor``.
    """
    lib_rev = _installed_core_revision()
    if _is_aethel_source_repo(workspace_path):
        return CoreState("source", lib_rev, lib_rev)

    lib_core = _installed_core_block()
    if lib_core is None:
        return CoreState("no_template", None, lib_rev)

    aethel_path = os.path.join(workspace_path, "AETHEL.md")
    if not os.path.exists(aethel_path):
        return CoreState("no_workspace", None, lib_rev)
    try:
        with open(aethel_path, "r", encoding="utf-8") as f:
            ws_core = extract_managed_block(f.read(), "aethel-core")
    except OSError:
        return CoreState("no_workspace", None, lib_rev)

    if ws_core is None:
        return CoreState("no_block", None, lib_rev)

    if is_ejected(ws_core, "aethel-core"):
        return CoreState("ejected", parse_core_revision(ws_core), lib_rev)

    ws_rev = parse_core_revision(ws_core)
    # Obsolete-format guard: an unparseable (None) revision that still carries the legacy
    # semver stamp is a stale workspace needing `aethel update`, NOT a silent skew — surface
    # it distinctly before the structural compare (the legacy stamp line would otherwise read
    # as structural divergence).
    if ws_rev is None and has_legacy_core_version_stamp(ws_core):
        return CoreState("obsolete_stamp", None, lib_rev)

    structurally_equal = (
        normalize_block(strip_core_revision(ws_core)) == normalize_block(strip_core_revision(lib_core))
    )
    if not structurally_equal:
        return CoreState("diverged", ws_rev, lib_rev)
    if ws_rev == lib_rev:
        return CoreState("consistent", ws_rev, lib_rev)
    return CoreState("skew", ws_rev, lib_rev)


def check_core_consistency(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Core-consistency standard: a deployed workspace must not contradict the
    Aethel core. Mechanically, its `aethel-core` managed block must match the
    installed library's core block. The workspace may freely EXTEND the core
    (custom rules below the block, recipes, aethel.toml) — that asymmetry is
    allowed; the core is the invariant subset, not a copy of the workspace.

    The block carries an integer revision stamp (`AETHEL:CORE-REV`). It is stripped
    before the structural comparison so two failure modes are told apart:
    * **structure diverges** ⇒ the block was hand-edited / forked — severity
      `[consistency] enforce`;
    * **structure matches, revision differs** (incl. an unstamped older workspace, or a
      workspace still on the obsolete semver stamp) ⇒ the workspace is merely STALE —
      "run `aethel update`" at severity `[consistency] version_skew_enforce`
      (default warn, non-blocking).

    Returns True (non-blocking) unless a problem is found at its 'error' severity.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    state = classify_core_state(workspace_path)
    if state.status in ("source", "ejected"):
        return True
    if cfg.consistency_enforce == "off" and cfg.version_skew_enforce == "off":
        return True
    # Nothing comparable: missing AETHEL.md is a hygiene concern; missing template
    # = can't compare. Both are non-blocking here.
    if state.status in ("no_template", "no_workspace"):
        return True

    if state.status == "consistent":
        return True  # structure + version match: fully consistent

    if state.status in ("skew", "obsolete_stamp"):
        print("--- Running Core Consistency Validation ---")
        if state.status == "obsolete_stamp":
            msg = (
                "Core stamp obsolete: this workspace carries the superseded semver "
                "`AETHEL:CORE-VERSION` stamp instead of an integer `AETHEL:CORE-REV` "
                f"(library ships core-rev {state.lib_rev}). Run `aethel update` to re-sync it."
            )
        else:
            ws = f"core-rev {state.ws_rev}" if state.ws_rev is not None else "(unstamped)"
            msg = (
                f"Core revision skew: this workspace's managed core is {ws} but the installed "
                f"Aethel library ships core-rev {state.lib_rev}. The block is otherwise unchanged "
                "- run `aethel update` to re-sync it."
            )
        if cfg.version_skew_enforce == "error":
            print_error(msg)
            return False
        if cfg.version_skew_enforce == "warn":
            print_warning(msg)
        return True

    # Structure diverges (or no managed block): hand-edited / forked.
    if cfg.consistency_enforce == "off":
        return True
    print("--- Running Core Consistency Validation ---")
    if state.status == "no_block":
        msg = (
            "AETHEL.md has no managed core block (aethel-core): the workspace has forked "
            "from the Aethel core. Run `aethel update` to restore the managed block and keep "
            "project-specific rules BELOW it."
        )
    else:
        msg = (
            "AETHEL.md managed core block diverges from the installed Aethel core. Do NOT edit "
            "inside the managed block - the workspace may EXTEND the core (rules below the block, "
            "recipes, aethel.toml) but must not contradict it. If the library was upgraded, run "
            "`aethel update` to re-sync the core."
        )
    if cfg.consistency_enforce == "error":
        print_error(msg)
        return False
    print_warning(msg)
    return True


def run_linter(workspace_path: str = ".") -> bool:
    """Invoked internally by old API calls."""
    cfg = load_config(workspace_path)
    plan_ok = check_plan_stage(workspace_path, cfg)
    print()
    knowledge_ok = check_knowledge_index(workspace_path, cfg)
    print()
    agents_ok = check_agent_registry(workspace_path, cfg)
    print()
    hygiene_ok = check_workspace_hygiene(
        workspace_path, other_checks_passed=(plan_ok and knowledge_ok and agents_ok), cfg=cfg
    )
    print()
    return plan_ok and knowledge_ok and agents_ok and hygiene_ok


def ensure_resilient_stdio() -> None:
    """Make stdout/stderr survive characters the console's codepage can't encode.

    The linter re-prints arbitrary AUTHORED Markdown (task-checklist text, plan errors) back to
    the user. That content will eventually contain a character outside whatever codepage a
    non-UTF-8 console (e.g. plain `cp1251`/`cp1252` Windows terminal) uses - banning specific
    characters from prose is not a fix (this repo's own `report_lang=ru` policy means routinely
    non-ASCII content). Replacing unencodable characters is the correct boundary fix: legibility
    degrades gracefully instead of the process crashing.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def main() -> None:
    ensure_resilient_stdio()
    parser = argparse.ArgumentParser(description="Aethel Prompt Linter for agent artifacts.")
    parser.add_argument("--dir", default=".", help="Directory containing the workspace/artifacts")
    parser.add_argument("--stage", choices=["plan", "checklist", "report", "sync"], help="Verification stage to run")

    args = parser.parse_args()
    workspace = os.path.abspath(args.dir)

    if not os.path.exists(workspace):
        print(f"Error: Directory {workspace} does not exist.")
        sys.exit(1)

    cfg = load_config(workspace)
    errors: list[str] = []
    warnings: list[str] = []

    if args.stage == "plan":
        errors, warnings = check_plan_file(workspace, cfg)
    elif args.stage == "checklist":
        errors, warnings = check_checklist_file(workspace, cfg)
    elif args.stage == "report":
        errors, warnings = check_report_file(workspace, cfg)
    elif args.stage == "sync":
        spec_ok = check_spec_sync(workspace, cfg)
        changelog_ok = check_changelog_sync(workspace, cfg)
        walkthrough_ok = check_walkthrough_sync(workspace, cfg)
        sys.exit(0 if (spec_ok and changelog_ok and walkthrough_ok) else 1)
    else:
        # Parameterless run / General checks (Pre-commit hook default)
        plan_ok = check_plan_stage(workspace, cfg)
        print()
        knowledge_ok = check_knowledge_index(workspace, cfg)
        print()
        agents_ok = check_agent_registry(workspace, cfg)
        print()
        hygiene_ok = check_workspace_hygiene(
            workspace, other_checks_passed=(plan_ok and knowledge_ok and agents_ok), cfg=cfg
        )
        print()
        sync_ok = check_spec_sync(workspace, cfg)
        changelog_ok = check_changelog_sync(workspace, cfg)
        walkthrough_ok = check_walkthrough_sync(workspace, cfg)

        if plan_ok and knowledge_ok and agents_ok and hygiene_ok and sync_ok and changelog_ok and walkthrough_ok:
            print_success("All linter checks PASSED.")
            sys.exit(0)
        else:
            print_error("Linter checks FAILED. Please resolve issues above.")
            sys.exit(1)

    # Print results for stage-based checks
    for w in warnings:
        print(f"Warning: {w}")
    for e in errors:
        print(f"Error: {e}")

    if errors:
        sys.exit(1)
    else:
        print(f"{args.stage.capitalize()} is valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
