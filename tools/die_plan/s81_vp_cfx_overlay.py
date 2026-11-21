#!/usr/bin/env python3
"""S81-VP-CFX overlay (FABLE-FIX-S81-LEAF 11-20): the CFX form of main e828eac088 on an S81 source TREE whose ot_s81sl_vp.sv
carries the tree overlays (WRP / XR / DSR / CFR 1), where the main commit's diff does not apply (3 of 6 hunks miss).

Measured again on leaf t39 (b05c CTS DB under the J5 SDC, TT, post-hook): g_u_lf1_u_vp_driver_dodd_q -> vp_cf native_memory,
193 failing ends, worst -177.6 ps, 8.0 of the 14.2 ns setup TNS: the q0 / q1 row mux (one dodd flop, 128 selects) and about
300 um of wire into the 640 cf flops at the group HI stations, captured on clk_t6.  CFX writes cf register to register.

Opt-in by the bare-name define OT_S81SL_VP_CFX (parameter CFX).  CFX 0 is the tree source exactly (g_ncfx is plain wires).
With CFX 1: cf is written one edge later from yrow_d[0] under the row select one edge later; the POST lanes issue one edge
later (lane_v, ly one stage deeper, lr from hq held one edge); the write-back tag waits one edge more.  Contract: the hc_post
write-back (hw_v / hw_j / hw_hf / hw_d of a lane result) exactly one clk later, every other output in the same cycle.
Bind latency: vp hc_post write-back + 1 (compiler pin-cycle table).

  python3 -I s81_vp_cfx_overlay.py ROOT     ROOT = an S81 source tree (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv) or the file.
Exact, counted replacements; refuses on any miss, on a second run and on a file that already has CFX.  The file is rewritten
by write-new + rename.
"""
import sys
from pathlib import Path

REL = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"

HEAD = """// CFX (FABLE-FIX-S81-LEAF 11-19 / 11-20 overlay, r713 close by construction; S81 leaf vp-glue TT class): ONE more cycle on the
// hc_post POST path so the coefficient rows are written register to register.  With CFX = 1:
//   cf is written one edge later, from yrow_d[0] (= q1r one edge later, a flop beside the store) under cfs one edge later;
//   the POST lanes issue one edge later (lane_v, ly from the y-row line one stage deeper, lr from hq held one edge);
//   the write-back tag waits one edge more.  hr (the vn read request) and the pin-time fault terms keep their cycle.
// Contract: ot_s81sl_vp #(.CFX(1)) == ot_s81sl_vp #(.CFX(0)) with the hc_post write-back (hw_v / hw_j / hw_hf / hw_d of a lane
// result) exactly one clk later and every other output in the same cycle.  The parent pays the cycle on the POST write-back.
`ifdef OT_S81SL_VP_CFX
`define OT_S81SL_VP_CFX_DEFAULT 1
`else
`define OT_S81SL_VP_CFX_DEFAULT 0
`endif
"""

G_CFX = """    initial if (CFX != 0 && CFX != 1) $fatal(1, "ot_s81sl_vp: CFX must be 0 or 1");
    wire [255:0] hqd_l;                                       // the h half row the lanes capture (CFX: held one edge)
`ifndef OT_S81SL_VP_MUT_POSTLAST
    generate if (CFX != 0) begin : g_cfx
        reg [4:0] cfs_x; reg [255:0] hqd_x;
        always @(posedge clk or negedge rs_s) if (!rs_s) cfs_x <= 5'd0; else cfs_x <= cfs;
        always @(posedge clk) hqd_x <= hqd_c;
        assign cfw = cfs_x; assign cfd = yrow_d[0];
`ifndef OT_S81SL_VP_MUT_CFXHQ
        assign hqd_l = hqd_x;
`else
        assign hqd_l = hqd_c;                  // bench mutant: the h half row is not held with the later lane issue
`endif
    end else begin : g_ncfx
        assign cfw = cfs; assign cfd = q1r; assign hqd_l = hqd_c;
    end endgenerate
`else
    assign hqd_l = hqd_c;
`endif
"""

# (old, new, count)
EDITS = [
    ("module ot_s81sl_vp #(\n", HEAD + "module ot_s81sl_vp #(\n", 1),
    ("    parameter integer SR = `OT_S81SL_VP_SR_DEFAULT,",
     "    parameter integer CFX = `OT_S81SL_VP_CFX_DEFAULT,  // +1 cycle on the hc_post POST path, cf written register to register (see CFX above)\n"
     "    parameter integer SR = `OT_S81SL_VP_SR_DEFAULT,", 1),
    ("    always @(posedge clk)\n"
     "        for (int i = 0; i < 4; i = i + 1) begin\n"
     "            if (cfs[0]) cf[16 + i] <= q1r[32 * i +: 32];\n"
     "            for (int j = 1; j < 5; j = j + 1) if (cfs[j]) cf[4 * (j - 1) + i] <= q1r[32 * i +: 32];\n",
     "    wire [4:0] cfw; wire [127:0] cfd;                         // CFX: the select and the row one edge later (g_cfx below)\n"
     "    always @(posedge clk)\n"
     "        for (int i = 0; i < 4; i = i + 1) begin\n"
     "            if (cfw[0]) cf[16 + i] <= cfd[32 * i +: 32];\n"
     "            for (int j = 1; j < 5; j = j + 1) if (cfw[j]) cf[4 * (j - 1) + i] <= cfd[32 * i +: 32];\n", 1),
    ("    reg [127:0] yrow_d [0:YA]; reg [YA:0] ydv;\n",
     "    localparam integer YL = YA + (CFX != 0 ? 1 : 0);         // CFX: the lanes issue one edge later (hq still arrives with ydv[YA])\n"
     "    reg [127:0] yrow_d [0:YL]; reg [YL:0] ydv;\n", 1),
    ("    always @(posedge clk or negedge rs_p) if (!rs_p) ydv <= {(YA + 1){1'b0}};\n"
     "        else ydv <= {ydv[YA - 1:0], dv && dop == OP_POST && dsi >= 8'd5};\n",
     "    always @(posedge clk or negedge rs_p) if (!rs_p) ydv <= {(YL + 1){1'b0}};\n"
     "        else ydv <= {ydv[YL - 1:0], dv && dop == OP_POST && dsi >= 8'd5};\n", 1),
    ("        yrow_d[0] <= q1r; for (yj = 1; yj <= YA; yj = yj + 1) yrow_d[yj] <= yrow_d[yj - 1];\n    end\n",
     "        yrow_d[0] <= q1r; for (yj = 1; yj <= YL; yj = yj + 1) yrow_d[yj] <= yrow_d[yj - 1];\n    end\n" + G_CFX, 1),
    ("else lane_v <= ydv[YA];\n", "else lane_v <= ydv[YL];\n", 1),
    ("                ly[4 * k + i] <= yrow_d[YA][32 * i +: 32];\n", "                ly[4 * k + i] <= yrow_d[YL][32 * i +: 32];\n", 1),
] + [(f"                lr[4 * k + i][{n}] <= {{hqd_c[(4 * {n} + i) * 16 +: 16], 16'd0}};\n",
      f"                lr[4 * k + i][{n}] <= {{hqd_l[(4 * {n} + i) * 16 +: 16], 16'd0}};\n", 1) for n in range(4)]

# the write-back tag delay: the tree form names the HI depth CS_HI_E (XR), main CS_HI_D
TAG = [(f"D(HPL + HQX + {hi} + CS_HO_D + SRO)) u_wi (", f"D(HPL + HQX + {hi} + CS_HO_D + SRO + (CFX != 0 ? 1 : 0))) u_wi (")
       for hi in ("CS_HI_E", "CS_HI_D")]


def overlay(text):
    """text of ot_s81sl_vp.sv -> text with the CFX form; ValueError on any miss / repeat."""
    if "OT_S81SL_VP_CFX" in text or "g_cfx" in text:
        raise ValueError("s81_vp_cfx_overlay: the file already carries CFX")
    for old, new, n in EDITS:
        if text.count(old) != n:
            raise ValueError(f"s81_vp_cfx_overlay: expected {n} x {old.splitlines()[0][:80]!r}, found {text.count(old)}")
        text = text.replace(old, new)
    hits = [(o, w) for o, w in TAG if text.count(o) == 1]
    if len(hits) != 1:
        raise ValueError(f"s81_vp_cfx_overlay: write-back tag delay u_wi: {len(hits)} forms match (need 1)")
    text = text.replace(*hits[0])
    return text


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    p = Path(argv[1])
    f = p if p.is_file() else p / REL
    new = overlay(f.read_text())
    tmp = f.with_name(f.name + ".cfx_new")
    tmp.write_text(new)
    tmp.replace(f)
    print(f"s81_vp_cfx_overlay: {f} ({len(EDITS) + 1} edits)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
