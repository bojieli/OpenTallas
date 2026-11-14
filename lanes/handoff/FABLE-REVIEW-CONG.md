# FABLE-REVIEW-CONG (Fable) 2026-11-14 12:0x PST - S81 routing-congestion families: leaf, column, others

## 0. Answer in five lines
1. LEAF is not leaf-wide congestion. 71 leaf GRT reports of wave 7073a6b4a59 use 3-12 percent of the routing capacity, and 80 percent of each type's overflow sits in 1-24 bins of 40 um. Three local structures own it: clock-landing ring bands (L1), ft output stations behind a close core (L2), glue logic in core-core slots (L3).
2. The rulebook street rule is NOT applied to leaf. Wave kits still have the generator gaps (core to face 34.56-50 um, core to core 8.64-23.8 um). The auto-fix cannot do it without growth (S81-FORMS-1 A5: 16 of 79 types at 0 growth), and the band-only form at 43.2 um moved no core on t2, t11, t32, t68.
3. Proven: t32 with its landing band under its own pins (private re-place) reaches GRT overflow 0 in 2 extra iterations, against 18; t68 with two lanes moved off the vn_a face reaches 0 in 5, against 66 left after 30. Not proven: the t75 corner form (run not finished) and a 17.28 um gutter blockage as the only lever on t68 (not converged by iteration 26).
4. COLUMN: only bf-wall crossings matter (element cores leave M6/M7 room). col_h9_r2 has none; col_h10_r0 has 536 + 283 + 266 bits across col3_c and is the next r1-type failure. Use an automatic channel path in relay_mid, not hand polylines (R-COL-7). The r0 top strip carries ft0 and frame_int_o0 together, 2273 bits in 77.8 um (R-COL-8, posted 08:5x).
5. No third congestion family. Other S81 route failures are timing (slice_station), cell cap (dsdv c1x), and DRT-0073 on the col3_c clock pin (6 cases, a pin-access class, not congestion). kv_leaf is the leaf L2 class.

Work dirs: epyc8, epyc9 /srv/opentallas-scratch2/claude/fable-review-cong (d/<type> dumps and GRT logs, k/<type> private kit copies, scripts); epyc7 /srv/opentallas-scratch2/claude/fable-review-col (r0grp.py, r0src.py, wallx.py, */wallx.txt, p_r0_base, p_h10r0_base). Scripts, renders and tables: intel2 ~/fable-review-cong/ (png/leaf_t11, t53, t68, t75). Per-type table: lanes/handoff/FABLE-REVIEW-CONG-leaf-violations.tsv (620 rows). All builds are private, DO_NOT_COUNT.

## 1. Leaf: what was measured
Leaf outline 1442.88 x 1226.88, 27 hard cores covering 34 percent of it, std cells under 1 percent. So room exists inside every type; no growth is needed.

| class | owner of the overflow | types (overflow at GRT iteration 15, or final) | geometry behind it |
| L1 | u_cland_<bus>_i ring cells | t2 61,348; t11 51,517 (attempt 2); t47 32,030; t53 31,560; t12 27,744; t55 19,540; t59 5,244; t32 fails on 1-4 gcells; t6, t15, t57, t7 small | band is 5 um2 per bit while the ring cells take 3.1-5.3 um2 per bit; in 13 of 69 types the band is a 24-30 um column in a core-core slot or beside its window (t2 ft1_i 24 x 237, t32 ft2_i 26 x 108 between ve_m and ve_s, t53 30 x 100) |
| L2 | u_ft_ft<N>_o stations | t75 83,030; t62 54,061; t61 40,771; t34 35,432; t52 30,922; t13, t71, t24, t58, kv_leaf t3 | a core 34.6-50 um behind the window; t75 has ve_m and ve_s 34.6 um above the S face and 43.3 um off the W face in the corner that holds ft0_o and ft1_o (2 x 1105 bits) |
| L3 | u_bound glue (vp logic), no station | t56 61,035; t68 1,003 then 51-66 final; t42, t74, t10, t5, t45; t11 on its 11-13 DB | cells in the 15.1 and 23.7 um slots between vn_a / vn_b and the ln lane column |
Also t72 (OT_CLAND no legal site in the ft0_i band) is the far end of L1: the ring does not fit its band at all.

Not measured: the 97,900 DRT violations of t6. Its GRT 2D overflow was 48, at the ft0_i ring and ft1_o, so I expect L1 plus the PG-track class of FLOW-PGCAP-1, but I ran no detail route.

## 2. Leaf rules
R-LEAF-1 BAND (plan generator of the landing bands, with DIE-S81-92). The band of a landed input bus lies under its own window: at least 80 percent of the window span, long axis along the face, never in a core-core slot and never beside the window. 128 bands in 42 types break it (rows L1a). Target, not a gate: 10 um2 per bit where the strip allows (201 bands in 64 types are at about 5; rows L1b).
R-LEAF-2 FACE CLEAR (plan, core moves only). Over a window of 16 pins or more, no core nearer the face than 43.2 um, and 86.4 um when the window is landed (one street for the ring, one for wires). A core in a corner keeps both. 217 items in 63 types (rows L2).
R-LEAF-3 SLOT (plan). Two cores abut (under 4.32 um) or keep 43.2 um; the ln lane column stands 43.2 um off the vn_a / vn_b pin faces. Every one of the 74 types has such slots (rows L3; 25-33 per type).
How to apply: the three rules need a hand template per leaf form, because street_rule.py legalize at 0 growth fails on 63 of 79 types (growth, station regs, reach). Draw one template with the cores pulled to the empty side of the outline, then let legalize finish stations. Start with the 13 column-band types (R-LEAF-1 alone needs no core move where the under-window strip is free, as on t32).

## 3. Leaf proofs (GRT M2-M8, adjustment 0.25, same deck for every pair)
| run | DB | change | result |
| t32 base | wave 3_place | none | overflow 0 after 18 extra iterations, 1664 s, wirelength 9.50 M um |
| t32 E1 | private re-place, epyc9 k/t32e1 | band u_cland_ft2_i {516.24 1101.53 542.16 1209.60} -> {372.60 1183.68 480.60 1209.60} in landing_placement.tcl | 0 after 2 iterations, 1112 s, 9.40 M um |
| t68 base | wave 3_place | none | 66 left after 30 iterations, all at x 880-920 y 360-440 (the wave failed there with 51) |
| t68 fix | wave 4_cts, in place | ln_12 and ln_13 moved to free area (650,920) and (800,920) | 0 after 5 iterations, 399 s (same DB without the move: 1,357 left after 15) |
| t68 E2 | private re-place, epyc9 k/t68e2 | OT_GUTTER_BLOCK_UM 17.28, min span 50: 13 blockages, 21,829 um2 | not converged by iteration 26; read epyc9 d/t68e2/grt.log for the end |
| t11 | wave 4_cts of 11-13, in place | ln_10 and ln_11 moved off the N face | NO gain: 2,830 against 1,601 after 30 iterations. On this DB the overflow is the 15 um slot between ln_9 / ln_11 and vn_b (L3), the ring owns 7 percent |
| t75 base | wave 3_place | none | 63,816 after 15 iterations, owned by ft1_o, ft0_o, ft5_o stations in the SW corner |
| t75 fix | same, in place | vsw, vs, ve_m, ve_s moved +129.6 um in y (10,177 cells relocated) | running at iteration 11; read epyc8 d/t75/fix.log |
Limits: GRT only, no repair, no timing, no detail route. In-place moves leave the cells where the old placement put them, so they prove the cause, not the new form. A 43.2 um gutter blockage fails the place on t68 because reset collector rst_rl_236 has its band in the 17.3 um ve_s | ve_m slot; collectors must be re-sited with R-LEAF-3.

## 4. Column
R-COL-7 WALL PATH (FIX-RELAYPOLY, answers the DIE-S81-92 question). Take the automatic channel path, not hand polylines: there are 36-48 crossing hops per r0 type and they move with placement. Only the bf wall cores (col3_c, bf16_half, front_roots) are walls; element cores are not (r1 passed with 536 bits over e8 once the col3_c crossing was gone). Reference generator: epyc7 fable-review-col/wallx.py (A-star on an 8.64 um grid, cores plus 4.32 um halo blocked, narrow channels cost more); output per type in */wallx.txt with polylines.
bf-wall crossings found (bits, straight length): r1 n19.o -> lpl_5_w 66 bits 708 um, y_rt_20a/b -> n20 (already in B3y); h10 r2 y_rt_30a_5 -> n30.a, y_rt_30b_2 -> n30.b, y_rt_26a_6 / 26b_sk -> n26.a / .b, 63 bits each; h9 r0 y_rt_10a_5 -> n10.a 63 bits; h10 r0 y_x2_2_0 -> t2_payload.i 536 bits, lpl_0_w 283 bits, y_xa_2_0 -> t2.xai 283, y_xb_2_0 -> t2.xbi 266; h9 r2 none.
Evidence: col_h9_r0_p2 4_cts reaches overflow 0 after 14 iterations on plain GRT (2788 s), so r0 fails only after repair buffering. col_h10_r0 baseline is at iteration 11 (epyc7 p_h10r0_base/proof.log). TYPE-COLH9R1 and TYPE-COLH9R2 need nothing beyond R-COL-1..4.
R-COL-8 r0 TOP STRIP: see the queue RESULT of 08:5x (two lanes with explicit station sites, M8 as a fourth horizontal layer, OT_MAXWIRE_UM 200). Untested by a build.

## 5. Deltas
DIE-S81-92 (plan):
1. Landing bands under their windows for the 42 types in rows L1a; t32, t2, t53, t59, t22, t73, t9 first.
2. One leaf template per form with R-LEAF-2 and R-LEAF-3; t75, t62, t61, t34, t52 (L2) and t56, t68 (L3) first. Re-site reset collector bands that stand in slots.
3. R-COL-7: emit relay path keys from the auto channel path for the crossings listed; col_h10_r0 before its GRT.
4. R-COL-8 P1/P2 station sites for col_h9_r0_p1..p6 and col_h10_r0.
KIT-OPS-4 (kit / env): nothing to roll out for leaf yet (the 17.28 um gutter blockage is unproven). For r0 column kits, offer TL-COLH9R0P2 / P6 the two forms of R-COL-8: signal max M8, and OT_MAXWIRE_UM 200 with OT_FT_MAXWIRE_UM 220.

## 6. Addendum 15:2x PST: the three runs that were still going
- t68 E2 (17.28 um gutter blockage only, re-place): 227 left after 30 iterations, against 66 for the wave placement. The lever is REJECTED as a stand-alone fix: the glue moves to the next slot (x 880-920, y 280-360). R-LEAF-3 needs the lane column moved (t68 fix: 0 in 5).
- t75 fix (vsw, vs, ve_m, ve_s +129.6 um in y, in place): 49,604 after 15 iterations against 63,816; layer total 476,498 against 1,204,815. The S strip is clear; what remains is the W strip (x 0-80, y 160-280), where ve_m is still 43.3 um off a face with 2 x 1105 bits, plus 10,177 relocated cells. So R-LEAF-2 is PARTLY shown: the corner needs the W gap opened too (86.4 um); a re-place of a real template is the proof still owed.
- col_h10_r0 baseline (3_place, plain GRT, 15 iterations): 23,454 left, owned by u_ist_frame_int_o0 31 percent, u_ft_ft0_o 20 percent, lpl_w 5 percent; hot bins x 1000-1080 y 1080-1200 and x 480 y 1120-1160; 15 percent of it on zero-capacity gcells. CORRECTION to line 4 of section 0: on col_h10_r0 the first owner is the frame-int / ft0 station strip (R-COL-8), and the col3_c crossings are second. R-COL-8 P1/P2 come before the relay path keys for col_h10_r0.
