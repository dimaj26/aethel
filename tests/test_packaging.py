"""Guards a real packaging bug found while preparing the first PyPI release: the built wheel
silently shipped with NO files from `aethel/templates/` at all - `aethel init`/`update` would be
completely broken for anyone installing from PyPI.

Two independent bugs compounded:
1. `[tool.setuptools.packages.find] include = ["aethel*"]` (a wildcard) matched dotted names too,
   so setuptools treated `aethel.templates`, `aethel.templates.knowledge`, etc. as separate
   (empty) Python sub-packages instead of `templates/**` being package_data of `aethel`.
2. `MANIFEST.in` had `recursive-exclude aethel/templates **/.ruff_cache *` - the trailing bare
   `*` is a SECOND pattern, unanchored, that excluded every file under `aethel/templates`
   (verified by running the real `sdist` command with `DISTUTILS_DEBUG=1`).

`test_wheel_contains_every_real_template` does a REAL build (subprocess, `python -m build
--wheel --no-isolation`) and inspects the resulting wheel - setuptools' data-file resolution has
enough internal lazy state (`manifest_files`, `egg_info` side effects) that mocking it is more
fragile than just building. It is the slow integration test here; the other two are fast static
checks for the same two root causes.
"""

import os
import subprocess
import sys
import zipfile

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


def test_packages_find_has_no_wildcard():
    """The `aethel*` wildcard previously matched dotted sub-names like `aethel.templates`
    too, turning the data directory into phantom empty sub-packages (bug 1)."""
    import tomllib

    with open(os.path.join(_REPO_ROOT, "pyproject.toml"), "rb") as f:
        pyproject = tomllib.load(f)
    include = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
    assert include == ["aethel"], (
        f"packages.find.include {include!r} must name the package exactly, no wildcard "
        "(a wildcard like 'aethel*' matches 'aethel.templates' etc. too)"
    )


def test_manifest_in_has_no_unanchored_wildcard_exclude():
    """Regression for bug 2: a bare `*` pattern on a `recursive-exclude`/`exclude` line wipes
    out everything `graft` just added, with no warning. Every exclude pattern must be scoped."""
    manifest_path = os.path.join(_REPO_ROOT, "MANIFEST.in")
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] in ("exclude", "recursive-exclude", "global-exclude"):
                patterns = parts[2:] if parts[0] == "recursive-exclude" else parts[1:]
                for pattern in patterns:
                    assert pattern not in ("*", "**"), (
                        f"unscoped wildcard exclude pattern {pattern!r} in MANIFEST.in line: {line!r}"
                    )


def test_wheel_contains_every_real_template(tmp_path):
    dist_dir = tmp_path / "dist"
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(dist_dir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as z:
        shipped = {n for n in z.namelist() if n.startswith("aethel/templates/")}

    templates_root = os.path.join(_REPO_ROOT, "aethel", "templates")
    on_disk = set()
    for dirpath, _dirnames, filenames in os.walk(templates_root):
        if ".ruff_cache" in dirpath.replace("\\", "/").split("/"):
            continue
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), os.path.join(_REPO_ROOT, "aethel"))
            on_disk.add("aethel/" + rel.replace(os.sep, "/"))

    missing = on_disk - shipped
    assert not missing, f"templates missing from the built wheel: {missing}"
    assert not any(".ruff_cache" in n for n in shipped)
