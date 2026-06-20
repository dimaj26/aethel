#!/usr/bin/env python3
import os
import sys
import shutil
import tempfile
import subprocess
import glob
import time

# Ensure c:\aethel is in PYTHONPATH for subprocesses
ENV = os.environ.copy()
ENV["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ANSI Color Codes
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def print_banner(title):
    print(f"\n==========================================")
    print(f"=== {title}")
    print(f"==========================================\n")

def run_cmd(args, cwd, expected_code=0):
    print(f"Running in {cwd}: {' '.join(args)}")
    res = subprocess.run(args, cwd=cwd, env=ENV, capture_output=True, text=True)
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
    
    # Verify AETHEL.md was overwritten with standard template (does NOT contain G-999)
    with open(aethel_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert "[G-999]: Project specific custom rule." not in new_content, "AETHEL.md was not updated/overwritten"
    
    # Verify AETHEL_ONBOARDING.md is created
    onboarding_path = os.path.join(scen_dir, "AETHEL_ONBOARDING.md")
    assert os.path.exists(onboarding_path), "AETHEL_ONBOARDING.md not created during update"
    
    # Verify Case C guidelines are in AETHEL_ONBOARDING.md
    with open(onboarding_path, "r", encoding="utf-8") as f:
        onboarding_content = f.read()
    assert "Case C: Library Upgrade & Rules Merging" in onboarding_content, "Case C not found in onboarding guidelines"
    
    # Verify linter fails as long as AETHEL_ONBOARDING.md is present
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=1)
    
    # Simulate developer merging: append G-999 back to AETHEL.md
    with open(aethel_path, "a", encoding="utf-8") as f:
        f.write("\n- [G-999]: Project specific custom rule.\n")
        
    # Simulate developer deleting onboarding file
    os.remove(onboarding_path)
    
    # Verify linter passes now
    run_cmd([sys.executable, "-m", "aethel.cli", "lint"], scen_dir, expected_code=0)
    
    print(f"{GREEN}[PASS] Scenario E completed successfully.{RESET}")

def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")
        test_scenario_a(temp_dir)
        test_scenario_b(temp_dir)
        test_scenario_c(temp_dir)
        test_scenario_d(temp_dir)
        test_scenario_e(temp_dir)
        
    print(f"\n{GREEN}ALL TEST SCENARIOS PASSED SUCCESSFULLY!{RESET}\n")

if __name__ == "__main__":
    main()
