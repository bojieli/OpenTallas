"""KW-FIX-1/S81PF 11-02: plan macro paths -> bound netlist paths (S81 kit-wave macro_instances class, 42+ items:
'placed macro u_r0.u_bn0: component u_r0 is neither an instance nor a generate block')."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_macro_paths as BMP  # noqa: E402
import reset_tree as RT  # noqa: E402

BOUND = """module s81p_x__t1_bound #(parameter P_u_r0_u_e0_INSTANCE = "") (input wire clk);
    // as-built u_f_0R01.u_r0.u_bn0
    dsfd_qbank_N u_u_r0_u_bn0 (
        .ck(clk)
    );
    // as-built u_f_0R01.u_r0.u_e1e
    dsfd_bf_col #(.INSTANCE(""), .MB(0)) u_u_r0_u_e1e (
        .ck(clk)
    );
    // as-built u_f_0R01.u_r0.u_e0
    ot_v41_rom_elem_q_qxpq_w10_gb #(.INSTANCE(P_u_r0_u_e0_INSTANCE)) u_u_r0_u_e0 (
        .ck(clk)
    );
    // as-built u_f_0R01.u_r0.u_x
    other_mod u_u_r0_u_x (
        .ck(clk)
    );
endmodule
"""

LEAF = """    // as-built u_s_0N.u_sl.u_lf4.u_ve.u_m
    ot_s81sl_ve_m #(.LA(4), .LM(5), .MUT(0)) u_u_lf4_u_ve_u_m (
        .clk(clk)
    );
    // as-built u_s_0N.u_sl.u_lf4.u_vsw
    ot_s81sl_vsw #(.LA(4), .LM(5), .LR(1)) u_u_lf4_u_vsw (
        .clk(clk)
    );
"""


def _core(inst, module, **kw):
    return dict(inst=inst, module=module, lef=f"v/{module}.lef", origin_um=[1.0, 2.0], outline_um=[3.0, 4.0], **kw)


def test_col_flat_nested_and_mismatch():
    t = dict(contents=[dict(inst="u_r0", module="col_r0")],
             hard_cores=[_core("u_r0.u_bn0", "dsfd_qbank_N"), _core("u_r0.u_e1e.u_view", "ot_v41_bf_col"),
                         _core("u_r0.u_e0", "ot_v41_rom_elem_q_qxpq_w10_gb"),
                         _core("u_r0.u_x", "dsfd_qbank_S"),             # same path, different module: unmapped
                         _core("u_r0.u_t0__payload", "ot_s81_sstn_payload536"),   # no as-built leaf: unmapped
                         _core("u_bound.u_done", "m"),                  # already a bound path: untouched
                         _core("u_r0.u_k", "m", physical_inst="u_bound.k", physical_master="m")])
    rows = {r["inst"]: r for r in BMP.resolve(t, BOUND)}
    assert rows["u_r0.u_bn0"]["physical_inst"] == "u_bound.u_u_r0_u_bn0"
    assert rows["u_r0.u_e1e.u_view"]["physical_inst"] == "u_bound.u_u_r0_u_e1e.u_view"
    assert rows["u_r0.u_e0"]["physical_inst"] == "u_bound.u_u_r0_u_e0"
    assert rows["u_r0.u_e0"]["physical_master"] == "ot_v41_rom_elem_q_qxpq_w10_gb"
    assert set(rows) == {"u_r0.u_bn0", "u_r0.u_e1e.u_view", "u_r0.u_e0"}


def test_leaf_renamed_content_root():
    # plan content u_lf is the as-built u_s_0N.u_sl.u_lf4: the root comes from the macros' common suffix match
    t = dict(contents=[dict(inst="u_lf", module="ot_s81sl_leaf")],
             hard_cores=[_core("u_lf.u_ve.u_m", "ot_s81sl_ve_m"), _core("u_lf.u_vsw", "ot_s81sl_vsw")])
    rows = {r["inst"]: r["physical_inst"] for r in BMP.resolve(t, "module b(input clk);\n" + LEAF + "endmodule\n")}
    assert rows == {"u_lf.u_ve.u_m": "u_bound.u_u_lf4_u_ve_u_m", "u_lf.u_vsw": "u_bound.u_u_lf4_u_vsw"}


def test_ambiguous_root_unmapped():
    two = LEAF + LEAF.replace("u_lf4", "u_lf5")
    t = dict(contents=[dict(inst="u_lf", module="l")], hard_cores=[_core("u_lf.u_vsw", "ot_s81sl_vsw")])
    assert BMP.resolve(t, "module b(input clk);\n" + two + "endmodule\n") == []


def test_project_receipt_and_overlay(tmp_path):
    kd = tmp_path / "rtl"
    kd.mkdir()
    (kd / "s81p_x__t1_bound.sv").write_text(BOUND)
    (kd / "s81p_x__t1.sv").write_text("module s81p_x__t1(input wire clk); s81p_x__t1_bound u_bound(.clk(clk)); endmodule\n")
    (kd / "kit_rtl.f").write_text(f"{kd}/s81p_x__t1.sv\n{kd}/s81p_x__t1_bound.sv\n")
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="s81p_x__t1_bound")))
    raw = dict(partition_types=dict(x__t1=dict(module="s81p_x__t1", contents=[dict(inst="u_r0", module="c")],
                                               hard_cores=[_core("u_r0.u_bn0", "dsfd_qbank_N")])))
    before = json.dumps(raw, sort_keys=True)
    new, rec = BMP.project(raw, {"x__t1": str(kd / "kit_rtl.f")})
    assert json.dumps(raw, sort_keys=True) == before                    # plan of record untouched
    c = new["partition_types"]["x__t1"]["hard_cores"][0]
    assert (c["inst"], c["physical_inst"], c["physical_master"]) == ("u_r0.u_bn0", "u_bound.u_u_r0_u_bn0", "dsfd_qbank_N")
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / BMP.RECEIPT).write_text(json.dumps(rec["x__t1"]))
    ent = BMP.overlay(kit, {"u_r0.u_bn0": raw["partition_types"]["x__t1"]["hard_cores"][0]})
    assert ent["u_bound.u_u_r0_u_bn0"]["module"] == "dsfd_qbank_N" and ent["u_bound.u_u_r0_u_bn0"]["outline_um"] == [3.0, 4.0]
    # no bound module text -> nothing projected, the same object back
    assert BMP.project(raw, {})[0] is raw


def test_reset_tcl_resolves_physical_name():
    T = dict(entry="sync", reach_um=100, root=[0, 0], taps=[], n_tree=0, n_pad=0, max_hop_um=1, relays=[], depth=1,
             core_resets=[dict(inst="u_r0.u_e0", physical_inst="u_bound.u_u_r0_u_e0", pin="rst_n", tap=3,
                               pin_um=[1.0, 2.0], xy=[1.0, 2.0], internal_depth=1)])
    line = next(x for x in RT.tcl_text(T).splitlines() if "lappend rtr_ci" in x)
    assert "$n eq {u_r0.u_e0}" in line and "$n eq {u_bound.u_u_r0_u_e0}" in line
    T["core_resets"][0].pop("physical_inst")
    line = next(x for x in RT.tcl_text(T).splitlines() if "lappend rtr_ci" in x)
    assert line == ("foreach i [$ff_blk getInsts] { set n [string map {\\\\[ [ \\\\] ]} [$i getName]]; if {$n eq {u_r0.u_e0} || [string range $n "
                    "end-[string length {u_r0.u_e0}] end] eq {/u_r0.u_e0} || [string range $n end-[string length {u_r0.u_e0}] end] eq {.u_r0.u_e0}} "
                    "{ lappend rtr_ci $i } }")   # no physical_inst: exact, /inst or .inst (flat core u_bound.<inst>)


def test_flat_core_names_resolve_inside_wrapper():
    t = {"hard_cores": [_core("u_lane0", "qfd_lane"), _core("u_t22", "qfd_tile_nk_a0c"), _core("u_bt", "qfd_rom"),
                         _core("u_missing", "qfd_x"), _core("u_other", "qfd_y")]}
    bound = """module top ();
    qfd_lane u_lane0 (.a(a));
    qfd_tile_nk_a0c u_t22 (.a(a));
    qfd_rom #(.W(4)) u_u_bt (.a(a));
    qfd_wrong u_other (.a(a));
endmodule
"""
    rows = {r["inst"]: r for r in BMP.resolve(t, bound)}
    assert rows["u_lane0"]["physical_inst"] == "u_bound.u_lane0"
    assert rows["u_t22"]["physical_inst"] == "u_bound.u_t22"
    assert rows["u_bt"]["physical_inst"] == "u_bound.u_u_bt"
    assert rows["u_bt"]["physical_master"] == "qfd_rom"
    assert "u_missing" not in rows and "u_other" not in rows


def test_macros_under_content_bound_whole():
    t = {"contents": [{"inst": "u_bk_sel", "module": "vmtx"}],
         "hard_cores": [{"inst": "u_bk_sel.u_sel.g_q[0].u_q", "module": "q", "lef": "q.lef"},
                        {"inst": "u_bk_sel.u_tx", "module": "tx", "lef": "tx.lef"}]}
    bound = "    // as-built u_bk_sel\n    vmtx #(.V(276)) u_core (\n"
    rows = {r["inst"]: r["physical_inst"] for r in BMP.resolve(t, bound)}
    assert rows == {"u_bk_sel.u_sel.g_q[0].u_q": "u_bound.u_core.u_sel.g_q[0].u_q",
                    "u_bk_sel.u_tx": "u_bound.u_core.u_tx"}
    t["contents"][0]["module"] = "other"
    assert BMP.resolve(t, bound) == []


SCOPED = """    // as-built u_s_3S.u_sl.g_c3.u_xr
    ot_s81sl_xrt3 #(.FOREG(1)) u_u_s_3S_u_sl_g_c3_u_xr (
        .clk(clk)
    );
    // as-built u_s_3S.u_sl.u_cap
    %s u_u_s_3S_u_sl_u_cap (
        .clk(clk)
    );
    // as-built u_s_3S.u_sl.u_eg.u_nh
    ot_s81sl_egn #(.LA(4)) u_u_s_3S_u_sl_u_eg_u_nh (
        .clk(clk)
    );
"""
SCOPED_T = dict(hard_cores=[dict(inst="u_c.u_cap", module="ot_s81sl_capc5r", lef="a.lef"),
                            dict(inst="u_c.u_xr", module="ot_s81sl_xrt3", lef="b.lef"),
                            dict(inst="u_c.u_eg.u_nh", module="ot_s81sl_egn", lef="c.lef")])


def test_generate_scope_below_root():
    rows = {r["inst"]: r for r in BMP.resolve(SCOPED_T, SCOPED % "ot_s81sl_capc5r")}
    assert rows["u_c.u_xr"]["physical_inst"] == "u_bound.u_u_s_3S_u_sl_g_c3_u_xr"
    assert rows["u_c.u_cap"]["physical_inst"] == "u_bound.u_u_s_3S_u_sl_u_cap"
    assert rows["u_c.u_eg.u_nh"]["physical_inst"] == "u_bound.u_u_s_3S_u_sl_u_eg_u_nh"


def test_generate_scope_wrong_module_stays_unmapped():
    rows = {r["inst"] for r in BMP.resolve(SCOPED_T, SCOPED % "ot_s81sl_capc2_w3")}
    assert rows == {"u_c.u_xr", "u_c.u_eg.u_nh"}


def test_generate_scope_two_roots_no_rows():
    two = (SCOPED % "ot_s81sl_capc5r").replace("u_s_3S.u_sl.u_eg.u_nh", "u_s_4S.u_sl.u_eg.u_nh")
    assert BMP.resolve(SCOPED_T, two) == []


def test_plan_path_in_bound_instance_names():
    """KW-FIX-17 11-05: S81 serdes plan path u_core.u_dec.u_chn names the bound leaf u_core (as-built u_lk_ES1 bound
    whole, plan content u_phy of another module) -> u_bound.u_core.u_dec.u_chn; ambiguous or unknown names stay."""
    t = {"contents": [{"inst": "u_phy", "module": "ot_pdie_serdes"}],
         "hard_cores": [{"inst": "u_core.u_dec.u_chn", "module": "ot_s81_kp4_dchn", "lef": "k.lef"}]}
    bound = "    // as-built u_lk_ES1\n    ot_pdie_serdes_col #(.TXL(2)) u_core (\n"
    rows = {r["inst"]: r["physical_inst"] for r in BMP.resolve(t, bound)}
    assert rows == {"u_core.u_dec.u_chn": "u_bound.u_core.u_dec.u_chn"}
    two = bound + "    // as-built u_lk_WN2\n    ot_pdie_serdes_col #(.TXL(2)) u_core (\n"
    assert BMP.resolve(t, two) == []                                  # two leaves named u_core: no row
    t2 = {"contents": [], "hard_cores": [{"inst": "u_nope.u_dec.u_chn", "module": "ot_s81_kp4_dchn", "lef": "k.lef"}]}
    assert BMP.resolve(t2, bound) == []                               # no bound leaf of that name: no row


def test_explicit_split_core_path_requires_producer_table():
    c = dict(inst="u_lk_N2__chn", module="ot_s81_kp4_dchn", lef="k.lef",
             physical_inst="u_lk_N2.u_fcore.u_core.u_chn", physical_master="ot_s81_kp4_dchn")
    t = dict(hard_cores=[c])
    text = "    // as-built lk_N2\n    ot_pdie_serdes__p37glue u_u_lk_N2 (\n"
    assert BMP.resolve_sub_cores(t, text, {}) == []
    assert BMP.resolve_sub_cores(t, text, {"u_lk_N2": "lk_N0"}) == []
    rows = BMP.resolve_sub_cores(t, text, {"u_lk_N2": "lk_N2"})
    assert rows[0]["physical_inst"] == "u_bound.u_u_lk_N2.u_fcore.u_core.u_chn"
    assert rows[0]["physical_master"] == c["physical_master"]
    assert c["physical_inst"] == "u_lk_N2.u_fcore.u_core.u_chn"


def test_split_projection_preserves_explicit_master_and_subpath(tmp_path):
    bound = tmp_path / "bound.sv"
    bound.write_text("    // as-built lk_N2\n    ot_pdie_serdes__p37glue u_u_lk_N2 (\n")
    fl = tmp_path / "kit_rtl.f"
    fl.write_text(str(bound))
    ab = tmp_path / "asbuilt.json"
    ab.write_text(json.dumps(dict(sub_core_leaf={"u_lk_N2": "lk_N2"})))
    fl.with_name("kit_rtl.json").write_text(json.dumps(dict(bound_module="bound", asbuilt_manifest=str(ab))))
    c = dict(inst="u_lk_N2__rx__bm0", module="ot_pdie_serdes_rx_bm_native", lef="k.lef",
             physical_inst="u_lk_N2.u_fcore.u_core.u_rx.u_bm0", physical_master="ot_pdie_serdes_rx_bm_native")
    raw = dict(partition_types={"T": dict(hard_cores=[c], contents=[dict(inst="u_lk_N2", module="ot_pdie_serdes")])})
    projected, receipts = BMP.project(raw, {"T": str(fl)})
    assert projected["partition_types"]["T"]["hard_cores"][0]["physical_inst"] == "u_bound.u_u_lk_N2.u_fcore.u_core.u_rx.u_bm0"
    assert raw["partition_types"]["T"]["hard_cores"][0] == c
    assert receipts["T"]["rows"][0]["asbuilt"] == "lk_N2"
    import gen_phys
    placed = gen_phys.pg_placed_blocks(projected["partition_types"]["T"])
    assert len(placed) == 1 and placed[0]["inst"] == c["inst"]
    assert placed[0]["sub_core_parent"] == "u_lk_N2"
    kd = tmp_path / "physical_kit"
    kd.mkdir()
    (kd / BMP.RECEIPT).write_text(json.dumps(receipts["T"]))
    entries = {c["physical_inst"]: dict(c, inst=c["physical_inst"])}
    over = BMP.overlay(kd, entries)
    assert over["u_bound.u_u_lk_N2.u_fcore.u_core.u_rx.u_bm0"]["module"] == c["physical_master"]


def test_physical_variant_roots_through_bound_parent_name():
    """DIE-HBM-92-PHY: q_spb0__physical_v1 binds plan u_lk_S0 from as-built lk_S3 (bound u_u_lk_S0)."""
    c = dict(inst="u_lk_S0__tx", module="ot_pdie_serdes_tx", lef="k.lef",
             physical_inst="u_lk_S0.u_fcore.u_core.u_tx", physical_master="ot_pdie_serdes_tx")
    t = dict(hard_cores=[c])
    text = "    // as-built lk_S3\n    ot_pdie_serdes__p37glue u_u_lk_S0 (\n"
    table, alt = {"u_lk_S0": "lk_S0"}, {"u_lk_S0": ["lk_S3"]}
    assert BMP.resolve_sub_cores(t, text, table) == []                # alternate leaf not declared: no row
    rows = BMP.resolve_sub_cores(t, text, table, alt)
    assert rows[0]["physical_inst"] == "u_bound.u_u_lk_S0.u_fcore.u_core.u_tx" and rows[0]["asbuilt"] == "lk_S3"
    assert BMP.resolve_sub_cores(t, text, {}, alt) == []              # no producer table entry: no row
    both = text + "    // as-built lk_S0\n    ot_pdie_serdes__p37glue u_u_lk_S0x (\n"
    assert BMP.resolve_sub_cores(t, both, table, alt) == []           # two declared leaves present: no row


def test_flat_core_folded_underscores():
    # DIE-HBM-92-SU-IDX 11-08: the bind folds runs of _ in u_<inst> (HBM h1 half columns)
    t = {"hard_cores": [_core("u_hb_idx__s_Q2_r0c0_k0h1", "ot_hbm_idx_score_hcol_h1"), _core("u_a__b", "m_x")]}
    bound = """    // as-built hb_idx__s_SE.scorer.ge[0].gc[0].leaf.core.g_col[0].g_half[1].u_hc
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k0h1 (
        .cf_in(c));
    m_y u_u_a_b (.a(a));
"""
    rows = {r["inst"]: r for r in BMP.resolve(t, bound)}
    assert rows["u_hb_idx__s_Q2_r0c0_k0h1"]["physical_inst"] == "u_bound.u_u_hb_idx_s_Q2_r0c0_k0h1"
    assert "u_a__b" not in rows                      # folded name of another module: no row


WRAP = """module s81p_x__t1 (input wire clk);
    // plan wrapper: s81p_x__t1_ot_native_w would be named in this comment only
    s81p_x__t1_bound u_bound (
        .clk(clk)
    );
endmodule
"""


def test_unplaceable_module_name_inst_refused():
    # T51-INST 11-10: S81 t51 native_w/_e placed by module name over the unsplit bound station
    m = "s81p_x__t1_ot_native_w"
    t = dict(hard_cores=[_core(m, m), _core("u_bound.u_u_r0_u_bn0", "dsfd_qbank_N")])
    err = BMP.unplaceable("x__t1", t, WRAP, BOUND, source="kit RTL s81p_x__t1.sv")
    assert len(err) == 1 and f"placed macro {m}" in err[0] and "is the module name" in err[0], err


def test_unplaceable_bound_leaf_missing_refused():
    t = dict(hard_cores=[_core("u_bound.u_nope", "m"), _core("u_bound.u_u_r0_u_e1e.u_view", "ot_v41_bf_col")])
    err = BMP.unplaceable("x__t1", t, WRAP, BOUND)
    assert len(err) == 1 and "'u_bound.u_nope'" in err[0], err


def test_unplaceable_leaves_uncertain_to_preflight():
    # physical identity, physical_parts, escaped flat names and generate-indexed leaves are not refused here
    flat = BOUND.replace("endmodule", "    m \\u_c.u_b.g_w[1].u_m  (.ck(clk));\nendmodule")
    t = dict(hard_cores=[_core("u_r0.u_k", "m", physical_inst="u_bound.u_u_r0_u_x", physical_master="other_mod"),
                         _core("u_bound.u_c.u_b.g_w[1].u_m", "m"),
                         dict(inst="u_nolef", module="m")],                       # no lef: never placed
             contents=[dict(inst="u_s", module="s", physical_parts=[
                 dict(physical_inst="u_bound.u_u_r0_u_e0", physical_master="ot_v41_rom_elem_q_qxpq_w10_gb")])])
    assert BMP.unplaceable("x__t1", t, WRAP, flat) == []
    assert BMP.unplaceable("x__t1", t, WRAP, None) == []          # no bound file: only the top component is checked
