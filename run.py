#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from address_to_proxy.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
