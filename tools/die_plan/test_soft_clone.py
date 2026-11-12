"""KV-HG-SPLIT-1 11-12: soft_clone.py (kit-local renamed exact copy of a module that is also a hard core master)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import soft_clone as SC  # noqa: E402

BASE = """`timescale 1ns/1ps
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
// module qkd_astk_ex_s ( in a comment must not count
module qkd_astk_ep_s (input wire ck); endmodule

module qkd_astk_ex_s (
    input  wire ck,
    input  wire [65:0] xa,
    output reg  [33:0] xe
);
    always @(posedge ck) xe <= xa[33:0] ^ ((`KVD_STMUT == 2) ? 34'd1 : 34'd0);  // endmodule in a comment
endmodule

module qkd_astk_ctl_s (input wire ck); endmodule
"""

BOUND = """module kv3_hg_v1_part (input wire clk);
    qkd_astk_ex_s u_astk_u_strip_u_strip_g_ep_p_g_ex_0_u_ex (
        .ck(clk), .xa(a0), .xe(e0));
    qkd_astk_ex_s u_astk_u_strip_u_strip_g_ep_p_g_ex_1_u_ex (
        .ck(clk), .xa(a1), .xe(e1));
endmodule
"""
ROW = dict(physical_inst="u_bound.u_astk_u_strip_u_strip_g_ep_p_g_ex_0_u_ex", base="qkd_astk_ex_s",
           master="qkd_astk_ex_s_soft")


def test_rename_only_the_planned_instance():
    out, rows = SC.clone_bound(BOUND, [ROW])
    assert "    qkd_astk_ex_s_soft u_astk_u_strip_u_strip_g_ep_p_g_ex_0_u_ex (" in out
    assert "    qkd_astk_ex_s u_astk_u_strip_u_strip_g_ep_p_g_ex_1_u_ex (" in out
    assert out.replace("qkd_astk_ex_s_soft", "qkd_astk_ex_s") == BOUND
    assert rows == [dict(ROW, cycles_changed=0)]


def test_absent_key_is_identity():
    assert SC.clone_bound(BOUND, None) == (BOUND, [])
    assert SC.clone_bound(BOUND, []) == (BOUND, [])


def test_clone_text_exact_body_and_guards():
    txt, row = SC.clone_text(BASE, "qkd_astk_ex_s", "qkd_astk_ex_s_soft", "leaves.sv")
    assert "module qkd_astk_ex_s_soft (" in txt and "module qkd_astk_ex_s (" not in txt
    assert "qkd_astk_ep_s" not in txt and "qkd_astk_ctl_s" not in txt
    assert "`ifndef KVD_STMUT\n`define KVD_STMUT 0\n`endif\n" in txt
    assert row["body_sha256"] == row["clone_body_sha256"] and row["macro_guards"] == 1
    body = SC.module_text(BASE, "qkd_astk_ex_s")
    assert txt.endswith(body.replace("module qkd_astk_ex_s (", "module qkd_astk_ex_s_soft (", 1) + "\n")


def test_sources_receipt_per_instance():
    _, rows = SC.clone_bound(BOUND, [ROW])
    txt, rec = SC.clone_sources(rows, lambda m: (BASE, "leaves.sv"))
    assert txt.count("module qkd_astk_ex_s_soft") == 1
    assert rec[0]["physical_inst"] == ROW["physical_inst"] and rec[0]["cycles_changed"] == 0


@pytest.mark.parametrize("row,msg", [
    (dict(ROW, base="qkd_astk_ep_s"), "plan says"),
    (dict(ROW, physical_inst="u_bound.u_nope"), "expected one instance"),
    (dict(ROW, physical_inst="u_bound.a.b"), "physical_inst"),
    (dict(ROW, master="qkd_astk_ex_s"), "new module name"),
    (dict(ROW, master="kv3_hg_v1_part"), "new module name"),
])
def test_fail_closed(row, msg):
    with pytest.raises(ValueError, match=msg):
        SC.clone_bound(BOUND, [row])


def test_missing_define_and_duplicate_definition_fail():
    with pytest.raises(ValueError, match="no `define"):
        SC.clone_text(BASE.replace("`define KVD_STMUT 0", ""), "qkd_astk_ex_s", "x_soft")
    with pytest.raises(ValueError, match="2 definitions"):
        SC.clone_text(BASE + "\nmodule qkd_astk_ex_s (); endmodule\n", "qkd_astk_ex_s", "x_soft")
