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

# DIEPLAN-DEPS-1124 (COORD, KV-RSTREACH: 4 test_bind_stream tests "fail on main"): gen_phys imports tools/autopilot/goal_table.py at
# import time (149a58c42d0), so a cone with tools/die_plan but not tools/autopilot failed the yosys bind tests with ModuleNotFoundError.
REQUIRED_DIRS = ("physical/common_flow", "tools/autopilot")


def pytest_sessionstart(session):
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    if missing:
        raise pytest.UsageError(
            f"tools/die_plan tests need {missing} in the checkout at {ROOT} (sparse checkout too narrow?); "
            "use `git -C <wt> sparse-checkout set --cone tools physical rtl`")


@pytest.fixture(autouse=True)
def _lec_rawprefix_wall_off(monkeypatch):
    """LEC-RAWPREFIX-BOUND (DIE-HBM-61/LEC 11-03): the raw prefix sweep's wall-clock backstop is off in tests
    (OT_LEC_RAWPREFIX_S=0), so no test result depends on host load; the deterministic AND-node cap stays at its
    default.  A test that checks the wall bound sets or deletes the variable itself."""
    monkeypatch.setenv("OT_LEC_RAWPREFIX_S", "0")


@pytest.fixture(autouse=True)
def _pre_crash_warn_for_toy_plans(monkeypatch):
    """P-FALSE-GREEN-1126 (HEAD-INT-R2): plan_gate_pre.check() now turns a crashed check (WARN ...-UNCHECKED <Exception>) into a FAIL.
    The fixture plans of the PRE tests are deliberately minimal ({"die": "x"}), so estimators crash on them by construction; those tests
    judge the finding classes they build, so they run with the old WARN (OT_PRE_CRASH_WARN=1).  test_false_green_r2.py tests the
    promotion itself and passes env explicitly / removes the variable."""
    monkeypatch.setenv("OT_PRE_CRASH_WARN", "1")
