# 12.14b ESTIMATE v3: qc, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_compute/die_plan.json (sha256 54a1aeb5065d), 377 partitions, 3005 ports; clock wire v = 199 ps/mm TT (QC measured 199 ps/mm x1.0); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map tree_s3.5c5, feed fish

* 136 regions, max span 4.79 mm, bit-mm inside 35.4 %, 1354 crossings (600843 bits), 1 connected component(s), start-tree edges clean 135/135, max path ambiguity 0 cycles.
* **DEPTH4 1354, DEPTH8 0 (0 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 1125.3 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 52, '3': 1302}; max 3; bit-weighted mean 2.50.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'1': 65, '2': 688, '3': 590, '4': 11}; bit-weighted: {'1': 21144, '2': 375318, '3': 201626, '4': 2755}.
* Render: qc_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree_s3.5c5 | fish | 136 | 4.79 | 35.4 % | 1354 | 1354 | 0 | 0 | 104.1 / 1125.3 | 3 | {'2': 52, '3': 1302} | -697 / -531 |
| tree_s3.5c5 | fwd | 136 | 4.79 | 35.4 % | 1354 | 1354 | 0 | 0 | 104.1 / 320.8 | 4 | {'2': 238, '3': 1111, '4': 5} | -838 / -651 |
| v1_s3.5 | fwd | 142 | 3.28 | 34.1 % | 1418 | 1418 | 0 | 0 | 104.1 / 416.3 | 4 | {'2': 246, '3': 1169, '4': 3} | -624 / -468 |
| tree_s3.5c5 | spine | 136 | 4.79 | 35.4 % | 1354 | 1354 | 0 | 0 | 104.1 / 271.5 | 4 | {'2': 46, '3': 1223, '4': 85} | -739 / -565 |
| v1_s3.5 | fish | 142 | 3.28 | 34.1 % | 1418 | 1418 | 0 | 0 | 104.1 / 885.5 | 4 | {'2': 51, '3': 1365, '4': 2} | -671 / -504 |
| tree_s3.5c5 | dme | 136 | 4.79 | 35.4 % | 1354 | 808 | 546 | 0 | 104.1 / 665.9 | 4 | {'2': 592, '3': 430, '4': 332} | -160 / -68 |
| v1_s3.5 | spine | 142 | 3.28 | 34.1 % | 1418 | 1418 | 0 | 0 | 104.1 / 400.9 | 4 | {'2': 48, '3': 1292, '4': 78} | -741 / -564 |
| v1_s3.5 | dme | 142 | 3.28 | 34.1 % | 1418 | 926 | 492 | 0 | 104.1 / 691.0 | 4 | {'2': 593, '3': 514, '4': 311} | -144 / -54 |
| tree_s1.5c3 | fish | 274 | 2.68 | 25.5 % | 1759 | 1759 | 0 | 0 | 104.1 / 882.2 | 4 | {'2': 173, '3': 1574, '4': 12} | -3994 / -3342 |
| tree_s2c3.5 | fish | 248 | 3.20 | 25.4 % | 1686 | 1686 | 0 | 0 | 104.1 / 376.2 | 4 | {'2': 96, '3': 1586, '4': 4} | -3802 / -3178 |
| tree_s1.5c3 | spine | 274 | 2.68 | 25.5 % | 1759 | 1759 | 0 | 0 | 104.1 / 348.5 | 4 | {'2': 166, '3': 1541, '4': 52} | -3999 / -3346 |
| tree_s2c3.5 | spine | 248 | 3.20 | 25.4 % | 1686 | 1686 | 0 | 0 | 104.1 / 370.7 | 4 | {'2': 59, '3': 1623, '4': 4} | -3808 / -3182 |
| tree_s2c3.5 | fwd | 248 | 3.20 | 25.4 % | 1686 | 1668 | 18 | 0 | 104.1 / 186.4 | 5 | {'2': 245, '3': 1385, '4': 48, '5': 8} | -4954 / -4161 |
| tree_s1.5c3 | fwd | 274 | 2.68 | 25.5 % | 1759 | 1743 | 16 | 0 | 104.1 / 416.3 | 5 | {'2': 224, '3': 1455, '4': 68, '5': 12} | -5253 / -4416 |
| tree_s2c3.5 | dme | 248 | 3.20 | 25.4 % | 1686 | 1040 | 646 | 0 | 104.1 / 641.1 | 5 | {'2': 659, '3': 659, '4': 362, '5': 6} | -251 / -137 |
| tree_s1.5c3 | dme | 274 | 2.68 | 25.5 % | 1759 | 841 | 918 | 0 | 104.1 / 518.9 | 6 | {'2': 598, '3': 561, '4': 543, '5': 54, '6': 3} | -353 / -221 |
| slices | fish | 13 | 26.27* | 97.7 % | 264 | 264 | 0 | 0 | 104.1 / 343.2 | 4 | {'2': 9, '3': 243, '4': 12} | -1142 / -910 |
| slices | spine | 13 | 26.27* | 97.7 % | 264 | 264 | 0 | 0 | 104.1 / 105.9 | 4 | {'2': 9, '3': 146, '4': 109} | -952 / -745 |
| slices | fwd | 13 | 26.27* | 97.7 % | 264 | 243 | 21 | 0 | 104.1 / 118.3 | 4 | {'2': 9, '3': 126, '4': 129} | -3346 / -2792 |
| slices | dme | 13 | 26.27* | 97.7 % | 264 | 59 | 205 | 0 | 104.1 / 716.9 | 4 | {'2': 9, '3': 144, '4': 111} | -127 / -40 |
| tree_s3.5c5 | top | 136 | 4.79 | 35.4 % | 1354 | 1105 | 249 | 0 | 104.1 / 861.8 | 4 | {'2': 866, '3': 340, '4': 148} | -42 / 33 |
| v1_s3.5 | top | 142 | 3.28 | 34.1 % | 1418 | 1160 | 258 | 0 | 104.1 / 859.8 | 4 | {'2': 921, '3': 350, '4': 147} | -43 / 32 |
| tree_s2c3.5 | top | 248 | 3.20 | 25.4 % | 1686 | 1340 | 346 | 0 | 104.1 / 859.9 | 4 | {'2': 1090, '3': 404, '4': 192} | -45 / 31 |
| tree_s1.5c3 | top | 274 | 2.68 | 25.5 % | 1759 | 1485 | 274 | 0 | 104.1 / 866.1 | 5 | {'2': 1218, '3': 377, '4': 162, '5': 2} | -39 / 36 |
| slices | top | 13 | 26.27* | 97.7 % | 264 | 94 | 170 | 0 | 104.1 / 827.9 | 4 | {'2': 11, '3': 164, '4': 89} | -64 / 14 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| coll_core__crec_tx_s2__3 | T037 -> T012 | 548 | on | nontree (amb 0) | 1349..1790 | 4 | 2 / 3 | 932.9 / 1125.3 |
| sl_E5_fw__ag_eo_ag_wi__0 | T075 -> T074 | 10 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__ard_eo_ard_wi__0 | T075 -> T074 | 512 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__arl_eo_arl_wi__0 | T075 -> T074 | 1 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__arm_eo_arm_wi__0 | T075 -> T074 | 1 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__art_eo_art_wi__0 | T075 -> T074 | 32 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__arv_eo_arv_wi__0 | T075 -> T074 | 1 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__dd_eo_dd_wi__0 | T075 -> T074 | 548 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fe__l9_eo_l9_wi__3 | T075 -> T074 | 514 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__sc_eo_sc_wi__0 | T075 -> T074 | 48 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__st_eo_st_wi__0 | T075 -> T074 | 1087 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E5_fw__flte__0 | T075 -> T074 | 1 | on | nontree (amb 0) | 1281..1777 | 4 | 4 / 3 | 864.5 / 1138.9 |
| sl_E0_fw__ard_eo_ard_ei__0 | T070 -> T069 | 512 | on | nontree (amb 0) | 1334..1770 | 4 | 2 / 3 | 917.3 / 1145.5 |
| sl_E0_fw__arl_eo_arl_ei__0 | T070 -> T069 | 1 | on | nontree (amb 0) | 1334..1770 | 4 | 2 / 3 | 917.3 / 1145.5 |
| sl_E0_fw__arm_eo_arm_ei__0 | T070 -> T069 | 1 | on | nontree (amb 0) | 1334..1770 | 4 | 2 / 3 | 917.3 / 1145.5 |

Per-crossing K/DEPTH/latency/margins: qc_v3_crossings.tsv (all 1354).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
