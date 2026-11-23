#!/usr/bin/env python3
"""S81-VP-SELREP (OPUS-FIX-S81-LEAF-R10 11-22, J9 row J9-LEAF-SRE-SRC): replicated select flops for the two wide vp
register muxes, 0 cycles.

Post-place TT, event 18a2688b741: leaf t37 -817 ps vp_driver g_sre.nm_r -> n_pre (vp_src_*_q[10]; span 613 um, 26 stages),
t8 -855 ps same pair, t16 -462 ps xsw2 -> x_qd[199] (span 519 um, 20 stages).  One select flop drives the mux select of a
128-bit (n_pre) or 256-bit (x_qd) register: the buffer tree plus the mux spans the whole register footprint.
SELREP (opt-in by the bare-name define OT_S81SL_VP_SELREP):
  * n_pre (needs SR): 8 copies of nm_r (same D cv_c && op == OP_NORM, same async reset), copy g selects n_pre[16g +: 16]
    (e_nm ? e_cd : nr_done ? q1r : hold, per bit exactly as the source); nm_r keeps n_go / m_v / m_* / fault.
  * x_qd: 8 copies of xsw2 (D = xsw1), copy g selects x_qd[32g +: 32].
Same edges, same values, 0 cycles; the copies are (* keep *) so synthesis does not merge them and placement can put each
by its slice.  SELREP 0 (define absent) is the source logic (constant-folded selects).
Every edit stays on its own source line (no line is added or removed), so every source position the netlist names carry
is unchanged; the parameter comes from an inline `ifdef in the vp header.

  python3 -I s81_vp_selrep_overlay.py ROOT|FILE     exact counted replacements; refuses on a miss or a second run.
"""
import os
import sys
from pathlib import Path

REL = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
TAG = "S81-VP-SELREP"
EDITS = [  # (old line text, new line text), each must occur exactly once
    ("parameter integer WRP = `OT_S81SL_VP_WRP_DEFAULT  // WRP:",
     "parameter integer WRP = `OT_S81SL_VP_WRP_DEFAULT, parameter integer SELREP = `ifdef OT_S81SL_VP_SELREP 1 `else 0 `endif  // WRP:"),
    ("    always @(posedge clk) begin q0 <= rq0; q1 <= rq1; xsw1 <= t_xsw; xsw2 <= xsw1; end\n",
     "    always @(posedge clk) begin q0 <= rq0; q1 <= rq1; xsw1 <= t_xsw; xsw2 <= xsw1; end"
     "  wire [255:0] xq_sel; generate if (SELREP != 0) begin : g_xsr (* keep *) reg [7:0] q; always @(posedge clk) q <= {8{xsw1}}; wire [255:0] xq_a = {q0, q1}, xq_b = {q1, q0};"
     " genvar gx; for (gx = 0; gx < 8; gx = gx + 1) begin : g_x assign xq_sel[32 * gx +: 32] = q[gx] ? xq_a[32 * gx +: 32] : xq_b[32 * gx +: 32]; end"
     " end else begin : g_nxsr assign xq_sel = 256'd0; end endgenerate  // " + TAG + "\n"),
    ("    wire e_nm, e_su, e_flt; wire [159:0] e_cd;\n",
     "    wire e_nm, e_su, e_flt; wire [159:0] e_cd; wire [127:0] npre_d; localparam integer SRP = (SELREP != 0 && SR != 0) ? 1 : 0;  // " + TAG + "\n"),
    ("        reg nm_r, su_r, flt_r; reg [159:0] cd_r;\n",
     "        reg nm_r, su_r, flt_r; reg [159:0] cd_r;"
     "  if (SRP != 0) begin : g_nmr (* keep *) reg [7:0] q; always @(posedge clk or negedge rs_o) if (!rs_o) q <= 8'd0; else q <= {8{cv_c && op == OP_NORM}};"
     " genvar gq; for (gq = 0; gq < 8; gq = gq + 1) begin : g_q assign npre_d[16 * gq +: 16] = q[gq] ? e_cd[32 + 16 * gq +: 16] : nr_done ? q1r[16 * gq +: 16] : n_pre[16 * gq +: 16]; end"
     " end else begin : g_nnmr assign npre_d = 128'd0; end  // " + TAG + "\n"),
    ("        assign e_nm = cv_c && op == OP_NORM; assign e_su = cv_c && op[3]; assign e_flt = flt_pin; assign e_cd = cd_c;\n",
     "        assign e_nm = cv_c && op == OP_NORM; assign e_su = cv_c && op[3]; assign e_flt = flt_pin; assign e_cd = cd_c; assign npre_d = 128'd0;\n"),
    ("        if (e_nm) begin n_pre <= e_cd[159:32]; m_q <= e_cd[24]; m_b <= e_cd[25]; m_i <= e_cd[21:14]; end\n",
     "        if (SRP != 0) n_pre <= npre_d; if (e_nm) begin if (SRP == 0) n_pre <= e_cd[159:32]; m_q <= e_cd[24]; m_b <= e_cd[25]; m_i <= e_cd[21:14]; end\n"),
    ("            n_pre <= q1r;\n",
     "            if (SRP == 0) n_pre <= q1r;\n"),
    ("        x_qd <= xsw2 ? {q0, q1} : {q1, q0};\n",
     "        x_qd <= (SELREP != 0) ? xq_sel : xsw2 ? {q0, q1} : {q1, q0};\n"),
]


def patch(s):
    if TAG in s:
        raise SystemExit("SELREP_OVERLAY_TWICE ot_s81sl_vp.sv already carries SELREP")
    n0 = s.count("\n")
    for old, new in EDITS:
        c = s.count(old)
        if c != 1:
            raise SystemExit(f"SELREP_OVERLAY_MISS expected 1 x {old.strip()[:70]!r}, found {c}")
        s = s.replace(old, new)
    if s.count("\n") != n0:
        raise SystemExit("SELREP_OVERLAY_LINES the edit moved a source line")
    return s


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    p = Path(argv[0])
    if p.is_dir():
        p = p / REL
    new = patch(p.read_text())
    tmp = p.with_name(p.name + ".selrep.tmp")
    tmp.write_text(new)
    os.replace(tmp, p)
    print(f"{TAG}: {p} patched (define OT_S81SL_VP_SELREP: 8 nm_r copies -> n_pre, 8 xsw2 copies -> x_qd)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
