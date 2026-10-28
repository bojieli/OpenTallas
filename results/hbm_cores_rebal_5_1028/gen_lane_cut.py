#!/usr/bin/env python3
"""HBM-CORES-REBAL-5 (2026-10-28): per-lane connectivity cut of hnx_rp3lp3h_n/_s (flat 765-806k > 400k cap).

Verbatim text transform of hnx_rp4lp4_leaf_selfcontained.sv (no pinned file edited):
  * the body of hnx_rp4lp4_lfx's g_ln generate loop (XREL stations + u_bdc + u_tcc + gather registers) becomes ONE
    module hnx_lane_x (no parameters -> one master, 3 replicas per half, the same master in N and S);
  * the lane-side face selection (p < PW ? W : E) stays in the parent as constant-select wires, so every replica is
    byte-identical; the cut nets are exactly the existing lane inputs (all land on the lane's XREL station flops) and
    the 50-bit registered gather output g_p[p] (gv_q/gf_q/gy_q/gt_q) -> registered both sides, no logic moved across.
Usage: gen_lane_cut.py SRC_LEAF OUT_LEAF
"""
import re
import sys

BODY_START = "        wire r_bdc = rr[1 + 4*p], r_tcc = rr[2 + 4*p], r_g = rr[3 + 4*p], r_x = rr[4 + 4*p];\n"
SEL_START = "        // BF16 operands from the x store face of this lane's side (W lanes < PW, E lanes >= PW)\n"
SEL_END = "        always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xf_v <= 0; else xf_v <= sv_f;\n"
BODY_END = "        assign g_p[p*50 +: 50] = {gv, gf, gy, gt};\n    end endgenerate\n"


def one(t, s):
    assert t.count(s) == 1, (s[:60], t.count(s))
    return t.index(s)


def main(src, out):
    t = open(src).read()
    m = re.search(r"(?ms)^module hnx_rp4lp4_lfx\b.*?^endmodule\n", t)
    lfx = m.group(0)
    loop = lfx.index("    generate for (p = 0; p < P; p = p + 1) begin : g_ln\n")
    b0 = one(lfx, BODY_START)
    assert b0 > loop
    s0, s1 = one(lfx, SEL_START), one(lfx, SEL_END)
    e0 = one(lfx, BODY_END)
    stations = lfx[b0 + len(BODY_START):s0]          # XREL station regs (xb_v + regs + always)
    sel = lfx[s0:s1]                                 # face selection (stays in the parent)
    rest = lfx[s1:e0]                                # xf_v, station loads, bdc, tcc, gather regs
    # child: identical statements; the selected face nets are ports of the same names
    child = (
        "// HBM-CORES-REBAL-5: one lane of hnx_rp4lp4_lfx (P = 3, TAGW 16, LBS 2, LSB 16), verbatim g_ln body.\n"
        "module hnx_lane_x (\n"
        "    input wire clk, input wire r_bdc, input wire r_tcc, input wire r_g, input wire r_x,\n"
        "    input wire iv_b, input wire ifirst, input wire ilast, input wire ifp4, input wire [15:0] itag,\n"
        "    input wire [531:0] iwb, input wire [531:0] ixb_p,\n"
        "    input wire sv_f, input wire sfirst, input wire slast, input wire [15:0] stag,\n"
        "    input wire [255:0] swf, input wire [255:0] sxf,\n"
        "    output wire [49:0] g\n);\n"
        "    localparam integer TAGW = 16, LBS = 2, LSB = 16;\n"
        + stations.replace("xb_x <= ixb[p*LBS*266 +: LBS*266];", "xb_x <= ixb_p;")
        + rest.replace("xb_x <= ixb[p*LBS*266 +: LBS*266];", "xb_x <= ixb_p;")
        + "        assign g = {gv, gf, gy, gt};\nendmodule\n")
    assert "ixb[" not in child and "[p" not in child and "(p " not in child, "lane index leaked into the child"
    child = child.replace("\n        ", "\n    ")
    inst = (
        "        hnx_lane_x u_lane (.clk(clk), .r_bdc(rr[1 + 4*p]), .r_tcc(rr[2 + 4*p]), .r_g(rr[3 + 4*p]), .r_x(rr[4 + 4*p]),\n"
        "            .iv_b(iv_b), .ifirst(ifirst), .ilast(ilast), .ifp4(ifp4), .itag(itag), .iwb(iwb),\n"
        "            .ixb_p(ixb[p*LBS*266 +: LBS*266]), .sv_f(sv_f), .sfirst(sfirst), .slast(slast), .stag(stag),\n"
        "            .swf(swf), .sxf(sxf), .g(g_p[p*50 +: 50]));\n    end endgenerate\n")
    assert P_OK(lfx)
    new_lfx = lfx[:b0] + sel + inst + lfx[e0 + len(BODY_END):]
    t = t.replace(lfx, new_lfx + "\n" + child)
    open(out, "w").write("// HBM-CORES-REBAL-5 lane cut of " + src.split("/")[-1] + " (gen_lane_cut.py)\n" + t)


def P_OK(lfx):
    # the cut assumes the production widths (TAGW 16, LBS 2, LSB 16) used by the child ports
    return ("parameter integer TAGW = 16, parameter integer LBS = 2, parameter integer LSB = 16" in lfx)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
