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


def print_success(msg: str) -> None:
    print(f"{GREEN}[PASS] {msg}{RESET}")


def print_warning(msg: str) -> None:
    print(f"{YELLOW}[WARN] {msg}{RESET}")


def print_error(msg: str) -> None:
    print(f"{RED}[FAIL] {msg}{RESET}")


def check_plan_stage(workspace_path: str) -> bool:
    """Validates implementation_plan.md and task.md format in the workspace."""
    print("--- Running Plan Stage Validation ---")

    plan_path = os.path.join(workspace_path, "implementation_plan.md")
    task_path = os.path.join(workspace_path, "task.md")

    # Check implementation plan
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_headers = [
            r"#\s+Implementation Plan",
            r"##\s+User Review Required",
            r"##\s+Proposed Changes",
            r"##\s+Verification Plan",
        ]

        missing = []
        for header in required_headers:
            if not re.search(header, content, re.IGNORECASE):
                missing.append(header.replace(r"\s+", " ").replace(r"## ", "").replace(r"# ", ""))

        if missing:
            print_warning(f"'{plan_path}' is missing suggested sections: {', '.join(missing)}")
        else:
            print_success(f"'{plan_path}' structure is valid.")
    else:
        print_warning(f"No '{plan_path}' found in workspace. Skipping.")

    # Check task list
    if os.path.exists(task_path):
        with open(task_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not re.search(r"-\s+`\[[ x/]\]`", content):
            print_error(f"'{task_path}' does not contain checklist items of format '- `[ ]`', '- `[/]`' or '- `[x]`'.")
            return False
        else:
            print_success(f"'{task_path}' format is valid.")
    else:
        print_warning(f"No '{task_path}' found in workspace. Skipping.")

    return True


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
    # (Since this is client-side validation, check if there's any entity at all)
    if not entities:
        print_error("No entities found in memory.json.")
        has_errors = True

    # Check 2: Broken Relations (pointing to non-existent nodes)
    for rel in relations:
        if rel["from"] not in entities:
            print_error(f"Line {rel['line']}: Relation 'from' node '{rel['from']}' does not exist in entities.")
            has_errors = True
        if rel["to"] not in entities:
            print_error(f"Line {rel['line']}: Relation 'to' node '{rel['to']}' does not exist in entities.")
            has_errors = True

    # Check 3: Orphan Rules/Entities (no relations)
    connected_entities = set()
    for rel in relations:
        connected_entities.add(rel["from"])
        connected_entities.add(rel["to"])

    for entity_name in entities:
        if entity_name not in connected_entities:
            print_warning(f"Orphan entity detected: '{entity_name}' (no relations link to or from it).")

    # Check 4: Cycle detection in rule/dependency graph
    adj: dict[str, list[str]] = {name: [] for name in entities}
    for rel in relations:
        if rel["from"] in adj:
            adj[rel["from"]].append(rel["to"])

    visited: dict[str, int] = {}  # None=unvisited, 1=visiting, 2=visited
    cycle_detected = False

    def dfs(node: str) -> None:
        nonlocal cycle_detected
        visited[node] = 1  # visiting
        for neighbor in adj.get(node, []):
            if visited.get(neighbor) == 1:
                print_error(f"Dependency cycle detected involving node: '{node}' -> '{neighbor}'.")
                cycle_detected = True
            elif neighbor not in visited:
                dfs(neighbor)
        visited[node] = 2  # visited

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


def run_linter(workspace_path: str = ".") -> bool:
    plan_ok = check_plan_stage(workspace_path)
    print()
    memory_ok = check_memory_integrity(workspace_path)
    print()

    if plan_ok and memory_ok:
        print_success("All linter checks PASSED.")
        return True
    else:
        print_error("Linter checks FAILED. Please resolve issues above.")
        return False


if __name__ == "__main__":
    success = run_linter()
    sys.exit(0 if success else 1)
