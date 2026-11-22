#!/usr/bin/env python3
"""S81-VPW-XRB (OPUS-FIX-S81-LEAF-R10 11-22, COORD-approved J9 row): per-bank copies of the XR write-port flops in
ot_s81sl_vpw, 0 cycles.

Measured (post-place TT, both endpoints at the VP banks under the OT_VPW_BANK form, the cone scattered across the leaf):
  t31 J5 @4: g_slr.g_b[0].g_r[7] select (sa_q copy) -> wdo_q[0][114], -498 ps, 5 gates (INV AO21 OR3 OA222 OAI21) + 17
             placement buffers of ~180 um (1,688 um): the slice mux is pulled toward the ONE shared XR data cohort.
  t1  J7 @1: g_xr.sw_a_q[0] -> wmw_q[0][0], -348 ps, 1,264 um over 16 stages, endpoints 180 um apart: the shared b_dec
             address/mask decode reads the ONE shared XR control cohort and serves both banks.
The g_xr flops feed both banks, so wherever they sit one bank's write cone crosses the leaf and comes back.

XRB (opt-in by the bare-name define OT_S81SL_VP_XRB; needs XR and SLR) gives each bank k its own kept copy of every XR
write-port input (data: sw_d 256, hs_d 256, cw_d 64, xwd 256; control: sw_v/sw_a/sw_m, cw_v/cw_a, x_wv/x_wa/x_wm,
hs_v/hs_a = 75), loaded from the raw writer pins on the XR edge (valid bits with the same async reset), so each equals
its g_xr flop in every cycle.  Bank k's slice muxes (g_slr.g_b[k]), its x-data AND-OR (wdx[k]) and its b_dec iteration
(n_wv / n_wa / n_wm / n_wdo / n_xl / n_xh [k], and its terms of the collision flag) read only bank k's copy.  With the
bank-affine VPW placement (s81_vpw_bank.tcl, OT_S81_VPW_BANK_AFF=1) the whole bank-k write cone is local and the
VS/port-to-bank distance is carried by the XR edge (pin -> flop, no logic).  Function and cycles are unchanged; the shared
g_xr flops lose all loads and synthesis removes them, so the net cost is one more copy of 907 bits.  XRB 0 is the source
exactly (the *_b wires are the *_i wires).

  python3 -I s81_vpw_xrb_overlay.py ROOT     ROOT = an S81 source tree whose ot_s81sl_vp.sv carries WRP + XR + SLR
(ot_s81sl_vpw with g_xr and g_slr), or the file itself.  Exact, counted replacements (refuses on any miss or a second
run); the file is rewritten by write-new + rename.  Every edit is inside / just before ot_s81sl_vpw, after every line of
ot_s81sl_vp, so no source position of the vp module moves.
"""
import os
import re
import sys
from pathlib import Path

REL = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
TAG = "S81-VPW-XRB"

# (name, width, async-reset valid)
SIGS = (("sw_v", 1, True), ("sw_a", 10, False), ("sw_m", 8, False), ("sw_d", 256, False),
        ("cw_v", 2, True), ("cw_a", 24, False), ("cw_d", 64, False),
        ("x_wv", 1, True), ("x_wa", 10, False), ("x_wm", 8, False), ("xwd", 256, False),
        ("hs_v", 1, True), ("hs_a", 10, False), ("hs_d", 256, False))

HEAD_A = "module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0, parameter integer SLR = XR) ("
HEAD_B = ("module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0, parameter integer SLR = XR,\n"
          "                       parameter integer XRB = `OT_S81SL_VP_XRB_DEFAULT) (")
DEFINE = f"""// {TAG} (tools/die_plan/s81_vpw_xrb_overlay.py): per-bank XR write-port copies, 0 cycles; opt-in by OT_S81SL_VP_XRB.
`ifndef OT_S81SL_VP_XRB_DEFAULT
`ifdef OT_S81SL_VP_XRB
`define OT_S81SL_VP_XRB_DEFAULT 1
`else
`define OT_S81SL_VP_XRB_DEFAULT 0
`endif
`endif
"""
DEC_ANCHOR = "    localparam integer SL = 128 / REP;\n"
B_DEC_HEAD = "    always @(*) begin : b_dec\n"
B_DEC_END = "    // S81-VPW-SLR: per (bank, slice) kept copies of the 14 writer-control bits"


def _block():
    decl = "".join(f"    wire [{w - 1}:0] {n}_b [0:1];\n" for n, w, _ in SIGS)
    regs, assign_q, assign_i = [], [], []
    for n, w, rst in SIGS:
        regs.append(f"            (* keep *) reg [{w - 1}:0] {n}_q;\n")
        if rst:
            regs.append(f"            always @(posedge clk or negedge rst_n) if (!rst_n) {n}_q <= {w}'d0; else {n}_q <= {n};\n")
        else:
            regs.append(f"            always @(posedge clk) {n}_q <= {n};\n")
        assign_q.append(f"            assign {n}_b[kb] = {n}_q;\n")
        assign_i.append(f"        assign {n}_b[0] = {n}_i; assign {n}_b[1] = {n}_i;\n")
    return (f"    // {TAG}: bank k's b_dec iteration, slice muxes and x-data AND-OR read bank k's own copy of every XR write-port\n"
            f"    // input (see tools/die_plan/s81_vpw_xrb_overlay.py).  The copies load from the raw pins on the XR edge, so they\n"
            f"    // equal the g_xr flops in every cycle.\n"
            + decl +
            "    generate if (XR != 0 && SLR != 0 && XRB != 0) begin : g_xrb\n"
            "        genvar kb;\n"
            "        for (kb = 0; kb < 2; kb = kb + 1) begin : g_b\n"
            + "".join(regs) + "".join(assign_q) +
            "        end\n"
            "    end else begin : g_nxrb\n"
            + "".join(assign_i) +
            "    end endgenerate\n")


BLOCK = _block()
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
BDEC_RE = re.compile(r"\b(" + "|".join(n for n, _, _ in SIGS) + r")_i\b")
BDEC_REFS = 35   # *_i reads inside b_dec of the J7 (WRP + XR + SLR) source


def patch(s):
    if TAG in s:
        raise SystemExit("XRB_OVERLAY_TWICE ot_s81sl_vp.sv already carries XRB")
    for a, what in ((HEAD_A, "vpw header (WRP + XR + SLR form)"), (B_DEC_END, "g_slr block (SLR overlay)"),
                    (DEC_ANCHOR, "vpw localparam SL"), (B_DEC_HEAD, "b_dec block"),
                    ("    generate if (XR != 0) begin : g_xr\n", "g_xr stage")) + tuple((o, w) for o, _, w in EDITS):
        if s.count(a) != 1:
            raise SystemExit(f"XRB_OVERLAY_MISS {what}: expected 1 x {a[:70]!r}, found {s.count(a)}")
    if s.index(HEAD_A) < s.rindex("module ot_s81sl_vp #("):
        raise SystemExit("XRB_OVERLAY_ORDER ot_s81sl_vpw is not after ot_s81sl_vp: source positions of vp would move")
    if not s.index(DEC_ANCHOR) < s.index(B_DEC_HEAD) < s.index(B_DEC_END):
        raise SystemExit("XRB_OVERLAY_ORDER expected localparam SL < b_dec < g_slr")
    # b_dec: every read of an XR write-port input becomes bank b's copy
    i, j = s.index(B_DEC_HEAD), s.index(B_DEC_END)
    body, n = BDEC_RE.subn(r"\1_b[b]", s[i:j])
    if n != BDEC_REFS:
        raise SystemExit(f"XRB_OVERLAY_MISS b_dec reads: expected {BDEC_REFS}, found {n}")
    s = s[:i] + body + s[j:]
    head = s.index(HEAD_A)
    cut = s.rfind("\nendmodule", 0, head)
    if cut < 0 or cut < s.rindex("module ot_s81sl_vp #("):
        raise SystemExit("XRB_OVERLAY_ORDER no endmodule between ot_s81sl_vp and ot_s81sl_vpw")
    cut = s.index("\n", cut + 1) + 1
    s = s[:cut] + DEFINE + s[cut:]
    s = s.replace(HEAD_A, HEAD_B).replace(DEC_ANCHOR, BLOCK + DEC_ANCHOR)
    for o, nw, _ in EDITS:
        s = s.replace(o, nw)
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
    print(f"{TAG}: {p} patched (define OT_S81SL_VP_XRB, {len(SIGS)} XR inputs per bank, {BDEC_REFS} b_dec reads)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
