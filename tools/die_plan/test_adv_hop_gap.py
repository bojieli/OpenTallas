"""ADV-HOP-GAP: direct one-cycle internal hops > 405 um with no station (FABLE-RC-S81 RC-GAP 11-23).

Fixtures modeled on the real S81 J8 f65f62779bef positives:
  gunit__t1  u_gunit.u_l1.c_bn (MY at (768.96, 380.16)) -> soft g_l1f[1].u_l1f -> nested u_f.c_bn (R0 at (17.28, 855.216)):
             1,277.9 um, no station (bind out native_bind/out rtl/s81p_gunit__t1.sv).
  col_h10_r2 u_y_xd_u_e11_u_e_go_0_0 / u_y_xd_u_e11_u_w_go_0_0: d = w_u_e11_2_Y[549] / w_u_e11_1_Y[549], both aliases of
             w_u_e11_0_Y[604:0] -> merge-prone duplicate stations feeding the abutted ROM halves u_e / u_w (272 um apart).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_hop_gap as H  # noqa: E402

GUNIT_SV = """module s81p_gunit__t1 (input clk);
    // as-built u_gunit.u_l1
    dsdv_gunit_l1 #(.MUT(0)) u_u_gunit_u_l1 (
        .c_bn(w_u_gunit_u_l1_c_bn),
        .clk(clk),
        .rst_n(rst_n_t38)
    );
    // as-built u_gunit.g_l1f[1].u_l1f
    dsdv_gunit_l1f #(.MUT(0)) u_u_gunit_g_l1f_1_u_l1f (
        .c_bn(%s),
        .clk(clk)
    );
%s
endmodule
"""

COL_SV = """module col_h10_r2__t1 (input clk);
    assign w_u_e11_1_Y = w_u_e11_0_Y[604:0];
    assign w_u_e11_2_Y = w_u_e11_0_Y[604:0];
    ot_dp_dly #(.W(1), .D(1)) u_y_xd_u_e11_u_e_go_0_0 (.clk(clk), .d(w_u_e11_2_Y[549]), .q(lp_u_e11_u_e_go_0));  // relay_depth
    ot_dp_dly #(.W(1), .D(1)) u_y_xd_u_e11_u_w_go_0_0 (.clk(clk), .d(%s[549]), .q(lp_u_e11_u_w_go_0));  // relay_depth
    // as-built u_f_5L01.u_r2.u_e11.u_e
    ot_v41_rom_elem_q_qxpq_w10_gb_he #(.OLAT(1)) u_u_e11_u_e (
        .go(lp_u_e11_u_e_go_0[0]),
        .clk(clk)
    );
    // as-built u_f_5L01.u_r2.u_e11.u_w
    ot_v41_rom_elem_q_qxpq_w10_gb_hw #(.OLAT(1)) u_u_e11_u_w (
        .go(lp_u_e11_u_w_go_0[0]),
        .clk(clk)
    );
endmodule
"""


def _tree(tmp, types, svs, pins):
    die = tmp / "physical" / "die_plan" / "s81"
    out = die / "plan_of_record" / "native_bind" / "out"
    (out / "rtl").mkdir(parents=True)
    (die / "inputs" / "core_pins").mkdir(parents=True)
    rep = {"die": "s81", "types": {}}
    for tn, (mod, sv) in svs.items():
        (out / "rtl" / f"{mod}.sv").write_text(sv)
        rep["types"][tn] = {"module": mod}
    (out / "bind_report.json").write_text(json.dumps(rep))
    for name, pl in pins.items():
        (die / "inputs" / "core_pins" / f"{name}.json").write_text(json.dumps({"module": name, "pins": pl}))
    raw = {"die": {"name": "s81"}, "partition_types": types}
    plan = die / "plan.json"
    plan.write_text(json.dumps(raw))
    return raw, str(plan), str(tmp)


def _gunit(tmp, net, extra=""):
    t = {"outline_um": [2885.76, 1226.88], "hard": False, "module": "s81p_gunit__t1",
         "hard_cores": [
             {"inst": "u_gunit.u_l1", "module": "dsdv_gunit_l1", "origin_um": [768.96, 380.16], "outline_um": [345.6, 216.0],
              "orient": "MY", "pins_file": "inputs/core_pins/dsdv_gunit_l1.json"},
             {"inst": "u_gunit.g_l1f[1].u_l1f.u_f", "module": "dsdv_gunit_l1f_bf", "origin_um": [17.28, 855.216],
              "outline_um": [432.0, 216.0], "orient": "R0", "pins_file": "inputs/core_pins/dsdv_gunit_l1f_bf.json"}]}
    pins = {"dsdv_gunit_l1": [{"name": f"c_bn[{i}]", "x": 345.558, "y": 136.668 + 0.192 * i} for i in range(3)],
            "dsdv_gunit_l1f_bf": [{"name": f"c_bn[{i}]", "x": 0.042, "y": 187.692 + 0.36 * i} for i in range(3)]}
    return _tree(tmp, {"gunit__t1": t}, {"gunit__t1": ("s81p_gunit__t1", GUNIT_SV % (net, extra))}, pins)


def test_gunit_positive(tmp_path):
    raw, plan, tree = _gunit(tmp_path, "w_u_gunit_u_l1_c_bn[2:0]")
    out = H.findings(raw, plan, tree)
    hit = [ln for ln in out if "HOP u_gunit.u_l1.c_bn -> u_gunit.g_l1f[1].u_l1f.u_f.c_bn" in ln]
    assert hit, out
    assert "1277.9 um > reach 405" in hit[0] and "+3 station(s)" in hit[0]
    rows, _ = H.rows(raw, plan, tree)
    assert rows[0]["family"] == "gunit" and rows[0]["stations"] == 3 and 590 <= rows[0]["over_ps"] <= 600


def test_gunit_staged_not_flagged(tmp_path):
    """the same leg through an ot_dp_* station (relay_depth u_y_xd_*) is not a gap."""
    st = "    ot_dp_dly #(.W(3), .D(1)) u_y_xd_c_bn_0_0 (.clk(clk), .d(w_u_gunit_u_l1_c_bn[2:0]), .q(lp_c_bn_0));"
    raw, plan, tree = _gunit(tmp_path, "lp_c_bn_0[2:0]", st)
    assert not any(" HOP " in ln for ln in H.findings(raw, plan, tree))


def test_gunit_planned_station_row_not_flagged(tmp_path):
    raw, plan, tree = _gunit(tmp_path, "w_u_gunit_u_l1_c_bn[2:0]")
    raw["partition_types"]["gunit__t1"]["internal_stations"] = [
        {"conn": "core:c_bn", "launch": "u_gunit.u_l1.c_bn", "capture": "u_gunit.g_l1f[1].u_l1f.u_f.c_bn", "regs_um": [[400, 700]]}]
    assert not any(" HOP " in ln for ln in H.findings(raw, plan, tree))


def _col(tmp, wnet):
    cores = [{"inst": "u_r2.u_e11.u_e", "module": "ot_v41_rom_elem_q_qxpq_w10_gb_he", "origin_um": [17.28, 181.44],
              "outline_um": [268.38, 221.4], "orient": "R0", "pins_file": "inputs/core_pins/he.json"},
             {"inst": "u_r2.u_e11.u_w", "module": "ot_v41_rom_elem_q_qxpq_w10_gb_hw", "origin_um": [289.44, 181.44],
              "outline_um": [268.38, 221.4], "orient": "R0", "pins_file": "inputs/core_pins/hw.json"}]
    t = {"outline_um": [600.0, 1300.0], "hard_cores": cores}
    pins = {"he": [{"name": "go", "x": 148.14, "y": 0.042}], "hw": [{"name": "go", "x": 148.14, "y": 0.042}]}
    tn = "col_h10_r2__t1__cl99efd374__pv1619ecc6"
    return _tree(tmp, {tn: t}, {tn: (tn, COL_SV % wnet)}, pins)


def test_col_h10_dupstn(tmp_path):
    raw, plan, tree = _col(tmp_path, "w_u_e11_1_Y")
    hit = [ln for ln in H.findings(raw, plan, tree) if "DUPSTN" in ln and "summary" not in ln]
    assert hit and "u_r2.u_e11.u_e" in hit[0] and "u_r2.u_e11.u_w" in hit[0] and "272.2 um apart" in hit[0]


def test_col_h10_distinct_d_clean(tmp_path):
    raw, plan, tree = _col(tmp_path, "w_u_e11_9_Y")      # the u_w station on its own source bits: no merge
    assert not any("DUPSTN" in ln for ln in H.findings(raw, plan, tree))


def test_never_raises(tmp_path):
    assert H.findings({"partition_types": {"t": {}}}, str(tmp_path / "x.json"), str(tmp_path))[0].startswith("WARN ADV-HOP-GAP")
    assert H.findings({}, "x")[0].startswith("WARN ADV-HOP-GAP not checked")


# ---------------------------------------------------------------- COORD 11-23 corrections
# (1) concat assigns: S81 svc t4_att (FABLE-UNC-S81-SVC): w_..._1733_Y = {tile3 .. tile0}, tile = {g_h[k].oy}; h4 sinks take
#     slices, so g_m[t].h4.iy is driven only by tile t's hcores (was ~8x over-counted at net level).
SVC_SV = """module svc_t (input clk);
    wire [31:0] w_u_h0_oy;
    wire [31:0] w_u_h1_oy;
    wire [31:0] w_u_h2_oy;
    wire [31:0] w_u_h3_oy;
    wire [63:0] w_1739_Y;
    wire [63:0] w_1745_Y;
    wire [127:0] w_1733_Y;
    wire [15:0] w_sel_Y;
    assign w_1739_Y = {w_u_h1_oy[31:0], w_u_h0_oy[31:0]};
    assign w_1745_Y = {w_u_h3_oy[31:0], w_u_h2_oy[31:0]};
    assign w_1733_Y = {w_1745_Y[63:0], w_1739_Y[63:0]};
    assign w_sel_Y = s_q ? {w_u_h0_oy[15:0]} : {w_u_h3_oy[15:0]};
%s
    // as-built u_rsv.g_m[0].h4
    ot_h4 u_u_m0 (
        .iy(w_1733_Y[63:0]),
        .clk(clk)
    );
    // as-built u_rsv.g_m[1].h4
    ot_h4 u_u_m1 (
        .iy(w_1733_Y[127:64]),
        .clk(clk)
    );
    // as-built u_rsv.g_x.u_t
    ot_h4 u_u_tx (
        .iy(w_sel_Y[15:0]),
        .clk(clk)
    );
endmodule
"""


def _svc(tmp):
    hc = "".join(f"""    // as-built u_rsv.g_h[{k}].u_c
    ot_hc u_u_h{k} (
        .oy(w_u_h{k}_oy),
        .clk(clk)
    );
""" for k in range(4))
    cores = [{"inst": f"u_rsv.g_h[{k}].u_c", "module": "ot_hc", "origin_um": [0.0, 100.0 * k], "outline_um": [50, 50],
              "orient": "R0", "pins_file": "inputs/core_pins/hc.json"} for k in range(4)]
    cores += [{"inst": f"u_rsv.g_m[{t}].h4", "module": "ot_h4", "origin_um": [2000.0, 100.0 * t], "outline_um": [50, 50],
               "orient": "R0", "pins_file": "inputs/core_pins/h4.json"} for t in range(2)]
    cores.append({"inst": "u_rsv.g_x.u_t", "module": "ot_h4", "origin_um": [2000.0, 900.0], "outline_um": [50, 50],
                  "orient": "R0", "pins_file": "inputs/core_pins/h4.json"})
    pins = {"hc": [{"name": f"oy[{i}]", "x": 50.0, "y": 25.0} for i in range(32)],
            "h4": [{"name": f"iy[{i}]", "x": 0.0, "y": 25.0} for i in range(64)]}
    t = {"outline_um": [2100.0, 1000.0], "hard_cores": cores}
    return _tree(tmp, {"svc_hi_dsdv_svc_rs__t4": t}, {"svc_hi_dsdv_svc_rs__t4": ("svc_t", SVC_SV % hc)}, pins)


def test_svc_concat_slices(tmp_path):
    raw, plan, tree = _svc(tmp_path)
    rr, _ = H.rows(raw, plan, tree)
    pairs = {(r["src"].split(".")[1], r["dst"].split(".")[1]) for r in rr if r["kind"] == "HOP"}
    assert pairs == {("g_h[0]", "g_m[0]"), ("g_h[1]", "g_m[0]"), ("g_h[2]", "g_m[1]"), ("g_h[3]", "g_m[1]"),
                     ("g_h[0]", "g_x"), ("g_h[3]", "g_x")}, pairs        # never tile 0 -> g_m[1]; both ternary arms kept


def test_expr_bits():
    w = {"a": (0, 3), "b": (0, 1)}
    bits = H.expr_bits("{a[3:2], b, 2'b0}", w)
    assert [sorted(x) for x in bits] == [[("a", 3)], [("a", 2)], [("b", 1)], [("b", 0)], [], []]
    assert H.expr_bits("a + b", w) is None                                # arithmetic: ident fallback
    assert len(H.expr_bits("{2{b}}", w)) == 4


# (2) unplaced soft relays: centroid > 405 from one end but a site within 405 of every end exists -> SOFT-SITE (pin it),
#     else SOFT-GAP (real gap).  FAM-S81-COL-H10-R4: 76 col_h10 relay legs 408-455 um with a feasible site.
RELAY_SV = """module col_t (input clk);
    // as-built u_r0.u_a
    ot_ca u_u_a (
        .q(w_u_a_q),
        .clk(clk)
    );
    // as-built u_f_2R01.u_r0.u_y_xa_1_0
    ot_relay_soft u_u_y_xa_1_0 (
        .d(w_u_a_q[99:0]),
        .o(w_u_y_xa_1_0_o),
        .clk(clk)
    );
    // as-built u_r0.u_b
    ot_cb u_u_b (
        .xai(w_u_y_xa_1_0_o[0]),
        .clk(clk)
    );
endmodule
"""


def _relay(tmp, bx):
    cores = [{"inst": "u_r0.u_a", "module": "ot_ca", "origin_um": [0.0, 0.0], "outline_um": [10, 10], "orient": "R0",
              "pins_file": "inputs/core_pins/ca.json"},
             {"inst": "u_r0.u_b", "module": "ot_cb", "origin_um": [bx, 0.0], "outline_um": [10, 10], "orient": "R0",
              "pins_file": "inputs/core_pins/cb.json"}]
    pins = {"ca": [{"name": f"q[{i}]", "x": 0.0, "y": 0.0} for i in range(100)], "cb": [{"name": "xai", "x": 0.0, "y": 0.0}]}
    t = {"outline_um": [1200.0, 400.0], "hard_cores": cores}
    return _tree(tmp, {"col_h10_r0_p4__t1": t}, {"col_h10_r0_p4__t1": ("col_t", RELAY_SV)}, pins)


def test_soft_site_feasible(tmp_path):
    raw, plan, tree = _relay(tmp_path, 800.0)       # centroid ~ (8, 0): 792 um from u_b, but (400, 0) reaches both
    rr, _ = H.rows(raw, plan, tree)
    kinds = {r["kind"] for r in rr}
    assert kinds == {"SOFT-SITE"}, rr
    r = rr[0]
    assert r["stations"] == 0 and r["over_ps"] == 0 and "feasible site (400,0)" in r["src"]
    assert any("SOFT-SITE" in ln and "pin the leaf" in ln for ln in H.findings(raw, plan, tree))


def test_soft_gap_infeasible(tmp_path):
    raw, plan, tree = _relay(tmp_path, 900.0)       # best seat (450, 0) is 450 um from both ends
    rr, _ = H.rows(raw, plan, tree)
    assert {r["kind"] for r in rr} == {"SOFT-GAP"}, rr
    assert rr[0]["len_um"] == 450.0 and rr[0]["stations"] == 1 and "no feasible site" in rr[0]["src"]


def test_expr_bits_bitwise_or():
    w = {"a": (0, 1), "b": (0, 1), "m": (0, 0)}
    bits = H.expr_bits("{a[1], a[0]} | {m[0], m[0]}", w)
    assert [sorted(x) for x in bits] == [[("a", 1), ("m", 0)], [("a", 0), ("m", 0)]]
    assert H.expr_bits("a || b", w) is None


# (1b) a SEATED plan stage (relay_sites) whose seat is > reach from one end, but a seat within reach of both exists:
#      HOP-SITE (re-seat, 0 stations); when no such seat exists it stays a HOP.
SEAT_SV = """module col_s (input clk);
    // as-built u_r0.u_a
    ot_ca u_u_a (
        .q(w_u_a_q),
        .clk(clk)
    );
    ot_dp_st #(.W(1)) u_y_cc_0 (.clk(clk), .d(w_u_a_q[0]), .q(w_cc_q));
    // as-built u_r0.u_b
    ot_cb u_u_b (
        .xai(w_cc_q),
        .clk(clk)
    );
endmodule
"""


def _seat(tmp, bx):
    raw, plan, tree = _relay(tmp, bx)
    t = raw["partition_types"]["col_h10_r0_p4__t1"]
    t["relay_sites"] = {"u_y_cc_0/q[0]": [10.0, 0.0]}
    import pathlib
    root = pathlib.Path(tree) / "physical" / "die_plan" / "s81"
    (root / "plan_of_record" / "native_bind" / "out" / "rtl" / "col_t.sv").write_text(SEAT_SV.replace("col_s", "col_t"))
    pathlib.Path(plan).write_text(json.dumps(raw))
    return raw, plan, tree


def test_hop_site_reseat(tmp_path):
    raw, plan, tree = _seat(tmp_path, 800.0)
    rr, _ = H.rows(raw, plan, tree)
    assert [r["kind"] for r in rr] == ["HOP-SITE"], rr
    assert "(400,0)" in rr[0]["site"] and rr[0]["stations"] == 0


def test_hop_no_seat(tmp_path):
    raw, plan, tree = _seat(tmp_path, 900.0)
    rr, _ = H.rows(raw, plan, tree)
    assert [r["kind"] for r in rr] == ["HOP"] and rr[0]["stations"] == 2, rr


def test_face_reg_window_site(tmp_path):
    sv = """module col_f (input clk);
    // as-built u_r0.u_a
    ot_ca u_u_a (
        .q(w_u_a_q),
        .clk(clk)
    );
    ot_dp_st #(.W(1)) u_bout_ret (.clk(clk), .d(w_u_a_q[0]), .q(ret_o[0]));
endmodule
"""
    cores = [{"inst": "u_r0.u_a", "module": "ot_ca", "origin_um": [0.0, 0.0], "outline_um": [10, 10], "orient": "R0",
              "pins_file": "inputs/core_pins/ca.json"}]
    pins = {"ca": [{"name": f"q[{i}]", "x": 0.0, "y": 0.0} for i in range(100)]}
    for lo, kind in ((200.0, "HOP-SITE"), (500.0, "HOP")):
        t = {"outline_um": [1200.0, 400.0], "hard_cores": cores,
             "buses": [{"name": "ret", "face": "S", "window_um": [lo, 1000.0], "dir": "out"}]}
        sub = tmp_path / kind
        raw, plan, tree = _tree(sub, {"col_h10_r0_p1__t1": t}, {"col_h10_r0_p1__t1": ("col_f", sv)}, pins)
        rr, _ = H.rows(raw, plan, tree)
        assert [r["kind"] for r in rr] == [kind], (lo, rr)


# (3) clock domains (FABLE-RC-S81 11-23): launch and capture on different clocks -> CDC-SYNC (0 stations), a multi-clock
#     end whose clocks overlap the other end's -> CLOCK-UNKNOWN; clk / clk_t<i> are one domain.
CDC_SV = """module cdc_t (input clk, input clk_t3, input [0:0] io_pma_rck);
    wire [0:0] w_0_Y;
    assign w_0_Y = clk_t3;
    // as-built u_r0.u_a
    ot_ca u_u_a (
        .q(w_u_a_q),
        %s
    );
    // as-built u_r0.u_b
    ot_cb u_u_b (
        .xai(w_u_a_q[0]),
        .ck(w_0_Y[0])
    );
endmodule
"""


def _cdc(tmp, clocks):
    cores = [{"inst": "u_r0.u_a", "module": "ot_ca", "origin_um": [0.0, 0.0], "outline_um": [10, 10], "orient": "R0",
              "pins_file": "inputs/core_pins/ca.json"},
             {"inst": "u_r0.u_b", "module": "ot_cb", "origin_um": [900.0, 0.0], "outline_um": [10, 10], "orient": "R0",
              "pins_file": "inputs/core_pins/cb.json"}]
    pins = {"ca": [{"name": "q[0]", "x": 0.0, "y": 0.0}], "cb": [{"name": "xai", "x": 0.0, "y": 0.0}]}
    t = {"outline_um": [1200.0, 400.0], "hard_cores": cores}
    return _tree(tmp, {"s81p_serdes__t2": t}, {"s81p_serdes__t2": ("cdc_t", CDC_SV % clocks)}, pins)


def test_clock_classes(tmp_path):
    for i, (clocks, kind, st) in enumerate(((".clk(clk)", "HOP", 2),                       # clk vs clk_t3 tap: one domain
                                            (".pma_rck(io_pma_rck[0])", "CDC-SYNC", 0),
                                            (".clk(clk),\n        .pma_rck(io_pma_rck[0])", "CLOCK-UNKNOWN", 2))):
        raw, plan, tree = _cdc(tmp_path / str(i), clocks)
        rr, _ = H.rows(raw, plan, tree)
        assert [(r["kind"], r["stations"]) for r in rr] == [(kind, st)], (clocks, rr)
        if kind != "HOP":
            assert rr[0]["was"] == "HOP" and "io_pma_rck" in rr[0]["clocks"]
            assert any(kind in ln for ln in H.findings(raw, plan, tree))
