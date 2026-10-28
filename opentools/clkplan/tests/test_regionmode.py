"""region-mode predictor + shared-OCV parity tests (light)."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from common import plan as PL  # noqa: E402
from clkplan import model as MD, ocv, regionmode as RM  # noqa: E402

M = MD.load()
EX = ROOT / "examples" / "regions_toy.json"


def run(P):
    return RM.analyse(P, M, PL.clock_sinks(P))


def test_forwarded_hop_fails_on_nominal_d():
    """neighbour-forwarded 3-mm hop: nominal |d| ~ one hop (~640 ps TT) > P/2 -> FAIL (QC-SLICECLK-2 finding)."""
    res = run(PL.load(EX))
    assert res["verdict"] == "FAIL"
    x = {r["name"]: r for r in res["crossings"]["rows"]}
    assert 600 < abs(x["x01"]["TT"]["d_ps"]) < 700 and x["x01"]["TT"]["margin_ps"] < 0
    assert x["x11"]["pass"] and x["x11"]["same_region"]


def test_balanced_spine_feed_passes():
    """same regions fed from a shared spine with equal taps: d = 0, unshared = feed + local -> PASS."""
    P = PL.load(EX)
    P["feeds"] = [dict(name=f"s{i}", src="root", dst=f"r{i}", len_um=1500.0, kind="spine") for i in range(3)]
    res = run(P)
    assert res["verdict"] == "PASS", res["crossings"]["summary"]
    r = res["crossings"]["rows"][0]
    assert abs(r["TT"]["d_ps"]) < 30 and r["TT"]["margin_ps"] > 100      # d = local-tree length difference only


def test_feed_graph_rejects_two_parents():
    P = json.loads(EX.read_text())
    P["feeds"].append(dict(name="dup", src="root", dst="r0", len_um=10))
    assert any("more than one incoming feed" in e for e in PL.validate(PL.fill_defaults(P)))


def _pess_qc(L1_mm, L2_mm, d_mm, corner):
    """QC-SLICECLK-2 predict.py branch form: 199.4 ps/mm TT, 405-um A stages, no B part, droop not shared."""
    T = M.T
    ps_mm = 199.4 if corner == "TT" else 199.4 * T["classes"]["A"]["FF"]["mu_stage_ps"] / T["classes"]["A"]["TT"]["mu_stage_ps"]

    def br(L):
        u = L * ps_mm
        fc = T["classes"]["A"][corner]["cell_share"]
        return dict(cell_ps=fc * u, net_ps=(1 - fc) * u, stages={"A": max(1, round(L / 0.405))})
    a, b = br(L1_mm), br(L2_mm)
    return max(ocv.branch_pessimism(T, corner, a, b, d_mm * 1000, False), ocv.branch_pessimism(T, corner, b, a, d_mm * 1000, False))


def test_parity_with_qc_sliceclk2_prediction():
    """reproduces claude/qc-sliceclk2-1027@d2a6b2d12b predict_out.txt: K=1 slice<->slice damage 235 TT / 194 FF,
    K=3 forwarded 133 TT / 109 FF (same math as main tools/die_plan/clk_aocv.branch_pessimism)."""
    W = 2.471
    d = math.hypot(2 * W, 1.0)
    assert round(_pess_qc(14.37, 14.37, d, "TT")) == 235
    assert round(_pess_qc(14.37, 14.37, d, "FF")) == 194
    h = 26.266 / 3
    L = h / 2 + W / 2
    d3 = math.hypot(2 * W, h / 2)
    assert round(_pess_qc(L + W, L, d3, "TT")) == 133 and round(_pess_qc(L + W, L, d3, "FF")) == 109


def test_parity_with_main_clk_aocv():
    """opentools ocv == main tools/die_plan/clk_aocv.py on the same branches (skipped outside the repo)."""
    p = REPO / "tools" / "die_plan" / "clk_aocv.py"
    if not p.exists():
        return
    sys.path.insert(0, str(p.parent))
    import clk_aocv as CA
    T = M.T
    for c in ("TT", "FF"):
        a = ocv.branch(T, c, 1800.0, 18, 250.0)
        b = ocv.branch(T, c, 900.0, 9, 202.5)
        for same in (True, False):
            ours = ocv.branch_pessimism(T, c, a, b, 3200.0, same)
            ref = CA.branch_pessimism(T, c, a, b, 3200.0, same, "setup")
            assert abs(ours - ref) < 1e-9


def test_leaf_tap_adds_parent_insertion():
    """locality.py 'fwd' form: a child fed from a LEAF of its parent arrives I_parent later than from the root."""
    P = PL.load(EX)
    a = RM.predict(P, M, PL.clock_sinks(P))["regions"]["r0"]["root_arrival_ps"]["TT"]
    for f in P["feeds"]:
        f["tap"] = "leaf"
    pr = RM.predict(P, M, PL.clock_sinks(P))["regions"]
    assert abs(pr["r0"]["root_arrival_ps"]["TT"] - a - pr["r1"]["local_insertion_ps"]["TT"]) < 0.2


# ------------------------------------------------------------------ count-aligned crossing margin (COORD definitions)
T833 = 833.333
AP = {"TT": 10.86 + 15.63, "FF": 6.68 + 12.61}       # asap7 DFFHQNx1 setup + hold (model data)
TRIP = {"TT": (-437.0, 100.0, 100.0), "FF": (-376.0, 100.0, 100.0)}


def test_count_aligned_period_whole_vs_half_cycle():
    """COORD 20:26 'period' form: window +-(T - setup - hold)/2, ONE K for TT and FF, residual counts.
    whole cycle: K=0 -> TT 403.42 - 537 = -133.6 (K=-1 is worse: FF -150.3); half cycle: K=-1 -> FF 266.3 (worst)."""
    w = ocv.count_aligned_margin(TRIP, T833, AP, form="period")
    assert w["K"] == 0 and abs(w["margin_ps"] - (-133.58)) < 0.05
    h = ocv.count_aligned_margin(TRIP, T833, AP, form="period", half_cycle=True)
    assert h["K"] == -1 and abs(h["step_ps"] - T833 / 2) < 1e-9
    assert abs(h["corners"]["FF"]["margin_ps"] - ((T833 - AP["FF"]) / 2 - (-376 + T833 / 2 + 100))) < 1e-6
    assert h["margin_ps"] > 100 > w["margin_ps"]


def test_count_aligned_ring_smallest_k_and_window():
    """COORD 20:35 ring form: L = K T + d inside [(0.5T+ap), (DEPTH-0.5)T-ap]; smallest K passing 100 ps (latency)."""
    r = ocv.count_aligned_margin(TRIP, T833, AP, form="ring", depth=4, target_ps=100.0)
    assert r["K"] == 2                                  # K=1: TT low end 296.3 < 443.2 -> FAIL
    tt = r["corners"]["TT"]
    assert abs(tt["margin_lo_ps"] - (2 * T833 - 537 - (0.5 * T833 + AP["TT"]))) < 1e-6
    assert abs(tt["margin_hi_ps"] - ((3.5 * T833 - AP["TT"]) - (2 * T833 - 337))) < 1e-6
    assert abs(r["margin_ps"] - tt["margin_lo_ps"]) < 1e-9
    # origin uncertainty of one whole cycle on the low side moves K up by one
    r2 = ocv.count_aligned_margin(TRIP, T833, AP, form="ring", depth=4, target_ps=100.0, origin_cycles=(1, 0))
    assert r2["K"] == 3
    # a spread wider than the DEPTH window fails at every K
    wide = {"TT": (0.0, 1500.0, 1500.0), "FF": (0.0, 1400.0, 1400.0)}
    assert ocv.count_aligned_margin(wide, T833, AP, form="ring", depth=4, target_ps=100.0)["margin_ps"] < 0


def test_forwarded_hop_passes_count_aligned_ring():
    """the toy 3-mm forwarded hop FAILS the one-period ring on nominal d alone, but its derated variation fits the
    count-aligned ring window: same predictor, crossing_mode only changes the window."""
    P = PL.load(EX)
    ph = RM.analyse(P, M, PL.clock_sinks(P))
    ca = RM.analyse(P, M, PL.clock_sinks(P), crossing_mode="count_aligned")
    x = {r["name"]: r for r in ca["crossings"]["rows"]}["x01"]
    assert x["mode"] == "count_aligned" and x["TT"]["phase_margin_ps"] < 0 < x["TT"]["margin_ps"]
    assert x["pass"] and isinstance(x["count_aligned"]["K"], int)
    assert ca["crossings"]["summary"]["crossing_mode"] == "count_aligned"
    assert ph["verdict"] == "FAIL"
