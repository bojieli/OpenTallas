"""QC-S28-ROUTE 11-12: tests for the cbx_q10 spine parser extension and the guarded route-delta apply."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RTL = """
    ot_dp_st #(.W(516)) u_bin_bc_i30 (.clk(clk), .d(cland_bc_i30[515:0]), .q(bc_i30_q), .eq(bc_i30_eq));
    ot_dp_st #(.W(516)) u_bout_bc_o31 (.clk(clk), .rst_n(rst_n), .d(w_u_fab_u_x_3_1_a_d[515:0]), .q(bc_o31[515:0]));
    ot_dp_dly #(.W(516), .D(6)) u_d6_u_fab_u_x_3_0_a_d (.clk(clk), .d(w_u_fab_u_x_3_0_a_d), .q(d6_u_fab_u_x_3_0_a_d));
    ot_dp_dly #(.W(508), .D(1)) u_pc_nk_u_t_3_1_tap (.clk(clk), .d(w_u_fab_u_x_3_1_tap_d[507:0]), .q(pq_u_t_3_1_tap));
    qfd_c_xstnw u_u_fab_u_x_3_0 (
        .a_d(w_u_fab_u_x_3_0_a_d),
        .b_d(bc_i30_q[515:0]),
        .tap_d(w_u_fab_u_x_3_0_tap_d)
    );
    qfd_c_xstnw u_u_fab_u_x_3_1 (
        .a_d(w_u_fab_u_x_3_1_a_d),
        .b_d(d6_u_fab_u_x_3_0_a_d[515:0]),
        .tap_d(w_u_fab_u_x_3_1_tap_d)
    );
    qfd_tile_nl_rp2_romleaf_rr u_u_t_3_0 (
        .ck(clk),
        .tap(w_u_fab_u_x_3_0_tap_d[507:0]),
        .n_y(w_u_t_3_0_n_y)
    );
"""


def test_parse_rtl_direct_nl_tap_and_pipe_tap():
    sp = _load("s28d_spine")
    st, dly, tap, bout = sp.parse_rtl(RTL)
    assert sorted(st) == ["u_u_fab_u_x_3_0", "u_u_fab_u_x_3_1"]
    assert dly == {"u_d6_u_fab_u_x_3_0_a_d": 6}
    assert tap == {"u_u_fab_u_x_3_1": "u_t31", "u_u_fab_u_x_3_0": "u_t30"}   # pipe tap kept, NL direct tap added
    assert bout == {"u_u_fab_u_x_3_1": "bc_o31"}


def _plan():
    t = dict(outline_um=[100.0, 200.0], hard_cores=[dict(inst="u_t21", origin_um=[1.0, 2.0])],
             internal_stations=[dict(conn="bus:y_o21", from_um=[1, 2], to_um=[3, 4], regs_um=[[5, 6]])],
             ft_slots=[dict(name="a22", in_face="W", out_face="N", width=4, stations=1, out_window_um=[0, 1],
                            layers=["M7", "M5"])])
    ap = _load("apply_route")
    return {"partition_types": {tn: json.loads(json.dumps(t)) for tn in ap.TYPES}}


def test_apply_refuses_on_from_value_and_guard(tmp_path):
    ap = _load("apply_route")
    pl = tmp_path / "p.json"; pl.write_text(json.dumps(_plan(), indent=1) + "\n")
    sp = tmp_path / "s.json"; sp.write_text(json.dumps({"changes": {tn: {"relay_sites": {"u_bin_bc_i30/q[0]": [1.0, 2.0]}}
                                                                    for tn in ap.TYPES}}))
    w = tmp_path / "w.json"; w.write_text(json.dumps({tn: dict(in_window_um=[10, 20], in_layers=["M6", "M4"],
                                                               in_order="lsb_high") for tn in ap.TYPES}))
    d = tmp_path / "d.json"
    ap.build(str(pl), str(sp), str(w), str(d))
    out = tmp_path / "o.json"
    ap.apply(str(pl), str(out), str(d))
    assert ap.check(str(out), str(d)) == 0
    assert json.loads(out.read_text())["partition_types"][ap.TYPES[0]]["ft_slots"][0]["in_window_um"] == [10, 20]
    # second apply: from-values are no longer absent -> refused
    r = subprocess.run([sys.executable, "-I", str(HERE / "apply_route.py"), "apply", str(out), str(tmp_path / "x.json"),
                        str(d)], capture_output=True, text=True)
    assert r.returncode != 0 and "REFUSED" in (r.stderr + r.stdout)
    # guard: a moved y_o21 station register refuses
    p = _plan(); p["partition_types"][ap.TYPES[2]]["internal_stations"][0]["regs_um"] = [[5, 7]]
    pl2 = tmp_path / "p2.json"; pl2.write_text(json.dumps(p, indent=1) + "\n")
    r = subprocess.run([sys.executable, "-I", str(HERE / "apply_route.py"), "apply", str(pl2), str(tmp_path / "y.json"),
                        str(d)], capture_output=True, text=True)
    assert r.returncode != 0 and "guard" in (r.stderr + r.stdout)
