import subprocess
import sys
from pathlib import Path


def test_run_script_help_works_without_package_install():
    script = Path(__file__).resolve().parents[1] / "run.py"

    result = subprocess.run(
        [sys.executable, str(script), "resolve", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--config" in result.stdout
    assert "config.yaml" in result.stdout
