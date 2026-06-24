"""Version-stamping invariants.

Two distinct version concepts must each stay internally consistent:
- `aethel.__version__` (the pip package) == `pyproject [project].version`.
- `aethel.CORE_REVISION` (the managed-core-block integer revision) == the stamp shipped in
  `templates/AETHEL.md.template`'s `aethel-core` block.
A drift in either is a release-hygiene bug, so it is guarded here rather than left
to be noticed by a deployed workspace.
"""

import os
import tomllib

import aethel
from aethel.markers import extract_managed_block

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_TEMPLATE = os.path.join(_REPO_ROOT, "aethel", "templates", "AETHEL.md.template")


def test_package_version_in_sync():
    with open(os.path.join(_REPO_ROOT, "pyproject.toml"), "rb") as f:
        pyproject = tomllib.load(f)
    assert aethel.__version__ == pyproject["project"]["version"]


def test_template_stamp_is_int_revision_matching_constant():
    """The core block stamp is an INTEGER revision (`AETHEL:CORE-REV N`), distinct from the
    semver package version, and equals `aethel.CORE_REVISION`."""
    from aethel.markers import parse_core_revision

    with open(_TEMPLATE, "r", encoding="utf-8") as f:
        block = extract_managed_block(f.read(), "aethel-core")
    assert block is not None
    rev = parse_core_revision(block)
    assert isinstance(rev, int), "core stamp must parse as an integer revision, not a semver string"
    assert rev == aethel.CORE_REVISION
