"""CLK-INV-CAL-1 follow-ups (COORD 10-28, after FLOW-ONEMODEL-1):
1. the one-model plan path (die_sta_related.sta_port_intervals) prices an inverter clock exactly as the gate
   (die_sta_related main --count-align): SPICE_CLOCK_CAL_INV on rise AND fall arrivals + AOCV class Ainv;
2. wander rule: a crossing's post-start wander = wander_frac x the worst unshared clock over its OWN launch/capture tap
   pairs (ca_pair_unshared), in the planner and in the gate - never a global max over all crossings and never a
   single legacy tap per partition (QC t10 sl_E4_su_c -> sl_E4_stm: plan 55.3 ps vs own pairs 65.7 ps)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count_align_bind as CAB  # noqa: E402
import count_align_plan as CAP  # noqa: E402
import die_sta_related as D  # noqa: E402

import pytest  # noqa: E402

T = 833.0
AP = T / 8


@pytest.fixture(autouse=True)
def _restore_cppr_lca(monkeypatch):
    # die_sta_related.main() sets the module flag CPPR_LCA from --cppr-lca; restore it for the other test modules
    monkeypatch.setattr(D, "CPPR_LCA", D.CPPR_LCA)
INV, BUF = "CKINVDCx16_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"


def _proof(d, cell="inv", far_late=0.0):
    """regions R1 = {suc}, R2 = {stm}; suc has a near tap (s0) and a far one (s1, + far_late ps later on the same
    branch: it raises the unshared clock of the s1 pairs only); LCA = 'h' for every pair."""
    d.mkdir(parents=True, exist_ok=True)
    n = 140 if cell == "inv" else 0
    (d / "ctree.v").write_text("module ctree ();\n" + "".join(f"  {INV} r{i} (.A(a), .Y(b));\n" for i in range(n))
                               + "".join(f"  {BUF} b{i} (.A(a), .Y(b));\n" for i in range(70 - n // 2)) + "endmodule\n")

    def tap(port, part, late, path, st, x):
        return dict(port=port, part=part, late_ps=late, early_ps=late - 10.0, fall_late_ps=late - 4.0,
                    fall_early_ps=late - 14.0, slew_ps=40.0, cppr_node=path[:2], tree_path=path, stages_from_root=st,
                    xy_um=[x, 100.0])
    taps = [tap("t_s0", "suc", 3000.0, "h00", 70, 100.0), tap("t_s1", "suc", 3000.0 + far_late, "h01", 74, 300.0),
            tap("t_m0", "stm", 3600.0, "h10", 84, 2000.0)]
    for c in ("TT", "FF"):
        meta = dict(corner=c, source="x", taps=taps, regions=2, clock_cell=cell,
                    node_late_ps={"h": 30.0, "h0": 1500.0, "h1": 1800.0, "h00": 2900.0, "h01": 2900.0, "h10": 3500.0},
                    node_early_ps={"h": 29.0, "h0": 1490.0, "h1": 1790.0, "h00": 2890.0, "h01": 2890.0, "h10": 3490.0},
                    node_fall_late_ps={"h": 26.0, "h0": 1496.0, "h1": 1796.0, "h00": 2896.0, "h01": 2896.0,
                                       "h10": 3496.0},
                    node_fall_early_ps={"h": 25.0, "h0": 1486.0, "h1": 1786.0, "h00": 2886.0, "h01": 2886.0,
                                        "h10": 3486.0},
                    node_stages={"h": 1, "h0": 35, "h1": 42, "h00": 66, "h01": 66, "h10": 80},
                    node_xy_um={"h": [1000.0, 100.0], "h0": [200.0, 100.0], "h1": [2000.0, 100.0],
                                "h00": [100.0, 100.0], "h01": [300.0, 100.0], "h10": [2000.0, 100.0]},
                    cppr_node_range_ps={"h": 1.0, "h0": 5.0, "h1": 5.0})
        (d / f"tap_arrivals_{c}.json").write_text(json.dumps(meta))
    plan = dict(clock=dict(common_latency_ps=250.0),
                ports=[dict(id="x", src=dict(part="suc"), dst=dict(part="stm"), width=1)])
    (d / "plan.json").write_text(json.dumps(plan))
    return d, plan


def _rows():
    return [dict(port="x", src="R1", dst="R2", src_part="suc", dst_part="stm", d_ps=600.0, p_up_ps=10.0, p_dn_ps=10.0,
                 unshared_a_ps=100.0, unshared_b_ps=100.0, margin_ps=0.0)]


KW = dict(clock_cal="spice", cppr_lca=True, clock_ocv="table", clock_droop="stated",
          margin_policy="legacy")   # OWNER 12.24b: the pre-12.24b form, reproduced on purpose


def _plan_gate(tmp_path, cell="inv", far_late=0.0, wander=0.05, corner="TT"):
    proof, plan = _proof(tmp_path / "proof", cell, far_late)
    rows = _rows()
    ports, pr = CAP.row_ports(rows)
    sta = D.sta_port_intervals(proof, plan, (corner,), ports, pr, fall=True, **KW)
    CAP.sta_hull(rows, sta)
    s, out, regs = CAP.plan(rows, T, AP, wander)
    s.update(period_ps=T, aperture_ps=AP, sync_aperture_ps=26.5, pad=0, wander_frac=wander)
    b = CAB.bind(CAB.plan_doc(s, out, regs), parts={"x": ("suc", "stm")})
    b["wander_frac"] = wander
    bf = tmp_path / "bind.json"
    bf.write_text(json.dumps(b))
    od = tmp_path / "sta"
    D.main([str(proof), "--plan", str(proof / "plan.json"), "--out", str(od), "--corner", corner, "--clock-cal", "spice",
            "--cppr-lca", "--clock-ocv", "table", "--clock-droop", "stated", "--count-align", str(bf),
            "--count-align-key", "region", "--hold-buffers", "none", "--margin-policy", "legacy"])
    res = json.loads((od / "die_sta_related.json").read_text())
    gate = {r["port"]: r for r in res["count_aligned"][corner]["rows"]}
    return sta, {o["port"]: o for o in out}, gate, res


def test_inverter_plan_equals_gate_both_corners(tmp_path):
    for c in ("TT", "FF"):
        sta, plan, gate, res = _plan_gate(tmp_path / c, corner=c)
        assert res["clock_cell"][c]["cell"] == "inv" and res["clock_cell"][c]["aocv_class"] == "Ainv"
        assert abs(gate["x"]["L_lo_ps"] - plan["x"]["L_lo_ps"]) < 0.11
        assert abs(gate["x"]["L_hi_ps"] - plan["x"]["L_hi_ps"]) < 0.11
        assert gate["x"]["wander_widen_ps"] == 0.0


def test_plan_path_uses_inverter_factor_on_rise_and_fall(tmp_path):
    proof, plan = _proof(tmp_path / "i", "inv")
    proofb, _ = _proof(tmp_path / "b", "buf")
    ports, pr = CAP.row_ports(_rows())
    si = D.sta_port_intervals(proof, plan, ("TT",), ports, pr, fall=True, **KW)["TT"]
    sb = D.sta_port_intervals(proofb, plan, ("TT",), ports, pr, fall=True, **KW)["TT"]
    meta, taps = D.load_taps(proof, "TT")
    m, t = D.scale_clock(meta, taps, D.SPICE_CLOCK_CAL_INV["TT"])
    D.CPPR_LCA = True
    try:
        ocv = D.ca_ocv(proof, m, t, "TT", 250.0, "table", "stated", clock_cell="inv")
        lms = [("t_s0", "t_m0", "x"), ("t_s1", "t_m0", "x")]
        want = D.count_align_port_intervals(ports, lms, t, m["cppr_node_range_ps"], pr, ocv)[0]["x"]
        wantf = D.count_align_port_intervals(ports, lms, t, m["cppr_node_range_ps"], pr, ocv, edge="fall")[0]["x"]
    finally:
        D.CPPR_LCA = False
    assert all(abs(p - q) < 1e-9 for p, q in zip(si["rise"]["x"], want))
    assert all(abs(p - q) < 1e-9 for p, q in zip(si["fall"]["x"], wantf))
    assert si["rise"]["x"] != sb["rise"]["x"]          # BUF proof keeps SPICE_CLOCK_CAL + class A


def test_pair_unshared_is_own_pairs_max():
    nl = {"h": 30.0, "h0": 1500.0}
    A = dict(late_ps=3000.0, early_ps=2990.0, cppr_node="h0", tree_path="h00")
    B = dict(late_ps=3600.0, early_ps=3590.0, cppr_node="h1", tree_path="h10")
    D.CPPR_LCA = True
    try:
        assert D.ca_pair_unshared(A, B, nl) == 3600.0 - 30.0
        C = dict(A, tree_path="h01")
        assert D.ca_pair_unshared(A, C, nl) == 3000.0 - 1500.0     # LCA h0: only below it
    finally:
        D.CPPR_LCA = False


def test_wander_from_own_tap_pairs_sl_e4_su_c_case(tmp_path):
    """QC t10 sl_E4_su_c -> sl_E4_stm: the landed_phase_ocv row carried one legacy tap per partition (unshared 100 ps
    here -> 5 ps wander); the crossing's own far tap (+300 ps unshared) must set the wander in the plan, and the gate
    must agree (no widening).  A bind planned on the legacy row is widened by the gate (fails closed below 100)."""
    sta, plan, gate, _ = _plan_gate(tmp_path / "own", far_late=300.0)
    f = D.SPICE_CLOCK_CAL_INV["TT"]
    own = (3300.0 * f - 30.0 * f)                         # far tap s1 / LCA 'h' (late 30)
    own = max(own, 3600.0 * f - 30.0 * f)
    assert abs(sta["TT"]["unshared"]["x"] - own) < 1e-6
    assert abs(plan["x"]["wander_ps"] - round(0.05 * own, 1)) < 0.06
    assert gate["x"]["wander_widen_ps"] == 0.0
    assert abs(gate["x"]["L_lo_ps"] - plan["x"]["L_lo_ps"]) < 0.11


def test_mutant_legacy_wander_is_widened_by_gate(tmp_path, monkeypatch):
    """mutant planner: the pre-rule wander (row unshared only).  The gate re-derives it over the port's own pairs and
    widens the lag window by the difference."""
    real = CAP.sta_hull

    def legacy(rows, sta):
        out = real(rows, sta)
        for r in rows:
            r.pop("unshared_sta_ps", None)
        return out
    monkeypatch.setattr(CAP, "sta_hull", legacy)
    _, plan, gate, _ = _plan_gate(tmp_path / "mut", far_late=300.0)
    assert plan["x"]["wander_ps"] == 5.0
    assert gate["x"]["wander_widen_ps"] > 150.0
    assert gate["x"]["L_lo_ps"] < plan["x"]["L_lo_ps"] - 150.0
