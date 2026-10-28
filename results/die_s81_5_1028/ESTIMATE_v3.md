# 12.14b ESTIMATE v3: s81, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan plan_base.json (sha256 06301f33d226), 398 partitions, 2306 ports; clock wire v = 351.75 ps/mm TT (335 ps/mm x1.05 spice (12.15b plan tools)); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map v1_s3.5, feed fish

* 210 regions, max span 8.66 mm, bit-mm inside 37.5 %, 1336 crossings (640446 bits), 1 connected component(s), start-tree edges clean 209/209, max path ambiguity 0 cycles.
* **DEPTH4 1290, DEPTH8 46 (13981 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 337.6 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 295, '3': 943, '4': 86, '5': 12}; max 5; bit-weighted mean 2.32.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-10': 2, '-9': 3, '-7': 1, '-6': 3, '-4': 2, '-3': 5, '-2': 11, '-1': 15, '0': 36, '1': 440, '2': 90, '3': 402, '4': 240, '5': 35, '6': 13, '7': 8, '8': 11, '9': 6, '11': 2, '14': 1, '15': 3, '16': 2, '17': 2, '18': 3}; bit-weighted: {'-10': 572, '-9': 607, '-7': 1104, '-6': 210, '-4': 575, '-3': 3753, '-2': 3089, '-1': 4628, '0': 17022, '1': 308607, '2': 47884, '3': 154709, '4': 61239, '5': 13397, '6': 4318, '7': 5544, '8': 5551, '9': 2740, '11': 838, '14': 1104, '15': 1381, '16': 838, '17': 90, '18': 646}.
* Render:  (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.66 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1_s3.5 | fish | 210 | 8.66 | 37.5 % | 1336 | 1290 | 46 | 0 | 104.1 / 337.6 | 5 | {'2': 295, '3': 943, '4': 86, '5': 12} | -12533 / -10620 |
| tree_s2c3.5 | fish | 376 | 8.66 | 7.1 % | 2109 | 2066 | 43 | 0 | 104.1 / 235.8 | 5 | {'2': 85, '3': 1950, '4': 63, '5': 11} | -7928 / -6690 |
| tree_s2c3.5 | spine | 376 | 8.66 | 7.1 % | 2109 | 2054 | 55 | 0 | 104.1 / 146.9 | 6 | {'2': 59, '3': 1933, '4': 91, '5': 10, '6': 16} | -7945 / -6704 |
| part | fish | 398 | 8.66 | 0.0 % | 2306 | 2271 | 35 | 0 | 104.1 / 115.5 | 6 | {'2': 69, '3': 2197, '4': 28, '5': 6, '6': 6} | -10511 / -8892 |
| part | spine | 398 | 8.66 | 0.0 % | 2306 | 2270 | 36 | 0 | 104.1 / 122.6 | 6 | {'2': 58, '3': 2193, '4': 43, '5': 5, '6': 7} | -10528 / -8906 |
| tree_s3.5c5 | fish | 194 | 8.66 | 41.9 % | 1222 | 1151 | 67 | 4 | 104.1 / 105.1 | 7 | {'2': 245, '3': 845, '4': 106, '5': 9, '6': 5, '7': 8} | -8529 / -7195 |
| v1_s3.5 | spine | 210 | 8.66 | 37.5 % | 1336 | 1233 | 78 | 25 | 104.1 / 118.3 | 7 | {'2': 262, '3': 797, '4': 222, '5': 18, '6': 7, '7': 5} | -12551 / -10634 |
| tree_s3.5c5 | spine | 194 | 8.66 | 41.9 % | 1222 | 1107 | 80 | 35 | 104.1 / 114.0 | 6 | {'2': 215, '3': 663, '4': 282, '5': 22, '6': 5} | -8546 / -7209 |
| tree_s2c3.5 | fwd | 376 | 8.66 | 7.1 % | 2109 | 1953 | 112 | 44 | 104.1 / 117.4 | 8 | {'2': 239, '3': 1585, '4': 189, '5': 27, '6': 17, '7': 5, '8': 3} | -11950 / -10120 |
| part | fwd | 398 | 8.66 | 0.0 % | 2306 | 2145 | 117 | 44 | 104.1 / 112.5 | 8 | {'2': 252, '3': 1768, '4': 196, '5': 26, '6': 14, '7': 3, '8': 3} | -17042 / -14460 |
| v1_s3.5 | fwd | 210 | 8.66 | 37.5 % | 1336 | 1123 | 161 | 52 | 104.1 / 105.6 | 7 | {'2': 26, '3': 833, '4': 331, '5': 70, '6': 20, '7': 4} | -16640 / -14121 |
| tree_s3.5c5 | fwd | 194 | 8.66 | 41.9 % | 1222 | 1014 | 151 | 57 | 104.1 / 114.7 | 7 | {'2': 18, '3': 796, '4': 285, '5': 55, '6': 7, '7': 4} | -11374 / -9619 |
| tree_s3.5c5 | dme | 194 | 8.66 | 41.9 % | 1222 | 450 | 627 | 145 | 104.1 / 117.6 | 6 | {'2': 260, '3': 365, '4': 374, '5': 68, '6': 10} | -1137 / -854 |
| tree_s2c3.5 | dme | 376 | 8.66 | 7.1 % | 2109 | 1046 | 890 | 173 | 104.1 / 139.2 | 7 | {'2': 624, '3': 689, '4': 564, '5': 41, '6': 16, '7': 2} | -997 / -743 |
| v1_s3.5 | dme | 210 | 8.66 | 37.5 % | 1336 | 481 | 679 | 176 | 104.1 / 117.6 | 7 | {'2': 259, '3': 417, '4': 369, '5': 93, '6': 20, '7': 2} | -1222 / -923 |
| part | dme | 398 | 8.66 | 0.0 % | 2306 | 1120 | 982 | 204 | 104.1 / 139.2 | 7 | {'2': 695, '3': 760, '4': 620, '5': 14, '6': 12, '7': 1} | -955 / -708 |
| part | top | 398 | 8.66 | 0.0 % | 2306 | 1773 | 511 | 22 | 104.1 / 341.0 | 6 | {'2': 534, '3': 1432, '4': 263, '5': 28, '6': 27} | -412 / -277 |
| tree_s2c3.5 | top | 376 | 8.66 | 7.1 % | 2109 | 1545 | 530 | 34 | 104.1 / 341.0 | 6 | {'2': 474, '3': 1266, '4': 282, '5': 38, '6': 15} | -412 / -277 |
| tree_s3.5c5 | top | 194 | 8.66 | 41.9 % | 1222 | 669 | 496 | 57 | 104.1 / 341.0 | 6 | {'2': 172, '3': 677, '4': 262, '5': 27, '6': 27} | -416 / -280 |
| v1_s3.5 | top | 210 | 8.66 | 37.5 % | 1336 | 764 | 508 | 64 | 104.1 / 341.0 | 6 | {'2': 187, '3': 768, '4': 256, '5': 26, '6': 35} | -412 / -277 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| idx__s_3S_C__iqf__4 | R057 -> R056 | 513 | OFF | nontree (amb 0) | 1107..4369 | 8 | 18 / 4 | 690.5 / 1878.8 |
| unit__seqhost__s_0N_C__1 | R057 -> R056 | 132 | OFF | nontree (amb 0) | 1107..4369 | 8 | 18 / 4 | 690.5 / 1878.8 |
| vid_seqhost__svc_0__1 | R057 -> R056 | 1 | OFF | nontree (amb 0) | 1107..4369 | 8 | 18 / 4 | 690.5 / 1878.8 |
| ctrl__s_0N_LP__seqhost__11 | R065 -> R066 | 32 | OFF | nontree (amb 0) | 1068..4155 | 8 | -9 / 5 | 651.7 / 2092.4 |
| rt_W2_out_0__7 | R096 -> R090 | 70 | OFF | nontree (amb 0) | 1288..4077 | 8 | -6 / 5 | 871.5 / 2170.7 |
| rt_W2_out_1__8 | R096 -> R090 | 70 | OFF | nontree (amb 0) | 1288..4077 | 8 | -6 / 5 | 871.5 / 2170.7 |
| rt_W2_out_2__9 | R096 -> R090 | 70 | OFF | nontree (amb 0) | 1288..4077 | 8 | -6 / 5 | 871.5 / 2170.7 |
| xring__s_2S_C__s_3S_C__0 | R080 -> R090 | 1104 | OFF | nontree (amb 0) | 1238..4075 | 8 | -7 / 5 | 821.0 / 2172.6 |
| xtier__s_4N_C__seqhost__3 | R132 -> R111 | 276 | OFF | nontree (amb 0) | 1255..3966 | 8 | -1 / 5 | 838.8 / 2281.4 |
| xtier__gunit__s_3S_C__7 | R132 -> R111 | 276 | OFF | nontree (amb 0) | 1255..3966 | 8 | -1 / 5 | 838.8 / 2281.4 |
| unit__seqhost__s_0S_LP__1 | R066 -> R065 | 45 | OFF | nontree (amb 0) | 843..3930 | 8 | 17 / 4 | 426.4 / 2317.7 |
| unit__seqhost__s_0N_LP__1 | R066 -> R065 | 45 | OFF | nontree (amb 0) | 843..3930 | 8 | 17 / 4 | 426.4 / 2317.7 |
| xtier__bk_sel__s_4S_C__8 | R122 -> R112 | 276 | OFF | nontree (amb 0) | 1341..3924 | 8 | 0 / 5 | 924.6 / 2323.0 |
| ctrl__s_0N_C__seqhost__10 | R056 -> R057 | 571 | OFF | nontree (amb 0) | 629..3891 | 8 | -10 / 5 | 212.8 / 2356.5 |
| vid_svc_1__seqhost__2 | R056 -> R057 | 1 | OFF | nontree (amb 0) | 629..3891 | 8 | -10 / 5 | 212.8 / 2356.5 |

Per-crossing K/DEPTH/latency/margins: s81_v3_crossings.tsv (all 1336).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
