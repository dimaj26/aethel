"""A non-UTF-8 console must never crash the linter (found by accident: `aethel lint .` raised
`UnicodeEncodeError` under a plain `cp1251` Windows console while reporting an incomplete task).

Root cause: the linter happily re-prints arbitrary AUTHORED Markdown content back to the user
(task-checklist item text, plan errors) via `print_error`/`print_warning`. That content is
written by humans/agents and WILL contain non-ASCII punctuation sooner or later (an arrow in a
checklist note, an em-dash, anything) - banning specific characters from prose is not a fix,
since this repo's own `report_lang=ru` policy means walkthroughs are routinely non-ASCII. The
correct fix is at the I/O boundary: the CLI/linter entry points must make stdout resilient
(`errors="replace"`) instead of trusting that every printed string is encodable by whatever
codepage the console happens to use.
"""

import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))

_MINIMAL_VALID_PLAN = """# Test Plan

## User Review Required
- none

## Open Questions
- none

## Proposed Changes
### x
- [NEW] x

## Verification Plan & TDD Reproducer
### Automated Tests
- x
"""


def _workspace_with_arrow_in_task(tmp_path):
    (tmp_path / "implementation_plan.md").write_text(_MINIMAL_VALID_PLAN, encoding="utf-8")
    (tmp_path / "task.md").write_text(
        "# Task Checklist\n\n## Chunk 1\n- [ ] step one → step two\n", encoding="utf-8"
    )
    return tmp_path


def test_lint_on_arrow_containing_task_is_console_encoding_safe(tmp_path):
    ws = _workspace_with_arrow_in_task(tmp_path)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"  # forces a non-UTF-8 stdout regardless of host platform
    proc = subprocess.run(
        [sys.executable, "-m", "aethel.cli", "lint", str(ws)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert "UnicodeEncodeError" not in proc.stderr, proc.stderr
    # The lint run itself may legitimately fail (incomplete task) - that must be a clean,
    # readable exit, never an interpreter crash.
    assert proc.returncode in (0, 1), proc.stderr
