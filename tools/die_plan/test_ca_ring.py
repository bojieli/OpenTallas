"""DIE-HEAD-18 (COORD 10-28 NUMBER-CHECK-HEAD-1 finding): opt-in --ca-ring times each count-aligned ring on its BUILT
clocks (writer = launch tap + fwd_out + fwd_wire + fclk_in, reader = capture tap + reader) instead of the declared
common latency on both sides.  Default (no spec) is unchanged; a pair whose types are not in the spec keeps the declared
form and is counted 'declared'; the planner hull gets the same spec (one model)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as R  # noqa: E402

T = 833.0
REG = dict(clkq_max_wire_ps=48.0, clkq_min_nowire_ps=30.0, setup_ps=10.0, hold_ps=10.0)
PLAN = {"partitions": [dict(name="A", type="tile"), dict(name="B", type="tile"), dict(name="C", type="other")]}
SPEC = {"types": {"tile": {"TT": dict(fwd_out_ps=[190.0, 200.0], fclk_in_ps=[180.0, 210.0], reader_ps=[500.0, 540.0])}},
        "fwd_wire_ps": {"TT": [0.0, 1.0]}, "source": "unit"}
OS, OH = 7.0, 3.0


def _ocv(a, b, check):
    return OS if check == "setup" else OH


def _taps():
    return {"a0": dict(part="A", cppr_node="A", late_ps=300.0, early_ps=280.0),
            "b0": dict(part="B", cppr_node="B", late_ps=520.0, early_ps=500.0),
            "c0": dict(part="C", cppr_node="C", late_ps=520.0, early_ps=500.0)}


def _bind(dst="B"):
    return {"sync_aperture_ps": 26.5, "ports": {
        "x": dict(src="A", dst=dst, K=1, depth=4, sched_lat=2, tree=False, L_lo_ps=T + 200.0, L_hi_ps=T + 240.0,
                  d_lo_ps=200.0, d_hi_ps=240.0, wander_ps=0.0)}, "regions": {}}


def test_shift_is_reader_minus_writer_and_default_unchanged():
    ring = R.ca_ring_fn(SPEC, PLAN, "TT")
    # lo: reader early - (fwd_out late + wire late + fclk_in late) = 500 - 411 = 89; hi: 540 - (190 + 0 + 180) = 170
    assert ring(_taps()["a0"], _taps()["b0"]) == (89.0, 170.0)
    L = [("a0", "b0", "A->B")]
    assert R.count_align_d_intervals(L, _taps()) == {"A->B": (200.0, 240.0)}
    assert R.count_align_d_intervals(L, _taps(), ring=ring) == {"A->B": (289.0, 410.0)}
    # exactly one variation term, applied after the shift
    assert R.count_align_d_intervals(L, _taps(), ocv=_ocv, ring=ring) == {"A->B": (289.0 - OS, 410.0 + OH)}


def test_ca_row_moves_by_the_shift_and_is_labelled_built():
    L = [("a0", "b0", "A->B")]
    r0 = R.count_align_landed(L, _taps(), _bind(), T, REG, ocv=_ocv, ocv_label="table")
    r1 = R.count_align_landed(L, _taps(), _bind(), T, REG, ocv=_ocv, ocv_label="table",
                              ring=R.ca_ring_fn(SPEC, PLAN, "TT"))
    x0, x1 = r0["rows"][0], r1["rows"][0]
    assert round(x1["margin_lo_ps"] - x0["margin_lo_ps"], 3) == 89.0
    assert round(x0["margin_hi_ps"] - x1["margin_hi_ps"], 3) == 170.0
    assert x1["ring"] == "built" and x1["ring_shift_ps"] == [89.0, 170.0] and "ring" not in x0
    assert r0["ring"] is None and r1["ring"]["built_ports"] == 1 and r1["ring"]["declared_ports"] == 0


def test_unknown_type_keeps_declared_and_is_counted():
    L = [("a0", "c0", "A->C")]
    ring = R.ca_ring_fn(SPEC, PLAN, "TT")
    assert ring(_taps()["a0"], _taps()["c0"]) is None
    r0 = R.count_align_landed(L, _taps(), _bind("C"), T, REG, ocv=_ocv, ocv_label="table")
    r1 = R.count_align_landed(L, _taps(), _bind("C"), T, REG, ocv=_ocv, ocv_label="table", ring=ring)
    assert r1["rows"][0]["margin_lo_ps"] == r0["rows"][0]["margin_lo_ps"]
    assert r1["rows"][0]["ring"] == "declared" and r1["ring"]["declared_ports"] == 1
    # a corner without spec data is declared too
    assert R.ca_ring_fn(SPEC, PLAN, "FF")(_taps()["a0"], _taps()["b0"]) is None


def test_planner_cli_passes_the_spec(tmp_path, monkeypatch):
    import count_align_plan as CAP
    seen = {}

    def fake(proof, plan, cs, ports, pr, cal, lca, fall=False, **kw):
        seen.update(kw)
        return {"TT": dict(rise={}, fall={}, unbound=[])}
    monkeypatch.setattr(R, "sta_port_intervals", fake)
    rows = dict(corners={"TT_x": dict(all=[dict(port="p", src="a", dst="b", d_ps=100.0, p_up_ps=1.0, p_dn_ps=1.0,
                                                unshared_a_ps=0.0, unshared_b_ps=0.0, margin_ps=0.0)])})
    (tmp_path / "r.json").write_text(json.dumps(rows))
    try:
        CAP.main([str(tmp_path / "r.json"), "--corner", "TT_x", "--sta-proof", str(tmp_path), "--sta-plan", "p.json",
                  "--sta-clock-ocv", "table", "--sta-ca-ring", "ring.json", "--out", str(tmp_path / "o.json")])
    except SystemExit:
        pass
    assert seen.get("ca_ring") == "ring.json"
