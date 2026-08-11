from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_installed_package_imports_outside_repository(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "-c", "import quran_etl; print(quran_etl.__version__)"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0.2.0"
