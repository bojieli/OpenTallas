#!/usr/bin/env python3
"""DIE-KV-14b (2026-10-28) kv3_pv_pair plan delta (b2): per-lane-group copies of the slice control stage c_r for
red_issue (c_r[17]) and red_capture (c_r[18]), 0 added cycles, opt-in NEW modules (existing modules untouched).

Root cause (KV-KITS-14, CHECKED path): c_r[17] = red_issue is ONE pin flop that selects the a/b operand muxes and the
valid of all 16 lane adders (16 x 65 = 1,040 loads; worst TT path spends 452 ps in its repair buffer tree); red_capture
(c_r[18]) has the same broadcast shape (512 reduce_a enables).

Why extra PINS (not copies behind bc[17]): face_guard (tools/die_plan/face_guard.py, run by every kit after synth) requires
'an input port bit loads exactly one cell pin, which leads to the D pin of a flop'.  A zero-cycle copy must load the same
value on the same edge as c_r[17], i.e. from the pin itself, so G copies need G pins.  Group g >= 1 therefore gets its
own pin register on a new port bcx (issue copies bcx[G-2:0], capture copies bcx[2G-3:G-1]); group 0 keeps c_r[17/18].
Outside the core the column drives every copy pin from the SAME command bit (cmd[25] / cmd[26]), so the function at the
pair boundary is unchanged; the RTL proof (lec_slice_lc.ys) closes the slice boundary with bcx tied to those bits.

Generated (exact text edits, assert-once) from the two committed sources:
  ot_qwen_tp8_pv16_slice     (rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv)  -> ot_qwen_tp8_pv16_slice_lc #(G, MUT_LC)
  ot_qwen_tp8_pv_slice_t     (rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv)     -> ot_qwen_tp8_pv_slice_lc_t #(RESET_PIN, G, MUT_LC)
Lane l reads copy l*G/16.  MUT_LC=1 (bench negative control only): lane 15 reads the CAPTURE copy as its issue select.

  gen_slice_lc.py           write rtl/hdc/nearhbm/ot_qwen_tp8_pv_slice_lc_gen.sv
  gen_slice_lc.py --check   fail if the committed output is stale
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SLICE = ROOT / "rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv"
PAIR = ROOT / "rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv"
OUT = ROOT / "rtl/hdc/nearhbm/ot_qwen_tp8_pv_slice_lc_gen.sv"


def edit(s, a, b):
    assert s.count(a) == 1, (a[:100], s.count(a))
    return s.replace(a, b)


def module(text, name):
    m = re.search(r"^module %s\b.*?^endmodule\n" % re.escape(name), text, re.S | re.M)
    assert m, name
    return m.group(0)


def derive():
    s = module(SLICE.read_text(), "ot_qwen_tp8_pv16_slice")
    s = edit(s, "module ot_qwen_tp8_pv16_slice(", "module ot_qwen_tp8_pv16_slice_lc #(parameter integer G=4,MUT_LC=0)(")
    s = edit(s, " input wire reduce_issue,reduce_capture,reduce_last,input wire[6:0] reduce_dst,\n",
             " input wire reduce_issue,reduce_capture,reduce_last,input wire[6:0] reduce_dst,\n"
             " input wire[G-1:0] reduce_issue_g,reduce_capture_g,   // per-lane-group copies: lane l reads copy l*G/16\n")
    s = edit(s, "  if(reduce_capture)reduce_a<=rd;\n", "")
    s = edit(s, "  ot_hdc_fp32_add_lat #(.LAT(7),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(pv[l]||reduce_issue),\n"
                "   .a(reduce_issue?reduce_a[32*l+:32]:(fp[3]?32'b0:old[2][32*l+:32])),.b(reduce_issue?rd[32*l+:32]:prod[32*l+:32]),",
             "  wire ri_l=(MUT_LC==1&&l==15)?reduce_capture_g[l*G/16]:reduce_issue_g[l*G/16];\n"
             "  always @(posedge clk)if(reduce_capture_g[l*G/16])reduce_a[32*l+:32]<=rd[32*l+:32];\n"
             "  ot_hdc_fp32_add_lat #(.LAT(7),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(pv[l]||ri_l),\n"
             "   .a(ri_l?reduce_a[32*l+:32]:(fp[3]?32'b0:old[2][32*l+:32])),.b(ri_l?rd[32*l+:32]:prod[32*l+:32]),")
    t = module(PAIR.read_text(), "ot_qwen_tp8_pv_slice_t")
    t = edit(t, "module ot_qwen_tp8_pv_slice_t #(parameter integer RESET_PIN=0)(\n"
                " input wire clk,rst_n,input wire[255:0] pv2,input wire[31:0] pe2,input wire[22:0] bc,\n",
             "module ot_qwen_tp8_pv_slice_lc_t #(parameter integer RESET_PIN=0,G=4,MUT_LC=0)(\n"
             " input wire clk,rst_n,input wire[255:0] pv2,input wire[31:0] pe2,input wire[22:0] bc,\n"
             " input wire[2*G-3:0] bcx,   // copy pins, driven from the same command bits as bc[17] (issue: bcx[G-2:0]) / bc[18]\n")
    t = edit(t, " reg[255:0] v_r;reg[31:0] e_r;reg[22:0] c_r;\n always @(posedge clk)begin v_r<=pv2;e_r<=pe2;c_r<=bc;end\n",
             " reg[255:0] v_r;reg[31:0] e_r;reg[22:0] c_r;reg[2*G-3:0] cx_r;\n"
             " always @(posedge clk)begin v_r<=pv2;e_r<=pe2;c_r<=bc;cx_r<=bcx;end\n")
    t = edit(t, " ot_qwen_tp8_pv16_slice u_slice(", " ot_qwen_tp8_pv16_slice_lc #(.G(G),.MUT_LC(MUT_LC)) u_slice(")
    t = edit(t, ".reduce_dst({4'd0,red_dst}),", ".reduce_dst({4'd0,red_dst}),.reduce_issue_g({cx_r[G-2:0],red_issue}),\n"
                "  .reduce_capture_g({cx_r[2*G-3:G-1],red_capture}),")
    hs = hashlib.sha256(SLICE.read_bytes()).hexdigest()
    hp = hashlib.sha256(PAIR.read_bytes()).hexdigest()
    return ("`timescale 1ns/1ps\n"
            "// GENERATED by results/die_kv_14_1028/pv_pair/gen_slice_lc.py (DIE-KV-14b) from\n"
            f"//   {SLICE.relative_to(ROOT)} sha256 {hs}\n//   {PAIR.relative_to(ROOT)} sha256 {hp}\n"
            "// Do not edit. Opt-in per-lane-group red_issue / red_capture copies (0 cycles); see the generator docstring.\n"
            + s + "\n" + t)


if __name__ == "__main__":
    txt = derive()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.is_file() and OUT.read_text() == txt else "STALE " + str(OUT))
    OUT.write_text(txt)
    print("wrote", OUT)
