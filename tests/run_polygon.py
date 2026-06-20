#!/usr/bin/env python3
import glob
import os
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

    # Verify core files
    core_files = ["AETHEL.md", "CONTEXT.md", "memory.json", ".gitattributes", "CLAUDE.md", "GEMINI.md", "prompt_linter.py"]
    for f in core_files:
        path = os.path.join(scen_dir, f)
        assert os.path.exists(path), f"File {f} not created"

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

    # 3. Test Graph validation (cycles)
    memory_path = os.path.join(scen_dir, "memory.json")
    # Create dependency cycle
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write('{"type":"entity","name":"A","entityType":"Component","observations":[]}\n')
        f.write('{"type":"entity","name":"B","entityType":"Component","observations":[]}\n')
        f.write('{"type":"relation","from":"A","to":"B","relationType":"depends_on"}\n')
        f.write('{"type":"relation","from":"B","to":"A","relationType":"depends_on"}\n')

    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # Fix cycle
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write('{"type":"entity","name":"A","entityType":"Component","observations":[]}\n')
        f.write('{"type":"entity","name":"B","entityType":"Component","observations":[]}\n')
        f.write('{"type":"relation","from":"A","to":"B","relationType":"depends_on"}\n')

    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # 4. Test invalid entityType in memory.json
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write('{"type":"entity","name":"A","entityType":"invalid_type","observations":[]}\n')
        f.write('{"type":"entity","name":"B","entityType":"Component","observations":[]}\n')
        f.write('{"type":"relation","from":"A","to":"B","relationType":"depends_on"}\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # 5. Test invalid relationType in memory.json
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write('{"type":"entity","name":"A","entityType":"Component","observations":[]}\n')
        f.write('{"type":"entity","name":"B","entityType":"Component","observations":[]}\n')
        f.write('{"type":"relation","from":"A","to":"B","relationType":"invalid_rel"}\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # 6. Test placeholder warning in memory.json
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write('{"type":"entity","name":"A","entityType":"Component","observations":["Some observation [Insert details here]"]}\n')
        f.write('{"type":"entity","name":"B","entityType":"Component","observations":[]}\n')
        f.write('{"type":"relation","from":"A","to":"B","relationType":"depends_on"}\n')
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # Restore valid memory.json
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write('{"type":"entity","name":"A","entityType":"Component","observations":[]}\n')
        f.write('{"type":"entity","name":"B","entityType":"Component","observations":[]}\n')
        f.write('{"type":"relation","from":"A","to":"B","relationType":"depends_on"}\n')

    # 7. Test missing required header in CONTEXT.md
    ctx_file = os.path.join(scen_dir, "CONTEXT.md")
    with open(ctx_file, "r", encoding="utf-8") as f:
        original_ctx = f.read()

    with open(ctx_file, "w", encoding="utf-8") as f:
        f.write(original_ctx.replace("## 1. Project Directory Structure", "## 1. Deleted Header"))
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    with open(ctx_file, "w", encoding="utf-8") as f:
        f.write(original_ctx)
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    # 8. Test missing required header in AETHEL.md
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

    # Generate 100+ entities and relations in memory.json
    memory_path = os.path.join(scen_dir, "memory.json")
    with open(memory_path, "w", encoding="utf-8") as f:
        # Entities
        for i in range(150):
            f.write(f'{{"type":"entity","name":"Node_{i}","entityType":"Component","observations":[]}}\n')
        # Relations (linear chain to avoid cycles)
        for i in range(149):
            f.write(f'{{"type":"relation","from":"Node_{i}","to":"Node_{i+1}","relationType":"depends_on"}}\n')

    # Measure runtime of linter
    start_time = time.time()
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    duration = time.time() - start_time
    print(f"Linter duration for 150 nodes and 149 links: {duration:.3f} seconds.")
    assert duration < 1.0, "Linter is too slow on large graphs"

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
    print_banner("Scenario F: Custom aethel.toml ontology & structure policy")
    scen_dir = os.path.join(temp_dir, "scenario_f")
    os.makedirs(scen_dir)

    run_cmd(["git", "init"], scen_dir)
    run_cmd([sys.executable, "-m", "aethel.cli", "init"], scen_dir)
    os.remove(os.path.join(scen_dir, "AETHEL_ONBOARDING.md"))

    # Use a project-specific type that is NOT in the default ontology.
    memory_path = os.path.join(scen_dir, "memory.json")
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write('{"type":"entity","name":"Widget","entityType":"Widget","observations":[]}\n')
        f.write('{"type":"entity","name":"Store","entityType":"Widget","observations":[]}\n')
        f.write('{"type":"relation","from":"Widget","to":"Store","relationType":"binds"}\n')

    # Without config, "Widget"/"binds" are invalid -> lint fails.
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)

    # Provide a custom config that allows the project's ontology and disables
    # the structural header checks.
    with open(os.path.join(scen_dir, "aethel.toml"), "w", encoding="utf-8") as f:
        f.write(
            '[ontology]\n'
            'entity_types = ["Widget"]\n'
            'relation_types = ["binds"]\n\n'
            '[structure]\n'
            'enforce = "off"\n'
        )

    # Break a required header to prove enforce="off" is honored.
    aethel_file = os.path.join(scen_dir, "AETHEL.md")
    with open(aethel_file, "r", encoding="utf-8") as f:
        original_aethel = f.read()
    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(original_aethel.replace("## 6. Response Rules", "## 6. Removed"))

    # Now lint passes: custom ontology accepted, structure check disabled.
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

    # Restore the core block and EXTEND below it (the allowed asymmetry): consistent again.
    with open(aethel_file, "w", encoding="utf-8") as f:
        f.write(original + "\n- [G-321]: project rule below the core block.\n")
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)

    print(f"{GREEN}[PASS] Scenario I completed successfully.{RESET}")

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

    print(f"\n{GREEN}ALL TEST SCENARIOS PASSED SUCCESSFULLY!{RESET}\n")

if __name__ == "__main__":
    main()
