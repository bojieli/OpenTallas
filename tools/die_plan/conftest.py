"""TEST-FIX 10-25: tools/die_plan pytest preconditions.

1. tools/die_plan is on sys.path for every test module, so a module that imports a sibling test helper
   (test_tapbal_grt -> test_flow_hold_basis) also passes when run on its own, not only after a module that
   happened to insert the path first.
2. The kit generators read Tcl from physical/common_flow (clock_family.tcl, die_constant_cells.tcl, ...).  A sparse
   checkout without it (e.g. `sparse-checkout set --cone tools physical/die_plan ...`) turned 20 kit tests into
   FileNotFoundError on 2026-10-25 and looked like a main regression.  Stop the session at once with one clear
   error instead (fail closed, nothing is skipped).  Documented sparse set: `tools physical rtl`.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

REQUIRED_DIRS = ("physical/common_flow",)


def pytest_sessionstart(session):
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    if missing:
        raise pytest.UsageError(
            f"tools/die_plan tests need {missing} in the checkout at {ROOT} (sparse checkout too narrow?); "
            "use `git -C <wt> sparse-checkout set --cone tools physical rtl`")
