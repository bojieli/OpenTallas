# INTENT T73-ST4 (CPL-S81-SLICE-4, DO_NOT_COUNT) - ot_s81sl_leaf__t73, base BASE_1200 b5faa1ba
Positions only (same orients, all origins on the 8.64 lattice; no RTL/pin/bus/cycle/outline change). ft station sites re-sited
(same counts; regs_um[0] = in-face flop kept; bit-site rows translated rigidly).
Dataflow: S buses leafdn_i0 (in 597 b) / leafup_o0 (out 668 b) at x 876-1149 -> vn_b/vn_a (-> 16 g_ln lanes, 256-b stations), vq,
vs (hub) -> ve_m (1484 b), vsw (642 b), vq (542 b), ve_s (200 b); ve_m <-> ve_s 772 b; rxsf -> rxsb 192 b.
Pass-through: ~3.9 kb N<->S ft (ft7 1104 W, ft8 1104, ft0-5 6x70, ft6 668, ft9 597) at x 6-874. In BASE every ft station site
except ft7 sits in the 34-um ve_m|ve_s street (x 510-544), so street_V p99 is 1.885.
Hand form ST4, three straight full-height N-S streets:
  W x 0-103.68 (ft7),
  A x 328.32-449.28 (121 um; ft8, ft0-3),
  B x 622.08-768.96 (147 um; ft4-6, ft9).
Column 1: ve_m (155.52,43.2), vsw (103.68,423.36).
Column 2 (x 449.28): ve_s at the S edge (43.2; 772 b to ve_m across A), vs above it (423.36; NE of ve_m N-face pins as in BASE, across A from vsw), rxsf (630.72), rxsb (812.16); gaps 34.56.
vq: (768.96,43.2), under vn_b (gap 34.56). vn_a/vn_b and the g_ln column are unchanged.
ft interior sites: one straight x per slot inside its street, with y spaced so that all hops of a slot are equal (jogs included),
  max 362 um. Band ft8_i moves into street A (same S edge, same y-span).
Internal stations follow their cores (fix.py), then resite.py: no new core crossings, hops <= 405 where reachable.
ST3 (vs at the S edge) was rejected: ve_m's 1484-b vs pins are on its N face (G0C core_faces), over-reach 37.
