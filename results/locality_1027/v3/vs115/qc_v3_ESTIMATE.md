# 12.14b ESTIMATE v3: qc, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_compute/die_plan.json (sha256 54a1aeb5065d), 377 partitions, 3005 ports; clock wire v = 228.8 ps/mm TT (QC measured 199 ps/mm x1.15); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map tree_s3.5c5, feed fwd

* 136 regions, max span 4.79 mm, bit-mm inside 35.4 %, 1354 crossings (600843 bits), 1 connected component(s), start-tree edges clean 135/135, max path ambiguity 0 cycles.
* **DEPTH4 1354, DEPTH8 0 (0 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 1059.3 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 167, '3': 1187}; max 3; bit-weighted mean 2.26.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'1': 637, '2': 116, '3': 411, '4': 190}; bit-weighted: {'1': 303186, '2': 93786, '3': 142908, '4': 60963}.
* Render: qc_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree_s3.5c5 | fwd | 136 | 4.79 | 35.4 % | 1354 | 1354 | 0 | 0 | 104.1 / 1059.3 | 3 | {'2': 167, '3': 1187} | -1020 / -806 |
| tree_s3.5c5 | fish | 136 | 4.79 | 35.4 % | 1354 | 1354 | 0 | 0 | 104.1 / 373.0 | 4 | {'2': 168, '3': 1088, '4': 98} | -858 / -668 |
| v1_s3.5 | fish | 142 | 3.28 | 34.1 % | 1418 | 1418 | 0 | 0 | 104.1 / 409.8 | 4 | {'2': 178, '3': 1148, '4': 92} | -825 / -635 |
| v1_s3.5 | spine | 142 | 3.28 | 34.1 % | 1418 | 1412 | 6 | 0 | 104.1 / 355.9 | 4 | {'2': 174, '3': 1001, '4': 243} | -907 / -705 |
| tree_s3.5c5 | dme | 136 | 4.79 | 35.4 % | 1354 | 782 | 572 | 0 | 104.1 / 547.3 | 4 | {'2': 402, '3': 605, '4': 347} | -235 / -132 |
| v1_s3.5 | dme | 142 | 3.28 | 34.1 % | 1418 | 814 | 604 | 0 | 104.1 / 576.2 | 4 | {'2': 390, '3': 647, '4': 381} | -217 / -116 |
| tree_s2c3.5 | fish | 248 | 3.20 | 25.4 % | 1686 | 1686 | 0 | 0 | 104.1 / 401.4 | 4 | {'2': 281, '3': 1389, '4': 16} | -4427 / -3711 |
| tree_s1.5c3 | fish | 274 | 2.68 | 25.5 % | 1759 | 1759 | 0 | 0 | 104.1 / 246.6 | 4 | {'2': 347, '3': 1388, '4': 24} | -4647 / -3899 |
| tree_s2c3.5 | fwd | 248 | 3.20 | 25.4 % | 1686 | 1684 | 2 | 0 | 104.1 / 260.4 | 4 | {'2': 198, '3': 1453, '4': 35} | -5750 / -4840 |
| tree_s1.5c3 | spine | 274 | 2.68 | 25.5 % | 1759 | 1759 | 0 | 0 | 104.1 / 240.7 | 4 | {'2': 225, '3': 1488, '4': 46} | -4653 / -3904 |
| tree_s1.5c3 | fwd | 274 | 2.68 | 25.5 % | 1759 | 1747 | 12 | 0 | 104.1 / 465.2 | 4 | {'2': 130, '3': 1571, '4': 58} | -6095 / -5133 |
| v1_s3.5 | fwd | 142 | 3.28 | 34.1 % | 1418 | 1415 | 3 | 0 | 104.1 / 204.5 | 5 | {'2': 196, '3': 1211, '4': 10, '5': 1} | -775 / -597 |
| tree_s2c3.5 | spine | 248 | 3.20 | 25.4 % | 1686 | 1682 | 4 | 0 | 104.1 / 371.6 | 5 | {'2': 237, '3': 1380, '4': 65, '5': 4} | -4432 / -3715 |
| tree_s2c3.5 | dme | 248 | 3.20 | 25.4 % | 1686 | 1030 | 656 | 0 | 104.1 / 518.8 | 5 | {'2': 616, '3': 698, '4': 366, '5': 6} | -339 / -210 |
| tree_s3.5c5 | spine | 136 | 4.79 | 35.4 % | 1354 | 1349 | 5 | 0 | 104.1 / 334.5 | 6 | {'2': 166, '3': 922, '4': 264, '6': 2} | -905 / -707 |
| tree_s1.5c3 | dme | 274 | 2.68 | 25.5 % | 1759 | 781 | 973 | 5 | 104.1 / 273.0 | 5 | {'2': 533, '3': 571, '4': 589, '5': 61} | -456 / -307 |
| slices | fish | 13 | 26.27* | 97.7 % | 264 | 264 | 0 | 0 | 104.1 / 1025.8 | 3 | {'2': 109, '3': 155} | -1369 / -1103 |
| slices | fwd | 13 | 26.27* | 97.7 % | 264 | 59 | 205 | 0 | 104.1 / 158.0 | 4 | {'2': 1, '3': 31, '4': 232} | -3903 / -3267 |
| slices | spine | 13 | 26.27* | 97.7 % | 264 | 59 | 205 | 0 | 104.1 / 278.3 | 4 | {'2': 1, '3': 38, '4': 225} | -1149 / -913 |
| slices | dme | 13 | 26.27* | 97.7 % | 264 | 38 | 226 | 0 | 104.1 / 605.9 | 4 | {'2': 6, '3': 136, '4': 122} | -198 / -100 |
| tree_s3.5c5 | top | 136 | 4.79 | 35.4 % | 1354 | 1063 | 291 | 0 | 104.1 / 772.6 | 4 | {'2': 783, '3': 403, '4': 168} | -101 / -17 |
| v1_s3.5 | top | 142 | 3.28 | 34.1 % | 1418 | 1118 | 300 | 0 | 104.1 / 770.3 | 4 | {'2': 920, '3': 331, '4': 167} | -102 / -18 |
| tree_s2c3.5 | top | 248 | 3.20 | 25.4 % | 1686 | 1340 | 346 | 0 | 104.1 / 770.4 | 4 | {'2': 1087, '3': 407, '4': 192} | -104 / -19 |
| tree_s1.5c3 | top | 274 | 2.68 | 25.5 % | 1759 | 1485 | 274 | 0 | 104.1 / 777.5 | 5 | {'2': 1215, '3': 380, '4': 162, '5': 2} | -97 / -14 |
| slices | top | 13 | 26.27* | 97.7 % | 264 | 12 | 252 | 0 | 104.1 / 733.5 | 4 | {'2': 11, '3': 120, '4': 133} | -126 / -38 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| c_E5_tn_00__rsn__0 | T099 -> T075 | 514 | on | nontree (amb 0) | 1339..1856 | 4 | 4 / 3 | 922.3 / 1059.3 |
| c_E5_tf_00__rsf__2 | T099 -> T075 | 514 | on | nontree (amb 0) | 1339..1856 | 4 | 4 / 3 | 922.3 / 1059.3 |
| c_W5_tn_00__rsn__0 | T088 -> T077 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W5_tf_00__rsf__2 | T088 -> T077 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W5_bn_00__rsn__0 | T039 -> T052 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W5_bf_00__rsf__2 | T039 -> T052 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W4_tn_00__rsn__0 | T089 -> T078 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W4_tf_00__rsf__2 | T089 -> T078 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W4_bn_00__rsn__0 | T040 -> T053 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W4_bf_00__rsf__2 | T040 -> T053 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W3_tn_00__rsn__0 | T090 -> T079 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W3_tf_00__rsf__2 | T090 -> T079 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W3_bn_00__rsn__0 | T041 -> T054 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W3_bf_00__rsf__2 | T041 -> T054 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |
| c_W2_tn_00__rsn__0 | T091 -> T080 | 514 | on | nontree (amb 0) | 1342..1854 | 4 | 4 / 3 | 925.1 / 1061.8 |

Per-crossing K/DEPTH/latency/margins: qc_v3_crossings.tsv (all 1354).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
