"""ADV-CHANNEL-PILE (FP-CONVERGE-QC C5): channel width vs through-wires and tap grid per CB channel."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_channel_pile as C  # noqa: E402
import plan_advisory as PA  # noqa: E402


def core(inst, x, y):
    return {"inst": inst, "module": "qfd_tile_nk_a0c", "origin_um": [x, y], "outline_um": [458.0, 1158.0]}


def good():
    """quad type 1235 x 2540: strips 200 um, central 200 um, one 515-bit bus in the W strip, 10 taps, 2000 sinks in the channel"""
    t = {"outline_um": [1316.0, 2540.0],
         "hard_cores": [core("a", 200.0, 70.0), core("b", 858.0, 70.0), core("c", 200.0, 1300.0), core("d", 858.0, 1300.0)],
         "internal_stations": [{"conn": "bus:x", "from_um": [100.0, 2500.0], "to_um": [100.0, 800.0], "regs_um": [[100.0, 1600.0]], "bits": 515}],
         "ft_slots": [],
         "relay_sites": {"r%d" % i: [760.0, 10.0 + i] for i in range(2000)},
         "clock": {"taps": [{"name": "t%d" % i, "xy": [758.0, 250.0 * i + 100], "kind": "glue"} for i in range(10)]}}
    return {"partition_types": {"cbn_q00__clgood": t}}


def test_pass_case_has_no_findings():
    assert C.findings(good(), "p.json") == []


def test_mutant_narrow_strip_fails_width():                      # W strip shrunk to 60 um: 515 wires / (60 x 32) > 0.6 ...
    p = good()
    t = p["partition_types"]["cbn_q00__clgood"]
    t["internal_stations"][0]["bits"] = 1545                    # three 515-bit buses through the 200 um strip
    t["internal_stations"][0]["regs_um"] = [[43.2, 1600.0]]
    t["internal_stations"][0]["from_um"] = [43.2, 2500.0]
    t["internal_stations"][0]["to_um"] = [43.2, 800.0]
    for h in t["hard_cores"]:
        h["origin_um"][0] -= 140.0 if h["origin_um"][0] < 600 else 0.0   # strip 60 um, central 340 um
    for r in t["relay_sites"].values():
        r[0] -= 140.0 * 0                                       # sinks stay in the central channel
    out = C.findings(p, "p.json")
    assert any("W strip" in x and "WIDTH" in x for x in out) and all(x.startswith("WARN ADV-CHANNEL-PILE ") for x in out)


def _one_bus_four_stations(p):
    t = p["partition_types"]["cbn_q00__clgood"]
    st = t["internal_stations"][0]
    st["from_um"], st["to_um"] = [30.0, 2500.0], [30.0, 800.0]
    st["regs_um"] = [[30.0, 2160.0], [30.0, 1820.0], [30.0, 1480.0], [30.0, 1140.0]]
    for h in t["hard_cores"]:
        h["origin_um"][0] -= 140.0 if h["origin_um"][0] < 600 else 0.0     # W strip 60 um
    return t


def test_multi_station_bus_counts_once():                    # one 515-bit bus, 4 stations, 60 um strip: util 0.27, no WIDTH
    p = good()
    t = _one_bus_four_stations(p)
    assert C.through_wires(t, 0.0, 60.0) == 515
    assert not any("W strip" in x and "WIDTH" in x for x in C.findings(p, "p.json"))


def test_mutant_per_leg_sum_would_fire():                     # mutant: the old per-leg sum (5 x 515 = 2575, util 1.34) fires
    p = good()
    t = _one_bus_four_stations(p)
    legs = sum(n for xa, ya, xb, yb, n, _ in C.R.legs(t) if xa <= 61 and xb <= 61 and abs(yb - ya) > abs(xb - xa))
    sup = 60.0 * C.TRACKS_PER_UM
    assert legs == 5 * 515 and legs / sup >= C.WARN_UTIL > C.through_wires(t, 0.0, 60.0) / sup


def test_two_buses_on_one_cut_add():                          # two distinct buses over the same cut do add
    p = good()
    t = p["partition_types"]["cbn_q00__clgood"]
    t["internal_stations"].append(dict(t["internal_stations"][0], conn="bus:y", from_um=[150.0, 2500.0],
                                       to_um=[150.0, 800.0], regs_um=[[150.0, 1600.0]]))
    assert C.through_wires(t, 0.0, 200.0) == 1030


def test_mutant_no_tap_grid_fails():                            # the q11 shape: 5 glue taps for 2000 sinks, 500 um apart
    p = good()
    t = p["partition_types"]["cbn_q00__clgood"]
    t["clock"]["taps"] = t["clock"]["taps"][:2]
    out = C.findings(p, "p.json")
    assert len(out) == 1 and "central" in out[0] and "TAPGRID" in out[0] and "no tap grid" in out[0]


def test_non_cb_types_and_registered():
    p = good()
    p["partition_types"]["other"] = copy.deepcopy(p["partition_types"].pop("cbn_q00__clgood"))
    p["partition_types"]["other"]["clock"]["taps"] = []
    assert C.findings(p, "p.json") == []
    assert ("CHANNEL-PILE", "adv_channel_pile") in PA.CHECKS
