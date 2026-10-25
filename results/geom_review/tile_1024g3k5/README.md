# GEOM-REVIEW tile batch g3k5 (2026-10-24 ~20:00 PDT) — S81 frame kits g3k5 (sub-review GR-S81G)
Images + dumps + STA: epyc1:/srv/opentallas-scratch/claude/geom-review/tiles/GR-S81G/{rev,dump,sta,deep}/<kit>/
(review.png = layout_review.py; clock_latency_taps.png = TT flop clock latency map + tap loads, CTS kits only).
STA: OpenSTA in openroad/orfs, propagated clock, placement RC, CPPR on, worst path per endpoint, TT and FF libs incl. macro libs.
Related-pair skew = launch - capture clock latency (PathEnd clk_skew minus 60/25 uncertainty), std flop -> std flop only.

| kit | stage | verdict | TT WNS / FF hold | pair skew max (>80 pairs) TT | kit-specific finding |
|---|---|---|---|---|---|
| col_h10_r0_p1__t1 | 4_cts | FAIL | -851.4 (arst_n) / -72.4 | 224 (5005) | x broadcast: one 284/267-b station -> u_bs0 ~650 um, u_bs2 ~510 um (-381/-372, 664 ep); ft0_i seam hold -123 TT |
| col_h10_r1__t1 | 4_cts | FAIL | -270.9 / -81.1 | 236 (2318) | face flops 339-489 ps vs 250 budget -> 15-19 hold buffers per frame_int_i bit; u_n13->u_n12 736 um (-234); lpl->elem -271 |
| col_h10_r2__t1 | 4_cts | FAIL | -140.8 (ROM->seq) / -16.7 | 123 (273) | closest: only ROM read path in setup; still fails reset + clock rules |
| col_h9_r2__t1 | 4_cts | FAIL | -43.5 / -56.4 | 178 (380) | relay rt_24a_1->2 cuts the elem macro corner (625 ps data) + 90 ps t9/t6 skew; 4 N taps empty, clk 2541 sinks |
| col_h9_r0_p1__t1 | 3_place | FAIL | ideal clk: arst_n -994 | n/a (no CTS) | u_s0.st -> u_t0.c0 905 um (S81 open item; needs RTL stage) |
| col_h9_r0_p3__t1 | 3_place | FAIL | ideal clk: arst_n -937 | n/a | same 905-um u_s0 -> u_t0 hop |
| col_h9_r1__t1 | 3_place | FAIL | ideal clk: arst_n -627 | n/a | x relay -> t payload -200, rr -> rg -177 (ideal clock) |

Common FAIL reasons (all 7): (R) per-tap async reset synchronisers fed by one arst_n tree (owner decision 2);
(K) clock taps assigned by distance only: 0..3007 sinks/tap, flop latency 176..489 ps TT, face flops off the 250-ps seam budget,
related-pair skew > 80 ps on hundreds to thousands of pairs (owner decision 5); ROMs still lack early core taps.
Geometry that passes: input face flops p90 7-10 um, macro gaps >= 6.5 um, 0 taps on macros, density <= 0.56, PDN M7 straps edge to edge.
Next: S81 g3k6 (pipelined reset 71bed19a4a + decision-5 tap rebuild + ROM early taps) -> re-REQ with CTS skew histogram.
