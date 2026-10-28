"""FLOW-ONEMODEL-1: the count-aligned plan and the die STA gate use ONE interval function (METHODOLOGY 12.16b(ii)/(d):
the plan-time check and the built-arrival recheck use the same model).

BUG 1 (DIE-KV-11): count_align_plan hulled each crossing with its partition-pair STA interval, die_sta_related
--count-align-key region timed it on the union of every partition pair of its REGION pair, so a phy ring was gated on
the 12 pc ports' clock pins (plan L_lo 523.0 vs gate 461.2 ps on phy_WN_3->phy_WN_2).  Both now call
die_sta_related.count_align_port_intervals: a port is timed on the tap pairs it carries.

BUG 2 (DIE-HEAD-11): a fall-edge start sample was planned and gated on rise + T/2; measured duty distortion on BUF
trees is 148-1149 ps.  Both now take the capture pins' MEASURED fall arrival (ca_pair_interval edge 'fall'); with
rise-only arrivals the planner never samples on fall and the gate fails a fall sample closed."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count_align_bind as CAB  # noqa: E402
import count_align_plan as CAP  # noqa: E402
import die_sta_related as D  # noqa: E402

spec = importlib.util.spec_from_file_location("st_fix", HERE / "test_count_align_starttree.py")
ST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ST)

T = 833.0
AP = T / 8
REG = dict(clkq_max_wire_ps=60.0, clkq_min_nowire_ps=50.0)


# ------------------------------------------------------------------ BUG 1: one per-port interval, plan == gate

def _two_region_proof(tmp_path):
    """regions R1 = {phyA, pcA}, R2 = {phyB, pcB}.  The pc partitions sit on a far, slow branch (their tap pair
    pcA -> pcB spans [100, 700]); the phy pair is tight ([600, 700]).  Region union = [100, 700]."""
    taps = [dict(port="t_phyA", part="phyA", late_ps=1000.0, early_ps=990.0, cppr_node="R1", slew_ps=10.0),
            dict(port="t_phyB", part="phyB", late_ps=1700.0, early_ps=1600.0, cppr_node="R2", slew_ps=10.0),
            dict(port="t_pcA", part="pcA", late_ps=1500.0, early_ps=1100.0, cppr_node="R1", slew_ps=10.0),
            dict(port="t_pcB", part="pcB", late_ps=1800.0, early_ps=1600.0, cppr_node="R2", slew_ps=10.0)]
    for c in ("TT", "FF"):
        (tmp_path / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(corner=c, cppr_node_range_ps={}, taps=taps)))
    plan = dict(ports=[dict(id="phy", src=dict(part="phyA"), dst=dict(part="phyB"), width=1),
                       dict(id="pc", src=dict(part="pcA"), dst=dict(part="pcB"), width=1)])
    return tmp_path, {t["port"]: t for t in taps}, plan


def _rows():
    # landed_phase_ocv rows (narrower than the STA: the STA hull decides)
    mk = lambda p, s, d, dd: dict(port=p, src="R1", dst="R2", src_part=s, dst_part=d, d_ps=dd, p_up_ps=10.0,  # noqa
                                  p_dn_ps=10.0, unshared_a_ps=0.0, unshared_b_ps=0.0, margin_ps=0.0)
    return [mk("phy", "phyA", "phyB", 650.0), mk("pc", "pcA", "pcB", 400.0),
            dict(port="back", src="R2", dst="R1", src_part="phyB", dst_part="phyA", d_ps=-650.0, p_up_ps=10.0,
                 p_dn_ps=10.0, unshared_a_ps=0.0, unshared_b_ps=0.0, margin_ps=0.0)]


def _plan_bind_gate(tmp_path, ports_fn=None):
    proof, taps, dplan = _two_region_proof(tmp_path)
    dplan["ports"].append(dict(id="back", src=dict(part="phyB"), dst=dict(part="phyA"), width=1))
    rows = _rows()
    ports, pr = CAP.row_ports(rows)
    sta = D.sta_port_intervals(proof, dplan, ("TT",), ports, pr, fall=True)
    CAP.sta_hull(rows, sta)
    s, out, regs = CAP.plan(rows, T, AP, 0.0)
    s.update(period_ps=T, aperture_ps=AP, sync_aperture_ps=26.5, pad=0)
    b = CAB.bind(CAB.plan_doc(s, out, regs), parts={r["port"]: (r["src_part"], r["dst_part"]) for r in rows})
    landed = [("t_phyA", "t_phyB", "phyA->phyB"), ("t_pcA", "t_pcB", "pcA->pcB"), ("t_phyB", "t_phyA", "phyB->phyA")]
    ca = D.count_align_landed(landed, taps, b, T, REG, key="region")
    return sta, {o["port"]: o for o in out}, {r["port"]: r for r in ca["rows"]}, ca, (landed, taps, b)


def test_plan_and_gate_time_each_port_on_its_own_tap_pairs(tmp_path):
    sta, plan, gate, ca, _ = _plan_bind_gate(tmp_path)
    assert sta["TT"]["rise"]["phy"] == (600.0, 710.0) and sta["TT"]["rise"]["pc"] == (100.0, 700.0)
    assert ca["unbound"] == 0 and ca["no_taps"] == 0
    for p in ("phy", "pc", "back"):
        # same function, same corner -> the gate's lag bounds ARE the plan's (no 60-80 ps disagreement)
        assert abs(gate[p]["L_lo_ps"] - plan[p]["L_lo_ps"]) < 0.11, p
        assert abs(gate[p]["margin_lo_ps"] - plan[p]["margin_lo_ps"]) < 0.11, p
    assert plan["phy"]["margin_lo_ps"] >= 100 and gate["phy"]["lag_ok"]


def test_mutant_region_union_gate_reproduces_the_kv11_disagreement(tmp_path, monkeypatch):
    """the pre-fix gate (region-pair union) puts the pc pair's early bound on the phy ring: plan PASS, gate FAIL"""
    _, plan, _, _, (landed, taps, b) = _plan_bind_gate(tmp_path)
    fixed = D.count_align_port_intervals

    def region_union(ports, landed, taps, cppr_range=None, part_region=None, ocv=None, stats=None, edge="rise"):
        flat = {pid: dict(src=c["src"], dst=c["dst"]) for pid, c in ports.items()}     # names dropped
        return fixed(flat, landed, taps, cppr_range, part_region, ocv, stats, edge)
    monkeypatch.setattr(D, "count_align_port_intervals", region_union)
    mut = {r["port"]: r for r in D.count_align_landed(landed, taps, b, T, REG, key="region")["rows"]}
    assert plan["phy"]["margin_lo_ps"] >= 100
    assert mut["phy"]["L_lo_ps"] < plan["phy"]["L_lo_ps"] - 400 and not mut["phy"]["lag_ok"]


def test_unnamed_partition_pair_goes_to_every_port_of_its_region_pair():
    taps = {"a": dict(part="phyA", late_ps=0.0, early_ps=0.0, cppr_node="h"),
            "b": dict(part="pcB", late_ps=300.0, early_ps=250.0, cppr_node="h"),
            "c": dict(part="phyB", late_ps=600.0, early_ps=600.0, cppr_node="h")}
    ports = {"phy": dict(src="R1", dst="R2", src_part="phyA", dst_part="phyB"),
             "x": dict(src="R1", dst="R3")}
    pr = {"phyA": "R1", "phyB": "R2", "pcB": "R2"}
    iv, unb, n = D.count_align_port_intervals(ports, [("a", "c", ""), ("a", "b", "")], taps, part_region=pr)
    # phyA -> pcB is named by nobody: the region crossing R1 -> R2 (port phy) carries it (conservative)
    assert iv["phy"] == (250.0, 600.0) and n["phy"] == 2 and "x" not in iv and unb == []
    iv, unb, _ = D.count_align_port_intervals({"x": ports["x"]}, [("a", "c", "")], taps, part_region=pr)
    assert unb == ["R1->R2"] and iv == {}                       # no crossing for the region pair: fail closed


# ------------------------------------------------------------------ BUG 2: measured fall arrival, both edges

def _start_gate(rows, ctx, clean_by="phase"):
    root, edges, info = CAP.clock_start_edges(copy.deepcopy(rows), ctx, clean_by=clean_by)
    s, out, regs = CAP.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=edges, start_root=root)
    doc = dict(summary=dict(s, period_ps=T, pad=0), regions=regs, crossings=out,
               start_edges=[{k: v for k, v in e.items() if not k.startswith("_")} for e in edges])
    b = CAB.bind(doc)
    k = ctx["TT"]
    taps = {q: t for q, t in k["taps"].items() if not q.startswith("__st__")}
    old, D.CPPR_LCA = D.CPPR_LCA, True
    try:
        rows_g = D.count_align_start_ports(b, taps, k["meta"], T, {}, k["ocv"])
    finally:
        D.CPPR_LCA = old
    return s, regs, edges, b, {r["port"]: r for r in rows_g}, info


def test_distorted_duty_plan_and_gate_agree_on_every_start_port():
    """a BUF tree whose fall arrival lags rise by 40 ps per level (deep taps: ~300 ps): the planner chooses each sample
    edge on the MEASURED arrivals, the gate re-times it on the same arrivals, and they agree port by port"""
    rows = ST.chain_rows()
    ctx = ST.ctx_chain(fall=lambda lev: 40.0 * lev)
    s, regs, edges, b, gate, _ = _start_gate(rows, ctx)
    plan_clean = {g["start_from"]["port"]: g["start_from"]["sync_values"] == 1 and g["start_from"].get("clean_ok", True)
                  for g in regs if g["start_from"]}
    assert set(plan_clean) == set(gate)
    for p, ok in plan_clean.items():
        assert gate[p]["ok"] == ok, (p, gate[p])
    falls = [g["start_from"] for g in regs if g["start_from"] and g["start_from"]["edge"] == "fall"]
    for e in falls:     # a fall sample is planned on its measured interval, not on the rise interval
        assert e["fall_measured"] and e["sample_interval_ps"] != e["start_interval_ps"]
    v = CAB.verify(b, 600)
    assert v["identity_and_loop_errors"] == [] and v["sim_window_violations"] == 0


def test_mutant_t2_assumption_is_caught_by_the_measured_gate():
    """MUTANT = the pre-fix planner (fall = rise + T/2, i.e. it plans on an undistorted copy of the arrivals): on the
    distorted tree some fall sample it calls clean lands on a boundary of the MEASURED fall arrival"""
    rows = ST.chain_rows()
    ideal = ST.ctx_chain(fall=0.0)
    root, edges, _ = CAP.clock_start_edges(copy.deepcopy(rows), ideal)
    s, out, regs = CAP.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=edges, start_root=root)
    # a uniform duty distortion that moves the first fall sample's boundary into the middle of its interval
    e0 = next(x["start_from"] for x in regs if x["start_from"] and x["start_from"]["edge"] == "fall")
    c = 0.5 * sum(e0["start_interval_ps"])
    shift = T / 2 + round((c - T / 2) / T) * T - c
    dist = ST.ctx_chain(fall=shift)
    doc = dict(summary=dict(s, period_ps=T, pad=0), regions=regs, crossings=out,
               start_edges=[{k: v for k, v in e.items() if not k.startswith("_")} for e in edges])
    b = CAB.bind(doc)
    k = dist["TT"]
    leg, fleg = D.tap_leg(k["meta"], k["taps"]), D.tap_leg_fall(k["meta"], k["taps"])
    for q in list(ideal["TT"]["taps"]):
        if q.startswith("__st__"):
            D.virtual_tap(k["meta"], k["taps"], q[6:], leg, fleg)     # the ocv stand-in reads the fixture's taps
    taps = {q: t for q, t in k["taps"].items() if not q.startswith("__st__")}
    old, D.CPPR_LCA = D.CPPR_LCA, True
    try:
        g = {r["port"]: r for r in D.count_align_start_ports(b, taps, k["meta"], T, {}, k["ocv"])}
    finally:
        D.CPPR_LCA = old
    fall_ports = [x["start_from"]["port"] for x in regs if x["start_from"] and x["start_from"]["edge"] == "fall"]
    assert fall_ports and not g[e0["port"]]["ok"]
    # the fixed planner on the SAME measured arrivals: plan and gate agree port by port (no clean claim that fails)
    rf, ef, _ = CAP.clock_start_edges(copy.deepcopy(rows), ST.ctx_chain(fall=shift))
    _, _, regs_f = CAP.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=ef, start_root=rf)
    for x in regs_f:
        e = x["start_from"]
        if e and e["edge"] == "fall":       # every fall sample it keeps is >= ap clear on the MEASURED interval
            lo, hi = e["sample_interval_ps"]
            assert e["fall_measured"] and CAP.boundary_dist(lo, hi, T, T / 2) >= AP - 0.1


def test_rise_only_arrivals_never_sample_fall_and_width_fails_closed():
    rows = ST.chain_rows()
    root, edges, info = CAP.clock_start_edges(copy.deepcopy(rows), ST.ctx_chain(fall=None))
    s, out, regs = CAP.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=edges, start_root=root)
    assert info["fall_measured"] == 0 and all(e["fall_lo"] is None for e in edges)
    assert all(g["start_from"]["edge"] == "rise" for g in regs if g["start_from"])
    rw, ew, iw = CAP.clock_start_edges(copy.deepcopy(rows), ST.ctx_chain(fall=None), clean_by="width")
    sw, _, _ = CAP.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=ew, start_root=rw)
    assert iw["clean_by_width"] == 0 and sw["start_tree"]["start_fail"] >= 1    # one edge cannot be width-robust
    # the gate fails a fall sample closed when the arrivals carry no measured fall (strip them from a measured bind)
    ctx = ST.ctx_chain(fall=lambda lev: 40.0 * lev)
    _, regs_m, _, b, gate, _ = _start_gate(rows, ctx)
    fall_ports = [g["start_from"]["port"] for g in regs_m if g["start_from"] and g["start_from"]["edge"] == "fall"]
    assert fall_ports
    k = ctx["TT"]
    taps = {q: {f: v for f, v in t.items() if not f.startswith("fall_")} for q, t in k["taps"].items()
            if not q.startswith("__st__")}
    meta = {f: v for f, v in k["meta"].items() if not f.startswith("node_fall_")}
    r = {q["port"]: q for q in D.count_align_start_ports(b, taps, meta, T, {}, k["ocv"])}
    for p in fall_ports:
        assert r[p]["ok"] is False and "measured fall" in r[p]["reason"]
    assert all(r[p]["ok"] == gate[p]["ok"] for p in r if p not in fall_ports)


def test_width_rule_reduces_to_the_original_at_50pct_duty_and_moves_with_distortion():
    for w in (50.0, 150.0, 200.0, 208.0, 209.0, 300.0):
        r = dict(lo=100.0, hi=100.0 + w)
        legacy = CAP.width_robust(r, T, AP)
        measured = CAP.width_robust(dict(r, fall_lo=r["lo"], fall_hi=r["hi"]), T, AP)
        assert legacy == measured == (w <= T / 2 - 2 * AP + 1e-9)
    r = dict(lo=100.0, hi=250.0, fall_lo=100.0 + 416.5, fall_hi=250.0 + 416.5)   # fall lags by T/2: edges coincide
    assert not CAP.width_robust(r, T, AP)
    assert not CAP.width_robust(dict(lo=100.0, hi=150.0, fall_lo=None, fall_hi=None), T, AP)


def test_fall_interval_uses_measured_fall_and_no_cppr_credit():
    A = dict(port="a", part="x", late_ps=100.0, early_ps=90.0, cppr_node="h", tree_path="hA0")
    B = dict(port="b", part="y", late_ps=300.0, early_ps=280.0, fall_late_ps=520.0, fall_early_ps=500.0,
             cppr_node="h", tree_path="hA1")
    old, D.CPPR_LCA = D.CPPR_LCA, True
    try:
        rng = {"hA": 5.0}
        assert D.ca_pair_interval(A, B, "a", "b", rng)[:2] == (185.0, 205.0)          # rise: CPPR credit 5
        assert D.ca_pair_interval(A, B, "a", "b", rng, edge="fall")[:2] == (400.0, 430.0)
        try:
            D.ca_pair_interval(B, A, "b", "a", rng, edge="fall")
            raise AssertionError("rise-only capture must fail closed on a fall sample")
        except D.FallArrivalMissing:
            pass
    finally:
        D.CPPR_LCA = old


def test_tap_fall_merge_reads_both_readout_forms(tmp_path):
    import tap_fall_merge as M
    p = tmp_path / "proof"
    p.mkdir()
    (p / "tap_arrivals_TT.json").write_text(json.dumps(dict(taps=[
        dict(port="a", part="x", late_ps=100.0, early_ps=90.0), dict(port="b", part="x", late_ps=200.0, early_ps=180.0),
        dict(port="c", part="x", late_ps=300.0, early_ps=280.0)])))
    (p / "droop_regions.json").write_text("{}")
    (tmp_path / "d.txt").write_text("D a 50 80 1 1\nF b 260 210 3\n")
    assert M.main([str(p), "TT", str(tmp_path / "d.txt"), "--out", str(tmp_path / "o")]) == 0
    t = {x["port"]: x for x in json.loads((tmp_path / "o" / "tap_arrivals_TT.json").read_text())["taps"]}
    assert (t["a"]["fall_late_ps"], t["a"]["fall_early_ps"]) == (130.0, 120.0)
    assert (t["b"]["fall_late_ps"], t["b"]["fall_early_ps"]) == (250.0, 230.0)
    assert "fall_late_ps" not in t["c"] and (tmp_path / "o" / "droop_regions.json").exists()
