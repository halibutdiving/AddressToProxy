#!/usr/bin/env python3
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
VENV_DIR = ROOT / ".venv"


def _should_reexec_venv() -> bool:
    if os.environ.get("ADDRESS_TO_PROXY_SKIP_VENV_REEXEC"):
        return False
    if not VENV_PYTHON.exists():
        return False
    return Path(sys.prefix).resolve() != VENV_DIR.resolve()


if "--print-selected-python-for-test" in sys.argv:
    print(VENV_PYTHON if _should_reexec_venv() else Path(sys.executable).resolve())
    raise SystemExit(0)

if _should_reexec_venv():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

if len(sys.argv) > 1 and sys.argv[1] not in {"resolve", "--help", "-h", "--version"}:
    sys.argv.insert(1, "resolve")

sys.path.insert(0, str(SRC))

from address_to_proxy.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
