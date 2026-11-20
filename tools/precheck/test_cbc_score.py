"""tests for cbc_score.py (CBC-ALL-0200 per-type CBC score)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbc_score as CS  # noqa: E402
import precheck as PC  # noqa: E402


def _t(**kw):
    t = {"outline_um": [800, 800], "buses": [], "hard_cores": [], "internal_stations": [], "ft_slots": []}
    t.update(kw)
    return t


TAPS = [("clk", 200.0, 200.0), ("clk_t1", 600.0, 200.0)]


def test_hop_cap_is_owner_300_unless_rules_define_it():
    assert CS.hop_cap("s81") == (CS.CBC.hop_cap_um("s81") if callable(getattr(CS.CBC, "hop_cap_um", None)) else 300.0)


def test_r1_flags_a_350_um_hop_and_passes_250():
    t = _t(internal_stations=[{"conn": "x", "from_um": [0, 0], "regs_um": [[350, 0]], "to_um": [600, 0], "bits": 8}])
    sc = CS.score_type("s81", {}, "t", t, None, None, lambda tt, r, m: PC.reach_findings(tt, r, m))
    assert sc["R1"][0] == "FLAG" and sc["R1"][1] == 350
    t["internal_stations"][0]["regs_um"] = [[250, 0], [500, 0]]
    t["internal_stations"][0]["to_um"] = [700, 0]
    assert CS.score_type("s81", {}, "t", t, None, None, lambda tt, r, m: PC.reach_findings(tt, r, m))["R1"][0] == "PASS"


def test_r2_cross_tap_zero_logic_hop_unless_latched():
    t = _t(ft_slots=[{"name": "ft0", "regs_um": [[150, 200], [650, 200]]}])
    assert CS.score_type("s81", {}, "t", t, TAPS, None)["R2"][:2] == ("FLAG", 1)
    raw = {"clock": {"ft_hop_lockup": {"types": ["t"]}}}
    sc = CS.score_type("s81", raw, "t", t, TAPS, None)["R2"]
    assert sc[1] == 0 and sc[0] == "FLAG" and "1 latched hops > 200" in sc[2]       # latched, but 500 um > half-cycle cap


def test_r3_counts_row_registers_on_top_of_bins_and_region_span():
    t = _t(clock={"sink_bins_file": "b.json"}, internal_stations=[{"regs_um": [[210, 210], [220, 220]], "bits": 600}])
    sinks = [(200.0, 200.0, 100.0), (600.0, 200.0, 100.0)]
    sc = CS.score_type("s81", {}, "t", t, TAPS, sinks)["R3"]
    assert sc[0] == "FLAG" and sc[1] == 1300
    sc = CS.score_type("s81", {}, "t", _t(), TAPS, [(50.0, 50.0, 1.0), (390.0, 390.0, 1.0)])["R3"]
    assert sc[0] == "FLAG" and "1 over 300" in sc[2]


def test_r4_r6_r8_r9():
    raw = {"reset": {"relay_um": 405}}
    t = _t(hard_cores=[{"name": "u_pc2", "origin_um": [552.576, 8.64], "outline_um": [90.72, 100], "orient": "R0"},
                       {"name": "u_ok", "origin_um": [17.28, 4.32], "outline_um": [10, 10], "orient": "R0"}],
           clock={"landing_contract": {"pins": [{"name": "fo", "kind": "clock", "dir": "out", "source_clock_tap": "clk_t9"}]}},
           reset={"consumer_localization": [{"instance": "u_a", "pin": "r", "new_reset": "rst_n_t1"}]})
    sc = CS.score_type("qwen_kvsys", raw, "t", t, TAPS, None, None, ["BUNDLE-DEPTH t: u_xr source bundle eg_*: eg_d D2, eg_v D1"])
    assert sc["R4"][0] == "FLAG" and sc["R6"][0] == "ERROR"
    assert sc["R8"][0] == "FLAG" and abs(sc["R8"][1] - 0.384) < 1e-6
    assert sc["R9"][0] == "FLAG" and "clk_t9" in sc["R9"][2] and "rst_n_t1" not in sc["R9"][2]
    ok, n = CS.summarize(sc)
    assert (n, ok) == (5, 1)           # R1 / R3 / R7 n/a, R5 INFO; R2 PASS (no chains)


def test_r8_mirrored_core_uses_far_edge():
    c = {"origin_um": [8.64 * 3 - 10.0, 0.0], "outline_um": [10.0, 4.32], "orient": "MY"}
    assert CS.lattice_resid(c) < 1e-9
