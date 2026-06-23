import os
import subprocess
import sys
import venv

import pytest

# Ensure the repository root is importable when tests run without an editable install.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


class InstalledAethel:
    """Paths into a throwaway venv with the built `aethel-cli` wheel installed."""

    def __init__(self, venv_dir: str):
        bin_dir = "Scripts" if os.name == "nt" else "bin"
        exe_suffix = ".exe" if os.name == "nt" else ""
        self.python = os.path.join(venv_dir, bin_dir, f"python{exe_suffix}")
        self.aethel = os.path.join(venv_dir, bin_dir, f"aethel{exe_suffix}")

    def run(self, *args: str, cwd: str | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.aethel, *args], cwd=cwd, capture_output=True, text=True, timeout=timeout
        )


@pytest.fixture(scope="session")
def installed_aethel_cli(tmp_path_factory) -> InstalledAethel:
    """Builds the `aethel-cli` wheel ONCE per test session and installs it into one throwaway
    venv - release-smoke / scenario-project tests run against this REAL console-script entry
    point (never `python -m aethel.cli` from source), so an editable-install blind spot (the
    root cause of the templates-missing-from-wheel bug) can't recur unnoticed."""
    build_dir = tmp_path_factory.mktemp("aethel_cli_build")
    dist_dir = build_dir / "dist"
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(dist_dir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, wheels

    venv_dir = tmp_path_factory.mktemp("aethel_cli_venv")
    venv.create(str(venv_dir), with_pip=True)
    installed = InstalledAethel(str(venv_dir))

    install = subprocess.run(
        [installed.python, "-m", "pip", "install", "--no-index", "--no-deps", "--quiet", str(wheels[0])],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    assert os.path.exists(installed.aethel), "console-script entry point was not installed"
    return installed
