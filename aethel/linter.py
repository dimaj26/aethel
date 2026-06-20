import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from typing import Any

from aethel.config import AethelConfig, load_config
from aethel.markers import extract_managed_block, normalize_block

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# Whitelist for Cyrillic words permitted in plans and checklists
PLAN_CYRILLIC_WHITELIST = {"шэф", "теңир-тоо", "тенир-тоо", "теңир", "тоо", "aethel"}

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


def _cyrillic_violations(content: str) -> list[str]:
    words = CYRILLIC_WORD_RE.findall(content)
    return [w for w in words if w.lower() not in PLAN_CYRILLIC_WHITELIST]


def _artifact_language_warning(content: str, cfg: AethelConfig, artifact_name: str) -> str | None:
    """Return a language warning for plan/checklist artifacts, honoring config."""
    if cfg.artifact_lang == "any":
        return None
    if cfg.artifact_lang == "en":
        violators = _cyrillic_violations(content)
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
    valid_last_items = ["run checklist-linter", "run prompt-linter", "run prompt linter", "запуск линтера-чеклиста"]
    if not any(item in cleaned_last_text for item in valid_last_items):
        errors.append("Error: Last item must be 'run checklist-linter' or 'запуск линтера-чеклиста'.")

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

    required_sections = ["Changes made", "What was tested", "Validation results"]
    for sec in required_sections:
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


def check_memory_integrity(workspace_path: str, cfg: AethelConfig | None = None) -> bool:
    """Validates memory.json graph integrity in the workspace."""
    cfg = _resolve_cfg(workspace_path, cfg)
    print("--- Running Memory Graph Integrity Validation ---")
    memory_path = os.path.join(workspace_path, "memory.json")

    if not os.path.exists(memory_path):
        print_error(f"Memory database '{memory_path}' not found!")
        return False

    allowed_entity_types = sorted(cfg.entity_types)
    allowed_relation_types = sorted(cfg.relation_types)

    entities: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []
    line_number = 0
    has_errors = False

    with open(memory_path, "r", encoding="utf-8") as f:
        for line in f:
            line_number += 1
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print_error(f"Line {line_number}: Invalid JSON syntax - {e}")
                has_errors = True
                continue

            record_type = data.get("type")
            if record_type == "entity":
                name = data.get("name")
                entity_type = data.get("entityType")
                observations = data.get("observations", [])

                if not name:
                    print_error(f"Line {line_number}: Entity is missing 'name'.")
                    has_errors = True
                elif name in entities:
                    print_warning(f"Line {line_number}: Entity '{name}' is duplicated.")
                else:
                    entities[name] = {"entityType": entity_type, "observations": observations, "line": line_number}

                if entity_type not in cfg.entity_types:
                    print_error(f"Line {line_number}: Entity '{name}' has invalid entityType '{entity_type}'. Allowed types: {allowed_entity_types}")
                    has_errors = True

                for obs in observations:
                    if any(placeholder in obs for placeholder in cfg.placeholder_markers):
                        print_warning(f"Line {line_number}: Entity '{name}' observation contains placeholder: '{obs}'")

            elif record_type == "relation":
                from_node = data.get("from")
                to_node = data.get("to")
                rel_type = data.get("relationType")

                if not from_node or not to_node or not rel_type:
                    print_error(f"Line {line_number}: Relation is missing 'from', 'to', or 'relationType'.")
                    has_errors = True
                else:
                    relations.append({"from": from_node, "to": to_node, "relationType": rel_type, "line": line_number})

                if rel_type and rel_type not in cfg.relation_types:
                    print_error(f"Line {line_number}: Relation '{from_node}' -> '{to_node}' has invalid relationType '{rel_type}'. Allowed types: {allowed_relation_types}")
                    has_errors = True
            else:
                print_warning(f"Line {line_number}: Unknown record type '{record_type}'. Skipping.")

    if has_errors:
        return False

    # Check 1: Mandatory core nodes
    if not entities:
        print_error("No entities found in memory.json.")
        has_errors = True

    # Check 2: Broken Relations
    for rel in relations:
        if rel["from"] not in entities:
            print_error(f"Line {rel['line']}: Relation 'from' node '{rel['from']}' does not exist in entities.")
            has_errors = True
        if rel["to"] not in entities:
            print_error(f"Line {rel['line']}: Relation 'to' node '{rel['to']}' does not exist in entities.")
            has_errors = True

    # Check 3: Orphan Rules/Entities
    connected_entities = set()
    for rel in relations:
        connected_entities.add(rel["from"])
        connected_entities.add(rel["to"])

    for entity_name in entities:
        if entity_name not in connected_entities:
            print_warning(f"Orphan entity detected: '{entity_name}' (no relations link to or from it).")

    # Check 4: Cycle detection (iterative DFS to avoid recursion limits on large graphs)
    adj: dict[str, list[str]] = {name: [] for name in entities}
    for rel in relations:
        if rel["from"] in adj:
            adj[rel["from"]].append(rel["to"])

    if _has_cycle(adj):
        has_errors = True

    if not has_errors:
        print_success("Knowledge Graph integrity check passed successfully.")
        return True
    else:
        return False


def _has_cycle(adj: dict[str, list[str]]) -> bool:
    """Iterative DFS cycle detection. Reports the first back-edge found.

    States: 0/absent = unvisited, 1 = on current stack, 2 = fully explored.
    """
    visited: dict[str, int] = {}
    cycle_detected = False

    for start in adj:
        if start in visited:
            continue
        # Stack holds (node, iterator over neighbors).
        stack: list[tuple[str, Any]] = [(start, iter(adj.get(start, [])))]
        visited[start] = 1
        while stack:
            node, neighbors = stack[-1]
            advanced = False
            for neighbor in neighbors:
                state = visited.get(neighbor)
                if state == 1:
                    print_error(f"Dependency cycle detected involving node: '{node}' -> '{neighbor}'.")
                    cycle_detected = True
                elif state is None:
                    visited[neighbor] = 1
                    stack.append((neighbor, iter(adj.get(neighbor, []))))
                    advanced = True
                    break
            if not advanced:
                visited[node] = 2
                stack.pop()

    return cycle_detected


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

    # 1. Verify core files presence
    core_files = ["AETHEL.md", "CONTEXT.md", "memory.json", ".gitattributes"]
    for core_file in core_files:
        fpath = os.path.join(workspace_path, core_file)
        if not os.path.exists(fpath):
            print_error(f"Core Aethel file '{core_file}' is missing from the workspace root.")
            has_errors = True
        else:
            print_success(f"Core file present: {core_file}")

    # 1.1 Verify CONTEXT.md does not contain boilerplate placeholders + required headers
    context_path = os.path.join(workspace_path, "CONTEXT.md")
    if os.path.exists(context_path):
        try:
            with open(context_path, "r", encoding="utf-8") as fh:
                ctx_content = fh.read()
            placeholders = ["[e.g. Next.js 15", "[Insert SQL DDL"]
            for ph in placeholders:
                if ph in ctx_content:
                    print_warning(f"CONTEXT.md contains default template placeholder '{ph}'. Please populate it with actual project details.")
            if _check_required_headers("CONTEXT.md", ctx_content, cfg.context_headers, cfg):
                has_errors = True
        except Exception as e:
            print_error(f"Failed to read CONTEXT.md for structural checks: {e}")
            has_errors = True

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

    # 2. Verify gitattributes configuration
    gitattrib_path = os.path.join(workspace_path, ".gitattributes")
    if os.path.exists(gitattrib_path):
        try:
            with open(gitattrib_path, "r", encoding="utf-8") as fh:
                content = fh.read()
            if "memory.json" not in content:
                print_error("File '.gitattributes' exists but does not configure 'memory.json' merge rule.")
                has_errors = True
            else:
                print_success("Git attributes merge configuration for memory.json is valid.")
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
        "Update the knowledge graph / CONTEXT.md (Route C), or set "
        "AETHEL_SKIP_SYNC=1 for an intentionally spec-irrelevant commit."
    )
    if cfg.sync_enforce == "error":
        print_error(msg)
        return False
    print_warning(msg)
    return True


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
    memory_ok = check_memory_integrity(workspace_path, cfg)
    print()
    hygiene_ok = check_workspace_hygiene(workspace_path, other_checks_passed=(plan_ok and memory_ok), cfg=cfg)
    print()
    return plan_ok and memory_ok and hygiene_ok


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
        sys.exit(0 if check_spec_sync(workspace, cfg) else 1)
    else:
        # Parameterless run / General checks (Pre-commit hook default)
        plan_ok = check_plan_stage(workspace, cfg)
        print()
        memory_ok = check_memory_integrity(workspace, cfg)
        print()
        hygiene_ok = check_workspace_hygiene(workspace, other_checks_passed=(plan_ok and memory_ok), cfg=cfg)
        print()
        sync_ok = check_spec_sync(workspace, cfg)

        if plan_ok and memory_ok and hygiene_ok and sync_ok:
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
