"""Version-stamping invariants.

Two distinct version concepts must each stay internally consistent:
- `aethel.__version__` (the pip package) == `pyproject [project].version`.
- `aethel.CORE_VERSION` (the managed-core-block version) == the stamp shipped in
  `templates/AETHEL.md.template`'s `aethel-core` block.
A drift in either is a release-hygiene bug, so it is guarded here rather than left
to be noticed by a deployed workspace.
"""

import os
import tomllib

import aethel
from aethel.markers import extract_managed_block, parse_core_version

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_TEMPLATE = os.path.join(_REPO_ROOT, "aethel", "templates", "AETHEL.md.template")


def test_package_version_in_sync():
    with open(os.path.join(_REPO_ROOT, "pyproject.toml"), "rb") as f:
        pyproject = tomllib.load(f)
    assert aethel.__version__ == pyproject["project"]["version"]


def test_template_stamp_matches_core_version():
    with open(_TEMPLATE, "r", encoding="utf-8") as f:
        block = extract_managed_block(f.read(), "aethel-core")
    assert block is not None
    assert parse_core_version(block) == aethel.CORE_VERSION
