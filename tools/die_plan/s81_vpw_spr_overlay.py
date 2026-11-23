#!/usr/bin/env python3
"""S81-VPW-SPR (OPUS-FIX-S81-LEAF-R10 11-22, COORD J9 ruling form (b) "register the select ahead of the wdo_q mux"):
pre-decoded, registered write-data selects in ot_s81sl_vpw g_slr, 0 cycles.

LOCAL-CONE-SCATTER on the leaf write-out cone (post-place TT, endpoints 31-65 um apart, 22-23 stages over 1.2-1.7 mm):
t14 -512 / t31 -503 / t74 -301 ps g_slr.g_b[k].g_r[r] select copy (hi_sw / a_hs) -> wdo_q[k][..].  After the SLR copies
the register-to-register path is still: control flop -> 5 gates of select decode (a_* / s_* priority terms) -> 4-way
priority mux -> wdo_q, and the placer spreads those gates.

SPR (opt-in by the bare-name define OT_S81SL_VP_SPR; needs XR and SLR) moves the select decode BEFORE the per-slice
flops: each (bank, slice) registers the six one-hot data selects (hs hi / hs lo / c1 / c0 / sw hi / sw lo), decoded from
the raw writer pins on the XR edge (the edge that already starts at the pins), so after the flop the wdo_q D input is one
AND-OR level: (sel & data) | ... .  The selects are exactly the SLR terms (s_hs = a_hs; s_c1 / s_c0 / s_sw with the same
exclusions; xw writes no wdo data), so the six are one-hot and the AND-OR equals the priority mux; registered on the same
edge as sv_q / sa_q, so wdo_q gets the same value in the same cycle.  0 cycles; 6 select flops per slice (the SLR sv_q / sa_q copies stay, kept, unloaded).  The +1
cycle form (decode kept after the flop, one more register) is the fallback if the XR edge does not close.
Data operands are whatever the source already uses (the shared *_i, or the per-bank *_b[sb] of S81-VPW-XRB), so SPR
composes with XRB: apply XRB first, then SPR (XRB refuses a tree that already carries SPR).  SPR 0 is the source logic exactly (same instance names; one constant-folded wire spr_wd).

  python3 -I s81_vpw_spr_overlay.py ROOT     ROOT = an S81 source tree whose ot_s81sl_vp.sv carries WRP + XR + SLR, or the
file.  Exact, counted replacements (refuses on any miss or a second run); write-new + rename.  Edits only inside / just
before ot_s81sl_vpw, so no source position of the vp module moves.
"""
import os
import re
import sys
from pathlib import Path

REL = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
TAG = "S81-VPW-SPR"
HEAD_RE = re.compile(r"(module ot_s81sl_vpw #\(parameter integer REP = 8, parameter integer XR = 0, parameter integer SLR = XR)"
                     r"((?:,\n\s*parameter integer XRB = `OT_S81SL_VP_XRB_DEFAULT)?)\) \(")
DEFINE = f"""// {TAG} (tools/die_plan/s81_vpw_spr_overlay.py): pre-decoded registered write-data selects, 0 cycles; opt-in by OT_S81SL_VP_SPR.
`ifndef OT_S81SL_VP_SPR_DEFAULT
`ifdef OT_S81SL_VP_SPR
`define OT_S81SL_VP_SPR_DEFAULT 1
`else
`define OT_S81SL_VP_SPR_DEFAULT 0
`endif
`endif
"""
BODY_START = "                (* keep *) reg [4:0] sv_q;\n"
BODY_END = "{SL{1'b0}};\n"
LOOP_HEAD = "            for (sr = 0; sr < REP; sr = sr + 1) begin : g_r\n"


def patch(s):
    if TAG in s:
        raise SystemExit("SPR_OVERLAY_TWICE ot_s81sl_vp.sv already carries SPR")
    heads = HEAD_RE.findall(s)
    if len(heads) != 1:
        raise SystemExit(f"SPR_OVERLAY_MISS vpw header (WRP + XR + SLR form): found {len(heads)}")
    for a, what in ((BODY_START, "g_slr sv_q copy"), (LOOP_HEAD, "g_slr slice loop"),
                    ("    generate if (XR != 0 && SLR != 0) begin : g_slr\n", "g_slr block")):
        if s.count(a) != 1:
            raise SystemExit(f"SPR_OVERLAY_MISS {what}: expected 1 x {a[:60]!r}, found {s.count(a)}")
    i = s.index(BODY_START)
    j = s.index(BODY_END, i) + len(BODY_END)
    old = s[i:j]
    if "assign n_wdo_s[sb][SL * sr +: SL] =" not in old or old.count("s_sw ?") != 1:
        raise SystemExit("SPR_OVERLAY_MISS g_slr slice body (sv_q .. n_wdo_s assign)")
    xrb = "sw_d_b[sb][" in old
    sw, hs = ("sw_d_b[sb]", "hs_d_b[sb]") if xrb else ("sw_d_i", "hs_d_i")
    m = re.search(r"wire \[127:0\] c0_w = \{4\{(\w+(?:\[sb\])?)\[31:0\]\}\}", old)
    if not m:
        raise SystemExit("SPR_OVERLAY_MISS c0_w data operand")
    cw = m.group(1)
    ind = "                    "
    ASSIGN = "                assign n_wdo_s[sb][SL * sr +: SL] =\n"
    if old.count(ASSIGN) != 1:
        raise SystemExit("SPR_OVERLAY_MISS n_wdo_s assign")
    ind = "                    "
    blk = (f"                // {TAG}: the SLR select terms decoded from the raw pins and registered on the same edge as sv_q / sa_q\n"
           f"                wire [SL-1:0] spr_wd;\n"
           f"                if (SPR != 0) begin : g_spr\n"
           f"{ind}wire d_hi_sw = (sw_a[0] != bb), d_hi_xw = (x_wa[0] != bb), d_hi_hs = (hs_a[0] != bb);\n"
           f"{ind}wire d_a_sw = sw_v && (d_hi_sw ? |sw_m[7:4] : |sw_m[3:0]);\n"
           f"{ind}wire d_a_c0 = cw_v[0] && (cw_a[2] == bb);\n"
           f"{ind}wire d_a_c1 = cw_v[1] && (cw_a[14] == bb);\n"
           f"{ind}wire d_a_xw = x_wv && (d_hi_xw ? |x_wm[7:4] : |x_wm[3:0]);\n"
           f"{ind}wire d_a_hs = hs_v;\n"
           f"{ind}wire d_s_c1 = d_a_c1 && !d_a_xw && !d_a_hs;\n"
           f"{ind}wire d_s_c0 = d_a_c0 && !d_a_c1 && !d_a_xw && !d_a_hs;\n"
           f"{ind}wire d_s_sw = d_a_sw && !d_a_c0 && !d_a_c1 && !d_a_xw && !d_a_hs;\n"
           f"{ind}wire [5:0] sel_d = {{d_a_hs && d_hi_hs, d_a_hs && !d_hi_hs, d_s_c1, d_s_c0, d_s_sw && d_hi_sw, d_s_sw && !d_hi_sw}};\n"
           f"{ind}(* keep *) reg [5:0] sel_q;\n"
           f"{ind}always @(posedge clk or negedge rst_n) if (!rst_n) sel_q <= 6'd0; else sel_q <= sel_d;\n"
           f"{ind}assign spr_wd = ({{SL{{sel_q[5]}}}} & {hs}[128 + SL * sr +: SL]) | ({{SL{{sel_q[4]}}}} & {hs}[SL * sr +: SL]) |\n"
           f"{ind}    ({{SL{{sel_q[3]}}}} & c1_w[SL * sr +: SL]) | ({{SL{{sel_q[2]}}}} & c0_w[SL * sr +: SL]) |\n"
           f"{ind}    ({{SL{{sel_q[1]}}}} & {sw}[128 + SL * sr +: SL]) | ({{SL{{sel_q[0]}}}} & {sw}[SL * sr +: SL]);\n"
           f"                end else begin : g_nspr\n"
           f"{ind}assign spr_wd = {{SL{{1'b0}}}};\n"
           f"                end\n")
    new = old.replace(ASSIGN, blk + ASSIGN + "                    (SPR != 0) ? spr_wd :\n")
    s = s[:i] + new + s[j:]
    hm = HEAD_RE.search(s)
    s = s[:hm.start()] + hm.group(1) + hm.group(2) + ",\n                       parameter integer SPR = `OT_S81SL_VP_SPR_DEFAULT) (" + s[hm.end():]
    head = s.index("module ot_s81sl_vpw #(")
    cut = s.rfind("\nendmodule", 0, head)
    if cut < 0 or cut < s.rindex("module ot_s81sl_vp #("):
        raise SystemExit("SPR_OVERLAY_ORDER no endmodule between ot_s81sl_vp and ot_s81sl_vpw")
    cut = s.index("\n", cut + 1) + 1
    return s[:cut] + DEFINE + s[cut:]


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    p = Path(argv[0])
    if p.is_dir():
        p = p / REL
    new = patch(p.read_text())
    tmp = p.with_name(p.name + ".spr.tmp")
    tmp.write_text(new)
    os.replace(tmp, p)
    print(f"{TAG}: {p} patched (define OT_S81SL_VP_SPR, 6 registered selects per bank slice)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
