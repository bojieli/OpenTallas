# 12.14b ESTIMATE v3: s81, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81/die_plan.json (sha256 d3dee0f39f5c), 398 partitions, 2306 ports; clock wire v = 335 ps/mm TT (S81 measured ~335 ps/mm x1.0); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map v1_s3.5, feed fish

* 210 regions, max span 8.66 mm, bit-mm inside 37.5 %, 1336 crossings (640446 bits), 1 connected component(s), start-tree edges clean 209/209, max path ambiguity 0 cycles.
* **DEPTH4 1297, DEPTH8 39 (11740 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 187.6 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 292, '3': 955, '4': 77, '5': 12}; max 5; bit-weighted mean 2.30.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-9': 3, '-8': 2, '-7': 1, '-6': 3, '-4': 2, '-3': 5, '-2': 11, '-1': 15, '0': 26, '1': 440, '2': 100, '3': 410, '4': 233, '5': 35, '6': 15, '7': 11, '8': 5, '9': 6, '10': 2, '13': 1, '14': 3, '16': 4, '17': 3}; bit-weighted: {'-9': 604, '-8': 575, '-7': 1104, '-6': 210, '-4': 575, '-3': 3753, '-2': 3089, '-1': 4628, '0': 14233, '1': 299840, '2': 59440, '3': 161749, '4': 55303, '5': 13413, '6': 4826, '7': 8641, '8': 826, '9': 2740, '10': 838, '13': 1104, '14': 1381, '16': 928, '17': 646}.
* Render: s81_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.66 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1_s3.5 | fish | 210 | 8.66 | 37.5 % | 1336 | 1297 | 39 | 0 | 104.1 / 187.6 | 5 | {'2': 292, '3': 955, '4': 77, '5': 12} | -11920 / -10097 |
| v1_s3.5 | spine | 210 | 8.66 | 37.5 % | 1336 | 1279 | 57 | 0 | 104.1 / 113.3 | 5 | {'2': 172, '3': 1055, '4': 76, '5': 33} | -11937 / -10111 |
| tree_s2c3.5 | fish | 376 | 8.66 | 7.1 % | 2109 | 2088 | 21 | 0 | 104.1 / 130.3 | 5 | {'2': 71, '3': 1972, '4': 65, '5': 1} | -7534 / -6354 |
| tree_s1.5c3 | fish | 376 | 8.66 | 7.1 % | 2109 | 2088 | 21 | 0 | 104.1 / 130.3 | 5 | {'2': 71, '3': 1972, '4': 65, '5': 1} | -7534 / -6354 |
| tree_s3.5c5 | fish | 194 | 8.66 | 41.9 % | 1222 | 1165 | 57 | 0 | 104.1 / 126.5 | 6 | {'2': 252, '3': 850, '4': 101, '5': 11, '6': 8} | -8106 / -6835 |
| tree_s2c3.5 | spine | 376 | 8.66 | 7.1 % | 2109 | 2079 | 30 | 0 | 104.1 / 113.3 | 6 | {'2': 46, '3': 1971, '4': 80, '5': 11, '6': 1} | -7550 / -6368 |
| tree_s1.5c3 | spine | 376 | 8.66 | 7.1 % | 2109 | 2079 | 30 | 0 | 104.1 / 113.3 | 6 | {'2': 46, '3': 1971, '4': 80, '5': 11, '6': 1} | -7550 / -6368 |
| tree_s3.5c5 | spine | 194 | 8.66 | 41.9 % | 1222 | 1136 | 55 | 31 | 104.1 / 111.0 | 6 | {'2': 167, '3': 892, '4': 123, '5': 8, '6': 1} | -8123 / -6849 |
| tree_s2c3.5 | fwd | 376 | 8.66 | 7.1 % | 2109 | 1956 | 112 | 41 | 104.1 / 144.3 | 8 | {'2': 245, '3': 1582, '4': 183, '5': 26, '6': 23, '7': 6, '8': 3} | -11365 / -9621 |
| tree_s1.5c3 | fwd | 376 | 8.66 | 7.1 % | 2109 | 1956 | 112 | 41 | 104.1 / 144.3 | 8 | {'2': 245, '3': 1582, '4': 183, '5': 26, '6': 23, '7': 6, '8': 3} | -11365 / -9621 |
| tree_s3.5c5 | fwd | 194 | 8.66 | 41.9 % | 1222 | 1035 | 139 | 48 | 104.1 / 149.5 | 7 | {'2': 30, '3': 737, '4': 335, '5': 49, '6': 16, '7': 7} | -10816 / -9144 |
| v1_s3.5 | fwd | 210 | 8.66 | 37.5 % | 1336 | 1106 | 160 | 70 | 104.1 / 136.5 | 7 | {'2': 38, '3': 782, '4': 374, '5': 63, '6': 8, '7': 1} | -15831 / -13432 |
| tree_s3.5c5 | dme | 194 | 8.66 | 41.9 % | 1222 | 452 | 642 | 128 | 104.1 / 163.4 | 6 | {'2': 260, '3': 369, '4': 394, '5': 61, '6': 10} | -1068 / -797 |
| v1_s3.5 | dme | 210 | 8.66 | 37.5 % | 1336 | 482 | 718 | 136 | 104.1 / 146.6 | 7 | {'2': 262, '3': 423, '4': 395, '5': 98, '6': 20, '7': 2} | -1149 / -863 |
| tree_s2c3.5 | dme | 376 | 8.66 | 7.1 % | 2109 | 1066 | 881 | 162 | 104.1 / 109.0 | 7 | {'2': 665, '3': 662, '4': 577, '5': 25, '6': 16, '7': 2} | -935 / -691 |
| tree_s1.5c3 | dme | 376 | 8.66 | 7.1 % | 2109 | 1066 | 881 | 162 | 104.1 / 109.0 | 7 | {'2': 665, '3': 662, '4': 577, '5': 25, '6': 16, '7': 2} | -935 / -691 |
| dies81 | fish | 91 | 11.54* | 58.6 % | 948 | 843 | 81 | 24 | 104.1 / 108.5 | 6 | {'2': 160, '3': 629, '4': 101, '5': 24, '6': 10} | -12559 / -10638 |
| land179 | fish | 179 | 11.54* | 47.6 % | 1173 | 1097 | 52 | 24 | 104.1 / 130.2 | 6 | {'2': 226, '3': 808, '4': 88, '5': 23, '6': 4} | -10557 / -8930 |
| dies81 | fwd | 91 | 11.54* | 58.6 % | 948 | 777 | 137 | 34 | 104.1 / 124.3 | 7 | {'2': 8, '3': 515, '4': 319, '5': 58, '6': 10, '7': 4} | -17221 / -14611 |
| dies81 | spine | 91 | 11.54* | 58.6 % | 948 | 583 | 322 | 43 | 104.1 / 133.0 | 6 | {'2': 105, '3': 432, '4': 311, '5': 44, '6': 13} | -13008 / -11020 |
| land179 | spine | 179 | 11.54* | 47.6 % | 1173 | 1024 | 105 | 44 | 104.1 / 133.0 | 6 | {'2': 117, '3': 870, '4': 101, '5': 34, '6': 7} | -10574 / -8943 |
| land179 | fwd | 179 | 11.54* | 47.6 % | 1173 | 1006 | 113 | 54 | 104.1 / 120.9 | 7 | {'2': 52, '3': 718, '4': 305, '5': 32, '6': 8, '7': 4} | -14803 / -12548 |
| land179 | dme | 179 | 11.54* | 47.6 % | 1173 | 411 | 637 | 125 | 104.1 / 148.7 | 7 | {'2': 223, '3': 341, '4': 392, '5': 79, '6': 9, '7': 4} | -1075 / -805 |
| dies81 | dme | 91 | 11.54* | 58.6 % | 948 | 209 | 545 | 194 | 104.1 / 132.2 | 7 | {'2': 102, '3': 277, '4': 281, '5': 69, '6': 16, '7': 9} | -1195 / -904 |
| tree_s2c3.5 | top | 376 | 8.66 | 7.1 % | 2109 | 1545 | 530 | 34 | 104.1 / 394.2 | 6 | {'2': 590, '3': 1150, '4': 282, '5': 38, '6': 15} | -376 / -247 |
| tree_s1.5c3 | top | 376 | 8.66 | 7.1 % | 2109 | 1545 | 530 | 34 | 104.1 / 394.2 | 6 | {'2': 590, '3': 1150, '4': 282, '5': 38, '6': 15} | -376 / -247 |
| tree_s3.5c5 | top | 194 | 8.66 | 41.9 % | 1222 | 669 | 496 | 57 | 104.1 / 394.2 | 6 | {'2': 208, '3': 641, '4': 262, '5': 27, '6': 27} | -380 / -250 |
| v1_s3.5 | top | 210 | 8.66 | 37.5 % | 1336 | 764 | 508 | 64 | 104.1 / 394.2 | 6 | {'2': 228, '3': 727, '4': 256, '5': 26, '6': 35} | -376 / -247 |
| dies81 | top | 91 | 11.54* | 58.6 % | 948 | 181 | 667 | 100 | 104.1 / 316.3 | 7 | {'2': 72, '3': 347, '4': 347, '5': 49, '6': 31, '7': 2} | -433 / -293 |
| land179 | top | 179 | 11.54* | 47.6 % | 1173 | 315 | 719 | 139 | 104.1 / 304.8 | 6 | {'2': 159, '3': 421, '4': 388, '5': 38, '6': 28} | -450 / -307 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| ctrl__s_0N_C__seqhost__10 | R056 -> R057 | 571 | OFF | nontree (amb 0) | 988..4111 | 8 | -9 / 5 | 571.8 / 2136.5 |
| vid_svc_1__seqhost__2 | R056 -> R057 | 1 | OFF | nontree (amb 0) | 988..4111 | 8 | -9 / 5 | 571.8 / 2136.5 |
| idx__s_3S_C__iqf__4 | R057 -> R056 | 513 | OFF | nontree (amb 0) | 887..4010 | 8 | 17 / 4 | 470.5 / 2237.8 |
| unit__seqhost__s_0N_C__1 | R057 -> R056 | 132 | OFF | nontree (amb 0) | 887..4010 | 8 | 17 / 4 | 470.5 / 2237.8 |
| vid_seqhost__svc_0__1 | R057 -> R056 | 1 | OFF | nontree (amb 0) | 887..4010 | 8 | 17 / 4 | 470.5 / 2237.8 |
| attn__svc_5__s_3S_C__0 | R033 -> R057 | 562 | OFF | nontree (amb 0) | 1166..3893 | 8 | -8 / 5 | 749.2 / 2354.6 |
| unit__svc_5__seqhost__0 | R033 -> R057 | 13 | OFF | nontree (amb 0) | 1166..3893 | 8 | -8 / 5 | 749.2 / 2354.6 |
| xtier__seqhost__s_4N_C__6 | R111 -> R132 | 276 | OFF | nontree (amb 0) | 1291..3890 | 8 | 9 / 4 | 874.5 / 2357.5 |
| unit__seqhost__gunit__6 | R111 -> R132 | 267 | OFF | nontree (amb 0) | 1291..3890 | 8 | 9 / 4 | 874.5 / 2357.5 |
| unit__seqhost__svc_5__1 | R057 -> R033 | 325 | OFF | nontree (amb 0) | 1105..3832 | 8 | 16 / 4 | 688.6 / 2415.2 |
| attn__s_3S_C__svc_5__4 | R057 -> R033 | 513 | OFF | nontree (amb 0) | 1105..3832 | 8 | 16 / 4 | 688.6 / 2415.2 |
| xtier__s_4S_C__bk_sel__2 | R112 -> R122 | 276 | OFF | nontree (amb 0) | 1291..3769 | 8 | 8 / 4 | 874.5 / 2478.9 |
| xtier__bk_sel__s_4S_C__8 | R122 -> R112 | 276 | OFF | nontree (amb 0) | 1229..3707 | 8 | 0 / 5 | 812.9 / 2540.5 |
| xtier__s_4N_C__seqhost__3 | R132 -> R111 | 276 | OFF | nontree (amb 0) | 1108..3707 | 8 | -1 / 5 | 691.5 / 2540.5 |
| xtier__gunit__s_3S_C__7 | R132 -> R111 | 276 | OFF | nontree (amb 0) | 1108..3707 | 8 | -1 / 5 | 691.5 / 2540.5 |

Per-crossing K/DEPTH/latency/margins: s81_v3_crossings.tsv (all 1336).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
