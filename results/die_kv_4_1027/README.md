# DIE-KV-4 (2026-10-27 23:2x-00:0x PDT) — KV die: x1.05 CA fix, QK-CORES-11 plan delta D9c, spice die STA, strap kit list

Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-4-1027 (proto/ = CA, pd9c/ = plan, kit_q9b|kit_q9c, sta_*).
Clock = DIE-KV-3 H200B (die_trial link_htree, leaf 200, rep 250, site-legal+slide) — inputs reproduced byte-identically.

## 1. The 7 crossings that failed at x1.05 (METHODOLOGY 12.15b)
Cause: the MESO-INTEG-1 planner (undirected Kruskal start tree) put pv_S_0/1 and hgi_WS_0/1 5 ambiguous tree edges apart, so
L width = 1.58 ns phase + 5 T > the D8 window (7 T - 2 ap). Neither D8 nor PAD+1 fixes that: they already were D8-sized
(L_hi 6.46-6.76 ns > 7.5 T - ap = 6.14 ns) and PAD is a constant per tree edge (it moves the origin, not the ambiguity).
D16 is RTL-legal but not formally proven (k-induction covers D4/D8 only).
Fix = the MESO-RECONCILE single-convention planner (count_align_plan.py @ claude/meso-reconcile-1027 cc2a50738 / 32e8cbb16,
identical plan() for default PAD): directed start tree with the fewest ambiguous edges (0-1 BFS per root). No tool change here.
Same measured H200B rows (landed_phase_ocv, GRT-RC, shared derate), per-corner spice scale (ca_spice.py):

| scale | D4 | D8 | FAIL | amb tree edges | max path amb | worst lo / hi margin | MC chips / viol |
|---|---|---|---|---|---|---|---|
| x1.00 | 3460 | 135 | 0 | 4 | 2 | 105.8 / 105.8 | 600 / 0 |
| x1.05 | 3321 | 274 | 0 | 10 | 3 | 108.4 / 187.6 | 600 / 0 |
| spice x1.0485 TT / x1.0552 FF | 3393 | 202 | 0 | 9 | 3 | 106.2 / 110.4 | 2000 / 0 (106.2 / 110.5) |

(DIE-KV-3 MESO-INTEG-1 planner: x1.00 0 FAIL, x1.05 7 FAIL.)  All CHECKED-own, UNCHECKED-indep.

Per affected link (ca/lanes_report.txt): the 7 ports all D8 at spice, margins lo/hi >= 137.7 / 1133.9 ps.
Lane latency (sum of landing sched_lat in the lane, KV-3 x1.00 -> spice): L2192 14->16 (+2), L2197 11->12 (+1), L2374 5->4,
L2390 9->7, L2391 7->5, L2401 9->7, L2402 6->5. Die-wide vs KV-3 x1.00: 216 lanes up (+236 cycles total, max +2), 116 down;
total landing cycles vs the old +3 ring: -1298. Static schedule: every KV lane latency is a plan parameter (LAT_Lxx =
natural + landing, pad 0), none of the 7 lanes is in a latency_group; the 3 r8 replica groups are unchanged ([2,6] before and
after). OWNER 12.15c: added latency accepted; TOK re-price of the +236 cycles is the KV-TOK step (not run here).

## 2. Plan event D9c (QK-CORES-11 default: kits carry islands + fMX MX ft_ck pins, plan follows)
hm_r26q9c = hm_r26q9b + (a) cores/kv3_pv_pair_pins_r26c.json (r25 + core_tree: entry island + 4 FIRM quadrant islands,
R0 slice) and cores/kv3_pv_pair_pins_fMX_r26c.json (pins_view_image MX of r25: ft_ck_i/o_0 (267.0|270.84, 146.745),
ft_ck_i/o_1 (106.344|111.816, 51.705) = GEOM-REVIEW-39 kit values; island_ft rects imaged; core_tree = fMX slice);
(b) 256 pins_file refs r25 -> r26c; (c) clock.mesh.core_islands.kv3_pv_pair.rects_um + the 3 MX-image cell rects.
Fail-closed: fMX islands = MX image of R0 as a set; no ft cell overlaps an island.
schema PASS, G0 PASS 0 err / 1892 WARN, G0C PASS 0 err / 1892 WARN (q9b A/B with the same check.py: G0C PASS 0 / 1892).
Die GRT0: die_trial kit on q9c == kit on q9b == DIE-KV-3 kit_h200b, every file byte-identical except kit.json (plan path/sha)
and renders -> the H200B die GRT incl clock (TT+FF, 50 it, -critical_nets_percentage 0, overflow 0 M1-M9, EXIT 0) holds for q9c.

## 3. Die STA (12.15b spice clock, related pairs, --cppr-lca, TT 250 / FF 202.5, droop class, AOCV table, HB4)
REAL VIEWS: none usable. No signed view (core.json + provenance pins_file) matches any q9c pins_file (30 modules, 663 inst);
kit-run views exist (kv-cores-r8 pv_pair fMX, flow-shared-10 e1, droop-recheck e5) but are not signed off and carry pre-r26
pins -> coverage 0/663, numbers below are modelled-core.
| run | intra TT setup | intra FF hold raw | intra skew TT/FF | intra kit-contract W80 | seam skew TT/FF | seam kit-contract |
|---|---|---|---|---|---|---|
| main tool, x1.00 | +511.23 | -129.71 | 98.56 / 86.26 | -6.26 (12 pairs) | 169.70 / 146.28 | -66.28 (323) |
| main tool, pre-scaled taps (scale_proof.py) | +504.65 | -136.22 | 103.34 / 91.02 | -11.02 (24) | 177.93 / 154.35 | -74.35 (339) |
| MESO-RECONCILE-2 --clock-cal spice (32e8cbb16) | +480.85 | -159.11 | 103.34 / 91.02 | -11.02 (24) | 177.93 / 154.35 | -74.35 (339) |
Skews and kit-contract numbers agree exactly between the two spice methods; raw setup/hold differ by ~24 ps (the reconcile tool
also scales terms the pre-scale does not reach) -> the reconcile tool is the gate number once merged.
ASK1 form (HB4 on the kit-contract pairs, accepted 22:43): 24 intra + 339 seam pairs at spice (was 12 + 323).
In-region spread 103.3 TT / 91.0 FF <= 150 (12.15c), CHECKED-own.

## 4. K straps (OWNER 12.15a): strap kit list only (strap/strap_kits_spice.json)
51 receiving types = 51 strap kits (DEPTH per bus = max over instances; 165 D8 buses), LEC variants 112 (type-split kits that
are now dropped: 112 on this plan; DIE-KV-3 counted 119 on its plan). Largest: kv3_pc_v1 24 inst / 29 buses all D8 / 11
variants; kv3_phy_v1 28 / 1 / 7. K frame = region; the ca-origin partition-frame offsets of the 32 multi-partition regions
are applied at bind (UNCHECKED here). Not built.
