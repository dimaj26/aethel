import argparse
import fnmatch
import os
import re
import subprocess
import sys

from aethel.config import AethelConfig, load_config
from aethel.markers import extract_managed_block, normalize_block

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


def check_plan_file(workspace_path: str, cfg: AethelConfig | None = None) -> tuple[list[str], list[str]]:
    """Validates implementation_plan.md format and language."""
    cfg = _resolve_cfg(workspace_path, cfg)
    errors: list[str] = []
    warnings: list[str] = []
    plan_path = os.path.join(workspace_path, "implementation_plan.md")

    if not os.path.exists(plan_path):
        return [f"Implementation plan file '{plan_path}' not found."], []

    with open(plan_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not re.search(r"^#\s+\S+", content, re.MULTILINE):
        errors.append("Missing H1 Goal Description header (e.g., '# Goal Description').")

    required_h2s = ["User Review Required", "Open Questions", "Proposed Changes", "Verification Plan"]
    for h2 in required_h2s:
        if not re.search(r"^##\s+" + re.escape(h2), content, re.MULTILINE):
            errors.append(f"Missing required H2 section: '## {h2}'.")

    warn = _artifact_language_warning(content, cfg, "plan")
    if warn:
        warnings.append(warn)
    return errors, warnings


def check_checklist_file(workspace_path: str, cfg: AethelConfig | None = None) -> tuple[list[str], list[str]]:
    """Validates task.md format and language."""
    cfg = _resolve_cfg(workspace_path, cfg)
    errors: list[str] = []
    warnings: list[str] = []
    task_path = os.path.join(workspace_path, "task.md")

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

    for status, text in tasks:
        if status in (" ", "/"):
            errors.append(f"Incomplete task: [{status}] {text}")

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
    walkthrough_path = os.path.join(workspace_path, "walkthrough.md")

    if not os.path.exists(walkthrough_path):
        return [f"Walkthrough report file '{walkthrough_path}' not found."], []

    with open(walkthrough_path, "r", encoding="utf-8") as f:
        content = f.read()

    for sec in cfg.report_sections:
        pattern = re.compile(r"(?:^##?\s+|^\s*\*\*\s*)" + re.escape(sec), re.MULTILINE | re.IGNORECASE)
        if not pattern.search(content):
            errors.append(f"Missing required section or heading: '{sec}'.")

    has_cyrillic = bool(CYRILLIC_CHAR_RE.search(content))
    if cfg.report_lang == "ru" and not has_cyrillic:
        warnings.append("No Cyrillic characters found in report. Walkthrough should be in Russian.")
    elif cfg.report_lang == "en" and has_cyrillic:
        warnings.append("Cyrillic characters found in report. Walkthrough should be in English.")

    return errors, warnings


def check_plan_stage(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Validates plan and task formats if they exist."""
    cfg = _resolve_cfg(workspace_path, cfg)
    print("--- Running Plan Stage Validation ---")
    plan_path = os.path.join(workspace_path, "implementation_plan.md")
    task_path = os.path.join(workspace_path, "task.md")

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
        errs, warns = check_checklist_file(workspace_path, cfg)
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

    # Dead-link check; also record which on-disk files the index references so the
    # orphan check below knows what is reachable.
    index_dir = os.path.dirname(index_path)
    linked: set[str] = set()
    for target in _extract_inline_links(content):
        if _is_external_link(target):
            continue
        rel = target.split("#", 1)[0].strip().replace("\\", "/")
        if not rel:
            continue  # pure in-page anchor (#section)
        resolved = os.path.normpath(os.path.join(index_dir, rel))
        if os.path.exists(resolved):
            linked.add(os.path.normcase(resolved))
        elif _emit(cfg.dead_link_enforce, f"Knowledge index dead link: '{target}' does not resolve on disk."):
            has_errors = True

    # Orphan check: every topic .md under the knowledge dir must be linked.
    knowledge_root = os.path.join(workspace_path, cfg.knowledge_dir)
    if os.path.isdir(knowledge_root):
        for root, _dirs, files in os.walk(knowledge_root):
            for fname in files:
                if not fname.lower().endswith(".md"):
                    continue
                topic = os.path.normpath(os.path.join(root, fname))
                if os.path.normcase(topic) not in linked:
                    topic_rel = os.path.relpath(topic, workspace_path).replace("\\", "/")
                    if _emit(cfg.orphan_enforce, f"Orphan knowledge file: '{topic_rel}' is not linked from the index."):
                        has_errors = True

    if has_errors:
        return False
    print_success("Knowledge index integrity check passed successfully.")
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
        print_warning("Package 'aethel' is not declared as a dependency in requirements.txt, setup.py, or pyproject.toml.")

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
    signalled by a `task.md` in the workspace; when such a task stages CODE for a
    commit, a session report (`walkthrough.md`) must exist and be well-formed.
    Like the other guards it is inert outside a real commit (no repo / no HEAD /
    nothing staged), honors `AETHEL_SKIP_SYNC`, and checks only at the configured
    severity. Returns True (non-blocking) unless drift is found and
    require_walkthrough == 'error'.
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
    # Route B signal: an execution checklist (task.md) is present.
    if not os.path.exists(os.path.join(workspace_path, "task.md")):
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


def _is_aethel_source_repo(workspace_path: str) -> bool:
    """True when the workspace IS the Aethel library source (it *defines* the
    core, so it cannot meaningfully 'diverge' from itself)."""
    return os.path.exists(os.path.join(workspace_path, "aethel", "templates", "AETHEL.md.template"))


def check_core_consistency(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Core-consistency standard: a deployed workspace must not contradict the
    Aethel core. Mechanically, its `aethel-core` managed block must match the
    installed library's core block. The workspace may freely EXTEND the core
    (custom rules below the block, recipes, aethel.toml) — that asymmetry is
    allowed; the core is the invariant subset, not a copy of the workspace.

    Returns True (non-blocking) unless the block diverges and enforce=='error'.
    """
    cfg = _resolve_cfg(workspace_path, cfg)
    if cfg.consistency_enforce == "off" or _is_aethel_source_repo(workspace_path):
        return True
    aethel_path = os.path.join(workspace_path, "AETHEL.md")
    lib_core = _installed_core_block()
    if not os.path.exists(aethel_path) or lib_core is None:
        return True  # missing AETHEL.md is a hygiene concern; missing template = can't compare

    try:
        with open(aethel_path, "r", encoding="utf-8") as f:
            ws_core = extract_managed_block(f.read(), "aethel-core")
    except OSError:
        return True

    if ws_core is not None and normalize_block(ws_core) == normalize_block(lib_core):
        return True

    print("--- Running Core Consistency Validation ---")
    if ws_core is None:
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
    hygiene_ok = check_workspace_hygiene(workspace_path, other_checks_passed=(plan_ok and knowledge_ok), cfg=cfg)
    print()
    return plan_ok and knowledge_ok and hygiene_ok


def main() -> None:
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
        hygiene_ok = check_workspace_hygiene(workspace, other_checks_passed=(plan_ok and knowledge_ok), cfg=cfg)
        print()
        sync_ok = check_spec_sync(workspace, cfg)
        changelog_ok = check_changelog_sync(workspace, cfg)
        walkthrough_ok = check_walkthrough_sync(workspace, cfg)

        if plan_ok and knowledge_ok and hygiene_ok and sync_ok and changelog_ok and walkthrough_ok:
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
