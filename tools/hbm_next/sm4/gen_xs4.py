#!/usr/bin/env python3
"""HBM-NEXT-SM4 (10-19): generate rtl/hbm_next/sm/hnx_xs4.sv, the SHARED P-lane x store (PROG lever (a)), as a mechanical
COPY of the closed d4g x store (ot_hbm_accel_smh_xs + ot_hbm_accel_smh_leaf, OT_SMH_HIER form, from
rtl/hbm_accel/sm/ot_hbm_accel_smh.sv) with the lane edits below.  The source file is never modified.

  python3 tools/hbm_next/sm4/gen_xs4.py                      -> rtl/hbm_next/sm/hnx_xs4.sv (P = 4 default, module hnx_xs4)
  python3 tools/hbm_next/sm4/gen_xs4.py --p 3 --name hnx_xs3  -> rtl/hbm_next/sm/hnx_xs3.sv (P = 3 default, module hnx_xs3):
      the PRODUCTION store of the P = 3 SM tile (owner 10-19 P3+(a)); the same generator and edits, only the default P and
      the module names differ, so the hard child elaborates WITHOUT a parameter override (no $paramod rename in the kit).
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv"


def grab(text, start):
    i = text.index(start)
    j = text.index("\nendmodule", i) + len("\nendmodule")
    return text[i:j]


def rep(s, a, b, n=1):
    assert s.count(a) == n, (a, s.count(a))
    return s.replace(a, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p", type=int, default=4)
    ap.add_argument("--name", default="hnx_xs4")
    a = ap.parse_args()
    t = SRC.read_text()
    leaf = grab(t, "module ot_hbm_accel_smh_leaf #(")
    xs = grab(t, "module ot_hbm_accel_smh_xs #(")
    s = leaf
    s = rep(s, "module ot_hbm_accel_smh_leaf #(", "module hnx_xs4_leaf #(\n    parameter integer P = 4,\n    parameter integer MUT = 0,")
    s = rep(s, "    input  wire [2047:0]            b_d,",
            "    input  wire [2047:0]            b_d,\n    input  wire [P-1:0]             b_wl,           // HNX: lane write mask (aligned with b_en)")
    s = rep(s, "    output wire [LBS*266+LSB*16-1:0] o_ix\n`else",
            "    output wire [P*(LBS*266+LSB*16)-1:0] o_ix,     // HNX: one x word per lane\n"
            "    // HNX-XS4 (face split 10-19): W-face copies of the BF16 column operand control + shared BF16 weight (kept registers)\n"
            "    output wire                     o_iv_fw,\n    output wire                     o_ifirst_w,\n"
            "    output wire                     o_ilast_w,\n    output wire [TAGW-1:0]          o_itag_w,\n"
            "    output wire [LSB*16-1:0]        o_iwf_w\n`else")
    s = rep(s, "    reg  [XW-1:0]  wa0;", "    reg  [XW-1:0]  wa0;\n    reg  [P-1:0]   wl0;")
    s = rep(s, "        wa0  <= b_a;", "        wa0  <= b_a;\n        wl0  <= b_wl;")
    s = rep(s, "    reg  [XW-1:0]  wa1;", "    reg  [XW-1:0]  wa1;\n    reg  [P-1:0]   wl1;")
    s = rep(s, "        wa1  <= wa0;", "        wa1  <= wa0;\n        wl1  <= wl0;")
    s = rep(s, "    reg  [XW-1:0]  wa_q;", "    reg  [XW-1:0]  wa_q;\n    reg  [P-1:0]   wl_q;")
    s = rep(s, "    always @(posedge clk) begin wa_q <= wa1; wd_q <= wd_n; wm_q <= wm_n; end",
            "    always @(posedge clk) begin wa_q <= wa1; wl_q <= wl1; wd_q <= wd_n; wm_q <= wm_n; end")
    i = s.index("    // ---- x store: NXL macros, read from the landed address ----")
    j = s.index("    // ---- E4 ----")
    blk = s[i:j]
    blk = rep(blk, "    wire [NXL*256-1:0] xrd;\n",
              "    // HNX-XS4: P lane copies of the NXL macros (one SRAM set per lane, written under the lane mask, read at the SAME\n"
              "    // address in the same cycle); every lane copy keeps its own kept pin-register set at its macros (as d4g per macro)\n"
              "    wire [P*NXL*256-1:0] xrd;\n    genvar ln;\n    generate for (ln = 0; ln < P; ln = ln + 1) begin : g_ln\n"
              "    localparam integer WLB = (MUT == 1 && ln == P - 1 && P > 1) ? 0 : ln;   // bench mutant: lane alias\n")
    blk = rep(blk, "    generate for (m = 0; m < NXL; m = m + 1) begin : g_xm", "    for (m = 0; m < NXL; m = m + 1) begin : g_xm")
    blk = rep(blk, ".d(wce_q[m]), .q(wce2));", ".d(wce_q[m] && wl_q[WLB]), .q(wce2));")
    blk = rep(blk, ".rd_out(xrd[256*m +: 256]),", ".rd_out(xrd[(ln*NXL+m)*256 +: 256]),")
    k = blk.rindex("    end endgenerate\n")
    blk = blk[:k] + "    end\n    end endgenerate\n" + blk[k + len("    end endgenerate\n"):]
    s = s[:i] + blk + s[j:]
    s = rep(s, "    reg [SLW-1:0]    ix;", "    reg [P*SLW-1:0]  ix;\n    integer lp;")
    s = rep(s, "        ix <= xrd[SLW-1:0];", "        for (lp = 0; lp < P; lp = lp + 1) ix[lp*SLW +: SLW] <= xrd[lp*NXL*256 +: SLW];")
    s = rep(s, "    assign o_itag = itag; assign o_iw = iw; assign o_ix = ix;\n",
            "    assign o_itag = itag; assign o_iw = iw; assign o_ix = ix;\n"
            "    // HNX-XS4 face split: the BF16 lanes on the W face take their own copy of the i stage (same D, same cycle; kept\n"
            "    // so synthesis cannot merge them back: one register set per face, no 500-um fan-out).  MUT 4 (bench only):\n"
            "    // W-face weight sign bits inverted.\n"
            "    (* keep *) reg iv_fw;\n    (* keep *) reg ifirst_w, ilast_w;\n    (* keep *) reg [TAGW-1:0] itag_w;\n"
            "    (* keep *) reg [LSB*16-1:0] iwf_w;\n"
            "    always @(posedge clk or negedge rst_n)\n        if (!rst_n) iv_fw <= 1'b0;\n        else iv_fw <= c3bv[0];\n"
            "    always @(posedge clk) begin\n        ifirst_w <= c3bd[CW-3]; ilast_w <= c3bd[CW-4]; itag_w <= c3bd[TAGW-1:0];\n"
            "        iwf_w <= w3b[LBS*266 +: LSB*16] ^ ((MUT == 4) ? {LSB{16'h8000}} : {(LSB*16){1'b0}});\n    end\n"
            "    assign o_iv_fw = iv_fw; assign o_ifirst_w = ifirst_w; assign o_ilast_w = ilast_w; assign o_itag_w = itag_w;\n"
            "    assign o_iwf_w = iwf_w;\n")
    leaf = s
    s = xs
    s = rep(s, "module ot_hbm_accel_smh_xs #(parameter integer TAGW = 16, parameter integer NBEAT = 13) (",
            "module hnx_xs4 #(parameter integer TAGW = 16, parameter integer NBEAT = 13, parameter integer P = 4, parameter integer MUT = 0) (")
    s = rep(s, "input wire [NBEAT-1:0] ohl1,",
            "input wire [NBEAT-1:0] ohl1,\n    input  wire [P-1:0] wl,                       // HNX: lane write mask of this x-write beat")
    s = rep(s, "output wire [787:0] o_iw, output wire [787:0] o_ix,",
            "// HNX-XS4 face split (10-19): N = block-dot operands (o_iwb shared, o_ixb per lane), W / E = BF16 operands\n"
            "    // (o_iwf_* shared weight copy per face, o_ixf_w lanes 0..PW-1, o_ixf_e lanes PW..P-1, PW = (P+1)/2)\n"
            "    output wire [531:0] o_iwb, output wire [P*532-1:0] o_ixb,\n"
            "    output wire [255:0] o_iwf_e, output wire [((P-(P+1)/2) > 0 ? (P-(P+1)/2) : 1)*256-1:0] o_ixf_e,\n"
            "    output wire [255:0] o_iwf_w, output wire [((P+1)/2)*256-1:0] o_ixf_w,\n"
            "    output wire o_iv_fw, output wire o_ifirst_w, output wire o_ilast_w, output wire [TAGW-1:0] o_itag_w,")
    s = rep(s, "    wire [NBEAT-1:0] ohl;\n",
            "    wire [NBEAT-1:0] ohl;\n    wire [P-1:0] wl1_n, wlq;\n    ot_hdly #(.W(P), .N(2)) u_hdly_wl (.a(wl), .y(wl1_n));\n"
            "    ot_hbm_accel_smh_kreg #(.W(P)) u_wl2 (.clk(clk), .rst_n(rl_n), .en(1'b1), .d(wl1_n), .q(wlq));\n")
    s = rep(s, "    ot_hbm_accel_smh_leaf #(.TAGW(TAGW), .NBEAT(NBEAT)) u_leaf (",
            "    hnx_xs4_leaf #(.TAGW(TAGW), .NBEAT(NBEAT), .P(P), .MUT(MUT)) u_leaf (")
    s = rep(s, ".b_d(bk[2047:0]), .ohr(ohr),", ".b_d(bk[2047:0]), .b_wl(wlq), .ohr(ohr),")
    s = rep(s, "        .o_iw(o_iw), .o_ix(o_ix));",
            "        .o_iw(iw_a), .o_ix(ix_a), .o_iv_fw(o_iv_fw), .o_ifirst_w(o_ifirst_w), .o_ilast_w(o_ilast_w),\n"
            "        .o_itag_w(o_itag_w), .o_iwf_w(o_iwf_w));\n"
            "    // face split of the leaf's i stage (wires only)\n"
            "    localparam integer PW = (P + 1) / 2;\n"
            "    assign o_iwb = iw_a[531:0]; assign o_iwf_e = iw_a[787:532];\n"
            "    genvar lq;\n    generate for (lq = 0; lq < P; lq = lq + 1) begin : g_fs\n"
            "        assign o_ixb[lq*532 +: 532] = ix_a[lq*788 +: 532];\n"
            "        if (lq < PW) begin : g_w assign o_ixf_w[lq*256 +: 256] = ix_a[lq*788+532 +: 256]; end\n"
            "        else begin : g_e assign o_ixf_e[(lq-PW)*256 +: 256] = ix_a[lq*788+532 +: 256]; end\n"
            "    end\n    if (P == 1) begin : g_e0 assign o_ixf_e = 256'd0; end\n    endgenerate")
    s = rep(s, "    hnx_xs4_leaf #(", "    wire [787:0] iw_a; wire [P*788-1:0] ix_a;\n    hnx_xs4_leaf #(")
    hdr = (
        "// GENERATED by tools/hbm_next/sm4/gen_xs4.py -- do not edit.\n"
        "// HBM-NEXT-SM4 (10-19, PROG decision lever (a)): hnx_xs4 = the SHARED P-lane x store of the P = 4 SM leaf: a COPY of the\n"
        "// closed d4g x store ot_hbm_accel_smh_xs + its leaf front (rtl/hbm_accel/sm/ot_hbm_accel_smh.sv, OT_SMH_HIER form) with\n"
        "// P lane copies of its NXL 128x256 macros.  Shared (paid once): row-bundle / x-write landing pin flops, strap fan-out\n"
        "// tree, 3-stage write rotation, row pipeline, weight operand register o_iw.  Per lane: the macros, their kept pin\n"
        "// registers, the x operand register (o_ix = P x 788 b).  A beat writes the lanes in its mask wl (riding the existing\n"
        "// write stages); all lanes read the same address in the same cycle: cycle timing identical to the d4g xs.\n"
        "// MUT 1 (bench only): lane P-1 takes lane 0's write mask.\n`timescale 1ns/1ps\n")
    out = hdr + leaf + "\n\n" + s + "\n"
    if a.name != "hnx_xs4" or a.p != 4:
        out = out.replace("parameter integer P = 4", f"parameter integer P = {a.p}")
        out = out.replace("hnx_xs4_leaf", f"{a.name}_leaf").replace("module hnx_xs4 #(", f"module {a.name} #(")
        out = out.replace("// GENERATED by tools/hbm_next/sm4/gen_xs4.py -- do not edit.\n",
                          f"// GENERATED by tools/hbm_next/sm4/gen_xs4.py --p {a.p} --name {a.name} -- do not edit.\n"
                          f"// {a.name}: the same shared x store with P = {a.p} lanes by default (owner 10-19 P3+(a) production store).\n")
    o = ROOT / f"rtl/hbm_next/sm/{a.name}.sv"
    o.write_text(out)
    print(o)


if __name__ == "__main__":
    main()
