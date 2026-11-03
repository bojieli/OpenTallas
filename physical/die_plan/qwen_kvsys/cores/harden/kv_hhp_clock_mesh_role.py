#!/usr/bin/env python3
"""Historical entry point; the portable normal consumer lives in tools/die_plan."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tools/die_plan"))
from hhp_clock_mesh_role import *  # noqa: F401,F403
if __name__ == "__main__":
    main()
