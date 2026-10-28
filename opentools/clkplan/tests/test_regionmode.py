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


def test_ring_phase_whole_vs_half_cycle():
    """SUPERSEDED one-period window (COORD 20:26), kept as crossing_mode ring_phase: +-(T - setup - hold)/2, ONE K for TT
    and FF, residual counts.  whole cycle: K=0 -> TT 403.42 - 537 = -133.6; half cycle: K=-1 -> FF 266.3 (worst)."""
    w = ocv.ring_phase_margin(TRIP, T833, AP)
    assert w["K"] == 0 and abs(w["margin_ps"] - (-133.58)) < 0.05
    h = ocv.ring_phase_margin(TRIP, T833, AP, half_cycle=True)
    assert h["K"] == -1 and abs(h["step_ps"] - T833 / 2) < 1e-9
    assert abs(h["corners"]["FF"]["margin_ps"] - ((T833 - AP["FF"]) / 2 - (-376 + T833 / 2 + 100))) < 1e-6
    assert h["margin_ps"] > 100 > w["margin_ps"]


def test_count_aligned_window_k_depth():
    """count-aligned ring (COORD 20:35 + 21:10): L = K T + rel inside [0.5T+ap, (DEPTH-0.5)T-ap], ap = T/8, K = the
    smallest integer from the DERATED lag (union of corners), DEPTH 4 else 8, margins measured to the guard edges."""
    ap = T833 / 8
    r = ocv.count_aligned_margin(TRIP, T833)
    assert r["aperture_ps"] == ap and r["K"] == 2 and r["depth"] == 4 and r["latency_cycles"] == 3
    assert abs(r["L_lo_ps"] - (2 * T833 - 537)) < 1e-6 and abs(r["L_hi_ps"] - (2 * T833 - 276)) < 1e-6
    assert abs(r["margin_lo_ps"] - (2 * T833 - 537 - 0.5 * T833)) < 1e-6
    assert abs(r["margin_hi_ps"] - (3.5 * T833 - (2 * T833 - 276))) < 1e-6
    assert r["margin_lo_ps"] >= ap and r["margin_ps"] == min(r["margin_lo_ps"], r["margin_hi_ps"])
    # K follows the derated low end, not the nominal d: d = -300 alone -> K 1; p_dn 50 pushes it below 0.5T + ap -> K 2
    assert ocv.count_aligned_margin({"TT": (-300.0, 0.0, 0.0)}, T833)["K"] == 1
    assert ocv.count_aligned_margin({"TT": (-300.0, 0.0, 50.0)}, T833)["K"] == 2
    # origin ambiguity (one whole cycle low) and wander widen the lag interval
    assert ocv.count_aligned_margin(TRIP, T833, origin_cycles=(1, 0))["K"] == 3
    rw = ocv.count_aligned_margin(TRIP, T833, wander_ps=30.0)
    assert abs((rw["L_hi_ps"] - rw["L_lo_ps"]) - (r["L_hi_ps"] - r["L_lo_ps"] + 60.0)) < 1e-6
    # 3000 ps spread: DEPTH 8; 6000 ps: FAIL (depth None, negative margin)
    assert ocv.count_aligned_margin({"TT": (0.0, 1500.0, 1500.0)}, T833)["depth"] == 8
    f = ocv.count_aligned_margin({"TT": (0.0, 3000.0, 3000.0)}, T833)
    assert f["depth"] is None and f["latency_cycles"] is None and f["margin_ps"] < 0


# HEAD feed40 rows (DIE-HEAD routed_sfb250/landed_ocv.json remapped to maps/feed36b.json; corners TT corelat250 + FF
# corelat202.5): [d, p_up, p_dn, unshared_a, unshared_b] and MESO-COUNT-2 count_align_plan.py (f7b28e70d) results
# (T 833, ap T/8, wander 5 %, spice scale OFF): K_eff, depth, L_lo, L_hi
FEED40 = [
    ("coll_WS0_u__0", [-41.86, 53.39, 54.53, 260.7, 218.8], [-36.86, 42.14, 43.0, 223.0, 186.2], 1, 4, 723.6, 857.6),
    ("coll_ES0_d__0", [33.18, 55.63, 54.73, 235.6, 268.8], [29.46, 43.94, 43.25, 201.0, 230.5], 1, 4, 798.0, 935.2),
    ("sp_x0__0", [-226.88, 64.66, 70.83, 526.2, 299.3], [-192.46, 51.88, 56.39, 448.0, 255.5], 2, 4, 1342.0, 1551.7),
]


def test_count_aligned_parity_count_align_plan():
    """same K / DEPTH / lag window as tools/die_plan/count_align_plan.py (MESO-COUNT-2) on clean-path crossings."""
    from clkplan import crossrows as CR
    Mn = MD.load(spice_scale=False)
    cs = ["TT_x", "FF_x"]
    by = {p: {cs[0]: dict(port=p, d_ps=t[0], p_up_ps=t[1], p_dn_ps=t[2], unshared_a_ps=t[3], unshared_b_ps=t[4]),
              cs[1]: dict(port=p, d_ps=f[0], p_up_ps=f[1], p_dn_ps=f[2], unshared_a_ps=f[3], unshared_b_ps=f[4])}
          for p, t, f, *_ in FEED40}
    out = {o["port"]: o for o in CR.evaluate(by, cs, Mn, T=833.0)}
    for p, t, f, K, D, lo, hi in FEED40:
        o = out[p]
        assert (o["K"], o["depth"]) == (K, D), p
        assert abs(o["L_lo_ps"] - lo) < 0.11 and abs(o["L_hi_ps"] - hi) < 0.11, (p, o)
    # spice-scaled (default model): every STA-basis term x1.0485 TT / x1.0552 FF -> lag interval widens
    Ms = MD.load()
    o2 = {o["port"]: o for o in CR.evaluate(by, cs, Ms, T=833.0)}["sp_x0__0"]
    assert o2["L_hi_ps"] - o2["L_lo_ps"] > out["sp_x0__0"]["L_hi_ps"] - out["sp_x0__0"]["L_lo_ps"]


def test_spice_scale_default_and_flag():
    """COORD 21:10: plan-time margins use spice-scaled arrivals by default (STA-basis delays x cal); flag disables;
    the built-in stage model is already spice basis (not scaled twice); an STA-fitted model file is scaled."""
    assert M.arrival_scale("TT", "sta") == 1.0485 and M.arrival_scale("FF", "sta") == 1.0552
    assert M.arrival_scale("TT", "model") == 1.0
    assert MD.load(spice_scale=False).arrival_scale("TT", "sta") == 1.0
    fit = REPO / "opentools" / "mscts" / "data" / "asap7_bufx24_sta_fit.json"
    if fit.exists():
        assert MD.load(fit).arrival_scale("FF", "model") == 1.0552
    # region mode: declared (STA) insertions -> d scales by the TT factor
    P = PL.load(EX)
    for r in P["regions"]:
        r.setdefault("clock", {})["local_insertion_ps"] = {"TT": 100.0 + 50 * int(r["name"][1:]), "FF": 80.0}
    P["feeds"] = [dict(name=f"s{i}", src="root", dst=f"r{i}", len_um=1500.0, kind="spine") for i in range(3)]
    on = RM.analyse(P, M, PL.clock_sinks(P))
    off = RM.analyse(P, MD.load(spice_scale=False), PL.clock_sinks(P))
    a = {r["name"]: r for r in on["crossings"]["rows"]}["x01"]
    b = {r["name"]: r for r in off["crossings"]["rows"]}["x01"]
    assert abs(b["TT"]["d_ps"]) > 10 and abs(a["TT"]["d_ps"] / b["TT"]["d_ps"] - 1.0485) < 0.01
    assert on["crossings"]["summary"]["spice_cal"]["TT"] == 1.0485


def test_forwarded_hop_passes_count_aligned_ring():
    """the toy 3-mm forwarded hop FAILS the one-period ring on nominal d alone, but its derated variation fits the
    count-aligned ring window: same predictor, crossing_mode only changes the window."""
    P = PL.load(EX)
    ph = RM.analyse(P, M, PL.clock_sinks(P))
    ca = RM.analyse(P, M, PL.clock_sinks(P), crossing_mode="count_aligned")
    x = {r["name"]: r for r in ca["crossings"]["rows"]}["x01"]
    assert x["mode"] == "count_aligned" and x["TT"]["phase_margin_ps"] < 0 < x["TT"]["margin_ps"]
    assert x["pass"] and isinstance(x["count_aligned"]["K"], int) and x["count_aligned"]["depth"] in (4, 8)
    assert x["count_aligned"]["margin_lo_ps"] >= T833 / 8 - 1        # K from the derated lag keeps >= ap low side
    rp = RM.analyse(P, M, PL.clock_sinks(P), crossing_mode="ring_phase")
    assert {r["name"]: r for r in rp["crossings"]["rows"]}["x01"]["mode"] == "ring_phase"
    assert ca["crossings"]["summary"]["crossing_mode"] == "count_aligned"
    assert ph["verdict"] == "FAIL"
