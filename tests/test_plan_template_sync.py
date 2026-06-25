"""#5: the shipped RNA plan template must list every plan section the linter REQUIRES.

The linter's required H2 set used to be a private list inside `check_plan_file`, free to
drift from the documented template — the actual incident: the template (and root AETHEL.md §2)
lacked `## Open Questions` while the linter required it, so a plan following the documented
template FAILed. The fix single-sources the set as `REQUIRED_PLAN_H2S`; this guard asserts both
the shipped template and this repo's own AETHEL.md §2 carry every required section, so the
doc<->enforcement drift cannot silently recur.
"""

import os
import re

from aethel.linter import REQUIRED_PLAN_H2S

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_FILES = ["aethel/templates/AETHEL.md.template", "AETHEL.md"]


def _read(rel_path: str) -> str:
    with open(os.path.join(_REPO_ROOT, rel_path), "r", encoding="utf-8") as f:
        return f.read()


def _has_h2(text: str, name: str) -> bool:
    return bool(re.search(r"^##\s+" + re.escape(name), text, re.MULTILINE))


def test_rna_template_lists_all_required_plan_sections():
    for rel in _FILES:
        text = _read(rel)
        missing = [s for s in REQUIRED_PLAN_H2S if not _has_h2(text, s)]
        assert not missing, (
            f"{rel} is missing linter-required plan section(s): {missing}. The documented RNA "
            f"template must contain exactly the linter's required set (single-sourced as "
            f"REQUIRED_PLAN_H2S) so a plan following the template never FAILs the plan linter."
        )
