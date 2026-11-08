"""DIE-HBM-90-TNAME 11-07, class (h): HBM q_su00/10/20/30 (+pv1) and q_hub_ne kit_rtl stopped on
"core clock clk_c0: expected one u_u_su_Q0_pretree.clk_ctl connection" / "clk_c6: expected one u_u_hb_vms_Q_q0.clk
connection".  The plan tap names the clock pin of the PLAN master; the bind of record keeps the NATIVE body as the
leaf, whose clock entries carry other names.  kit_core_clocks.wire maps the plan pin to the native leaf's clock entries
only when the leaf master is not the plan master and every clock-named pin is on the type clock; else fails closed."""
import inspect
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import kit_core_clocks as K  # noqa: E402

SU = """module hbm_arch_q_su00 (
    input wire clk,
    input wire [11:0] cmd,
    output wire [66:0] tree_o
);
    ot_hnx_su_pretree__rst u_u_su_Q0_pretree (
        .pretree_clk(clk),
        .pretree_tree_cmd(cmd),
        .rst_n(rst_n),
        .pretree_tree_o(tree_o)
    );
endmodule
"""
SU_ROW = ("clk_c0", "u_su_Q0_pretree", "clk_ctl", 0, 245.41)
SU_MASTERS = {"u_su_Q0_pretree": {"ot_hbm_su_static_pgslice_lg__pretree"}}

HUB = """module hbm_arch_q_hub__q_hub_ne (
    input wire clk,
    input wire d,
    output wire q
);
    hfd_hgi_vms_static_SE_glue u_u_hb_vms_Q_q0 (
        .clk_hub(clk),
        .clk_replay(clk),
        .clk_ring({clk, clk}),
        .rst_n(rst_n),
        .cw_in(d),
        .cw_out(q)
    );
endmodule
"""
HUB_ROW = ("clk_c6", "u_hb_vms_Q__q0", "clk", 0, 250)
HUB_MASTERS = {"u_hb_vms_Q__q0": {"hfd_hgi_vms_glue_nw_t"}}


def leaf_id(inst):
    return bind.short_id("u_" + inst, 90)


def test_pretree_plan_pin_maps_to_the_one_native_clock_entry():
    text, receipt = K.wire(SU, "hbm_arch_q_su00", [SU_ROW], leaf_id=leaf_id, core_masters=SU_MASTERS)
    assert ".pretree_clk(clk_c0)" in text and text.count("input wire clk_c0,") == 1
    assert ".pretree_tree_cmd(cmd)" in text and ".rst_n(rst_n)" in text
    assert [(r["instance"], r["pin"], r["plan_pin"], r["previous_net"], r["mode"]) for r in receipt] == \
        [("u_u_su_Q0_pretree", "pretree_clk", "clk_ctl", "clk", "rtl")]
    assert K.rtl_wired(receipt)


def test_vms_plan_clk_maps_to_every_native_clock_entry():
    text, receipt = K.wire(HUB, "hbm_arch_q_hub__q_hub_ne", [HUB_ROW], leaf_id=leaf_id, core_masters=HUB_MASTERS)
    for s in (".clk_hub(clk_c6)", ".clk_replay(clk_c6)", ".clk_ring({clk_c6, clk_c6})", ".cw_in(d)"):
        assert s in text
    assert sorted(r["pin"] for r in receipt) == ["clk_hub", "clk_replay", "clk_ring"]
    assert {r["native_master"] for r in receipt} == {"hfd_hgi_vms_static_SE_glue"}


def test_without_core_masters_it_still_fails_closed():
    with pytest.raises(ValueError, match="expected one u_u_su_Q0_pretree.clk_ctl connection"):
        K.wire(SU, "hbm_arch_q_su00", [SU_ROW], leaf_id=leaf_id)


def test_leaf_that_is_the_plan_master_fails_closed():
    masters = {"u_su_Q0_pretree": {"ot_hnx_su_pretree__rst"}}
    with pytest.raises(ValueError, match="expected one u_u_su_Q0_pretree.clk_ctl connection"):
        K.wire(SU, "hbm_arch_q_su00", [SU_ROW], leaf_id=leaf_id, core_masters=masters)


def test_native_clock_pin_on_another_net_fails_closed():
    two = HUB.replace(".clk_replay(clk)", ".clk_replay(clk_b)")
    with pytest.raises(ValueError, match="native clock pins not on clk"):
        K.wire(two, "hbm_arch_q_hub__q_hub_ne", [HUB_ROW], leaf_id=leaf_id, core_masters=HUB_MASTERS)


def test_two_plan_pins_on_one_native_body_fail_closed():
    rows = [HUB_ROW, ("clk_c7", "u_hb_vms_Q__q0", "clk2", 0, 250)]
    with pytest.raises(ValueError, match="more than one pin"):
        K.wire(HUB, "hbm_arch_q_hub__q_hub_ne", rows, leaf_id=leaf_id, core_masters=HUB_MASTERS)


def test_native_leaf_without_a_clock_entry_fails_closed():
    none = SU.replace(".pretree_clk(clk)", ".pretree_en(clk)")
    with pytest.raises(ValueError, match="expected one u_u_su_Q0_pretree.clk_ctl connection"):
        K.wire(none, "hbm_arch_q_su00", [SU_ROW], leaf_id=leaf_id, core_masters=SU_MASTERS)


def test_a_leaf_that_has_the_plan_pin_is_unchanged():
    has = SU.replace(".pretree_clk(clk)", ".clk_ctl(clk)")
    text, receipt = K.wire(has, "hbm_arch_q_su00", [SU_ROW], leaf_id=leaf_id, core_masters=SU_MASTERS)
    assert ".clk_ctl(clk_c0)" in text and "rule" not in receipt[0]


def test_kit_rtl_passes_the_plan_masters():
    src = inspect.getsource(bind.cmd_kit_rtl)
    assert "core_masters=masters" in src
