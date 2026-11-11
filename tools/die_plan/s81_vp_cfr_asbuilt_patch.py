"""TYPE-SAFE-5 11-10 (v2, no source position moves): VP CFR form on the src_28fc7 S81 elaboration base.

CFR 0 must elaborate byte-identically (COORD 11-10): every addition sits at the END of an existing line, and the
original cf write block keeps every token at its own line and column.  It is wrapped by a generate-if whose opening
is appended to the line before it and whose else branch (the CFR form) is appended to its last line.
  patch28b.py ROOT [--die]     (--die also sets LF_VP_CFR on u_s_3S = leaf__t35 in die_b178.v)
"""
import sys
from pathlib import Path

root = Path(sys.argv[1]); D = root / "rtl/dsrom_sys/s81_dv/slice"


def edit(f, pairs):
    p = Path(f); s = p.read_text(); n0 = s.count("\n")
    for a, b in pairs:
        assert s.count(a) == 1, (str(f), a[:90], s.count(a)); s = s.replace(a, b)
    assert s.count("\n") == n0, f"{f}: line count moved"
    if p.is_symlink() or p.stat().st_nlink > 1:
        p.unlink()                                   # never write through a hard link / symlink into a shared tree
    p.write_text(s); print("ok", f)


CFSB = ("reg [4:0] cfs_r; always @(posedge clk or negedge rs_s) if (!rs_s) cfs_r <= 5'd0; "
        "else for (int j = 0; j < 5; j = j + 1) cfs_r[j] <= dv1 && dop1 == OP_POST && dsi1 == j; always @(posedge clk) "
        "for (int i = 0; i < 4; i = i + 1) begin if (cfs_r[0]) cf[16 + i] <= q1r[32 * i +: 32]; for (int j = 1; j < 5; j = j + 1) "
        "if (cfs_r[j]) cf[4 * (j - 1) + i] <= q1r[32 * i +: 32]; end")
CMT = ("// CFR (TYPE-SAFE-5 11-10): the cf row select decoded one edge early from the dv1 stage into 5 flops, so dv / dop / "
       "dsi do not drive the 640-bit write decode; cfs_r(t) = f(dv1, dop1, dsi1)(t-1) = f(dv, dop, dsi)(t): 0 cycles. "
       "CFR 0 keeps the block above at its own source positions, so it elaborates byte-identically")
edit(D / "ot_s81sl_vp.sv", [
    ("    parameter integer HQX = 0\n) (\n",
     "    parameter integer HQX = 0, parameter integer CFR = 0  // CFR: see g_cfw1 (0 cycles; default 0 = this netlist)\n) (\n"),
    ("    reg [31:0] yv [0:3];\n    always @(posedge clk)\n        if (dv && dop == OP_POST && dsi < 8'd5)\n",
     "    reg [31:0] yv [0:3]; generate if (CFR == 0) begin : g_cfw0\n    always @(posedge clk)\n"
     "        if (dv && dop == OP_POST && dsi < 8'd5)\n"),
    ("   // bench mutant: the old order (comb rows a0..a0+3, post a0+4)\n`endif\n            end\n",
     "   // bench mutant: the old order (comb rows a0..a0+3, post a0+4)\n`endif\n            end end else begin : g_cfw1 "
     + CFSB + " end endgenerate  " + CMT + "\n"),
])
SL0 = ("    parameter integer CS_VSP_D = 0   // vs (KV) -> vp: x_rv / x_ra, x_wv / x_wa / x_wm / x_wd          (u_cst_vsp)\n",
       "    parameter integer CS_VSP_D = 0, parameter integer VP_CFR = 0   // vs (KV) -> vp: x_rv / x_ra, x_wv / x_wa / x_wm / "
       "x_wd          (u_cst_vsp); VP_CFR: u_vp.CFR (0 cycles)\n")
SL1 = ("                  .HQX(CS_VNI_D + CS_VNO_D)) u_vp (\n", "                  .HQX(CS_VNI_D + CS_VNO_D), .CFR(VP_CFR)) u_vp (\n")
for sl in (D / "ot_s81sl_slice.sv", root / "physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice.sv"):
    edit(sl, [SL0, SL1])
W3 = D / "cap_end/ot_s81sl_slice_w3.sv"; s = W3.read_text()
if "LF_CS_VSP_D = 20'd0  //" in s:        # main (DIE-S81-70 forwarding present)
    p1 = ("parameter [19:0] LF_CS_VSP_D = 20'd0  //", "parameter [19:0] LF_CS_VSP_D = 20'd0, parameter [4:0] LF_VP_CFR = 5'd0  //")
    p2 = (".CS_VSP_D(LF_CS_VSP_D[4 * k +: 4])", ".CS_VSP_D(LF_CS_VSP_D[4 * k +: 4]), .VP_CFR(LF_VP_CFR[k])")
else:                                     # src_28fc7 base
    p1 = ("    parameter integer VS_MUT = 0     // bench negative controls only (ot_s81sl_vs MUT through the leaves); 0 in every build\n",
          "    parameter integer VS_MUT = 0, parameter [4:0] LF_VP_CFR = 5'd0     // bench negative controls only (ot_s81sl_vs MUT "
          "through the leaves); 0 in every build; LF_VP_CFR[k]: leaf k u_vp.CFR (TYPE-SAFE-5 11-10, 0 cycles)\n")
    p2 = (".KV_HARD_RQ(KV_HARD_RQ)) u_lf (", ".KV_HARD_RQ(KV_HARD_RQ), .VP_CFR(LF_VP_CFR[k])) u_lf (")
edit(W3, [p1, p2,
    ("    parameter integer VQ_XMEM = 2,\n    parameter integer VS_MUT = 0\n) (\n",
     "    parameter integer VQ_XMEM = 2,\n    parameter integer VS_MUT = 0, parameter [4:0] LF_VP_CFR = 5'd0  // LF_VP_CFR[k]: leaf k "
     "u_vp.CFR (TYPE-SAFE-5 11-10, 0 cycles)\n) (\n"),
    ("ot_s81sl_slice_w3 #(.HB(HB), .DL(DL), .DR(DR), .DX(DX), .VQ_XMEM(VQ_XMEM), .VS_MUT(VS_MUT)) u_sl (",
     "ot_s81sl_slice_w3 #(.HB(HB), .DL(DL), .DR(DR), .DX(DX), .VQ_XMEM(VQ_XMEM), .VS_MUT(VS_MUT), .LF_VP_CFR(LF_VP_CFR)) u_sl ("),
])
if len(sys.argv) > 2 and sys.argv[2] == "--die":
    edit(root / "physical/die_plan/s81/bind/inputs/die_b178.v",
         [("  ot_s81sl_slice_iq_w3 #(.HB(1)) u_s_3S (", "  ot_s81sl_slice_iq_w3 #(.HB(1), .LF_VP_CFR(5'b10000)) u_s_3S (")])
