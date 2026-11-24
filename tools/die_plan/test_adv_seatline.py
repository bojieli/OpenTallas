"""pytest: ADV-SEATLINE on the QC sle_ctl hc1_o point seat (1,574 bits at one point) and a spread station."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_seatline as A  # noqa: E402


def row(bits, regs, sites=None):
    e = {"conn": "bus:b_hw_hc1_o", "bits": bits, "regs_um": regs}
    if sites:
        e["bit_sites_um"] = sites
    return e


def test_hc1_o_point_seat_is_narrow_and_hot():
    t = {"internal_stations": [row(1574, [[357.277, 318.0], [437.0, 420.486]])]}
    narrow, hot, _ = A.judge(A.seats(t))
    assert narrow and abs(narrow[0][4] - A.need_side(1574)) < 1e-6 and narrow[0][4] > 35 and narrow[0][3] == 0.0
    assert A.need_side(1574) >= A.STRONG_SIDE_UM


def test_spread_window_passes():
    sites = [[[x * 1.0, y * 1.0] for x in range(0, 60, 2) for y in range(0, 60, 2)]] * 2          # 60 um window
    t = {"internal_stations": [row(900, [[10.0, 10.0], [500.0, 500.0]], sites)]}
    assert A.judge(A.seats(t))[0] == []


def test_small_station_not_flagged():
    t = {"internal_stations": [row(8, [[10.0, 10.0]])]}
    assert A.judge(A.seats(t))[0] == []


def test_findings_strong_tier_and_never_raises():
    raw = {"partition_types": {"sle_ctl_x": {"internal_stations": [row(1574, [[357.277, 318.0]])]}}}
    out = A.findings(raw, "p")
    assert "sle_ctl_x" in out[0] and "36 um side" in out[0]
    assert A.findings(None, "p")[0].startswith("WARN ADV-SEATLINE not checked")
