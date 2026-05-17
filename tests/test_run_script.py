import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_script_help_works_without_package_install():
    script = ROOT / "run.py"

    result = subprocess.run(
        [sys.executable, str(script), "resolve", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--config" in result.stdout
    assert "config.yaml" in result.stdout


def test_run_script_is_executable():
    script = ROOT / "run.py"

    assert script.stat().st_mode & 0o111


def test_install_script_is_executable_and_valid_shell():
    script = ROOT / "install.sh"

    assert script.stat().st_mode & 0o111
    result = subprocess.run(
        ["bash", "-n", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_run_script_execs_project_venv_when_started_outside_venv():
    script = ROOT / "run.py"
    venv_python = ROOT / ".venv" / "bin" / "python"
    system_python = Path(getattr(sys, "_base_executable", sys.executable))

    result = subprocess.run(
        [
            str(system_python),
            str(script),
            "--print-selected-python-for-test",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={},
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(venv_python)


def test_executable_run_script_help_uses_project_venv():
    script = ROOT / "run.py"

    result = subprocess.run(
        [str(script), "resolve", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--config" in result.stdout


def test_run_script_accepts_address_without_resolve_subcommand():
    script = ROOT / "run.py"

    result = subprocess.run(
        [str(script), "123 Example St,Example City,North Carolina,28214, US", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage: run.py resolve" in result.stdout
    assert "--output" in result.stdout
