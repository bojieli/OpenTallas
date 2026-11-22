"""TAP-GRID-R5 11-21 (lever 6 fix 3): clock.tap_balance_to slowest.   python3 -m pytest -q tools/die_plan/test_tap_balance_slowest.py"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as G  # noqa: E402

TCL = (HERE / "tap_balance.tcl").read_text()


def test_exports_opt_in_only():
    assert G.tap_balance_to_exports({"clock": {}}) == []
    assert G.tap_balance_to_exports({"clock": {"tap_balance_to": "plan"}}) == []
    assert G.tap_balance_to_exports({"clock": {"tap_balance_to": "slowest"}}) == ["export OT_TAP_BALANCE_TO = slowest"]
    assert G.tap_balance_to_exports({"clock": {"tap_balance_to": "slowest", "tap_slowest_max_ps": 420}}) == [
        "export OT_TAP_BALANCE_TO = slowest", "export OT_TAP_SLOWEST_MAX_PS = 420"]


def test_tcl_slowest_target_and_bound():
    # target = max(plan, slowest raw tap mean), capped; the tree bound (OT_TAP_CHECK) follows the target
    assert 'eq "slowest"' in TCL and "OT_TAP_SLOWEST_MAX_PS" in TCL
    assert "set s [expr {max($tb_target, $longest)}]" in TCL
    assert "set ::tb_bnd $tgt" in TCL
    assert "set tb_bnd $tb_target" in TCL                     # unset: the plan insertion bound, unchanged
    assert "$tb_target + $tb_win - [lindex $v 2]" not in TCL
    assert len(re.findall(r"\$::tb_bnd \+ \$tb_win", TCL)) == 5


def test_tcl_braces_balanced():
    assert TCL.count("{") == TCL.count("}")
