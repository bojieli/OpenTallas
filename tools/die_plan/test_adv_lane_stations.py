"""ADV-LANE-STATIONS (COORD 11-22): QC V4 l1a sl_W4_fw arm/arv lanes delivered 12 vs table 8 at strict bind (UNPRICED_KIT_STATIONS)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_lane_stations as A  # noqa: E402
import plan_advisory as PA  # noqa: E402


def nat(cycles, fixed):
    return {"cycles": cycles, "fixed": fixed}


def test_l1a_shape_long():
    # boundary 2 + landing 2 + fixed 4 = 8; kit src 4 eats the budget, the receiver's 4 IN stations add on top
    assert A.estimate(nat(8, 4), 0, 4, 4) == 12


def test_receiver_pad_absorbs():
    # sl_E0_ctl x_ctl_su_c_p1: fixed 11, kit src 3 -> u_lpad D 8 absorbs the 10 receiver stations (bind PASS 25)
    assert A.estimate(nat(25, 11), 0, 3, 10) == 25
    assert A.estimate(nat(14, 6), 0, 3, 3) == 14
    assert A.estimate(nat(8, 4), 2, 4, 4) == 10       # an R8 pad keeps the receiver pad


def test_registered_and_not_checked_line():
    assert ("LANE-STATIONS", "adv_lane_stations") in PA.CHECKS
    out = A.findings({"partition_types": {}}, "p")
    assert out == [] or all(x.startswith("WARN ADV-LANE-STATIONS") for x in out)
