#!/usr/bin/env python3
"""S81-VPW-XRB (OPUS-FIX-S81-LEAF-R10 11-22, COORD-approved J9 row): per-bank copies of the XR write-DATA flops in
ot_s81sl_vpw, 0 cycles.

Measured on leaf t31 (J5 224567138ab @4, post-place TT, 3_detailed_place.rpt): g_slr.g_b[0].g_r[7].hi_sw (sa_q copy) ->
wdo_q[0][114], slack -498 ps.  The two flops are 31 um apart at the VP banks (OT_VPW_BANK form, 1,447 FFs FIRM), the path is
5 gates (INV AO21 OR3 OA222 OAI21) and 17 placement buffers of ~180 um each (1,688 um of wire): the slice mux is pulled
toward the ONE shared XR data cohort (sw_d_q / hs_d_q / cw_d_q / xwd_q), which feeds both banks and so sits at either bank
or between them, and every select crosses the leaf and comes back.

XRB (opt-in by the bare-name define OT_S81SL_VP_XRB; needs XR and SLR) gives each bank its own kept copy of the write
data (sw_d 256, hs_d 256, cw_d 64, xwd 256 bits), loaded from the raw writer pins on the XR edge, so it equals the g_xr
flop in every cycle.  Bank k's slice muxes (g_slr.g_b[k]) and its x-data AND-OR (wdx[k]) read only bank k's copy, so with
the bank-affine VPW placement (s81_vpw_bank.tcl, OT_S81_VPW_BANK_AFF=1) the whole bank-k write cone is local and the
VS/port-to-bank distance is carried by the XR edge (pin -> flop, no logic).  Function and cycles are unchanged; the shared
g_xr data flops lose all loads (only the b_dec n_wdo copy, unused under SLR, still names them) and synthesis removes them,
so the net cost is one more copy of 832 data bits.  XRB 0 is the source exactly.

  python3 -I s81_vpw_xrb_overlay.py ROOT     ROOT = an S81 source tree whose ot_s81sl_vp.sv carries WRP + XR + SLR
(ot_s81sl_vpw with g_xr and g_slr), or the file itself.  Exact, counted replacements (refuses on any miss or a second
run); the file is rewritten by write-new + rename.  Every edit is inside / just before ot_s81sl_vpw, after every line of
ot_s81sl_vp, so no source position of the vp module moves.
"""
import os
import sys
from pathlib import Path

REL = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
TAG = "S81-VPW-XRB"

HEAD_A = "module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0, parameter integer SLR = XR) ("
HEAD_B = ("module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0, parameter integer SLR = XR,\n"
          "                       parameter integer XRB = `OT_S81SL_VP_XRB_DEFAULT) (")
DEFINE = f"""// {TAG} (tools/die_plan/s81_vpw_xrb_overlay.py): per-bank XR write-data copies, 0 cycles; opt-in by OT_S81SL_VP_XRB.
`ifndef OT_S81SL_VP_XRB_DEFAULT
`ifdef OT_S81SL_VP_XRB
`define OT_S81SL_VP_XRB_DEFAULT 1
`else
`define OT_S81SL_VP_XRB_DEFAULT 0
`endif
`endif
"""
SLR_ANCHOR = "    // S81-VPW-SLR: per (bank, slice) kept copies of the 14 writer-control bits"
BLOCK = f"""    // {TAG}: bank k's slice muxes and x-data AND-OR read bank k's own copy of the XR write data (see
    // tools/die_plan/s81_vpw_xrb_overlay.py).  The copies load from the raw pins on the XR edge, so they equal the g_xr flops.
    wire [255:0] sw_d_b [0:1]; wire [255:0] hs_d_b [0:1]; wire [63:0] cw_d_b [0:1]; wire [255:0] xwd_b [0:1];
    generate if (XR != 0 && SLR != 0 && XRB != 0) begin : g_xrb
        genvar kb;
        for (kb = 0; kb < 2; kb = kb + 1) begin : g_b
            (* keep *) reg [255:0] sw_d_q;
            (* keep *) reg [255:0] hs_d_q;
            (* keep *) reg [63:0] cw_d_q;
            (* keep *) reg [255:0] xwd_q;
            always @(posedge clk) begin sw_d_q <= sw_d; hs_d_q <= hs_d; cw_d_q <= cw_d; xwd_q <= xwd; end
            assign sw_d_b[kb] = sw_d_q; assign hs_d_b[kb] = hs_d_q; assign cw_d_b[kb] = cw_d_q; assign xwd_b[kb] = xwd_q;
        end
    end else begin : g_nxrb
        assign sw_d_b[0] = sw_d_i; assign sw_d_b[1] = sw_d_i; assign hs_d_b[0] = hs_d_i; assign hs_d_b[1] = hs_d_i;
        assign cw_d_b[0] = cw_d_i; assign cw_d_b[1] = cw_d_i; assign xwd_b[0] = xwd_i; assign xwd_b[1] = xwd_i;
    end endgenerate
"""
EDITS = (
    ("                wire [127:0] c0_w = {4{cw_d_i[31:0]}}, c1_w = {4{cw_d_i[63:32]}};\n",
     "                wire [127:0] c0_w = {4{cw_d_b[sb][31:0]}}, c1_w = {4{cw_d_b[sb][63:32]}};\n", "g_slr cw data"),
    ("                    s_hs ? (hi_hs ? hs_d_i[128 + SL * sr +: SL] : hs_d_i[SL * sr +: SL]) :\n",
     "                    s_hs ? (hi_hs ? hs_d_b[sb][128 + SL * sr +: SL] : hs_d_b[sb][SL * sr +: SL]) :\n", "g_slr hs data"),
    ("                    s_sw ? (hi_sw ? sw_d_i[128 + SL * sr +: SL] : sw_d_i[SL * sr +: SL]) : {SL{1'b0}};\n",
     "                    s_sw ? (hi_sw ? sw_d_b[sb][128 + SL * sr +: SL] : sw_d_b[sb][SL * sr +: SL]) : {SL{1'b0}};\n",
     "g_slr sw data"),
    ("            assign wdx[gb][SL * gr +: SL] = ({SL{xl_q[gb][gr]}} & xwd_i[SL * gr +: SL]) | "
     "({SL{xh_q[gb][gr]}} & xwd_i[128 + SL * gr +: SL]) |\n",
     "            assign wdx[gb][SL * gr +: SL] = ({SL{xl_q[gb][gr]}} & xwd_b[gb][SL * gr +: SL]) | "
     "({SL{xh_q[gb][gr]}} & xwd_b[gb][128 + SL * gr +: SL]) |\n", "wdx x data"),
)


def patch(s):
    if TAG in s:
        raise SystemExit("XRB_OVERLAY_TWICE ot_s81sl_vp.sv already carries XRB")
    for a, what in ((HEAD_A, "vpw header (WRP + XR + SLR form)"), (SLR_ANCHOR, "g_slr block (SLR overlay)"),
                    ("    generate if (XR != 0) begin : g_xr\n", "g_xr stage")) + tuple((o, w) for o, _, w in EDITS):
        if s.count(a) != 1:
            raise SystemExit(f"XRB_OVERLAY_MISS {what}: expected 1 x {a[:70]!r}, found {s.count(a)}")
    if s.index(HEAD_A) < s.rindex("module ot_s81sl_vp #("):
        raise SystemExit("XRB_OVERLAY_ORDER ot_s81sl_vpw is not after ot_s81sl_vp: source positions of vp would move")
    # the define goes right before the vpw module's own header comment block (after every line of ot_s81sl_vp)
    head = s.index(HEAD_A)
    cut = s.rfind("\nendmodule", 0, head)
    if cut < 0 or cut < s.rindex("module ot_s81sl_vp #("):
        raise SystemExit("XRB_OVERLAY_ORDER no endmodule between ot_s81sl_vp and ot_s81sl_vpw")
    cut = s.index("\n", cut + 1) + 1
    s = s[:cut] + DEFINE + s[cut:]
    s = s.replace(HEAD_A, HEAD_B).replace(SLR_ANCHOR, BLOCK + SLR_ANCHOR)
    for o, n, _ in EDITS:
        s = s.replace(o, n)
    return s


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    p = Path(argv[0])
    if p.is_dir():
        p = p / REL
    new = patch(p.read_text())
    tmp = p.with_name(p.name + ".xrb.tmp")
    tmp.write_text(new)
    os.replace(tmp, p)
    print(f"{TAG}: {p} patched (define OT_S81SL_VP_XRB, {len(EDITS)} data reads per bank)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
