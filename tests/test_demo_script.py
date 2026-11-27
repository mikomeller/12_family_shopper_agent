# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_demo_script.py
# Pathname:  tests/test_demo_script.py
# Purpose:   Runs scripts/demo.py as a subprocess; the offline demo must exit 0 and print DEMO OK
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_demo_script_runs_clean() -> None:
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "demo.py")],
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    assert p.returncode == 0, p.stdout + p.stderr
    assert "DEMO OK" in p.stdout
