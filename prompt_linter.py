#!/usr/bin/env python3
import argparse
import os
import re
import sys

# Whitelist for Cyrillic words permitted in plans and checklists
PLAN_CYRILLIC_WHITELIST = {"шэф", "теңир-тоо", "тенир-тоо", "теңир", "тоо", "aethel"}


def validate_plan(content: str) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []

    # 1. Structural Checks
    if not re.search(r"^#\s+\S+", content, re.MULTILINE):
        errors.append("Missing H1 Goal Description header (e.g., '# Goal Description').")

    required_h2s = ["User Review Required", "Open Questions", "Proposed Changes", "Verification Plan"]
    for h2 in required_h2s:
        if not re.search(r"^##\s+" + re.escape(h2), content, re.MULTILINE):
            errors.append(f"Missing required H2 section: '## {h2}'.")

    # 2. Language check (no Russian text in implementation plan except whitelist)
    cyrillic_words = re.findall(r"\b[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ\-]+\b", content)
    violating_words = []
    for word in cyrillic_words:
        if word.lower() not in PLAN_CYRILLIC_WHITELIST:
            violating_words.append(word)

    if violating_words:
        unique_violators = sorted(list(set(violating_words)))
        display_words = ", ".join(unique_violators[:10])
        if len(unique_violators) > 10:
            display_words += "..."
        warnings.append(
            f"Cyrillic words found in plan: {display_words}. "
            "Implementation plan should be in English (except whitelisted terms)."
        )

    return errors, warnings


def validate_checklist(content: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # Find all checklist lines: - [x] text or - `[x]` text
    checklist_pattern = re.compile(r"^\s*-\s*`?\[([ x/])\]`?\s*(.*)$")
    tasks = []
    for line in content.splitlines():
        match = checklist_pattern.match(line)
        if match:
            tasks.append((match.group(1), match.group(2).strip()))

    if not tasks:
        errors.append("No task checklist items found in task.md.")
        return errors, warnings

    # Check for incomplete tasks
    for status, text in tasks:
        if status in (" ", "/"):
            errors.append(f"Incomplete task: [{status}] {text}")

    # Check last task is checklist linter execution
    last_status, last_text = tasks[-1]
    cleaned_last_text = re.sub(r"[`_*]", "", last_text).lower()
    valid_last_items = [
        "run checklist-linter",
        "run prompt-linter",
        "run prompt linter",
        "запуск линтера-чеклиста",
    ]
    if not any(item in cleaned_last_text for item in valid_last_items):
        errors.append("Error: Last item must be 'run checklist-linter' or 'запуск линтера-чеклиста'.")

    # Checklist language check: Enforce no Cyrillic in task.md except whitelist
    cyrillic_words = re.findall(r"\b[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ\-]+\b", content)
    violating_words = []
    for word in cyrillic_words:
        if word.lower() not in PLAN_CYRILLIC_WHITELIST:
            violating_words.append(word)

    if violating_words:
        unique_violators = sorted(list(set(violating_words)))
        display_words = ", ".join(unique_violators[:10])
        if len(unique_violators) > 10:
            display_words += "..."
        warnings.append(
            f"Cyrillic words found in checklist: {display_words}. "
            "Checklist (task.md) should be in English (except whitelisted terms)."
        )

    return errors, warnings


def validate_report(content: str) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []

    # 1. Structural Checks
    required_sections = ["Changes made", "What was tested", "Validation results"]
    for sec in required_sections:
        pattern = re.compile(r"(?:^##?\s+|^\s*\*\*\s*)" + re.escape(sec), re.MULTILINE | re.IGNORECASE)
        if not pattern.search(content):
            errors.append(f"Missing required section or heading: '{sec}'.")

    # 2. Language check (must be in Russian, so check for presence of Cyrillic characters)
    has_cyrillic = bool(re.search(r"[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ]", content))
    if not has_cyrillic:
        warnings.append(
            "Warning: No Cyrillic characters found in report. Walkthrough/Report must be written in Russian."
        )

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Aethel Prompt Linter for agent artifacts.")
    parser.add_argument("--dir", required=True, help="Directory containing artifacts")
    parser.add_argument("--stage", required=True, choices=["plan", "checklist", "report"], help="Verification stage")

    args = parser.parse_args()

    if not os.path.exists(args.dir):
        print(f"Error: Directory {args.dir} does not exist.")
        sys.exit(1)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        if args.stage == "plan":
            filepath = os.path.join(args.dir, "implementation_plan.md")
            if not os.path.exists(filepath):
                print(f"Error: {filepath} not found.")
                sys.exit(1)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            errors, warnings = validate_plan(content)

        elif args.stage == "checklist":
            filepath = os.path.join(args.dir, "task.md")
            if not os.path.exists(filepath):
                print(f"Error: {filepath} not found.")
                sys.exit(1)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            errors, warnings = validate_checklist(content)

        elif args.stage == "report":
            filepath = os.path.join(args.dir, "walkthrough.md")
            if not os.path.exists(filepath):
                print(f"Error: {filepath} not found.")
                sys.exit(1)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            errors, warnings = validate_report(content)

    except Exception as e:
        print(f"Error reading or parsing file: {e}")
        sys.exit(1)

    if warnings:
        for w in warnings:
            print(f"Warning: {w}")

    if errors:
        for err in errors:
            print(f"Error: {err}")
        sys.exit(1)

    if args.stage == "plan":
        print("Plan is valid.")
    elif args.stage == "checklist":
        print("Checklist is valid.")
    elif args.stage == "report":
        print("Report is valid.")

    sys.exit(0)


if __name__ == "__main__":
    main()
