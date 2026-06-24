#!/usr/bin/env python3
import glob
import os
import re
import subprocess
import sys
import tempfile
import time

# Ensure c:\aethel is in PYTHONPATH for subprocesses
ENV = os.environ.copy()
ENV["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ANSI Color Codes
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def print_banner(title):
    print("\n==========================================")
    print(f"=== {title}")
    print("==========================================\n")

def run_cmd(args, cwd, expected_code=0, env=None):
    print(f"Running in {cwd}: {' '.join(args)}")
    res = subprocess.run(args, cwd=cwd, env=env or ENV, capture_output=True, text=True)
    if res.returncode != expected_code:
        print(f"STDOUT:\n{res.stdout}")
        print(f"STDERR:\n{res.stderr}")
        print(f"Error: expected exit code {expected_code}, got {res.returncode}")
        sys.exit(1)
    return res

def test_scenario_a(temp_dir):
    print_banner("Scenario A: Clean Slate")
    scen_dir = os.path.join(temp_dir, "scenario_a")
    os.makedirs(scen_dir)

    # Init git first to test git hook creation
    run_cmd(["git", "init"], scen_dir)

    # Run aethel init
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)

    # Verify core files (memory.json retired; AGENTS.md is the universal entry point)
    core_files = ["AETHEL.md", "AGENTS.md", "CONTEXT.md", ".gitattributes", "CLAUDE.md", "GEMINI.md", "prompt_linter.py"]
    for f in core_files:
        path = os.path.join(scen_dir, f)
        assert os.path.exists(path), f"File {f} not created"
    assert not os.path.exists(os.path.join(scen_dir, "memory.json")), "memory.json must no longer be scaffolded"
    assert os.path.isdir(os.path.join(scen_dir, "knowledge")), "knowledge/ topic tree not scaffolded"
    with open(os.path.join(scen_dir, ".gitattributes"), "r", encoding="utf-8") as f:
        assert "text=auto" in f.read(), ".gitattributes should declare '* text=auto'"

    # Verify git pre-commit hook
    hook_path = os.path.join(scen_dir, ".git", "hooks", "pre-commit")
    assert os.path.exists(hook_path), "Git pre-commit hook not created"

    # 2. Test recipe initialization
    run_cmd([sys.executable, "-m", "aethel.cli", "init", "--recipe", "python"], scen_dir)

    # Verify recipe files created
    assert os.path.exists(os.path.join(scen_dir, ".ruff.toml")), ".ruff.toml not created by python recipe"
    assert os.path.exists(os.path.join(scen_dir, "semgrep-rules.yaml")), "semgrep-rules.yaml not created by python recipe"

    # Verify custom recipe guidelines appended to AETHEL.md
    with open(os.path.join(scen_dir, "AETHEL.md"), "r", encoding="utf-8") as f:
        aethel_content = f.read()
    assert "Python Linting & Code Verification Rules" in aethel_content, "Recipe guidelines not appended to AETHEL.md"

    # 3. Test safety/non-destructive check: modify .ruff.toml and verify it is not overwritten
    with open(os.path.join(scen_dir, ".ruff.toml"), "w", encoding="utf-8") as f:
        f.write("# User custom config\n")

    run_cmd([sys.executable, "-m", "aethel.cli", "init", "--recipe", "python"], scen_dir)

    with open(os.path.join(scen_dir, ".ruff.toml"), "r", encoding="utf-8") as f:
        ruff_content = f.read()
    assert ruff_content == "# User custom config\n", "Existing configuration file was overwritten"

    # 4. Discovery hygiene: cache dirs must never be copied into the workspace.
    assert not os.path.exists(os.path.join(scen_dir, ".ruff_cache")), \
        ".ruff_cache leaked into the deployed workspace"

    # 5. Unknown recipe is rejected at runtime (no argparse choices) and lists options.
    res = run_cmd(
        [sys.executable, "-m", "aethel.cli", "init", "--recipe", "zzz"],
        scen_dir, expected_code=2,
    )
    assert "unknown recipe 'zzz'" in res.stdout.lower(), "Unknown recipe not reported"
    assert "python" in res.stdout and "javascript" in res.stdout, "Discovered recipes not listed"

    print(f"{GREEN}[PASS] Scenario A completed successfully.{RESET}")

def test_scenario_b(temp_dir):
    print_banner("Scenario B: Legacy Migration")
    scen_dir = os.path.join(temp_dir, "scenario_b")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)

    # Create legacy files
    with open(os.path.join(scen_dir, "GEMINI.md"), "w", encoding="utf-8") as f:
        f.write("# Old Gemini Rules\nLegacy content here.")
    with open(os.path.join(scen_dir, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write("# Old Claude Rules\nLegacy content here.")

    # Run aethel init
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)

    # Verify legacy rename
    assert os.path.exists(os.path.join(scen_dir, "LEGACY_GEMINI.md")), "Legacy GEMINI.md not renamed"
    assert os.path.exists(os.path.join(scen_dir, "LEGACY_CLAUDE.md")), "Legacy CLAUDE.md not renamed"

    # Verify linter fails due to LEGACY_* and AETHEL_ONBOARDING.md
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # Resolve legacy and onboarding files
    os.remove(os.path.join(scen_dir, "LEGACY_GEMINI.md"))
    os.remove(os.path.join(scen_dir, "LEGACY_CLAUDE.md"))
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Verify linter passes now
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario B completed successfully.{RESET}")

def test_scenario_c(temp_dir):
    print_banner("Scenario C: Active Dev")
    scen_dir = os.path.join(temp_dir, "scenario_c")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # 1. Test Plan syntax
    plan_path = os.path.join(scen_dir, "implementation_plan.md")
    # Invalid plan
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write("# Missing other headers\n")
    run_cmd([sys.executable, "prompt_linter.py", "--stage", "plan"], scen_dir, expected_code=1)

    # Valid plan
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write("""# Goal Description
Test Goal.

## User Review Required
None.

## Open Questions
None.

## Proposed Changes
### Component
- [MODIFY] file.py

## Verification Plan
### Automated Tests
pytest
""")
    run_cmd([sys.executable, "prompt_linter.py", "--stage", "plan"], scen_dir, expected_code=0)

    # 2. Test Checklist syntax
    task_path = os.path.join(scen_dir, "task.md")
    # Invalid task.md (incomplete checklist item)
    with open(task_path, "w", encoding="utf-8") as f:
        f.write("- [ ] pending task\n- [x] run prompt-linter\n")
    run_cmd([sys.executable, "prompt_linter.py", "--stage", "checklist"], scen_dir, expected_code=1)

    # Valid task.md
    with open(task_path, "w", encoding="utf-8") as f:
        f.write("- [x] completed task\n- [x] run prompt-linter\n")
    run_cmd([sys.executable, "prompt_linter.py", "--stage", "checklist"], scen_dir, expected_code=0)

    # 3. Test missing required header in AETHEL.md (knowledge-index integrity is
    # covered by Scenario K; the memory.json graph checks are retired).
    aethel_file = os.path.join(scen_dir, "AETHEL.md")
    with open(aethel_file, "r", encoding="utf-8") as f:
        original_aethel = f.read()

    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(original_aethel.replace("## 6. Response Rules", "## 6. Deleted Rules"))
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(original_aethel)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario C completed successfully.{RESET}")

def test_scenario_d(temp_dir):
    print_banner("Scenario D: Production Scale")
    scen_dir = os.path.join(temp_dir, "scenario_d")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Generate 150 knowledge topic files and link every one from the index, so the
    # knowledge-index check resolves 150 links and finds zero orphans. (Reset the
    # scaffolded seed first so the topic count is exactly 150.)
    knowledge_dir = os.path.join(scen_dir, "knowledge")
    if os.path.isdir(knowledge_dir):
        import shutil as _shutil
        _shutil.rmtree(knowledge_dir)
    os.makedirs(knowledge_dir, exist_ok=True)
    links = []
    for i in range(150):
        topic = f"topic_{i}.md"
        with open(os.path.join(knowledge_dir, topic), "w", encoding="utf-8") as f:
            f.write(f"---\nname: topic-{i}\ndescription: scale topic {i}.\n---\n\n# Topic {i}\n")
        links.append(f"- [Topic {i}](knowledge/{topic}) — scale topic {i}.")
    with open(os.path.join(scen_dir, "CONTEXT.md"), "w", encoding="utf-8") as f:
        f.write("# Index\n\n> scale index\n\n## Topics\n" + "\n".join(links) + "\n")

    # Measure runtime of linter
    start_time = time.time()
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    duration = time.time() - start_time
    print(f"Linter duration for a 150-topic knowledge index: {duration:.3f} seconds.")
    # Duration includes `python -m aethel.cli` subprocess/interpreter startup, not just the
    # lint algorithm - a 1.0s threshold was observed to fail on a merely-busy machine with NO
    # code change (confirmed via `git stash`). 5.0s is generous enough to stop being flaky while
    # still catching a genuine O(n^2)-on-topic-count regression.
    assert duration < 5.0, "Linter is too slow on a large knowledge index"

    print(f"{GREEN}[PASS] Scenario D completed successfully.{RESET}")

def test_scenario_e(temp_dir):
    print_banner("Scenario E: Library Upgrade & Migration")
    scen_dir = os.path.join(temp_dir, "scenario_e")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)

    # Onboarding file is initially created; let's remove it to simulate an active, configured project
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Add a custom rule to AETHEL.md to simulate project custom rules
    aethel_path = os.path.join(scen_dir, "AETHEL.md")
    with open(aethel_path, "a", encoding="utf-8") as f:
        f.write("\n- [G-999]: Project specific custom rule.\n")

    # Simulate library update: run aethel update
    run_cmd([sys.executable, "-m", "aethel.cli", "update"], scen_dir)

    # Verify backup is created with timestamp pattern
    backups = glob.glob(os.path.join(scen_dir, "AETHEL.md.bak.*"))
    assert len(backups) == 1, "Timestamped backup was not created"
    backup_file = backups[0]
    print(f"Backup file found: {backup_file}")

    # Verify backup contains the custom rule
    with open(backup_file, "r", encoding="utf-8") as f:
        backup_content = f.read()
    assert "[G-999]: Project specific custom rule." in backup_content, "Backup does not contain original custom rules"

    # Verify the custom rule is PRESERVED (it lives outside the managed core block)
    with open(aethel_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert "[G-999]: Project specific custom rule." in new_content, "Custom rule was lost during update"
    # Verify the managed core block was refreshed and markers are intact
    assert "AETHEL:MANAGED:BEGIN id=aethel-core" in new_content, "Managed core marker missing after update"

    # Verify AETHEL_ONBOARDING.md is created (review gate for the refreshed rules)
    onboarding_path = os.path.join(scen_dir, "AETHEL_ONBOARDING.md")
    assert os.path.exists(onboarding_path), "AETHEL_ONBOARDING.md not created during update"

    # Verify Case C guidelines are in AETHEL_ONBOARDING.md
    with open(onboarding_path, "r", encoding="utf-8") as f:
        onboarding_content = f.read()
    assert "Case C: Library Upgrade & Rules Merging" in onboarding_content, "Case C not found in onboarding guidelines"

    # Verify linter fails as long as AETHEL_ONBOARDING.md is present
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # Developer reviews and deletes onboarding file; no manual re-merge required now
    os.remove(onboarding_path)

    # Verify linter passes now
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario E completed successfully.{RESET}")

def test_scenario_f(temp_dir):
    print_banner("Scenario F: Custom aethel.toml structure policy (enforce=off)")
    scen_dir = os.path.join(temp_dir, "scenario_f")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Break a required AETHEL.md header -> structure check fails by default.
    aethel_file = os.path.join(scen_dir, "AETHEL.md")
    with open(aethel_file, "r", encoding="utf-8") as f:
        original_aethel = f.read()
    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(original_aethel.replace("## 6. Response Rules", "## 6. Removed"))
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # Disable the structural header check via config -> lint passes again.
    with open(os.path.join(scen_dir, "aethel.toml"), "w", encoding="utf-8") as f:
        f.write('[structure]\nenforce = "off"\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario F completed successfully.{RESET}")

def test_scenario_g(temp_dir):
    print_banner("Scenario G: Non-destructive update preserves user files")
    scen_dir = os.path.join(temp_dir, "scenario_g")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # User adds a custom file inside the managed .agents tree.
    user_agent_file = os.path.join(scen_dir, ".agents", "user_custom.txt")
    with open(user_agent_file, "w", encoding="utf-8") as f:
        f.write("custom user agent asset")

    # User adds a custom rule below the managed block in AETHEL.md.
    aethel_path = os.path.join(scen_dir, "AETHEL.md")
    with open(aethel_path, "a", encoding="utf-8") as f:
        f.write("\n- [G-777]: Keep me across updates.\n")

    run_cmd([sys.executable, "-m", "aethel.cli", "update"], scen_dir)

    # User file under .agents must survive (merge is non-destructive).
    assert os.path.exists(user_agent_file), ".agents user file was deleted by update"
    with open(user_agent_file, "r", encoding="utf-8") as f:
        assert f.read() == "custom user agent asset", ".agents user file content was altered"

    # Shipped plugin file must still be present (refreshed).
    plugin_file = os.path.join(scen_dir, ".agents", "plugins", "aethel-plugin", "plugin.json")
    assert os.path.exists(plugin_file), "Shipped plugin file missing after update"

    # Custom AETHEL.md rule must be preserved.
    with open(aethel_path, "r", encoding="utf-8") as f:
        assert "[G-777]: Keep me across updates." in f.read(), "Custom AETHEL.md rule lost during update"

    print(f"{GREEN}[PASS] Scenario G completed successfully.{RESET}")

def test_scenario_h(temp_dir):
    print_banner("Scenario H: Spec-Sync drift guard")
    scen_dir = os.path.join(temp_dir, "scenario_h")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd(["git", "config", "user.email", "polygon@aethel.test"], scen_dir)
    run_cmd(["git", "config", "user.name", "Polygon"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Establish HEAD: the drift guard is intentionally inert before the first commit.
    run_cmd(["git", "add", "-A"], scen_dir)
    run_cmd(["git", "commit", "--no-verify", "-m", "chore: scaffold"], scen_dir)

    def reset_stage():
        run_cmd(["git", "reset", "-q"], scen_dir)

    code_file = os.path.join(scen_dir, "module.py")
    with open(code_file, "w", encoding="utf-8") as f:
        f.write("def f():\n    return 1\n")

    # 1. Drift under default 'warn': code staged, no spec -> warning, but commit not blocked.
    run_cmd(["git", "add", "module.py"], scen_dir)
    res = run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    assert "Spec drift" in res.stdout, "Drift warning not emitted in warn mode"

    # 2. Drift under 'error': same staged set must block.
    with open(os.path.join(scen_dir, "aethel.toml"), "w", encoding="utf-8") as f:
        f.write('[sync]\nenforce = "error"\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # 3. No drift: staging a spec file alongside code passes even under 'error'.
    with open(os.path.join(scen_dir, "CONTEXT.md"), "a", encoding="utf-8") as f:
        f.write("\n<!-- touched for sync -->\n")
    run_cmd(["git", "add", "CONTEXT.md"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # 4. Escape hatch: code-only staged under 'error' but AETHEL_SKIP_SYNC=1 bypasses.
    reset_stage()
    run_cmd(["git", "add", "module.py"], scen_dir)
    skip_env = dict(ENV)
    skip_env["AETHEL_SKIP_SYNC"] = "1"
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0, env=skip_env)

    # 5. Ignored/doc-only change must never count as code drift (even under 'error').
    reset_stage()
    with open(os.path.join(scen_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Readme change\n")
    run_cmd(["git", "add", "README.md"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario H completed successfully.{RESET}")

def test_scenario_i(temp_dir):
    print_banner("Scenario I: Core consistency standard")
    scen_dir = os.path.join(temp_dir, "scenario_i")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    aethel_file = os.path.join(scen_dir, "AETHEL.md")
    with open(aethel_file, "r", encoding="utf-8") as f:
        original = f.read()

    # Baseline: a freshly-deployed workspace is consistent with the core.
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # Editing INSIDE the managed core block is a principled disagreement.
    tampered = original.replace("**Be concise.**", "**Be verbose and chatty.**")
    assert tampered != original, "test setup: marker text not found in core block"
    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(tampered)
    res = run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    assert "diverges from the installed Aethel core" in res.stdout, "Core divergence not reported (warn)"

    # Under enforce='error' the in-block edit must block.
    with open(os.path.join(scen_dir, "aethel.toml"), "w", encoding="utf-8") as f:
        f.write('[consistency]\nenforce = "error"\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # Restore the core block and EXTEND below it (the allowed asymmetry): consistent again
    # even while enforce=error is still configured.
    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(original + "\n- [G-321]: project rule below the core block.\n")
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # Drop the enforce=error override so the skew sub-case runs at defaults.
    os.remove(os.path.join(scen_dir, "aethel.toml"))

    # Version skew: downgrade ONLY the core-version stamp (structure intact). This is a
    # stale workspace, not a fork -> warn "run aethel update", but DO NOT block.
    with open(aethel_file, "r", encoding="utf-8") as f:
        stamped = f.read()
    assert "AETHEL:CORE-VERSION" in stamped, "deployed core block is missing the version stamp"
    skewed = re.sub(r"(AETHEL:CORE-VERSION)\s+\S+", r"\1 0.0.1", stamped, count=1)
    assert skewed != stamped, "test setup: version stamp not found to downgrade"
    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(skewed)
    res = run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    assert "version skew" in res.stdout.lower(), "version skew not reported"
    assert "aethel update" in res.stdout.lower(), "skew message should point to `aethel update`"

    # Promoting version_skew_enforce to error makes the same skew block.
    with open(os.path.join(scen_dir, "aethel.toml"), "w", encoding="utf-8") as f:
        f.write('[consistency]\nversion_skew_enforce = "error"\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # `aethel update` refreshes the stamp back to the library core version -> clean again.
    os.remove(os.path.join(scen_dir, "aethel.toml"))
    run_cmd([sys.executable, "-m", "aethel.cli", "update"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario I completed successfully.{RESET}")

def test_scenario_j(temp_dir):
    print_banner("Scenario J: Changelog-Sync drift guard for rule changes")
    scen_dir = os.path.join(temp_dir, "scenario_j")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd(["git", "config", "user.email", "polygon@aethel.test"], scen_dir)
    run_cmd(["git", "config", "user.name", "Polygon"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Establish HEAD: the guard is intentionally inert before the first commit.
    run_cmd(["git", "add", "-A"], scen_dir)
    run_cmd(["git", "commit", "--no-verify", "-m", "chore: scaffold"], scen_dir)

    def reset_stage():
        run_cmd(["git", "reset", "-q"], scen_dir)

    aethel_file = os.path.join(scen_dir, "AETHEL.md")
    # Extend BELOW the managed core block so core-consistency stays green while the
    # rule file still registers as changed.
    with open(aethel_file, "a", encoding="utf-8") as f:
        f.write("\n- [G-9]: project-specific rule.\n")

    # 1. Rule file staged, no changelog, default 'warn' -> warning but commit not blocked.
    run_cmd(["git", "add", "AETHEL.md"], scen_dir)
    res = run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    assert "Changelog drift" in res.stdout, "Changelog drift warning not emitted in warn mode"

    # 2. Under 'error' the same staged set must block.
    with open(os.path.join(scen_dir, "aethel.toml"), "w", encoding="utf-8") as f:
        f.write('[sync]\nrequire_changelog = "error"\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # 3. Pairing CHANGELOG.md with the rule change passes even under 'error'.
    with open(os.path.join(scen_dir, "CHANGELOG.md"), "w", encoding="utf-8") as f:
        f.write("# Changelog\n\n## [Unreleased]\n- documented the rule change\n")
    run_cmd(["git", "add", "CHANGELOG.md"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # 4. Escape hatch: rule-only staged under 'error' but AETHEL_SKIP_SYNC=1 bypasses.
    reset_stage()
    run_cmd(["git", "add", "AETHEL.md"], scen_dir)
    skip_env = dict(ENV)
    skip_env["AETHEL_SKIP_SYNC"] = "1"
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0, env=skip_env)

    print(f"{GREEN}[PASS] Scenario J completed successfully.{RESET}")

def test_scenario_k(temp_dir):
    print_banner("Scenario K: Knowledge index drift (dead link = error, orphan = warn)")
    scen_dir = os.path.join(temp_dir, "scenario_k")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Baseline: the scaffolded index + knowledge seed lints clean.
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    ctx_file = os.path.join(scen_dir, "CONTEXT.md")
    with open(ctx_file, "r", encoding="utf-8") as f:
        original_ctx = f.read()

    # 1. A dead inline link in the index is an error (default dead_link_enforce="error").
    with open(ctx_file, "a", encoding="utf-8") as f:
        f.write("\n- [Gone](knowledge/does-not-exist.md) - dead link\n")
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # Restore the clean index.
    with open(ctx_file, "w", encoding="utf-8") as f:
        f.write(original_ctx)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # 2. An unlinked topic file is an orphan WARNING (non-blocking by default).
    with open(os.path.join(scen_dir, "knowledge", "orphan.md"), "w", encoding="utf-8") as f:
        f.write("# Orphan topic\n")
    res = run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    assert "Orphan knowledge file" in res.stdout, "Orphan warning not emitted in warn mode"

    # 3. Promoting orphan_enforce to "error" makes the same orphan block.
    with open(os.path.join(scen_dir, "aethel.toml"), "w", encoding="utf-8") as f:
        f.write('[knowledge]\norphan_enforce = "error"\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    print(f"{GREEN}[PASS] Scenario K completed successfully.{RESET}")

def test_scenario_l(temp_dir):
    print_banner("Scenario L: Walkthrough-report drift guard (Route B + staged code)")
    scen_dir = os.path.join(temp_dir, "scenario_l")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd(["git", "config", "user.email", "polygon@aethel.test"], scen_dir)
    run_cmd(["git", "config", "user.name", "Polygon"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Establish HEAD: the guard is inert before the first commit.
    run_cmd(["git", "add", "-A"], scen_dir)
    run_cmd(["git", "commit", "--no-verify", "-m", "chore: scaffold"], scen_dir)

    valid_report = (
        "# Walkthrough\n\n## Summary\nDid the thing.\n\n## Changes made\n- module.py\n\n"
        "## What was tested\n- aethel lint\n\n## Validation results\n- green\n"
    )

    # A Route B task is active (task.md present) and a code file is staged.
    with open(os.path.join(scen_dir, "task.md"), "w", encoding="utf-8") as f:
        f.write("- [x] done\n- [x] run prompt-linter\n")
    with open(os.path.join(scen_dir, "module.py"), "w", encoding="utf-8") as f:
        f.write("def f():\n    return 1\n")
    run_cmd(["git", "add", "module.py"], scen_dir)

    # 1. No walkthrough.md -> guard blocks at default 'error'.
    res = run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)
    assert "Walkthrough drift" in res.stdout, "Walkthrough drift not reported"

    # 2. A valid walkthrough.md -> passes.
    report_path = os.path.join(scen_dir, "walkthrough.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(valid_report)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # 3. Escape hatch: remove the report, AETHEL_SKIP_SYNC=1 bypasses.
    os.remove(report_path)
    skip_env = dict(ENV)
    skip_env["AETHEL_SKIP_SYNC"] = "1"
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0, env=skip_env)

    # 4. Not a Route B task: remove task.md -> passes even with code staged, no report.
    os.remove(os.path.join(scen_dir, "task.md"))
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario L completed successfully.{RESET}")

def test_scenario_m(temp_dir):
    print_banner("Scenario M: Multi-slot session lifecycle (start / sessions / switch / done / abandon)")
    scen_dir = os.path.join(temp_dir, "scenario_m")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd(["git", "config", "user.email", "polygon@aethel.test"], scen_dir)
    run_cmd(["git", "config", "user.name", "Polygon"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    aethel_dir = os.path.join(scen_dir, ".aethel")

    # `.aethel/` is gitignored by init.
    with open(os.path.join(scen_dir, ".gitignore"), "r", encoding="utf-8") as f:
        assert ".aethel" in f.read(), "init did not gitignore the .aethel/ tree"

    def current_session(d):
        with open(os.path.join(d, ".aethel", "CURRENT"), "r", encoding="utf-8") as fh:
            return fh.read().strip()

    valid_report = (
        "# Walkthrough\n\n## Summary\nDid the thing.\n\n## Changes made\n- module.py\n\n"
        "## What was tested\n- aethel lint\n\n## Validation results\n- green\n"
    )

    # 1. `aethel start` opens a session dir + CURRENT pointer.
    run_cmd([sys.executable, "-m", "aethel.cli", "start", "feat-one"], scen_dir)
    assert os.path.exists(os.path.join(aethel_dir, "CURRENT")), "CURRENT pointer not written"
    first_id = current_session(scen_dir)
    first_dir = os.path.join(aethel_dir, "sessions", first_id)
    assert os.path.isdir(first_dir), "session dir not created"
    assert first_id.endswith("-feat-one"), "run-id did not carry the slug"

    # 2. `aethel done` refuses without a valid report (session stays active).
    run_cmd([sys.executable, "-m", "aethel.cli", "done"], scen_dir, expected_code=1)

    # 3. Multi-slot: a SECOND `aethel start` leaves feat-one LIVE (no reconcile/archive).
    run_cmd([sys.executable, "-m", "aethel.cli", "start", "feat-two"], scen_dir)
    second_id = current_session(scen_dir)
    second_dir = os.path.join(aethel_dir, "sessions", second_id)
    assert second_id != first_id, "second start reused the first run-id"
    assert os.path.isdir(first_dir), "second start archived the first session (single-slot regression)"
    assert os.path.isdir(second_dir), "second session dir not created"
    assert not os.path.isdir(os.path.join(aethel_dir, "archive", "_incomplete", first_id)), \
        "a start must not push a prior session into _incomplete/"

    # 4. `aethel sessions` lists both live sessions; `aethel switch` repoints CURRENT to feat-one.
    res = run_cmd([sys.executable, "-m", "aethel.cli", "sessions"], scen_dir)
    assert first_id in res.stdout and second_id in res.stdout, "sessions did not list both live sessions"
    run_cmd([sys.executable, "-m", "aethel.cli", "switch", first_id], scen_dir)
    assert current_session(scen_dir) == first_id, "switch did not repoint CURRENT"

    # 5. The walkthrough guard reads from the SELECTED session (CURRENT=feat-one): code staged +
    #    task.md in that session, no report -> blocks; +report -> passes.
    run_cmd(["git", "add", "-A"], scen_dir)
    run_cmd(["git", "commit", "--no-verify", "-m", "chore: scaffold"], scen_dir)
    with open(os.path.join(first_dir, "task.md"), "w", encoding="utf-8") as f:
        f.write("- [x] done\n- [x] run prompt-linter\n")
    with open(os.path.join(scen_dir, "module.py"), "w", encoding="utf-8") as f:
        f.write("def f():\n    return 1\n")
    run_cmd(["git", "add", "module.py"], scen_dir)
    res = run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)
    assert "Walkthrough drift" in res.stdout, "guard did not read task.md from the selected session dir"
    with open(os.path.join(first_dir, "walkthrough.md"), "w", encoding="utf-8") as f:
        f.write(valid_report)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # 6. `aethel done` validates the selected session AND archives it immediately, clearing CURRENT.
    run_cmd([sys.executable, "-m", "aethel.cli", "done"], scen_dir, expected_code=0)
    assert os.path.isdir(os.path.join(aethel_dir, "archive", first_id)), \
        "done did not archive the validated session under archive/<id>/"
    assert not os.path.isdir(first_dir), "validated session still in sessions/ after done"
    assert not os.path.exists(os.path.join(aethel_dir, "CURRENT")), "done did not clear CURRENT"
    assert os.path.isdir(second_dir), "done archived the wrong session (feat-two should stay live)"

    # 7. `aethel abandon --session <id>` archives a still-active session under _incomplete/.
    run_cmd([sys.executable, "-m", "aethel.cli", "abandon", "--session", second_id], scen_dir)
    assert os.path.isdir(os.path.join(aethel_dir, "archive", "_incomplete", second_id)), \
        "abandon did not archive the session under archive/_incomplete/<id>/"

    print(f"{GREEN}[PASS] Scenario M completed successfully.{RESET}")

def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")
        test_scenario_a(temp_dir)
        test_scenario_b(temp_dir)
        test_scenario_c(temp_dir)
        test_scenario_d(temp_dir)
        test_scenario_e(temp_dir)
        test_scenario_f(temp_dir)
        test_scenario_g(temp_dir)
        test_scenario_h(temp_dir)
        test_scenario_i(temp_dir)
        test_scenario_j(temp_dir)
        test_scenario_k(temp_dir)
        test_scenario_l(temp_dir)
        test_scenario_m(temp_dir)

    print(f"\n{GREEN}ALL TEST SCENARIOS PASSED SUCCESSFULLY!{RESET}\n")

if __name__ == "__main__":
    main()
