"""Enforces the one-directional consistency rule the user explicitly requested: the dev
environment (this repo's OWN AETHEL.md) must never fail to carry a standard the shipped core
(`aethel/templates/AETHEL.md.template`) declares. The reverse asymmetry is explicitly allowed -
the dev environment may have taboos the core doesn't need (dev-env ⊇ core, not ==).

`check_core_consistency` exempts this repo from the structural compare entirely ("this repository
IS the source of the core"), so nothing mechanically caught the actual incident this guards: the
template's `## 5. Critical Coding Taboos` list and the root AETHEL.md's list drifted apart since
the project's first commit (confirmed via `git log` - the template has carried a taboo the root
file never adopted, since `ee1bfd1`), and a later session added a new Taboo (#9) to the root file
without propagating it to the template - the same class of mistake, opposite direction.
"""

import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))

_TABOO_TITLE_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)


def _taboo_titles(text: str) -> set[str]:
    return set(_TABOO_TITLE_RE.findall(text))


def _read(rel_path: str) -> str:
    with open(os.path.join(_REPO_ROOT, rel_path), "r", encoding="utf-8") as f:
        return f.read()


def test_root_aethel_md_has_every_core_taboo():
    """The dev environment must carry every taboo the shipped core declares (it may also have
    dev-only taboos the core doesn't need - that asymmetry is fine; the reverse is not)."""
    root_titles = _taboo_titles(_read("AETHEL.md"))
    template_titles = _taboo_titles(_read("aethel/templates/AETHEL.md.template"))
    missing_from_dev_env = template_titles - root_titles
    assert not missing_from_dev_env, (
        f"Core declares taboo(s) the dev environment's own AETHEL.md does not carry: "
        f"{missing_from_dev_env}. The dev environment must never fail to meet a standard the "
        f"core declares (one-directional sync: dev-env ⊇ core). Either this repo's AETHEL.md "
        f"never adopted it (adopt it now), or the template prescribes something we don't "
        f"ourselves follow (remove it from the template instead)."
    )
