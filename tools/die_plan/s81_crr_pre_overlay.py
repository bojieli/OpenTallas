#!/usr/bin/env python3
"""S81-CRR-PRE (OPUS-FIX-S81-LEAF-R10 11-23, row J9-LEAF-RST-LAND part 2, with LEAF-ROUTE-CBC [hg-S81-REACH]).

HOTSPOT-GAPS (S81 leaf): u_lpad_leafdn_iN -> u_lfN_u_crr_vs / crr_vsw / crr_rxsb / u_ve_u_crr_m D setup fails
(t23 -137, t29 -153, t50 -140 / -120, t54 -151 / -125 / -83, t67 -109).  ot_s81sl_crr (D8E-RSTRELAY) is one kept plain
D flop per hard-core reset pin, and plan relay_sites fix its q next to the core pin, so the pad register on the N face
(~1 mm away) must reach it in one cycle.  Moving the site only moves the long hop to crr -> core.

PRE (opt-in with the bare-name define OT_S81SL_CRR_PRE2; without it the source is unchanged) puts 2 kept plain D flops
before q (d -> s[0] -> s[1] -> q).  relay_sites name only .../q, so s[] are free cells, and GPL spreads the chain between
the two fixed ends (pad register, crr site): about 1/3 of the distance per hop.  Every ot_s81sl_crr in the type moves
together (slice vs / vsw / vq / rxsf / rxsb, vn a / b, ve m / s), so each crr core's reset assert and release move by
+2 edges (1 -> 3).  That matches the ot_rst_relay cores (vp / vn u_rr: SYNC_STAGES 2 + TREE_STAGES 1 = 3), so the
spread of release edges across the cores of a leaf shrinks from 1..3 (4 with XR) to 3..3 (4).  No data path changes.
Both edits stay on their own source lines (no line is added or removed).

  python3 -I s81_crr_pre_overlay.py ROOT|FILE     exact counted replacements; refuses on a miss or a second run.
"""
import os
import sys
from pathlib import Path

REL = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv"
TAG = "S81-CRR-PRE"
EDITS = [  # (old line text, new line text), each must occur exactly once
    ("module ot_s81sl_crr (input wire clk, input wire d, output reg q);\n",
     "module ot_s81sl_crr #(parameter integer PRE = `ifdef OT_S81SL_CRR_PRE2 2 `else 0 `endif) "
     "(input wire clk, input wire d, output reg q);  // " + TAG + "\n"),
    ("    always @(posedge clk) q <= d;\nendmodule\n",
     "    generate if (PRE == 0) begin : g_p0 always @(posedge clk) q <= d; end else begin : g_pre (* keep *) reg [PRE-1:0] s;"
     " integer i; always @(posedge clk) begin s[0] <= d; for (i = 1; i < PRE; i = i + 1) s[i] <= s[i - 1]; q <= s[PRE-1];"
     " end end endgenerate\nendmodule\n"),
]


def patch(s):
    if TAG in s:
        raise SystemExit("CRRPRE_OVERLAY_TWICE ot_s81sl_slice.sv already carries " + TAG)
    n0 = s.count("\n")
    for old, new in EDITS:
        c = s.count(old)
        if c != 1:
            raise SystemExit(f"CRRPRE_OVERLAY_MISS expected 1 x {old.strip()[:70]!r}, found {c}")
        s = s.replace(old, new)
    if s.count("\n") != n0:
        raise SystemExit("CRRPRE_OVERLAY_LINES the edit moved a source line")
    return s


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    p = Path(argv[0])
    if p.is_dir():
        p = p / REL
    new = patch(p.read_text())
    tmp = p.with_name(p.name + ".crrpre.tmp")
    tmp.write_text(new)
    os.replace(tmp, p)
    print(f"{TAG}: {p} patched (define OT_S81SL_CRR_PRE2: 2 kept pre-stages before every ot_s81sl_crr q)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
