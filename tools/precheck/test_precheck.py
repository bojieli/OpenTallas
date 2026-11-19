"""PRECHECK-1119: unit tests of the static pre-build estimator (pure geometry; no plan or tool tree needed)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import precheck as PC  # noqa: E402
import precheck_hook as PH  # noqa: E402
import type_census as TC  # noqa: E402
sys.path.insert(0, str(HERE.parent / "die_plan"))


def test_family_strips_type_and_variant_suffixes():
    assert PC.family("ot_s81sl_leaf__t25__cl431c660f") == "ot_s81sl_leaf"
    assert PC.family("sle_ctl__cl67434795") == "sle_ctl"
    assert PC.family("col_h9_r1__t1__cl49d7a23e__pv047ea3b3") == "col_h9_r1"
    assert PC.family("kv3_pv_v8") == "kv3_pv_v8"


def test_reach_flags_long_station_hop_only():
    t = {"outline_um": [1000, 1000], "internal_stations": [
        {"conn": "bus:a", "bits": 8, "from_um": [0, 0], "regs_um": [[300, 0]], "to_um": [600, 0]},      # hops 300, 300
        {"conn": "bus:b", "bits": 8, "from_um": [0, 0], "regs_um": [[100, 0]], "to_um": [100, 500]}]}   # hop 500
    f = PC.reach_findings(t, 405, margin=1.0)
    assert len(f) == 1 and f[0][0] == 500 and "bus:b" in f[0][1]
    f = PC.reach_findings(t)                                # CBC r713: 300 um per hop, any width
    assert len(f) == 1 and f[0][0] == 500
    t["internal_stations"][0]["regs_um"] = [[310, 0]]
    assert len(PC.reach_findings(t)) == 2


def test_reach_ft_slot_uses_window_centres_and_regs():
    t = {"outline_um": [1000, 800], "ft_slots": [
        {"name": "ft0", "width": 4, "stations": 2, "in_face": "S", "in_window_um": [100, 200], "out_face": "N", "out_window_um": [100, 200],
         "regs_um": [[150, 400]]}]}
    assert PC.reach_findings(t, 405, margin=1.0) == []
    t["ft_slots"][0]["regs_um"] = [[150, 100]]
    assert PC.reach_findings(t, 405, margin=1.0)[0][0] == 700


def test_tap_assign_nearest_and_cap():
    taps = [("clk", 0.0, 0.0), ("clk_t1", 1000.0, 0.0)]
    sinks = [(10.0, 0.0, 1.0)] * 1300 + [(990.0, 0.0, 1.0)] * 5
    c = PC.tap_assign(taps, sinks)
    assert c["clk"] == 1300 and c["clk_t1"] == 5


def test_tap_cover_reports_uncovered_free_area():
    t = {"outline_um": [1000, 400], "hard_cores": [{"origin_um": [600, 0], "outline_um": [400, 400]}]}
    unc, free, cen = PC.tap_cover(t, [("clk", 100.0, 200.0)], 200.0)
    assert free == 600 * 400
    assert 0 < unc < free and cen[0] > 250        # the far part of the free area x 300..600
    unc2, _, _ = PC.tap_cover(t, [("clk", 100.0, 200.0), ("t", 450.0, 200.0)], 200.0)
    assert unc2 < unc


def test_tap_span_flags_one_corner_taps():
    t = {"outline_um": [1440, 1220]}
    taps = [("clk", 40, 648), ("t1", 179, 17), ("t2", 286, 17), ("t3", 401, 17), ("t7", 97, 1210)]
    fx, fy = PC.tap_span(t, taps)
    assert fx < 0.35 and fy > 0.9


def test_pin_width_counts_bits_of_a_core_pin():
    doc = {"pins": [{"name": "rs"}, {"name": "d[0]"}, {"name": "d[1]"}, {"name": "rs_x"}]}
    assert PC.pin_width(doc, "rs") == 1 and PC.pin_width(doc, "d") == 2 and PC.pin_width(doc, "q") is None


def test_misaim_flags_wide_bus_aimed_at_one_bit_pin(tmp_path):
    (tmp_path / "pins").mkdir()
    (tmp_path / "pins/bn.json").write_text(json.dumps({"pins": [{"name": "rs"}] + [{"name": f"x[{i}]"} for i in range(4)]}))
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    ctx = PC.Ctx(None, {}, plan, None)
    t = {"buses": [{"name": "frame_int_i1", "width": 1167}], "hard_cores": [{"inst": "u_r1.u_bn5", "pins_file": "pins/bn.json"}],
         "internal_stations": [{"conn": "bus:frame_int_i1", "launch": "face flop", "capture": "u_r1.u_bn5.rs", "regs_um": [[1, 0]], "to_um": [5, 5]},
                               {"conn": "bus:frame_int_i1", "launch": "face flop", "capture": "u_r1.u_bn5.x", "regs_um": [[1, 0]], "to_um": [5, 5]}]}
    f = PC.misaim_findings(ctx, t)
    assert len(f) == 2 and f[0][0] < 0.001
    t["buses"][0]["width"] = 4
    assert PC.misaim_findings(ctx, t) == []


def test_reset_fanout_needs_relay_structure():
    t = {"buses": [{"width": 1368}] * 8, "reset": {"sync_stages": 2}}
    f = PC.reset_findings(t, 2000)
    assert f and f[0][0] == 8 * 1368
    t["reset"]["relay_um"] = 180
    assert PC.reset_findings(t, 2000) == []
    t2 = {"buses": [{"width": 1368}] * 8, "reset": {}, "clock": {"landing_contract": {"collector_tree": {"x": 1}}}}
    assert PC.reset_findings(t2, 2000) == []


def test_ns_stride_family_key_and_default():
    raw = {"budgets": {"face_flop_ns_types": {"ot_s81sl_leaf": {"row_stride": 2, "inset_rows": 0}}},
           "partition_types": {"ot_s81sl_leaf__t5": {}, "col_h9_r1__t1": {}}}
    assert PC.ns_stride(raw, "ot_s81sl_leaf__t5") == (2, 0)
    assert PC.ns_stride(raw, "col_h9_r1__t1") == (1, 0)


def test_face_bank_features_density_and_core_gap():
    pins = [("leafdn_i0", b, 0, 100.0 + 0.2 * b, 0.0, "S") for b in range(40)] + [("ft1_o", b, 0, 100.0 + 0.2 * b, 0.0, "S") for b in range(10)]
    n3, gap, face, x = PC.face_bank_features(pins, {"ft1"}, {"leafdn_i0"}, [(90, 30, 200, 100)], 1000)
    assert face == "S" and gap == 30 and n3 >= 60


def test_suggested_rows_face_bank_is_family_wide():
    f = [dict(type="ot_s81sl_leaf__t52", check="FACE-BANK", value=34.6, threshold=45, family="ot_s81sl_leaf", detail="x"),
         dict(type="ot_s81sl_leaf__t54", check="FACE-BANK", value=30.0, threshold=45, family="ot_s81sl_leaf", detail="y")]
    rows = PC.suggested_rows(f, {})
    assert len(rows) == 1 and rows[0]["path"] == "budgets.face_flop_ns_types.ot_s81sl_leaf.row_stride" and rows[0]["set"] == 1


def test_write_outputs_and_hook_summary(tmp_path):
    raw = {"partition_types": {"a__t1": {}, "a__t2": {}}}
    f = [dict(type="a__t1", check="TAP-CAP", value=3000, threshold=1200, family="a", detail="clk_t3 3000")]
    PC.write_outputs(tmp_path, "s81", "/p.json", f, [], 2, 1.0, raw)
    assert "| a | 1 / 2 | 3000 |" in (tmp_path / "family_summary.md").read_text()
    txt = PH.summary_text("s81", "D8g", "S81-DIE-R3", tmp_path, tmp_path / "findings.tsv")
    assert txt.startswith("PRECHECK [PRECHECK-1119 -> S81-DIE-R3; cc COORD] s81 event D8g: 1 findings") and "TAP-CAP: a 1" in txt


def test_census_rtl_hash_strips_type_name_and_rom_instance(tmp_path):
    a = tmp_path / "col__t1__pvaaaaaaaa.sv"
    b = tmp_path / "col__t1__pvbbbbbbbb.sv"
    a.write_text('module col__t1__pvaaaaaaaa #(parameter [3:0] S = 4\'b0001) (); // c\n rom #(.INSTANCE("u_f_0R13")) u (); endmodule\n')
    b.write_text('module col__t1__pvbbbbbbbb #(parameter [3:0] S = 4\'b0111) (); // d\n rom #(.INSTANCE("u_f_7R10")) u (); endmodule\n')
    assert TC.rtl_hash(a, a.stem) != TC.rtl_hash(b, b.stem)
    assert TC.rtl_hash(a, a.stem, True) == TC.rtl_hash(b, b.stem, True)


def test_tap_rebalance_moves_excess_within_radius_only():
    taps = [("a", 0.0, 0.0), ("b", 150.0, 0.0), ("c", 900.0, 0.0)]
    assert PC.tap_rebalance(taps, {"a": 2000, "b": 100, "c": 0}, 1200, 200) == {}
    left = PC.tap_rebalance(taps, {"a": 3000, "b": 100, "c": 0}, 1200, 200)
    assert left == {"a": 700}           # b takes 1100, c is 900 um away


def test_synth_blackbox_stubs_only_for_undefined_modules():
    import precheck_synth as PS
    top = ("module top(input wire clk);\n  ot_rom #(.INSTANCE(\"a\"), .VIAMAP(\"\")) u_r (.clk(clk), .addr_in(a), .rd_out(q));\n"
           "  ot_dp_st #(.W(4)) u_s (.clk(clk), .d(x), .q(y));\nendmodule\n")
    cells = "module ot_dp_st #(parameter W = 1) (input clk, input [W-1:0] d, output [W-1:0] q);\nendmodule\n"
    st = PS.blackbox_stubs([top, cells])
    assert "module ot_rom #(parameter INSTANCE = 0, parameter VIAMAP = 0) (addr_in, clk, rd_out);" in st and "ot_dp_st" not in st
    assert PS.reg_class("\\g_u_lf4_u_vp_g_ln_10_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q [3:0]") == "g_u_lf4_u_vp_g_ln_N_u_cst_hi_gd_s_N_u_src_H_q"


def test_kit_sinks_parse_line_and_type():
    import kit_sinks as KS
    ln = "OT_CLOCK_TAPS 3 taps, 120 sinks moved off clk: clk 100 clk_t1 15 clk_t2 5"
    assert KS.parse_line("noise " + ln) == (3, 120)
    assert KS.type_of("kv3_pv_v8-route-loved-redfish-2395315-1795051866") == "kv3_pv_v8"
    assert KS.type_of("tmp") is None


def test_stale_bins_flags_kit_count_far_from_plan_bins(tmp_path):
    d = tmp_path / "por"
    (d / "sink_bins").mkdir(parents=True)
    (d / "sink_bins/t.json").write_text(json.dumps({"n": 99260, "bins": []}))
    (d / "plan.json").write_text("{}")
    ctx = PC.Ctx(None, {}, d / "plan.json", None)
    n = PC.bins_count(ctx, {"sink_bins_file": "physical/x/sink_bins/t.json"})
    assert n == 99260
    r = PC.stale_bins(n, {"sinks": 120625, "taps": 248, "log": "h:/p"})
    assert r and r[0] == 1.215 and "99260" in r[1]
    assert PC.stale_bins(n, {"sinks": 101000}) is None


def test_cbc_rules_shared_constants():
    import cbc_rules as CBC
    assert (CBC.REACH_UM_PER_HOP, CBC.TAP_MAX_SINKS, CBC.RESET_LEAF_MAX_FANOUT, CBC.BOUNDARY_REG_UM, CBC.DEPTH_LEVELS_MAX) == (300.0, 1000, 32, 50.0, 13)
    assert PC.REACH_UM == 300.0 and PC.TAP_CAP == 1000 and PC.RESET_LEAF == 32


def test_boundary_unregistered_ports():
    pins = [("a_i", 0, 0, 0.0, 0.0, "S"), ("a_i", 1, 0, 10.0, 0.0, "S"), ("b_o", 0, 0, 500.0, 0.0, "S")]
    miss = PC.boundary_unregistered(pins, [(5.0, 20.0), (500.0, 80.0)], 50.0)
    assert set(miss) == {"b_o"} and miss["b_o"][0] == 1


def test_reset_leaf_fanout_over_cbc():
    assert PC.reset_findings({"reset": {"max_fanout": 64, "relay_um": 100}})[0][0] == 64
    assert PC.reset_findings({"reset": {"max_fanout": 32, "relay_um": 100}}) == []
