#!/usr/bin/env python3
"""Shim: the GEOM-REVIEW gate lives in tools/closure_loop/geom_review_gate.py (imported by tools/geom_attendance.py
via sys.path HERE/closure_loop).  This top-level name re-exports it so `import geom_review_gate` from tools/ and
`python3 tools/geom_review_gate.py hash <kit>@<commit>` both work."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "closure_loop"))
from geom_review_gate import *  # noqa: E402,F401,F403
import geom_review_gate as _g  # noqa: E402

if __name__ == "__main__":
    sys.exit(_g.main() if hasattr(_g, "main") else 0)
