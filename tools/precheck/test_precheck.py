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
    assert PC.reach_findings(t) == []                       # plan coordinates: an 8-bit chain may hop up to 506 um
    t["internal_stations"][1]["bits"] = 512
    assert len(PC.reach_findings(t)) == 1                   # a 512-bit chain only up to 439 um


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
    assert (CBC.REACH_UM_PER_HOP, CBC.TAP_MAX_SINKS, CBC.RESET_LEAF_MAX_FANOUT, CBC.BOUNDARY_REG_UM, CBC.DEPTH_LEVELS_MAX) == (405.0, 1000, 32, 50.0, 13)
    assert (CBC.TAP_SKEW_PASS_PS, CBC.TAP_SKEW_FAIL_PS) == (60.0, 100.0)
    assert PC.REACH_UM == 405.0 and PC.TAP_CAP == 1000 and PC.RESET_LEAF == 32


def test_boundary_unregistered_ports():
    pins = [("a_i", 0, 0, 0.0, 0.0, "S"), ("a_i", 1, 0, 10.0, 0.0, "S"), ("b_o", 0, 0, 500.0, 0.0, "S")]
    miss = PC.boundary_unregistered(pins, [(5.0, 20.0), (500.0, 80.0)], 50.0)
    assert set(miss) == {"b_o"} and miss["b_o"][0] == 1


def test_reset_leaf_fanout_over_cbc():
    assert PC.reset_findings({"reset": {"max_fanout": 64, "relay_um": 100}})[0][0] == 64
    assert PC.reset_findings({"reset": {"max_fanout": 32, "relay_um": 100}}) == []


def test_synth_kit_inputs_map_work_paths(tmp_path):
    import precheck_synth as PS
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = top_t1\nexport VERILOG_FILES = /work/rtl/a.sv /work/rtl/b_bb.v\n"
                                        "export VERILOG_DEFINES = -DSYNTHESIS -DX\nexport ADDITIONAL_LIBS = /work/macros/m_tt.lib\n")
    files, defs, libs, top = PS.kit_inputs(tmp_path)
    assert files == [str(tmp_path / "rtl/a.sv"), str(tmp_path / "rtl/b_bb.v")] and libs == [str(tmp_path / "macros/m_tt.lib")]
    assert defs == ["-DSYNTHESIS", "-DX"] and top == "top_t1"


def test_kit_scan_tap_assign_skew_and_class():
    import kit_scan as KS
    taps = [("clk", 0.0, 0.0), ("clk_t1", 100.0, 0.0)]
    regs = [(1.0, 0.0)] * 5 + [(90.0, 0.0)] * 3
    m = KS.assign_taps(taps, regs, 4, 200.0)
    assert len(m["clk"]) == 4 and len(m["clk_t1"]) == 4
    assert KS.skew_estimate([0.0] * 10 + [400.0] * 10, 0.25) == 100.0
    assert KS.reg_class("g_u_lf0_u_vp_g_ln_3_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q\\[65\\]$_DFF_P_") == "g_u_lf0_u_vp_g_ln_N_u_cst_hi_gd_s_N_u_src_H_q"
    assert KS.kit_type("/x/ot_s81sl_leaf__t27-route-civil-redfish-2152390-1795068054") == "ot_s81sl_leaf__t27"


def test_fold_scan_declared_vs_netlist():
    import fold_scan as FS
    dec = FS.declared(["reg [255:0] g_u_vp_g_hig_0_u_cst_gd_s_0_u_src_abcdef0123456789_q;\nreg [255:0] g_u_vp_g_hig_1_u_cst_gd_s_0_u_src_abcdef0123456789_q;\n"])
    assert dec["g_u_vp_g_hig_N_u_cst_gd_s_N_u_src_H_q"] == 512
    nl = "".join(f"  DFFHQNx1_ASAP7_75t_R \\\\u_bound.g_u_vp_g_hig_0_u_cst_gd_s_0_u_src_abcdef0123456789_q[{i}]$_DFF_P_ (\n" for i in range(128))
    assert FS.netlist_flops(nl)["g_u_vp_g_hig_N_u_cst_gd_s_N_u_src_H_q"] == 128


def test_kit_scan_hourly_digest_per_die():
    import kit_scan as KS
    rows = [dict(die="s81", type="leaf__t27", fold=9670, legs=3729, placed_status="OK", worst_pair=["cst_hi", "lane", 1193, 829.8], skew100=0),
            dict(die="s81", type="col__t1", fold=0, legs=0, placed_status="FAILED", worst_pair=[None, None, 0, 0], skew100=1)]
    out = KS.hourly_digest(rows)
    assert len(out) == 1 and out[0].startswith("s81: 2 kits; FOLD 1 (leaf__t27); placed scans OK 1, FAILED 1; legs>405 in 1 of 1")
    assert out[0].endswith("tap skew>=100 ps in 1")


def test_classify_leg_core_channel_logic_strap():
    import cbc_rules as CBC
    core = [[100, -50, 200, 50]]
    assert CBC.classify_leg("u_a.q", "u_b.d", [0, 0], [500, 0], core) == "core"          # a straight run through the core
    assert CBC.classify_leg("u_a.q", "u_b.d", [0, 100], [500, 100], core) == "logic"     # passes above it
    assert CBC.classify_leg("port:x_i", "u_b.d", [0, 100], [500, 100], core) == "channel"
    assert CBC.classify_leg("u_strap_tie.q", "u_b.d", [0, 0], [500, 0], core) == "strap"


def test_qc_skips_tap_cover_and_plan_reach():
    assert PC.DIE_SKIP["qwen_compute"] == {"TAP-COVER", "REACH"}


def test_low_util_flags_glue_like_partition():
    t = {"outline_um": [777.6, 1468.8], "hard_cores": [{"outline_um": [100, 262.98]}]}
    f = PC.util_findings(t, 164563, 0.15, [(10.0, 10.0, 1.0), (700.0, 1400.0, 1.0)])
    assert f and 0.015 < f[0][0] < 0.03 and "fence" in f[0][1]
    assert PC.util_findings(t, 3_000_000, 0.15) == []


def test_depth_scan_counts_cell_levels():
    import depth_scan as DS
    nl = """module t(clk, a, z);
  output z;
  DFFHQNx1_ASAP7_75t_R r0 ( .CLK(clk), .D(a), .QN(n0) );
  INVx1_ASAP7_75t_R i1 ( .A(n0), .Y(n1) );
  NAND2xp5_ASAP7_75t_R g2 ( .A(n1), .B(n0), .Y(n2) );
  INVx1_ASAP7_75t_R i3 ( .A(n2), .Y(n3) );
  DFFHQNx1_ASAP7_75t_R r1 ( .CLK(clk), .D(n3), .QN(z) );
  ot_rom u_rom ( .addr(n2), .q({n9, n8}) );
endmodule
"""
    rows, mx = DS.levels(nl, 1)
    d = dict(rows)
    assert mx == 3 and d["r1.D"] == 3 and d["u_rom.addr"] == 2 and "r0.D" not in d


def test_reach_leg_pin_to_pin_no_core_no_strap():
    # COORD 11-19 05:55: count only pin-to-pin legs over the reach that do not span a core and are no strap / tie
    import cbc_rules as R
    core = [[100, -50, 400, 50]]
    assert R.reach_leg([500, 500, "u_a.q", "u_b.d", "D", [0, 0], [500, 0]], core) == "core"         # detour 600 > reach
    assert R.reach_leg([500, 500, "u_a.q", "u_b.d", "D", [0, 100], [500, 100]], core) == "logic"
    assert R.reach_leg([500, 500, "u_tie_x.q", "u_b.d", "D", [0, 100], [500, 100]], core) is None   # strap / tie
    assert R.reach_leg([500, 500, "port:x_i", "u_b.d", "D", [0, 100], [500, 100]], core) is None    # channel <= 550
    assert R.reach_leg([600, 600, "port:x_i", "u_b.d", "D", [0, 100], [600, 100]], core) == "channel"
    assert R.reach_leg([400, 900, "u_a.q", "u_b.d", "D", [0, 100], [400, 100]], core) is None       # pin-to-pin <= reach


def test_kit_scan_counts_reach_legs_only():
    import kit_scan as KS
    ph = dict(macros=[[100, -50, 400, 50]], legs=[[500, 500, "u_a.q", "u_b.d", "D", [0, 0], [500, 0]],
                                                  [500, 500, "u_a.q", "u_c.d", "D", [0, 100], [500, 100]],
                                                  [500, 500, "u_strap_id.q", "u_c.d", "D", [0, 100], [500, 100]]])
    s = KS.summarise_placed(Path("/nonexistent/kit"), ph)
    assert s["legs_over"] == 2 and s["by_class"] == {"core": 1, "logic": 1, "strap": 1} and s["leg_rule"] == KS.LEG_RULE


def test_reach_face_bus_uses_worst_bit_of_the_window():
    """WINDOW-HOP (COL-CENSUS-1119 11-19, FABLE-PD-S81-2040 1c): col_h10_r0_p4 x_i0, 1,104 bits on the E face over y 980.7-1220.7;
    plan from_um = the window centre (hop 392 um), worst bit = the top end (hop 512 um)."""
    t = {"outline_um": [1442.88, 1296.0],
         "buses": [{"name": "x_i0", "dir": "in", "face": "E", "width": 1104, "window_um": [980.736, 1220.7]},
                   {"name": "f_o0", "dir": "out", "face": "N", "width": 8, "window_um": [100.0, 500.0]}],
         "internal_stations": [{"conn": "bus:x_i0", "from_um": [1442.88, 1100.718], "regs_um": [[1438.56, 712.8]],
                                "to_um": [1430.028, 518.412]}]}
    f = PC.reach_findings(t, 405, margin=1.0)
    assert len(f) == 1 and abs(f[0][0] - (4.32 + 1220.7 - 712.8)) < 0.2 and "hop 0" in f[0][1]
    assert len(PC.reach_findings(t)) == 1                       # 512 > 439 (wide calibration) as well
    t["internal_stations"][0]["regs_um"] = [[1442.88, 864.0]]  # the CC-WHOP-1 re-site: both hops <= 357 um
    assert PC.reach_findings(t, 405, margin=1.0) == []
    # out bus: the last hop goes to the window end farther from the last register
    t["internal_stations"] = [{"conn": "bus:f_o0", "from_um": [300.0, 700.0], "regs_um": [[120.0, 900.0]], "to_um": [300.0, 1296.0]}]
    f = PC.reach_findings(t, 405, margin=1.0)
    assert len(f) == 1 and f[0][0] == 380 + 396
    # a chain whose end is not on the bus face (an inner launch) keeps its own coordinates
    t["internal_stations"] = [{"conn": "bus:f_o0", "from_um": [300.0, 700.0], "regs_um": [[120.0, 900.0]], "to_um": [300.0, 1000.0]}]
    assert PC.reach_findings(t, 405, margin=1.0) == []


def test_core_leg_measured_at_detour_length():
    """COORD 11-21 (FAM-S81-COL-R4): a placed leg that crosses a hard core is measured at its detour around the core
    (shortest path outside core bodies), or at the routed length when known, never at its straight length"""
    import cbc_rules as R
    core = [[100, -50, 400, 50]]
    assert abs(R.detour_um([0, 0], [500, 0], core) - 600.0) < 0.1                  # over the top: 500 + 2 x 50
    assert abs(R.detour_um([0, 100], [500, 100], core) - 500.0) < 0.1              # clear of the core: straight
    assert abs(R.detour_um([0, -20], [500, 30], core) - 590.0) < 0.1               # over the top: 70 up + 500 + 20 down
    # 250 straight, but the core forces 350: counted at the detour (the old rule dropped every core leg)
    c, L = R.reach_leg_um([250, 250, "u_a.q", "u_b.d", "D", [0, 0], [250, 0]], [[100, -50, 200, 50]], reach=300)
    assert c == "core" and abs(L - 350.0) < 0.1
    assert R.reach_leg([250, 250, "u_a.q", "u_b.d", "D", [0, 0], [250, 0]], [[100, -50, 200, 50]], reach=300, routed_um=290) is None
    # two abutting cores are one body: no path along the shared edge
    two = [[100, -50, 200, 0], [100, 0, 200, 50]]
    assert abs(R.detour_um([0, 0], [300, 0], two) - 400.0) < 0.1
    # a macro pin just inside its own core walks out by the nearest side
    assert abs(R.detour_um([100.5, 0], [500, 0], [[100, -50, 400, 50]]) - 500.5) < 0.2
    # cap: a detour longer than the cap is reported as inf (the window search stops there)
    assert R.detour_um([0, 0], [500, 0], [[100, -400, 400, 400]], cap=600) == float("inf")
    assert abs(R.detour_um([0, 0], [500, 0], [[100, -400, 400, 400]]) - 1300.0) < 0.1


def test_shards_partition_types():
    ts = [f"t{i}" for i in range(11)]
    got = [x for k in range(3) for x in PC.shard_types(ts, f"{k}/3")]
    assert sorted(got) == sorted(ts) and len(got) == len(ts)
    assert PC.shard_types(ts, "0/1") == ts


def test_shard_mutant_rejects_bad_spec():
    import pytest
    for bad in ("3/3", "-1/2", "0/0"):
        with pytest.raises(ValueError):
            PC.shard_types(["a"], bad)


def test_lib_clocks_cache_parses_once_and_returns_copies(tmp_path):
    import os
    import types
    calls = []
    lib = tmp_path / "x.lib"
    lib.write_text("a")
    C = types.SimpleNamespace(lib_clocks=lambda p: (calls.append(p), {"clk": {"rise": 1.0}})[1])
    PC.install_lib_clocks_cache(C)
    r1 = C.lib_clocks(lib)
    r1["clk"]["rise"] = 99.0                    # a caller mutating its result must not poison the cache
    assert C.lib_clocks(lib) == {"clk": {"rise": 1.0}} and len(calls) == 1
    os.utime(lib, ns=(1, 2))                    # new mtime -> re-parse (mutant: a path-only key would serve stale data)
    C.lib_clocks(lib)
    assert len(calls) == 2


def test_run_types_parallel_equals_serial(monkeypatch):
    def fake(ctx, tn, checks, opts):
        if tn == "bad":
            raise RuntimeError("boom")
        return [dict(type=tn, check="X", value=len(tn), threshold=0, family=tn, detail="")]
    monkeypatch.setattr(PC, "type_findings", fake)
    ts = ["a", "bb", "bad", "cccc", "d"]
    ser = PC.run_types(None, ts, set(), None, 1)
    par = PC.run_types(None, ts, set(), None, 3)
    assert ser == par and [f["type"] for f in par[0]] == ["a", "bb", "cccc", "d"]
    assert par[1] == [("bad", "RuntimeError: boom")]            # an error is reported per type, never stops the run


def _drift_ctx(names):
    import types
    t = {"clock": {"added_taps": [{"name": n, "xy": [1, 1]} for n in names]}}
    return types.SimpleNamespace(P=types.SimpleNamespace(types={"T": t}))


def test_tap_census_by_position_recovers_name_drift(monkeypatch):
    # FP-CONVERGE-KV: kv3_hgi_v5 added_taps clk_t98.. vs density 107 taps raised and emptied the census of 61 of 93 KV types
    import types
    fake = types.ModuleType("taps")
    fake._density_base = lambda P, tn, control=True: list(range(107))
    monkeypatch.setitem(sys.modules, "taps", fake)

    def seen(ctx, tn):
        names = [p["name"] for p in ctx.P.types[tn]["clock"]["added_taps"]]
        if names != ["clk_t107", "clk_t108"]:
            raise ValueError("density added tap names/order must be clk_t107..clk_t108")
        return [("clk_t0", 0.0, 0.0)], [(1.0, 1.0)]
    monkeypatch.setattr(PC, "_taps_and_sinks", seen)
    ctx = _drift_ctx(["clk_t98", "clk_t99"])
    g, s, how = PC.tap_census_by_position(ctx, "T", ValueError("x"))
    assert how == "renamed" and s == [(1.0, 1.0)]
    assert [p["name"] for p in ctx.P.types["T"]["clock"]["added_taps"]] == ["clk_t98", "clk_t99"]      # plan restored


def test_tap_census_by_position_mutant_stays_error(monkeypatch):
    def boom(ctx, tn):
        raise ValueError("boom")
    monkeypatch.setattr(PC, "_taps_and_sinks", boom)
    g, s, how = PC.tap_census_by_position(_drift_ctx([]), "T", ValueError("x"))
    assert how is None and g == [] and s == []
    assert PC.tap_census_by_position(_drift_ctx(["clk_t1"]), "T", ValueError("x"))[2] is None   # dropping the table fails too -> TAP-ERROR


def test_reach_severity_gate_vs_aim():
    assert PC.reach_severity(405.0) == "AIM" and PC.reach_severity(405.1) == "GATE"      # mutant: a >= would flip the 405.0 case
    assert PC.reach_severity(330.0) == "AIM"

def test_tap_cal_level_thresholds():
    assert PC.tap_cal_level(5200) == "BLOCK-CANDIDATE"       # blocks once flipped
    assert PC.tap_cal_level(4800) == "WATCH"                 # advises only
    assert PC.tap_cal_level(2000) == "WARN" and PC.tap_cal_level(900) is None


def test_tap_cal_prediction_uses_flops_and_tap_share():
    t = {"outline_um": [1000, 1000]}
    one = [("clk", 500.0, 500.0)]
    four = [("a", 250.0, 250.0), ("b", 750.0, 250.0), ("c", 250.0, 750.0), ("d", 750.0, 750.0)]
    assert PC.voronoi_share_max(t, one) == 1.0
    assert abs(PC.voronoi_share_max(t, four) - 0.25) < 0.02
    assert PC.predict_tap_max(0, 1.0) == 0 and PC.predict_tap_max(60000, 1.0) > PC.predict_tap_max(60000, 0.25)
    big = PC.tap_cal_findings(t, one, 64000)                 # 64k flops on one tap: > 5000 (iq_C: measured 27,453)
    assert big and big[0][1] == "BLOCK-CANDIDATE"
    assert PC.tap_cal_findings(t, four, 20000)[0][1] in ("WARN", "WATCH")
    assert PC.tap_cal_findings(t, four, 300) == []           # mutant: a tiny type must not flag
    assert PC.tap_cal_findings(t, one, None) == []           # no flop count: silent


def test_tap_cal_calibration_on_measured_types():
    # two measured S81 kits: dsdv_slice_iq_C__t1 (64,564 flops, 187 taps) max tap 27,453; col_h9_r1 (24,421 flops) 4,161
    assert PC.predict_tap_max(64564, 0.02) > 1000 and PC.predict_tap_max(24421, 0.05) > 1000


def _perbit_type(regs, leaf=(430.0, 780.0), n_bits=8):
    return {"outline_um": [1442.88, 2000.0],
            "buses": [{"name": "be_i", "dir": "in", "face": "E", "width": n_bits, "window_um": [504.26, 1008.5]}],
            "internal_stations": [{"conn": "bus:be_i", "bits": n_bits, "bit_route": "per_bit", "leaf_um": list(leaf), "from_um": [1442.88, 756.0],
                                   "regs_um": regs, "to_um": list(leaf)}]}


def test_reach_per_bit_ignores_regs_um_like_the_kit(monkeypatch):
    """HEAD-INT-R2 F1 (P-FALSE-GREEN): the kit seats per_bit stations from pin / leaf_um / count only.  Re-seating regs_um must not
    change the verdict (it did: lean 598.5 / 756 false red, then a reseat turned it green with identical placed sites).  Opt-in."""
    monkeypatch.setenv("OT_PERBIT_REACH", "1")
    far = _perbit_type([[457.5, 760.0]] * 4)
    near = _perbit_type([[1100.0, 1000.0]] * 4)
    a, b = PC.reach_findings(far, 405, margin=1.0), PC.reach_findings(near, 405, margin=1.0)
    assert a == b == []                                    # worst pin end (1442.88,504.26) -> leaf: 1012.88+275.74 = 1288.6; / 5 = 257.7
    assert PC.reach_findings(_perbit_type([[0, 0]] * 2), 405, margin=1.0)[0][0] == 429.5      # 3 hops: 1288.62 / 3, whatever regs_um says


def test_reach_per_bit_mutant_old_reading_disagrees_with_kit(monkeypatch):
    """MUTANT: the old regs_um reading (OT_PERBIT_REACH=0) gives a different, kit-blind answer; the default agrees with the kit model
    taps.per_bit_station_sites (placed stations) on the worst hop."""
    import taps
    monkeypatch.setenv("OT_PERBIT_REACH", "1")                          # opt-in (default OFF, COORD 11-26)
    t = _perbit_type([[457.5, 760.0]], leaf=(100.0, 1000.0))     # 1 station: kit hop = L/2
    pins = [("be_i", b, "be_i[%d]" % b, 1442.88, 504.26 + 72.0 * b, "E") for b in range(8)]
    sites = taps.per_bit_station_sites(t, pins)
    worst_kit = 0.0
    for b in range(8):
        px, py = pins[b][3], pins[b][4]
        sx, sy, _ = sites[b]
        worst_kit = max(worst_kit, abs(px - sx) + abs(py - sy), abs(sx - 100.0) + abs(sy - 1000.0))
    f = PC.reach_findings(t, 405, margin=1.0)
    assert f and abs(f[0][0] - max(abs(1442.88 - 100.0) + abs(504.26 - 1000.0), abs(1442.88 - 100.0) + abs(1008.5 - 1000.0)) / 2) < 0.2
    assert worst_kit <= f[0][0] + 0.2                                      # real Manhattan <= the path-length bound the check reports
    monkeypatch.setenv("OT_PERBIT_REACH", "0")
    g = PC.reach_findings(t, 405, margin=1.0)
    assert g != f                                                           # old reading differs (regs_um chain from the window end)


def test_reach_per_bit_other_forms_unchanged():
    t = _perbit_type([[457.5, 760.0]])
    del t["internal_stations"][0]["bit_route"]
    assert PC.reach_findings(t, 405, margin=1.0)                           # no bit_route: regs_um chain, 1442.88-457.5+... > 405


def test_reach_per_bit_default_off_keeps_regs_um_reading(monkeypatch):
    """COORD 11-26: OT_PERBIT_REACH defaults OFF (packed_input_delay and knee-split mismatches with the kit): unset == the old
    regs_um reading; only OT_PERBIT_REACH=1 opts in to the per_bit model."""
    monkeypatch.delenv("OT_PERBIT_REACH", raising=False)
    off = PC.reach_findings(_perbit_type([[0, 0]] * 2), 405, margin=1.0)
    monkeypatch.setenv("OT_PERBIT_REACH", "0")
    assert PC.reach_findings(_perbit_type([[0, 0]] * 2), 405, margin=1.0) == off
    monkeypatch.setenv("OT_PERBIT_REACH", "1")
    assert PC.reach_findings(_perbit_type([[0, 0]] * 2), 405, margin=1.0) != off
