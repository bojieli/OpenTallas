"""CLK-INV-CAL-1: the ONE shared die timing model keyed by the die clock cell (BUFx24 'buf' unchanged, CKINVDCx16 'inv'
= SPICE_CLOCK_CAL_INV + AOCV class Ainv), auto-detected from the proof's clock netlist."""
import json
from pathlib import Path

import clk_aocv as CA
import die_sta_related as R

HERE = Path(R.__file__).resolve().parent
INV, BUF = "CKINVDCx16_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"


def _netlist(d, n_inv, n_buf):
    d.mkdir(parents=True, exist_ok=True)
    lines = ["module ctree (root, t0);", "  input root;"]
    lines += [f"  {INV} r{i} (.A(a), .Y(b));" for i in range(n_inv)]
    lines += [f"  {BUF} b{i} (.A(a), .Y(b));" for i in range(n_buf)]
    (d / "ctree.v").write_text("\n".join(lines + ["endmodule"]) + "\n")


def _taps():
    t = {"a": dict(late_ps=4700.0, early_ps=4660.0, cppr_node="h", stages_from_root=110, xy_um=[1000.0, 1000.0]),
         "b": dict(late_ps=4710.0, early_ps=4670.0, cppr_node="h", stages_from_root=112, xy_um=[1300.0, 1000.0])}
    meta = dict(corner="TT", node_stages={"h": 1}, node_xy_um={"h": [5000.0, 13000.0]}, node_late_ps={"h": 40.0},
                node_early_ps={"h": 39.6})
    return t, meta


def test_table_carries_inverter_classes_and_buf_rows_untouched():
    T = CA.load(HERE / R.APPROVED_AOCV_TABLE)
    for k in ("Ainv", "Ainv2"):
        for c in ("TT", "FF"):
            r = T["classes"][k][c]
            assert 0 < r["s_cell"] < 0.1 and 0 < r["cell_share"] < 1 and r["mu_cell_ps"] > 0
    # the BUFx24 rows the gate used before CLK-INV-CAL-1 (NUMBER-CHECK-AOCV CHECKED values)
    assert T["classes"]["A"]["TT"]["s_cell"] == 0.03885 and T["classes"]["A"]["FF"]["s_cell"] == 0.03992
    assert T["classes"]["A"]["TT"]["cell_share"] == 0.5326 and T["systematic"]["g_per_mm"] == 0.0021
    assert R.CLOCK_CELL_AOCV_CLASS == {"buf": "A", "inv": "Ainv"}


def test_spice_factor_keyed_by_cell():
    assert R.SPICE_CLOCK_CAL == {"TT": 1.0485, "FF": 1.0552}
    assert R.spice_cal_factor("TT") == 1.0485 and R.spice_cal_factor("FF", "buf") == 1.0552
    assert R.spice_cal_factor("SS", "buf") == 1.0485
    assert R.spice_cal_factor("TT", "inv") == R.SPICE_CLOCK_CAL_INV["TT"]
    assert R.spice_cal_factor("FF", "inv") == R.SPICE_CLOCK_CAL_INV["FF"]
    assert R.SPICE_CLOCK_CAL_INV == {"TT": 0.9324, "FF": 0.9380}                   # CLK-INV-CAL-1 measured (NDR envelope)


def test_detect_clock_cell(tmp_path):
    import pytest
    p = tmp_path / "proof"
    p.mkdir()
    # COORD ruling ba28d3143: no silent BUFx24 fallback -> missing and unknown declarations fail closed
    with pytest.raises(R.ClockCellUndeclared, match="declares no clock_cell"):
        R.detect_clock_cell(p, {})
    with pytest.raises(R.ClockCellUndeclared, match="not one of buf / inv / inv2"):
        R.detect_clock_cell(p, dict(clock_cell="ckbuf"))
    with pytest.raises(R.ClockCellUndeclared, match="not one of"):
        R.resolve_clock_cell("BUFx8", p, {})
    assert R.detect_clock_cell(p, dict(clock_cell="buf"))[0] == "buf"
    assert R.detect_clock_cell(p, dict(clock_cell="inv2"))[0] == "inv"
    run = tmp_path / "run"
    _netlist(run / "clk", 30, 2)
    meta = dict(source=f"{run}/out_TT/arr_TT.txt (die_trial region trees, combo GRT routed RC, OpenSTA)")
    with pytest.raises(R.ClockCellUndeclared):          # a netlist alone is not a declaration
        R.detect_clock_cell(p, meta)
    cell, basis = R.detect_clock_cell(p, dict(meta, clock_cell="inv"))
    assert cell == "inv" and "30 CKINVDCx16 / 2 BUFx24" in basis
    with pytest.raises(R.ClockCellUndeclared, match="contradicts"):   # declaration vs built netlist
        R.detect_clock_cell(p, dict(meta, clock_cell="buf"))
    with pytest.raises(R.ClockCellUndeclared, match="contradicts"):
        R.resolve_clock_cell("buf", p, meta)
    assert R.resolve_clock_cell("inv2", p, meta)[0] == "inv"


def test_planner_and_gate_fail_closed_without_declaration(tmp_path):
    import pytest
    import count_align_plan as CAP
    p = _proof(tmp_path, "inv")
    for c in ("TT", "FF"):
        f = p / f"tap_arrivals_{c}.json"
        m = json.loads(f.read_text())
        m.pop("clock_cell")
        f.write_text(json.dumps(m))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"clock": {"common_latency_ps": 250.0}, "ports": []}))
    kw = dict(clock_cal="spice", clock_ocv="table", clock_droop="shared")
    with pytest.raises(R.ClockCellUndeclared):
        CAP.clock_contexts(p, plan, ("TT",), **kw)                                # planner
    with pytest.raises(R.ClockCellUndeclared):
        R.sta_port_intervals(p, json.loads(plan.read_text()), ("TT",), {}, None, "spice", True, clock_ocv="table")
    with pytest.raises(SystemExit, match="declares no clock_cell"):            # gate
        R.main([str(p), "--plan", str(plan), "--out", str(tmp_path / "o"), "--corner", "TT"])
    for c in ("TT", "FF"):
        f = p / f"tap_arrivals_{c}.json"
        f.write_text(json.dumps(dict(json.loads(f.read_text()), clock_cell="bufx")))
    with pytest.raises(SystemExit, match="not one of"):
        R.main([str(p), "--plan", str(plan), "--out", str(tmp_path / "o"), "--corner", "TT"])


def test_clock_ocv_fn_inverter_class_and_buf_unchanged():
    t, meta = _taps()
    T = CA.load(HERE / R.APPROVED_AOCV_TABLE)
    fb = R.clock_ocv_fn("table", "shared", meta, t, 250.0)
    fb2 = R.clock_ocv_fn("table", "shared", meta, t, 250.0, clock_cell="buf")
    fi = R.clock_ocv_fn("table", "shared", meta, t, 250.0, clock_cell="inv")
    assert fb("a", "b", "setup") == fb2("a", "b", "setup")
    # direct recomputation with class Ainv: N = inverters below the node, cell share of Ainv
    B = T["classes"]["B"]["TT"]
    nB = max(1, round(250.0 / B["mu_stage_ps"]))
    fc = T["classes"]["Ainv"]["TT"]["cell_share"]

    def br(r, late):
        arr = (r["late_ps"] if late else r["early_ps"]) - (meta["node_late_ps"] if late else meta["node_early_ps"])["h"]
        return dict(cell_ps=fc * arr + B["cell_share"] * 250.0, net_ps=(1 - fc) * arr + (1 - B["cell_share"]) * 250.0,
                    stages={"Ainv": r["stages_from_root"] - 1, "B": nB})
    pts = [t["a"]["xy_um"], t["b"]["xy_um"], meta["node_xy_um"]["h"]]
    d = ((max(p[0] for p in pts) - min(p[0] for p in pts)) ** 2 + (max(p[1] for p in pts) - min(p[1] for p in pts)) ** 2) ** 0.5
    want = CA.branch_pessimism(T, "TT", br(t["a"], True), br(t["b"], False), d, False, "setup")
    assert abs(fi("a", "b", "setup") - want) < 1e-9
    assert fi("a", "b", "setup") != fb("a", "b", "setup")


def test_clock_ocv_fn_fails_closed_without_inverter_class(tmp_path):
    T = json.loads((HERE / R.APPROVED_AOCV_TABLE).read_text())
    del T["clock_aocv"]["classes"]["Ainv"]
    f = tmp_path / "t.json"
    f.write_text(json.dumps(T))
    t, meta = _taps()
    try:
        R.clock_ocv_fn("table", "shared", meta, t, 250.0, table_path=f, clock_cell="inv")
    except SystemExit as e:
        assert "Ainv" in str(e)
    else:
        raise AssertionError("inverter clock without class Ainv must fail closed")


def _proof(tmp_path, cell):
    """minimal proof + plan: two partitions in two regions, one landed port; clock netlist beside the proof."""
    p = tmp_path / f"proof_{cell}"
    p.mkdir()
    for c in ("TT", "FF"):
        taps = [dict(port="t_A__clk", part="A", late_ps=3000.0, early_ps=2990.0, slew_ps=40.0, cppr_node="A",
                     tree_path="h0", stages_from_root=70, xy_um=[100.0, 100.0]),
                dict(port="t_B__clk", part="B", late_ps=3100.0, early_ps=3090.0, slew_ps=40.0, cppr_node="B",
                     tree_path="h1", stages_from_root=72, xy_um=[900.0, 100.0])]
        meta = dict(corner=c, source="x", clock_cell=cell, node_late_ps={"h": 30.0, "h0": 2900.0, "h1": 2950.0},
                    node_early_ps={"h": 29.0, "h0": 2890.0, "h1": 2940.0}, node_stages={"h": 2, "h0": 66, "h1": 66},
                    node_xy_um={"h": [500.0, 100.0], "h0": [100.0, 100.0], "h1": [900.0, 100.0]},
                    cppr_node_range_ps={"h": 1.0, "h0": 10.0, "h1": 10.0}, taps=taps, regions=2)
        (p / f"tap_arrivals_{c}.json").write_text(json.dumps(meta))
    _netlist(p, 140 if cell == "inv" else 0, 0 if cell == "inv" else 70)
    return p


def test_sta_d_intervals_auto_detects_inverter_model(tmp_path, monkeypatch):
    pi, pb = _proof(tmp_path, "inv"), _proof(tmp_path, "buf")
    seen = []

    def fake_pairs(plan, taps):
        return {"landed": [("t_A__clk", "t_B__clk", "A->B")]}, None
    monkeypatch.setattr(R, "build_pairs", fake_pairs)
    real = R.scale_clock
    monkeypatch.setattr(R, "scale_clock", lambda m, t, f: (seen.append(f), real(m, t, f))[1])
    plan = {"clock": {"common_latency_ps": 250.0}}
    kw = dict(clock_cal="spice", cppr_lca=True, clock_ocv="table", clock_droop="shared", margin_policy="legacy")
    di = R.sta_d_intervals(pi, plan, ("TT", "FF"), **kw)
    db = R.sta_d_intervals(pb, plan, ("TT", "FF"), **kw)
    assert seen == [R.SPICE_CLOCK_CAL_INV["TT"], R.SPICE_CLOCK_CAL_INV["FF"], 1.0485, 1.0552]
    assert di != db
    import pytest
    with pytest.raises(R.ClockCellUndeclared, match="contradicts"):   # a BUF override on an inverter netlist fails
        R.sta_d_intervals(pi, plan, ("TT", "FF"), clock_cell="buf", **kw)


def test_count_align_plan_contexts_use_detected_cell(tmp_path):
    import count_align_plan as CAP
    pi = _proof(tmp_path, "inv")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"clock": {"common_latency_ps": 250.0}}))
    ctx = CAP.clock_contexts(pi, plan, ("TT",), clock_cal="spice", clock_ocv="table", clock_droop="shared",
                             margin_policy="legacy")
    f = R.SPICE_CLOCK_CAL_INV["TT"]
    assert abs(ctx["TT"]["taps"]["t_A__clk"]["late_ps"] - 3000.0 * f) < 1e-9
    assert abs(ctx["TT"]["meta"]["clock_cal_factor"] - f) < 1e-12


def test_trial_tap_arrivals_records_inverter_clock(tmp_path):
    import trial_tap_arrivals as TA
    for cell, want in (("inv", "inv"), ("buf", "buf")):
        d = tmp_path / cell / "clk"
        _netlist(d, 3 if cell == "inv" else 0, 0 if cell == "inv" else 3)
        tree = dict(nodes={"0": dict(parent=None, x=0.0, y=0.0, kids=[])}, node_buf={"0": "b0"}, parent_of={},
                    taps=[dict(port="t_A__clk", part="A", node=0, xy=[0.0, 0.0])], sites={"b0": [0.0, 0.0]})
        (d / "tree.json").write_text(json.dumps(tree))
        arr = d / "arr_TT.txt"
        arr.write_text("T t_A__clk 100.0 99.0 30.0\nN b0 50.0 49.0\n")
        res, miss = TA.export(d / "tree.json", arr, "TT")
        assert res.get("clock_cell") == want and miss == 0


def test_clk_inv_cal_comb_and_affine():
    import clk_inv_cal as IC
    cells, edges, sinks = IC.comb(16, 8, 2)
    assert len(cells) == 16 + 2 * 2 and sinks == ["s7_1", "s15_1"] and ("t7", "s7_0") in edges
    f = IC.affine([(100.0, 110.0), (200.0, 215.0), (300.0, 320.0)])
    assert f["slope"] == 1.05 and f["offset_ps"] == 5.0 and f["points"] == 3
