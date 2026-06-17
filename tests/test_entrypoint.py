from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_package_main_runs_when_pyinstaller_executes_it_as_a_script():
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, str(src_dir / "intrastat_generator" / "__main__.py"), "--help"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Generator INTRASTAT XLSX" in result.stdout
