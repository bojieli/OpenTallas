#!/usr/bin/env python3
"""S81-KITS-RTLC 10-24 ruling (b): drop bksel_c's 146 constant-zero vd bits (vd[513], vd[501:357]) on the shared bk_g
master.  Packed vd (368) = {vd[512:502], vd[356:0]}.  dsdv_bk_g VD_PK = 1 (default, the S81 die master) takes the packed
bus; VD_PK = 0 keeps the legacy 514-bit bus for the plana / bk_col parents (their vd producers are not dsfd_selt_c)."""
import re, sys
R = sys.argv[1] + "/rtl/dsrom_sys/s81_dv/unit/bk/"
def sub(f, a, b, n=1):
    s = open(R + f).read(); c = s.count(a)
    assert c == n, (f, a[:60], c)
    open(R + f, "w").write(s.replace(a, b))
# bk_g
sub("dsdv_bk_g.sv", "    parameter integer BK_DRAIN_SINK = 0\n) (",
    "    parameter integer BK_DRAIN_SINK = 0,\n"
    "    // S81-KITS-RTLC 10-24 (ruling b): VD_PK = 1 (default; the S81 die master under dsdv_bk_sel): vd is the PACKED\n"
    "    // dsfd_selt_c word {vd[512:502], vd[356:0]} (368 bits); vd[513] (kind msb) and vd[501:357] are constant 0 at\n"
    "    // the producer (ot_s81ph_sel_tile.sv o_d kinds 3/4/5/7) and are not pins.  VD_PK = 0: legacy 514-bit vd.\n"
    "    parameter integer VD_PK = 1\n) (")
sub("dsdv_bk_g.sv", "    input  wire [513:0]      vd,          // the merger / select control's vd {data 512, valid, rst}",
    "    input  wire [(VD_PK ? 367 : 513):0] vd,   // the merger / select control's vd {data 512, valid, rst} (VD_PK: packed)")
sub("dsdv_bk_g.sv", "    always @(posedge clk[0]) vdd <= vd[513:2];",
    "    wire [513:0] vdu;                                  // vd unpacked (VD_PK: dropped constant bits are 0)\n"
    "    generate if (VD_PK) begin : g_vpk assign vdu = {1'b0, vd[367:357], 145'd0, vd[356:0]}; end\n"
    "    else begin : g_vfl assign vdu = vd; end endgenerate\n"
    "    always @(posedge clk[0]) vdd <= vdu[513:2];")
sub("dsdv_bk_g.sv", "vdv <= vd[1];", "vdv <= vdu[1];")
# bksel_c
sub("dsdv_bksel_c.sv", "    output wire [513:0]     vd\n);",
    "    output wire [367:0]     vd    // S81-KITS-RTLC 10-24: packed {vd[512:502], vd[356:0]} (dsdv_bk_g VD_PK)\n);")
sub("dsdv_bksel_c.sv", "wire vf_unused;", "wire vf_unused; wire [513:0] vdw;")
sub("dsdv_bksel_c.sv", ".vd(vd), .vf(vf_unused));",
    ".vd(vdw), .vf(vf_unused));\n"
    "    assign vd = {vdw[512:502], vdw[356:0]};             // vdw[513], vdw[501:357]: constant 0 (dropped pins)")
# parents with dsdv_bksel_c -> packed net
sub("dsdv_bk_sel.sv", "wire [514:0] l0, l1, l2, l3; wire [513:0] vd;", "wire [514:0] l0, l1, l2, l3; wire [367:0] vd;   // packed (bk_g VD_PK)")
sub("dsdv_bk_sel_x.sv", "    wire [513:0] vd;", "    wire [367:0] vd;   // packed (bk_g VD_PK)")
sub("lp/dsdv_bk_sel_x_lp.sv", "    wire [513:0] vd;", "    wire [367:0] vd;   // packed (bk_g VD_PK)")
# legacy producers -> VD_PK 0
sub("dsdv_bk_col.sv", "    dsdv_bk_g u_g (", "    dsdv_bk_g #(.VD_PK(0)) u_g (")
sub("dsdv_bk_col.sv", "    dsdv_bk_g #(.V(V), .MUT(MUT)) u_g (", "    dsdv_bk_g #(.V(V), .MUT(MUT), .VD_PK(0)) u_g (")
sub("plana/dsdv_bk_sel_pa.sv", " dsdv_bk_g u_g(", " dsdv_bk_g #(.VD_PK(0)) u_g(")
for f in ("plana/lp/dsdv_bk_sel_pa_lp.sv", "plana/n32/dsdv_bk_sel_pa_n32_lp.sv", "plana/lp/tb_dsdv_bk_sel_pa_lp.sv"):
    sub(f, "    dsdv_bk_g u_g (", "    dsdv_bk_g #(.VD_PK(0)) u_g (")
print("ok")
