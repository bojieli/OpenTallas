#!/usr/bin/env python3
"""DIE-HBM-91-KCLS 11-08 (class k2): the native reset export's selected kit hierarchy (gen_phys._kit_rooted_rtl)
accepts a generate-terminated self-recursive module (HBM root ot_hdc_v41x_addtree #(.N(N/2)) u_l/u_r); mutual
recursion, a missing or a duplicated definition still fail closed."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_phys as G

ADDTREE = """
module ot_add (input wire clk, input wire [31:0] a, b, output wire [31:0] y);
  assign y = a + b;
endmodule
module ot_addtree #(parameter integer N = 2) (input wire clk, input wire [N*32-1:0] x, output wire [31:0] y);
  generate if (N == 1) begin : g_one
    assign y = x;
  end else if (N == 2) begin : g_two
    ot_add u_a (.clk(clk), .a(x[31:0]), .b(x[63:32]), .y(y));
  end else begin : g_rec
    wire [31:0] yl, yr;
    ot_addtree #(.N(N / 2)) u_l (.clk(clk), .x(x[0 +: N*16]), .y(yl));
    ot_addtree #(.N(N / 2)) u_r (.clk(clk), .x(x[N*16 +: N*16]), .y(yr));
    ot_add u_a (.clk(clk), .a(yl), .b(yr), .y(y));
  end endgenerate
endmodule
module unused_mod (input wire a);
endmodule
module top (input wire clk, input wire [255:0] x, output wire [31:0] y);
  ot_addtree #(.N(8)) u_t (.clk(clk), .x(x), .y(y));
endmodule
"""


def _mods(text):
    import re
    return re.findall(r"^\s*module\s+(\w+)", text, re.M)


def test_self_recursive_generate_selected_once():
    got = G._kit_rooted_rtl(ADDTREE, "top")
    assert sorted(_mods(got)) == ["ot_add", "ot_addtree", "top"]


def test_mutual_recursion_still_fails():
    txt = """
module a_m (input wire x); b_m u_b (.x(x)); endmodule
module b_m (input wire x); a_m u_a (.x(x)); endmodule
module top (input wire x); a_m u (.x(x)); endmodule
"""
    with pytest.raises(ValueError, match="recursive selected kit hierarchy at a_m"):
        G._kit_rooted_rtl(txt, "top")


def test_duplicate_definition_still_fails():
    txt = ADDTREE + "\nmodule ot_add (input wire clk); endmodule\n"
    with pytest.raises(ValueError, match="ot_add is missing or duplicated"):
        G._kit_rooted_rtl(txt, "top")


def test_missing_top_still_fails():
    with pytest.raises(ValueError, match="nope is missing or duplicated"):
        G._kit_rooted_rtl(ADDTREE, "nope")
