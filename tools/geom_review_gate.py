#!/usr/bin/env python3
"""Shim: the GEOM-REVIEW gate lives in tools/closure_loop/geom_review_gate.py (tools/geom_attendance.py imports it via
sys.path HERE/closure_loop).  This top-level name loads that file and re-exports it, so `import geom_review_gate` with
tools/ on sys.path and `python3 tools/geom_review_gate.py hash <kit>@<commit>` both work."""
import importlib.util
import sys
from pathlib import Path

_p = Path(__file__).resolve().parent / "closure_loop" / "geom_review_gate.py"
_spec = importlib.util.spec_from_file_location("_closure_loop_geom_review_gate", _p)
_g = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _g
_spec.loader.exec_module(_g)
globals().update({k: v for k, v in vars(_g).items() if not k.startswith("__")})

if __name__ == "__main__":
    sys.exit(_g.main() if hasattr(_g, "main") else 0)
