"""DIE-HBM-90-ISTA 11-07, class (e) of the DIE-HBM-89-HBMBIND READY: HBM q_hub_nw kit_rtl stopped on
"core clock clk_c1: expected one bound leaf u_hb_coll_Q_ring_ag__q0, got 0".  The bind emits that plan core as leaf
u_u_hb_coll_Q_ring_ag_q0 (bind.sv_id folds "__" to "_"); kit_core_clocks.wire now also tries the binder's own leaf
name, still requiring exactly one match."""
import inspect
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import kit_core_clocks as K  # noqa: E402

HUB = """module hbm_arch_q_hub (
    input wire clk,
    input wire d,
    output wire q
);
    ot_hfd_coll_q2_hard_v8g__ring_ag u_u_hb_coll_Q_ring_ag_q0 (
        .clk(clk),
        .d(d),
        .q(q)
    );
endmodule
"""
ROW = ("clk_c1", "u_hb_coll_Q_ring_ag__q0", "clk", 0, 250)


def leaf_id(inst):
    return bind.short_id("u_" + inst, 90)


def test_binder_leaf_name_of_a_double_underscore_core():
    assert leaf_id("u_hb_coll_Q_ring_ag__q0") == "u_u_hb_coll_Q_ring_ag_q0"


def test_wire_finds_the_bound_leaf_by_the_binder_name():
    text, receipt = K.wire(HUB, "hbm_arch_q_hub", [ROW], leaf_id=leaf_id)
    assert ".clk(clk_c1)" in text and text.count("input wire clk_c1,") == 1
    assert (receipt[0]["instance"], receipt[0]["previous_net"], receipt[0]["mode"]) == \
        ("u_u_hb_coll_Q_ring_ag_q0", "clk", "rtl")
    again, _ = K.wire(text, "hbm_arch_q_hub", [ROW], leaf_id=leaf_id)
    assert again == text


def test_without_leaf_id_the_old_lookup_still_fails_closed():
    with pytest.raises(ValueError, match="expected one bound leaf u_hb_coll_Q_ring_ag__q0, got 0"):
        K.wire(HUB, "hbm_arch_q_hub", [ROW])


def test_two_matches_fail_closed():
    two = HUB.replace("endmodule", "    child u_hb_coll_Q_ring_ag__q0 (.clk(clk));\nendmodule")
    with pytest.raises(ValueError, match="got 2"):
        K.wire(two, "hbm_arch_q_hub", [ROW], leaf_id=leaf_id)


def test_dotted_physical_inst_is_not_renamed():
    text, receipt = K.wire(HUB, "hbm_arch_q_hub", [("clk_c1", "u_x.u_y__q0", "clk", 0, 250)], leaf_id=leaf_id)
    assert text == HUB and receipt[0]["mode"] == "physical_tap"


def test_kit_rtl_passes_the_binder_leaf_name():
    src = inspect.getsource(bind.cmd_kit_rtl)
    assert 'kit_core_clocks.wire(btxt, bmod, core_rows,' in src and 'short_id("u_" + inst, 90)' in src
