"""CA-OCV-1 (DIE-S81-8 finding, COORD 2026-10-28 06:31): the count-aligned (CA) crossing interval of die_sta_related =
STA phase (OpenSTA late/early, CPPR) + EXACTLY ONE clock variation term, the same callable the related-pair classes
get (ONE SHARED DIE TIMING MODEL; METHODOLOGY 12.14a crossing margin counted after OCV + droop).  Includes the mutant
(pre-fix interval, no variation term) and the swapped-side mutant, both of which these tests reject."""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clk_aocv as CA  # noqa: E402
import die_sta_related as R  # noqa: E402

T = 833.0
REG = dict(clkq_max_wire_ps=48.0, clkq_min_nowire_ps=30.0, setup_ps=10.0, hold_ps=10.0)
OS, OH = 7.0, 3.0      # asymmetric so a swapped (setup<->hold) mutant is visible


def _ocv(a, b, check):
    return OS if check == "setup" else OH


def _taps():
    return {"a0": dict(part="A", cppr_node="A", late_ps=300.0, early_ps=280.0),
            "b0": dict(part="B", cppr_node="B", late_ps=520.0, early_ps=500.0)}


def _bind(lo_margin_extra=0.0):
    # one non-tree crossing A->B, plan d [200, 240], K = 1, depth 4: STA lo margin = T + 200 - T/2 = 616.5
    return {"sync_aperture_ps": 26.5, "ports": {
        "x": dict(src="A", dst="B", K=1, depth=4, sched_lat=2, tree=False, L_lo_ps=T + 200.0 + lo_margin_extra,
                  L_hi_ps=T + 240.0, d_lo_ps=200.0, d_hi_ps=240.0, wander_ps=0.0)}, "regions": {}}


_FIXED = R.count_align_d_intervals


def _pre_fix_interval(landed, taps, cppr_range=None, part_region=None, ocv=None, stats=None):
    """MUTANT = main before CA-OCV-1: the variation callable is ignored."""
    return _FIXED(landed, taps, cppr_range, part_region)


def _swapped_interval(landed, taps, cppr_range=None, part_region=None, ocv=None, stats=None):
    """MUTANT: setup and hold pessimism applied to the wrong ends."""
    sw = None if ocv is None else (lambda a, b, c: ocv(a, b, "hold" if c == "setup" else "setup"))
    return _FIXED(landed, taps, cppr_range, part_region, ocv=sw, stats=stats)


def test_interval_is_sta_phase_plus_exactly_one_variation_term():
    L = [("a0", "b0", "A->B")]
    assert R.count_align_d_intervals(L, _taps()) == {"A->B": (200.0, 240.0)}           # unchanged without ocv
    st = {}
    lo, hi = R.count_align_d_intervals(L, _taps(), ocv=_ocv, stats=st)["A->B"]
    # d_lo = capture early - launch late - ocv(setup: launch late + capture early); d_hi = ... + ocv(hold)
    assert (lo, hi) == (200.0 - OS, 240.0 + OH)
    assert st == {"A->B": [OS, OH]}
    assert _swapped_interval(L, _taps(), ocv=_ocv)["A->B"] == (200.0 - OH, 240.0 + OS)   # mutant differs


def test_ca_row_margins_drop_by_exactly_the_ocv_and_record_it():
    L = [("a0", "b0", "A->B")]
    r0 = R.count_align_landed(L, _taps(), _bind(), T, REG)
    r1 = R.count_align_landed(L, _taps(), _bind(), T, REG, ocv=_ocv, ocv_label="table")
    x0, x1 = r0["rows"][0], r1["rows"][0]
    assert round(x0["margin_lo_ps"] - x1["margin_lo_ps"], 3) == OS
    assert round(x0["margin_hi_ps"] - x1["margin_hi_ps"], 3) == OH
    assert (x1["ocv_lo_ps"], x1["ocv_hi_ps"]) == (OS, OH) and "ocv_lo_ps" not in x0
    assert r0["clock_variation"] == "none" and r1["clock_variation"] == "table"
    assert (r1["ocv_max_lo_ps"], r1["ocv_max_hi_ps"]) == (OS, OH) and r0["ocv_max_lo_ps"] is None


def test_mutant_without_variation_passes_a_crossing_the_fixed_gate_fails(monkeypatch):
    # plan lag shifted so the STA lo margin is 104 ps: PASS on the bare STA phase, FAIL after the 7 ps OCV (97 < 100),
    # the DIE-S81-8 failure mode (gate PASS hid crossings < 100 ps after OCV + droop)
    L = [("a0", "b0", "A->B")]
    b = _bind()
    ml = R.count_align_landed(L, _taps(), b, T, REG)["rows"][0]["margin_lo_ps"]
    shift = 104.0 - ml
    b["ports"]["x"]["L_lo_ps"] += shift
    b["ports"]["x"]["L_hi_ps"] += shift
    good = R.count_align_landed(L, _taps(), b, T, REG, ocv=_ocv, ocv_label="table")
    assert good["fail"] == 1 and good["below_need"] == 1 and good["verdict"] == "FAIL"
    fixed_pair = R.ca_pair_interval
    # MUTANT (pre CA-OCV-1) on the one pair function every interval goes through (FLOW-ONEMODEL-1)
    monkeypatch.setattr(R, "ca_pair_interval", lambda A, B, a, b, rng=None, ocv=None, edge="rise":
                        fixed_pair(A, B, a, b, rng, None, edge))
    mut = R.count_align_landed(L, _taps(), b, T, REG, ocv=_ocv, ocv_label="table")
    assert mut["fail"] == 0 and mut["verdict"] == "PASS"            # the mutant hides it: this test catches the mutant


def test_ss_info_scales_the_same_variation_term():
    L = [("a0", "b0", "A->B")]
    s = R.count_align_ss_info(L, _taps(), _bind(), T, REG, scale=1.27, ocv=_ocv, ocv_label="table")
    s0 = R.count_align_ss_info(L, _taps(), _bind(), T, REG, scale=1.27)
    assert abs((s0["rows"][0]["margin_lo_ps"] - s["rows"][0]["margin_lo_ps"]) - 1.27 * OS) < 0.11
    assert s["gates"] is False and s["clock_variation"] == "table x 1.27"


# ---- table mode end to end: sta_d_intervals (planner) == hand clk_aocv computation == main() CA row

def _fold_proof(tmp_path):
    """two regions under die root h, taps 3 mm apart, branch 1200/1150 (A) and 1500/1440 (B) below h."""
    taps = [dict(port="pa", part="A", cppr_node="A", late_ps=1220.0, early_ps=1160.0, slew_ps=10.0,
                 stages_from_root=12, xy_um=[0.0, 0.0]),
            dict(port="pb", part="B", cppr_node="B", late_ps=1520.0, early_ps=1450.0, slew_ps=10.0,
                 stages_from_root=14, xy_um=[3000.0, 0.0])]
    meta = dict(cppr_node_range_ps={"h": 0.0}, node_late_ps={"h": 20.0}, node_early_ps={"h": 10.0},
                node_stages={"h": 0}, node_xy_um={"h": [1500.0, 0.0]})
    for c in ("TT", "FF"):
        (tmp_path / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(corner=c, taps=taps, clock_cell="buf", **meta)))
    plan = dict(clock=dict(common_latency_ps=250.0), ports=[dict(id="x", src=dict(part="A"), dst=dict(part="B"), width=1)])
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    return tmp_path, {t["port"]: t for t in taps}, meta, plan


def _hand(corner, late_br, early_br, lat, same=False):
    """independent re-derivation from the table file (not via clock_ocv_fn)."""
    t = CA.load(Path(R.__file__).resolve().parent / R.APPROVED_AOCV_TABLE)
    fa, B = t["classes"]["A"][corner]["cell_share"], t["classes"]["B"][corner]
    nB = max(1, round(lat / B["mu_stage_ps"]))

    def side(arr, st):
        cell = fa * arr + B["cell_share"] * lat
        net = (1 - fa) * arr + (1 - B["cell_share"]) * lat
        var = (t["classes"]["A"][corner]["mu_cell_ps"] * t["classes"]["A"][corner]["s_cell"]) ** 2 * st \
            + (B["mu_cell_ps"] * B["s_cell"]) ** 2 * (nB + 2 * sum((nB - l) * r for l, r in enumerate(B["rho"], 1) if l < nB))
        mu = st * t["classes"]["A"][corner]["mu_cell_ps"] + nB * B["mu_cell_ps"]
        return cell, net, t["k_sigma"] * math.sqrt(var) / mu
    d_mm = 3.0
    g = t["systematic"]["g_per_mm"] * d_mm / 2
    cl, nl, rl = side(*late_br)
    ce, ne, re_ = side(*early_br)
    droop = 0.0 if same else t["droop"]["one_sided_late_frac"]
    return cl * (rl + g + droop) + ce * (re_ + g) + nl * (t["net_flat"]["late"] - 1) + ne * (1 - t["net_flat"]["early"])


def test_sta_d_intervals_table_equals_hand_aocv_and_default_unchanged(tmp_path):
    proof, taps, meta, plan = _fold_proof(tmp_path)
    base = R.sta_d_intervals(proof, plan, ("TT",), "none", False)["TT"]["A->B"]
    assert base == (1450.0 - 1220.0, 1520.0 - 1160.0)
    got = R.sta_d_intervals(proof, plan, ("TT",), "none", False, clock_ocv="table", clock_droop="shared",
                            margin_policy="legacy")["TT"]["A->B"]
    # setup side: launch A late branch (1220-20, 12 st), capture B early (1450-10, 14 st); hold: B late, A early
    ps = _hand("TT", (1200.0, 12), (1440.0, 14), 250.0)
    ph = _hand("TT", (1500.0, 14), (1150.0, 12), 250.0)
    assert ps > 50 and ph > 50                            # cross-region: one-sided droop + AOCV on ~1.2-1.5 ns
    assert abs(got[0] - (base[0] - ps)) < 1e-6 and abs(got[1] - (base[1] + ph)) < 1e-6


def test_main_count_align_row_carries_the_class_ocv(tmp_path, monkeypatch):
    proof, taps, meta, plan = _fold_proof(tmp_path)
    monkeypatch.setattr(R, "characterise", lambda *a, **k: dict(REG))
    d_lo, d_hi = 230.0, 360.0
    bind = {"sync_aperture_ps": 26.5, "ports": {"x": dict(src="A", dst="B", K=1, depth=8, tree=False,
                                                          L_lo_ps=T + d_lo, L_hi_ps=T + d_hi, d_lo_ps=d_lo,
                                                          d_hi_ps=d_hi, wander_ps=0.0)}, "regions": {}}
    (tmp_path / "bind.json").write_text(json.dumps(bind))
    base = [str(proof), "--plan", str(tmp_path / "plan.json"), "--corner", "TT", "--count-align",
            str(tmp_path / "bind.json"), "--period-ps", str(T), "--count-align-ss-scale", "0", "--margin-policy", "legacy"]
    R.main(base + ["--out", str(tmp_path / "o0")])
    R.main(base + ["--out", str(tmp_path / "o1"), "--clock-ocv", "table", "--clock-droop", "shared"])
    r0 = json.loads((tmp_path / "o0" / "die_sta_related.json").read_text())
    r1 = json.loads((tmp_path / "o1" / "die_sta_related.json").read_text())
    x0, x1 = r0["count_aligned"]["TT"]["rows"][0], r1["count_aligned"]["TT"]["rows"][0]
    ps = _hand("TT", (1200.0, 12), (1440.0, 14), 250.0)
    ph = _hand("TT", (1500.0, 14), (1150.0, 12), 250.0)
    assert abs((x0["margin_lo_ps"] - x1["margin_lo_ps"]) - ps) < 0.11 and abs((x0["margin_hi_ps"] - x1["margin_hi_ps"]) - ph) < 0.11
    assert r0["count_aligned"]["TT"]["clock_variation"] == "none"
    assert r1["count_aligned"]["TT"]["clock_variation"] == "table"
    assert r1["summary"]["landed"]["clock_variation"] == {"TT": "table"}
    # one term only: the landed class (same callable) charges the same setup pessimism on that pair
    assert abs(r1["corners"]["TT"]["classes"]["landed"]["clock_ocv_pessimism_max_ps"]["setup"] - ps) < 0.011


def test_planner_cli_flags_reach_sta_port_intervals(tmp_path, monkeypatch):
    import count_align_plan as CAP
    seen = {}

    def fake(proof, plan, cs, ports, pr, cal, lca, fall=False, **kw):
        seen.update(kw)
        return {"TT": dict(rise={}, fall={}, unbound=[])}
    import die_sta_related as DSR
    monkeypatch.setattr(DSR, "sta_port_intervals", fake)
    rows = dict(corners={"TT_x": dict(all=[dict(port="p", src="a", dst="b", d_ps=100.0, p_up_ps=1.0, p_dn_ps=1.0,
                                                unshared_a_ps=0.0, unshared_b_ps=0.0, margin_ps=0.0)])})
    (tmp_path / "r.json").write_text(json.dumps(rows))
    try:
        CAP.main([str(tmp_path / "r.json"), "--corner", "TT_x", "--sta-proof", str(tmp_path), "--sta-plan", "p.json",
                  "--sta-clock-ocv", "table", "--sta-clock-droop", "shared", "--sta-droop-regions", "dr.json",
                  "--sta-core-latency-ff", "202.5", "--sta-clock-cell", "inv2", "--out", str(tmp_path / "o.json"),
                  "--margin-policy", "legacy"])
    except SystemExit:
        pass
    assert seen == dict(clock_ocv="table", clock_droop="shared", droop_regions_file="dr.json", core_latency_ff=202.5,
                       clock_cell="inv2", margin_policy="legacy")
