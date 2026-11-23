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
