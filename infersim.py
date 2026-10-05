#!/usr/bin/env python3
"""Compatibility entry point for the analytical simulator promised by the plan."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from opentallas.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
