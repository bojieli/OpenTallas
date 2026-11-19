#!/usr/bin/env python3
"""S81-VPW-SLR (FABLE-FIX-S81-LEAF 11-19, leaf TT class "about -840"): per-slice write-data selects in ot_s81sl_vpw, 0 cycles.

Measured on leaf t74 (D8f tree, CTS, TT, placement RC; the same value on t2 / t6): u_vp.g_wr1.u_w.g_xr.sw_a_q[0] ->
wdo_q[0][121], slack -844.55, 246 failing ends.  The two flops are 35 um apart, the path is 1,570 ps: only four gates (INV,
AOI211, AND2, AO221) but about 30 repeaters between them, 100 to 150 ps of wire each.  The writer-select terms (s_sw / s_c0 /
s_c1 / s_hs, built from 14 control bits of the XR stage) are ONE cone shared by both bank ports and all 2 x 128 write-data
bits, so its gates sit between the two leaf-store banks and every select crosses the leaf twice.

SLR (default = XR: on wherever the XR stage is on) gives every (bank, slice) of the write-data register its own kept copy of
those 14 control bits, loaded from the raw writer pins on the same edge as the XR stage (the two mask ORs are taken before the
flop), and its own select decode.  wdo_q then sees: local control flops -> 4 selects -> AND-OR with the slice's data bits.
Function and cycle are unchanged: the copies equal the XR flops in every cycle, the selects are the same expressions, and the
write address, mask, valid, collision and x-data paths are not touched.  2 x REP x 14 = 224 flops at REP 8.
SLR 0 is the source exactly.

  python3 -I s81_vpw_slr_overlay.py ROOT        ROOT = an S81 source tree whose ot_s81sl_vp.sv carries WRP + XR (ot_s81sl_vpw
with g_xr).  Exact, counted replacements (refuses on any miss or a second run); the file is rewritten by unlink + write.
The edit is inside ot_s81sl_vpw only, after every line of ot_s81sl_vp, so no source position of the vp module moves.
"""
import sys
from pathlib import Path

VP = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
TAG = "S81-VPW-SLR"

HEAD_A = "module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0) ("
HEAD_B = "module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0, parameter integer SLR = XR) ("
REG_A = "            wa_q[k] <= n_wa[k]; wmw_q[k] <= n_wm[k]; wdo_q[k] <= n_wdo[k];\n"
REG_B = "            wa_q[k] <= n_wa[k]; wmw_q[k] <= n_wm[k]; wdo_q[k] <= n_wdo_s[k];\n"
ANCHOR = "    reg [1:0] wv_q; reg wcol_q; reg [8:0] wa_q [0:1]; reg [3:0] wmw_q [0:1]; reg [127:0] wdo_q [0:1];\n"
BLOCK = f"""    // {TAG}: per (bank, slice) kept copies of the 14 writer-control bits and their own select decode (0 cycles; see
    // tools/die_plan/s81_vpw_slr_overlay.py).  sv_q / sa_q load from the raw pins on the XR edge, so they equal the g_xr flops.
    wire [127:0] n_wdo_s [0:1];
    generate if (XR != 0 && SLR != 0) begin : g_slr
        wire [4:0] sv_d = {{hs_v, x_wv, cw_v[1], cw_v[0], sw_v}};
        wire [8:0] sa_d = {{hs_a[0], |x_wm[3:0], |x_wm[7:4], x_wa[0], cw_a[14], cw_a[2], |sw_m[3:0], |sw_m[7:4], sw_a[0]}};
        genvar sb, sr;
        for (sb = 0; sb < 2; sb = sb + 1) begin : g_b
            for (sr = 0; sr < REP; sr = sr + 1) begin : g_r
                (* keep *) reg [4:0] sv_q;
                (* keep *) reg [8:0] sa_q;
                always @(posedge clk or negedge rst_n) if (!rst_n) sv_q <= 5'd0; else sv_q <= sv_d;
                always @(posedge clk) sa_q <= sa_d;
                wire bb = (sb == 1);
                wire hi_sw = (sa_q[0] != bb), hi_xw = (sa_q[5] != bb), hi_hs = (sa_q[8] != bb);
                wire a_sw = sv_q[0] && (hi_sw ? sa_q[1] : sa_q[2]);
                wire a_c0 = sv_q[1] && (sa_q[3] == bb);
                wire a_c1 = sv_q[2] && (sa_q[4] == bb);
                wire a_xw = sv_q[3] && (hi_xw ? sa_q[6] : sa_q[7]);
                wire a_hs = sv_q[4];
                wire s_hs = a_hs;
                wire s_c1 = a_c1 && !a_xw && !a_hs;
                wire s_c0 = a_c0 && !a_c1 && !a_xw && !a_hs;
                wire s_sw = a_sw && !a_c0 && !a_c1 && !a_xw && !a_hs;
                wire [127:0] c0_w = {{4{{cw_d_i[31:0]}}}}, c1_w = {{4{{cw_d_i[63:32]}}}};
                // the b_dec if-chain: sw, then c0, then c1 override; xw leaves the data; hs last (the selects are one-hot)
                assign n_wdo_s[sb][SL * sr +: SL] =
                    s_hs ? (hi_hs ? hs_d_i[128 + SL * sr +: SL] : hs_d_i[SL * sr +: SL]) :
                    s_c1 ? c1_w[SL * sr +: SL] :
                    s_c0 ? c0_w[SL * sr +: SL] :
                    s_sw ? (hi_sw ? sw_d_i[128 + SL * sr +: SL] : sw_d_i[SL * sr +: SL]) : {{SL{{1'b0}}}};
            end
        end
    end else begin : g_nslr
        assign n_wdo_s[0] = n_wdo[0]; assign n_wdo_s[1] = n_wdo[1];
    end endgenerate
"""


def patch(s):
    if TAG in s:
        raise SystemExit("SLR_OVERLAY_TWICE ot_s81sl_vp.sv already carries SLR")
    for a, what in ((HEAD_A, "vpw header (WRP + XR form)"), (REG_A, "wdo_q register line"), (ANCHOR, "vpw register declarations"),
                    ("    generate if (XR != 0) begin : g_xr\n", "g_xr stage")):
        if s.count(a) != 1:
            raise SystemExit(f"SLR_OVERLAY_MISS {what}: expected 1 x {a[:70]!r}, found {s.count(a)}")
    if s.index(HEAD_A) < s.rindex("module ot_s81sl_vp #("):
        raise SystemExit("SLR_OVERLAY_ORDER ot_s81sl_vpw is not after ot_s81sl_vp: source positions of vp would move")
    return s.replace(HEAD_A, HEAD_B).replace(ANCHOR, BLOCK + ANCHOR).replace(REG_A, REG_B)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    p = Path(argv[0]) / VP
    s = patch(p.read_text())
    p.unlink()                      # a link into a shared tree, or a read-only published file: never written through
    p.write_text(s)
    print(f"SLR_OVERLAY_OK {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
