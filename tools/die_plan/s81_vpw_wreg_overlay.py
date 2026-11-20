#!/usr/bin/env python3
"""S81-VPW-WREG (FABLE-FIX-S81-LEAF 11-19, COORD-approved +1 cycle): one register stage between the write-port decode and the
leaf-store bank registers of ot_s81sl_vpw, opt-in by the bare-name define OT_S81SL_VP_WREG.

Measured on leaf t31 (D8e tree, attempt 12, CTS TT): u_vp.g_wr1.u_w.g_xr.sw_a_q[0] -> wmw_q[0][0], slack -1,263 ps, one clk_t10
tree (skew +68 ps in its favour).  Data 2,160 ps: five gates (AND5 / AOI211 / AND5 / OA211 / OR5, about 240 ps) and about 40
repeaters over 11 long hops.  The five-writer priority decode (b_dec) reads the XR flops at the writer pins and drives the bank
registers wa_q / wmw_q / wdo_q / xl_q / xh_q / wv_q / wcol_q at the leaf-store banks: one cycle cannot hold the decode and the
cross-leaf wire.  SLR (s81_vpw_slr_overlay.py) localises only the write-DATA selects; address, mask, valid and collision keep
the long path (t31 fails on the mask).

A register on sw_a / sw_m alone would move the sw writer one edge against its own data and against the other four writers
(priority and collision would change).  WREG instead registers EVERY decoded bank-port value (valid, collision, address, mask,
data, x-data selects) once, and delays the raw x write data xwd_i by the same edge (wdx consumes it one edge after its
selects), so the whole write port lands exactly one clk later: vpw(WREG=1)(t) == vpw(WREG=0)(t-1) on every output,
store order, writer priority and collisions unchanged.  The decode now has a cycle to itself (writer pins -> p_*), and
p_* -> bank registers is a register-to-register wire cycle.

Latency contract: vp write availability +1 clk on every writer (sw, cw, x_w, hc_post hs write-back) of a leaf built with
the define; vp read latency, lane HI / HO stations and the reset tree are unchanged.  Without the define WREG = 0 and the
generate takes g_nwreg (plain wires): the source exactly, no cell, no cycle.

  python3 -I s81_vpw_wreg_overlay.py ROOT     ROOT = an S81 source tree whose ot_s81sl_vp.sv carries WRP + XR (ot_s81sl_vpw with
g_xr), with or without SLR (apply SLR first when both are used).  Exact, counted replacements (refuses on any miss or a
second run); the file is rewritten by unlink + write.  Every edit is inside or just before ot_s81sl_vpw, after the last line
of ot_s81sl_vp, so no source position of the vp module moves.
"""
import re
import sys
from pathlib import Path

VP = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
TAG = "S81-VPW-WREG"
DEFINE = "OT_S81SL_VP_WREG"

HEAD = re.compile(r"^module ot_s81sl_vpw #\((parameter integer REP = 8, parameter integer XR = 0(?:, parameter integer SLR = XR)?)\) \($",
                  re.M)
ANCHOR = "    reg [1:0] wv_q; reg wcol_q; reg [8:0] wa_q [0:1]; reg [3:0] wmw_q [0:1]; reg [127:0] wdo_q [0:1];\n"
RST_A = "        else begin wv_q <= n_wv; wcol_q <= n_wcol; end\n"
RST_B = "        else begin wv_q <= w_wv; wcol_q <= w_wcol; end\n"
REG_A = {"n_wdo": "            wa_q[k] <= n_wa[k]; wmw_q[k] <= n_wm[k]; wdo_q[k] <= n_wdo[k];\n",
         "n_wdo_s": "            wa_q[k] <= n_wa[k]; wmw_q[k] <= n_wm[k]; wdo_q[k] <= n_wdo_s[k];\n"}
REG_B = "            wa_q[k] <= w_wa[k]; wmw_q[k] <= w_wm[k]; wdo_q[k] <= w_wdo[k];\n"
XL_A = "            xl_q[k] <= {REP{n_xl[k]}}; xh_q[k] <= {REP{n_xh[k]}};\n"
XL_B = "            xl_q[k] <= {REP{w_xl[k]}}; xh_q[k] <= {REP{w_xh[k]}};\n"
WDX_A = "assign wdx[gb][SL * gr +: SL] = ({SL{xl_q[gb][gr]}} & xwd_i[SL * gr +: SL]) | ({SL{xh_q[gb][gr]}} & xwd_i[128 + SL * gr +: SL]) |"
WDX_B = "assign wdx[gb][SL * gr +: SL] = ({SL{xl_q[gb][gr]}} & xwd_w[SL * gr +: SL]) | ({SL{xh_q[gb][gr]}} & xwd_w[128 + SL * gr +: SL]) |"
DEF_BLOCK = (f"`ifdef {DEFINE}\n`define {DEFINE}_DEFAULT 1\n`else\n`define {DEFINE}_DEFAULT 0\n`endif\n"
             f"// {TAG}: WREG = one register stage between the write-port decode and the bank registers (see ot_s81sl_vpw)\n")


def block(src):
    return f"""    // {TAG}: WREG registers every decoded bank-port value once (and xwd_i by the same edge), so the whole write port
    // lands one clk later: vpw(WREG=1)(t) == vpw(WREG=0)(t-1).  See tools/die_plan/s81_vpw_wreg_overlay.py.
    wire [1:0] w_wv; wire w_wcol; wire [8:0] w_wa [0:1]; wire [3:0] w_wm [0:1]; wire [127:0] w_wdo [0:1];
    wire w_xl [0:1]; wire w_xh [0:1]; wire [255:0] xwd_w;
    generate if (WREG != 0) begin : g_wreg
        reg [1:0] p_wv; reg p_wcol; reg [8:0] p_wa [0:1]; reg [3:0] p_wm [0:1]; reg [127:0] p_wdo [0:1];
        reg p_xl [0:1]; reg p_xh [0:1]; reg [255:0] p_xwd;
        always @(posedge clk or negedge rst_n) if (!rst_n) begin p_wv <= 2'b00; p_wcol <= 1'b0; end
            else begin p_wv <= n_wv; p_wcol <= n_wcol; end
        integer j;
        always @(posedge clk) begin
            for (j = 0; j < 2; j = j + 1) begin
                p_wa[j] <= n_wa[j]; p_wm[j] <= n_wm[j]; p_wdo[j] <= {src}[j]; p_xl[j] <= n_xl[j]; p_xh[j] <= n_xh[j];
            end
            p_xwd <= xwd_i;
        end
        assign w_wv = p_wv; assign w_wcol = p_wcol; assign xwd_w = p_xwd;
        assign w_wa[0] = p_wa[0]; assign w_wa[1] = p_wa[1]; assign w_wm[0] = p_wm[0]; assign w_wm[1] = p_wm[1];
        assign w_wdo[0] = p_wdo[0]; assign w_wdo[1] = p_wdo[1];
        assign w_xl[0] = p_xl[0]; assign w_xl[1] = p_xl[1]; assign w_xh[0] = p_xh[0]; assign w_xh[1] = p_xh[1];
    end else begin : g_nwreg
        assign w_wv = n_wv; assign w_wcol = n_wcol; assign xwd_w = xwd_i;
        assign w_wa[0] = n_wa[0]; assign w_wa[1] = n_wa[1]; assign w_wm[0] = n_wm[0]; assign w_wm[1] = n_wm[1];
        assign w_wdo[0] = {src}[0]; assign w_wdo[1] = {src}[1];
        assign w_xl[0] = n_xl[0]; assign w_xl[1] = n_xl[1]; assign w_xh[0] = n_xh[0]; assign w_xh[1] = n_xh[1];
    end endgenerate
"""


def patch(s):
    if TAG in s:
        raise SystemExit("WREG_OVERLAY_TWICE ot_s81sl_vp.sv already carries WREG")
    heads = HEAD.findall(s)
    if len(heads) != 1:
        raise SystemExit(f"WREG_OVERLAY_MISS vpw header (WRP + XR form, SLR optional): found {len(heads)}")
    cut = s.index("module ot_s81sl_vpw #(")
    if cut < s.rindex("module ot_s81sl_vp #("):
        raise SystemExit("WREG_OVERLAY_ORDER ot_s81sl_vpw is not after ot_s81sl_vp: source positions of vp would move")
    head, body = s[:cut], s[cut:]
    end = body.index("endmodule")
    vpw, tail = body[:end], body[end:]
    srcs = [k for k, a in REG_A.items() if vpw.count(a) == 1]
    if len(srcs) != 1:
        raise SystemExit("WREG_OVERLAY_MISS bank register line (wdo_q <= n_wdo or n_wdo_s)")
    for a, what in ((ANCHOR, "vpw register declarations"), (RST_A, "wv_q / wcol_q register"), (XL_A, "xl_q / xh_q register"),
                    (WDX_A, "wdx x-data select"), ("    generate if (XR != 0) begin : g_xr\n", "g_xr stage")):
        if vpw.count(a) != 1:
            raise SystemExit(f"WREG_OVERLAY_MISS {what}: expected 1 x {a[:70]!r}, found {vpw.count(a)}")
    m = HEAD.search(vpw)
    vpw = vpw[:m.start()] + f"module ot_s81sl_vpw #({m.group(1)}, parameter integer WREG = `{DEFINE}_DEFAULT) (" + vpw[m.end():]
    vpw = vpw.replace(ANCHOR, block(srcs[0]) + ANCHOR).replace(RST_A, RST_B).replace(REG_A[srcs[0]], REG_B)
    vpw = vpw.replace(XL_A, XL_B).replace(WDX_A, WDX_B)
    return head + DEF_BLOCK + vpw + tail


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    p = Path(argv[0]) / VP
    s = patch(p.read_text())
    p.unlink()                      # a link into a shared tree, or a read-only published file: never written through
    p.write_text(s)
    print(f"WREG_OVERLAY_OK {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
