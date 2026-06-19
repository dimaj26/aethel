import argparse
import json
import os
import re
import sys
from typing import Any

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# Whitelist for Cyrillic words permitted in plans and checklists
PLAN_CYRILLIC_WHITELIST = {"шэф", "теңир-тоо", "тенир-тоо", "теңир", "тоо", "aethel"}


def print_success(msg: str) -> None:
    print(f"{GREEN}[PASS] {msg}{RESET}")


def print_warning(msg: str) -> None:
    print(f"{YELLOW}[WARN] {msg}{RESET}")


def print_error(msg: str) -> None:
    print(f"{RED}[FAIL] {msg}{RESET}")


def check_plan_file(workspace_path: str) -> tuple[list[str], list[str]]:
    """Validates implementation_plan.md format and language."""
    errors = []
    warnings = []
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

    # Language check
    cyrillic_words = re.findall(r"\b[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ\-]+\b", content)
    violating_words = [w for w in cyrillic_words if w.lower() not in PLAN_CYRILLIC_WHITELIST]
    if violating_words:
        unique_violators = sorted(list(set(violating_words)))
        display_words = ", ".join(unique_violators[:10])
        if len(unique_violators) > 10:
            display_words += "..."
        warnings.append(
            f"Cyrillic words found in plan: {display_words}. "
            "Implementation plan should be in English."
        )
    return errors, warnings


def check_checklist_file(workspace_path: str) -> tuple[list[str], list[str]]:
    """Validates task.md format and language."""
    errors = []
    warnings = []
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

    # Language check
    cyrillic_words = re.findall(r"\b[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ\-]+\b", content)
    violating_words = [w for w in cyrillic_words if w.lower() not in PLAN_CYRILLIC_WHITELIST]
    if violating_words:
        unique_violators = sorted(list(set(violating_words)))
        display_words = ", ".join(unique_violators[:10])
        if len(unique_violators) > 10:
            display_words += "..."
        warnings.append(
            f"Cyrillic words found in checklist: {display_words}. "
            "Checklist (task.md) should be in English."
        )
    return errors, warnings


def check_report_file(workspace_path: str) -> tuple[list[str], list[str]]:
    """Validates walkthrough.md format and language."""
    errors = []
    warnings = []
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

    has_cyrillic = bool(re.search(r"[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ]", content))
    if not has_cyrillic:
        warnings.append("No Cyrillic characters found in report. Walkthrough must be in Russian.")

    return errors, warnings


def check_plan_stage(workspace_path: str) -> bool:
    """Validates plan and task formats if they exist."""
    print("--- Running Plan Stage Validation ---")
    plan_path = os.path.join(workspace_path, "implementation_plan.md")
    task_path = os.path.join(workspace_path, "task.md")

    plan_ok = True
    if os.path.exists(plan_path):
        errs, warns = check_plan_file(workspace_path)
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
        errs, warns = check_checklist_file(workspace_path)
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


def check_memory_integrity(workspace_path: str) -> bool:
    """Validates memory.json graph integrity in the workspace."""
    print("--- Running Memory Graph Integrity Validation ---")
    memory_path = os.path.join(workspace_path, "memory.json")

    if not os.path.exists(memory_path):
        print_error(f"Memory database '{memory_path}' not found!")
        return False

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

            elif record_type == "relation":
                from_node = data.get("from")
                to_node = data.get("to")
                rel_type = data.get("relationType")

                if not from_node or not to_node or not rel_type:
                    print_error(f"Line {line_number}: Relation is missing 'from', 'to', or 'relationType'.")
                    has_errors = True
                else:
                    relations.append({"from": from_node, "to": to_node, "relationType": rel_type, "line": line_number})
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

    # Check 4: Cycle detection
    adj: dict[str, list[str]] = {name: [] for name in entities}
    for rel in relations:
        if rel["from"] in adj:
            adj[rel["from"]].append(rel["to"])

    visited: dict[str, int] = {}
    cycle_detected = False

    def dfs(node: str) -> None:
        nonlocal cycle_detected
        visited[node] = 1
        for neighbor in adj.get(node, []):
            if visited.get(neighbor) == 1:
                print_error(f"Dependency cycle detected involving node: '{node}' -> '{neighbor}'.")
                cycle_detected = True
            elif neighbor not in visited:
                dfs(neighbor)
        visited[node] = 2

    for node in entities:
        if node not in visited:
            dfs(node)

    if cycle_detected:
        has_errors = True

    if not has_errors:
        print_success("Knowledge Graph integrity check passed successfully.")
        return True
    else:
        return False


def check_workspace_hygiene(workspace_path: str, other_checks_passed: bool = True) -> bool:
    """Validates workspace core files, Git configuration, and cleans up onboarding files."""
    print("--- Running Workspace Hygiene Validation ---")
    has_errors = False

    # 1. Verify core files presence
    core_files = ["AETHEL.md", "CONTEXT.md", "memory.json", ".gitattributes"]
    for f in core_files:
        fpath = os.path.join(workspace_path, f)
        if not os.path.exists(fpath):
            print_error(f"Core Aethel file '{f}' is missing from the workspace root.")
            has_errors = True
        else:
            print_success(f"Core file present: {f}")

    # 1.1 Verify CONTEXT.md does not contain boilerplate placeholders
    context_path = os.path.join(workspace_path, "CONTEXT.md")
    if os.path.exists(context_path):
        try:
            with open(context_path, "r", encoding="utf-8") as f:
                ctx_content = f.read()
            placeholders = ["[e.g. Next.js 15", "[Insert SQL DDL"]
            for ph in placeholders:
                if ph in ctx_content:
                    print_warning(f"CONTEXT.md contains default template placeholder '{ph}'. Please populate it with actual project details.")
        except Exception as e:
            print_warning(f"Could not read CONTEXT.md for boilerplate verification: {e}")

    # 2. Verify gitattributes configuration
    gitattrib_path = os.path.join(workspace_path, ".gitattributes")
    if os.path.exists(gitattrib_path):
        try:
            with open(gitattrib_path, "r", encoding="utf-8") as f:
                content = f.read()
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
                with open(dfpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "aethel" in content.lower():
                    dep_found = True
                    break
            except Exception:
                pass
    if not dep_found:
        print_warning("Package 'aethel' is not declared as a dependency in requirements.txt, setup.py, or pyproject.toml.")

    return not has_errors


def run_linter(workspace_path: str = ".") -> bool:
    """Invoked internally by old API calls."""
    plan_ok = check_plan_stage(workspace_path)
    print()
    memory_ok = check_memory_integrity(workspace_path)
    print()
    hygiene_ok = check_workspace_hygiene(workspace_path, other_checks_passed=(plan_ok and memory_ok))
    print()
    return plan_ok and memory_ok and hygiene_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Aethel Prompt Linter for agent artifacts.")
    parser.add_argument("--dir", default=".", help="Directory containing the workspace/artifacts")
    parser.add_argument("--stage", choices=["plan", "checklist", "report"], help="Verification stage to run")

    args = parser.parse_args()
    workspace = os.path.abspath(args.dir)

    if not os.path.exists(workspace):
        print(f"Error: Directory {workspace} does not exist.")
        sys.exit(1)

    errors = []
    warnings = []

    if args.stage == "plan":
        errors, warnings = check_plan_file(workspace)
    elif args.stage == "checklist":
        errors, warnings = check_checklist_file(workspace)
    elif args.stage == "report":
        errors, warnings = check_report_file(workspace)
    else:
        # Parameterless run / General checks (Pre-commit hook default)
        plan_ok = check_plan_stage(workspace)
        print()
        memory_ok = check_memory_integrity(workspace)
        print()
        hygiene_ok = check_workspace_hygiene(workspace, other_checks_passed=(plan_ok and memory_ok))
        print()

        if plan_ok and memory_ok and hygiene_ok:
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
