"""pytest: ADV-LEG-DELAY (FP-CONVERGE-KV): the C4 / C6 station-free long legs must be flagged, short legs and staged legs must pass."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_leg_delay as L  # noqa: E402


def _t(gap=100.0, staged=False):
    t = {"hard_cores": [{"inst": "kvpc1", "origin_um": [500.0 + gap, 0.0], "outline_um": [300.0, 300.0]},
                        {"inst": "head_e0", "origin_um": [0.0, 0.0], "outline_um": [200.0, 200.0]},
                        {"inst": "head_e4", "origin_um": [200.0 + gap, 600.0], "outline_um": [200.0, 200.0]}],
         "internal_stations": []}
    if staged:
        t["internal_stations"] = [{"conn": "bus:i_phy", "regs_um": [[400.0, 100.0]]}]
    return t


CONNS = {"kvpc1": {"p": ["bus:i_phy"]}, "head_e0": {"q": ["core:head_e4"]}}
PTS = {"i_phy": (0.0, 0.0)}


def test_short_legs_pass():
    lv = L.legs(_t(gap=50.0), PTS, CONNS)
    assert L.type_line("T", lv) is None


def test_c4_long_face_leg_mutant_fails():
    lv = L.legs(_t(gap=1100.0), PTS, CONNS)
    ln = L.type_line("kv3_pc", lv)
    assert ln and ln.startswith("WARN ADV-LEG-DELAY kv3_pc:") and "face i_phy->kvpc1" in ln


def test_c6_core_to_core_leg_mutant_fails():
    t = _t(gap=1300.0)
    lv = L.legs(t, {}, {"head_e0": {"q": ["core:head_e4"]}})
    assert lv and lv[0][1] == "core" and L.est_slack(lv[0][0]) < L.SLACK_FLOOR_PS


def test_staged_bus_is_not_judged():
    assert not [x for x in L.legs(_t(gap=1100.0, staged=True), PTS, CONNS) if x[1] == "face"]


def test_calibration_point_c4():
    assert abs(L.est_slack(1218.0) - (-759.6)) < 20          # C4 measured -757..-824


def test_never_raises():
    assert L.findings(None, "p")[0].startswith("WARN ADV-LEG-DELAY not checked")


def test_core_pair_with_a_station_chain_is_not_judged():
    t = _t(gap=1300.0)
    t["internal_stations"] = [{"conn": "core:u_head_e0.kp_o|core:u_head_e4.kp_in", "regs_um": [[300.0, 300.0]]}]
    assert not L.legs(t, {}, {"head_e0": {"q": ["core:head_e4"]}})
