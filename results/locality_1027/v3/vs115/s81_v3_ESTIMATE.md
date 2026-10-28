# 12.14b ESTIMATE v3: s81, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81/die_plan.json (sha256 d3dee0f39f5c), 398 partitions, 2306 ports; clock wire v = 385.2 ps/mm TT (S81 measured ~335 ps/mm x1.15); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map tree_s2c3.5, feed fwd

* 376 regions, max span 8.66 mm, bit-mm inside 7.1 %, 2109 crossings (1017563 bits), 1 connected component(s), start-tree edges clean 368/375, max path ambiguity 3 cycles.
* **DEPTH4 2020, DEPTH8 85 (39588 bits), FAIL even at DEPTH8 4 (1104 bits)**; worst margin low 104.1 ps / high 105.2 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 354, '3': 1581, '4': 129, '5': 20, '6': 14, '7': 7}; max 7; bit-weighted mean 2.38.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-9': 1, '-7': 3, '-5': 8, '-4': 9, '-3': 16, '-2': 11, '-1': 10, '0': 29, '1': 491, '2': 370, '3': 913, '4': 110, '5': 46, '6': 15, '7': 32, '8': 4, '9': 14, '10': 9, '12': 3, '13': 1, '14': 2, '15': 5, '19': 3}; bit-weighted: {'-9': 1104, '-7': 579, '-5': 3612, '-4': 4154, '-3': 8504, '-2': 2501, '-1': 7096, '0': 12495, '1': 418643, '2': 175535, '3': 252260, '4': 75896, '5': 20188, '6': 4407, '7': 14846, '8': 1424, '9': 1945, '10': 3694, '12': 1672, '13': 1120, '14': 545, '15': 3133, '19': 1106}.
* Render: s81_v3_best_cap.png, s81_v3_best_cap_hop.png (VIEWED).

Hop chains (12.13c) ONLY for the 4 D8-fail crossings: 4 chains (0 already on-feed, cannot be chained), max 31 hops, 32568 extra bit-hops, 0 synthetic feed-edge crossings; after re-timing: D4 2020, D8 85, FAIL 0; chain latency (cycles: chains) {'109': 2, '112': 2} (landing cycles only, intra-region transit not counted).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.66 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree_s2c3.5 | fwd | 376 | 8.66 | 7.1 % | 2109 | 2020 | 85 | 4 | 104.1 / 105.2 | 7 | {'2': 354, '3': 1581, '4': 129, '5': 20, '6': 14, '7': 7} | -13119 / -11116 |
| tree_s1.5c3 | fwd | 376 | 8.66 | 7.1 % | 2109 | 2020 | 85 | 4 | 104.1 / 105.2 | 7 | {'2': 354, '3': 1581, '4': 129, '5': 20, '6': 14, '7': 7} | -13119 / -11116 |
| tree_s2c3.5 | fish | 376 | 8.66 | 7.1 % | 2109 | 2024 | 66 | 19 | 104.1 / 162.6 | 6 | {'2': 63, '3': 1886, '4': 108, '5': 25, '6': 8} | -8714 / -7360 |
| tree_s1.5c3 | fish | 376 | 8.66 | 7.1 % | 2109 | 2024 | 66 | 19 | 104.1 / 162.6 | 6 | {'2': 63, '3': 1886, '4': 108, '5': 25, '6': 8} | -8714 / -7360 |
| tree_s2c3.5 | spine | 376 | 8.66 | 7.1 % | 2109 | 2019 | 62 | 28 | 104.1 / 125.6 | 7 | {'2': 19, '3': 1915, '4': 117, '5': 22, '6': 6, '7': 2} | -8733 / -7376 |
| tree_s1.5c3 | spine | 376 | 8.66 | 7.1 % | 2109 | 2019 | 62 | 28 | 104.1 / 125.6 | 7 | {'2': 19, '3': 1915, '4': 117, '5': 22, '6': 6, '7': 2} | -8733 / -7376 |
| tree_s3.5c5 | fish | 194 | 8.66 | 41.9 % | 1222 | 1097 | 90 | 35 | 104.1 / 144.5 | 6 | {'2': 153, '3': 720, '4': 275, '5': 36, '6': 3} | -9371 / -7912 |
| tree_s3.5c5 | spine | 194 | 8.66 | 41.9 % | 1222 | 1059 | 123 | 40 | 104.1 / 109.1 | 6 | {'2': 15, '3': 804, '4': 300, '5': 45, '6': 18} | -9390 / -7928 |
| tree_s3.5c5 | fwd | 194 | 8.66 | 41.9 % | 1222 | 1062 | 120 | 40 | 104.1 / 109.3 | 7 | {'2': 28, '3': 924, '4': 185, '5': 34, '6': 9, '7': 2} | -12486 / -10566 |
| v1_s3.5 | fish | 210 | 8.66 | 37.5 % | 1336 | 1163 | 130 | 43 | 104.1 / 144.5 | 7 | {'2': 214, '3': 745, '4': 287, '5': 26, '6': 19, '7': 2} | -13758 / -11664 |
| v1_s3.5 | fwd | 210 | 8.66 | 37.5 % | 1336 | 1228 | 64 | 44 | 104.1 / 111.5 | 6 | {'2': 26, '3': 1073, '4': 167, '5': 18, '6': 8} | -18254 / -15498 |
| v1_s3.5 | spine | 210 | 8.66 | 37.5 % | 1336 | 1144 | 148 | 44 | 104.1 / 121.7 | 7 | {'2': 27, '3': 869, '4': 329, '5': 36, '6': 25, '7': 6} | -13777 / -11680 |
| tree_s3.5c5 | dme | 194 | 8.66 | 41.9 % | 1222 | 406 | 638 | 178 | 104.1 / 144.5 | 6 | {'2': 237, '3': 325, '4': 375, '5': 104, '6': 3} | -1275 / -967 |
| tree_s2c3.5 | dme | 376 | 8.66 | 7.1 % | 2109 | 931 | 969 | 209 | 104.1 / 112.5 | 7 | {'2': 612, '3': 613, '4': 601, '5': 58, '6': 14, '7': 2} | -1122 / -845 |
| tree_s1.5c3 | dme | 376 | 8.66 | 7.1 % | 2109 | 931 | 969 | 209 | 104.1 / 112.5 | 7 | {'2': 612, '3': 613, '4': 601, '5': 58, '6': 14, '7': 2} | -1122 / -845 |
| v1_s3.5 | dme | 210 | 8.66 | 37.5 % | 1336 | 429 | 671 | 236 | 104.1 / 121.3 | 6 | {'2': 245, '3': 388, '4': 372, '5': 82, '6': 13} | -1368 / -1042 |
| land179 | fish | 179 | 11.54* | 47.6 % | 1173 | 989 | 140 | 44 | 104.1 / 219.4 | 6 | {'2': 153, '3': 661, '4': 251, '5': 43, '6': 21} | -12190 / -10321 |
| dies81 | fish | 91 | 11.54* | 58.6 % | 948 | 740 | 156 | 52 | 104.1 / 148.1 | 7 | {'2': 75, '3': 463, '4': 294, '5': 39, '6': 23, '7': 2} | -14491 / -12285 |
| land179 | spine | 179 | 11.54* | 47.6 % | 1173 | 969 | 148 | 56 | 104.1 / 182.7 | 6 | {'2': 10, '3': 766, '4': 263, '5': 67, '6': 11} | -12209 / -10337 |
| land179 | fwd | 179 | 11.54* | 47.6 % | 1173 | 991 | 120 | 62 | 104.1 / 112.9 | 7 | {'2': 72, '3': 741, '4': 239, '5': 38, '6': 2, '7': 19} | -17070 / -14481 |
| dies81 | spine | 91 | 11.54* | 58.6 % | 948 | 731 | 150 | 67 | 104.1 / 113.7 | 6 | {'2': 28, '3': 488, '4': 297, '5': 51, '6': 17} | -15007 / -12724 |
| dies81 | fwd | 91 | 11.54* | 58.6 % | 948 | 724 | 148 | 76 | 104.1 / 106.8 | 7 | {'2': 12, '3': 485, '4': 314, '5': 34, '6': 14, '7': 13} | -19850 / -16852 |
| land179 | dme | 179 | 11.54* | 47.6 % | 1173 | 359 | 598 | 216 | 104.1 / 139.1 | 7 | {'2': 210, '3': 309, '4': 358, '5': 67, '6': 9, '7': 4} | -1283 / -976 |
| dies81 | dme | 91 | 11.54* | 58.6 % | 948 | 205 | 446 | 297 | 104.1 / 110.9 | 5 | {'2': 73, '3': 265, '4': 248, '5': 65} | -1420 / -1089 |
| tree_s2c3.5 | top | 376 | 8.66 | 7.1 % | 2109 | 1545 | 530 | 34 | 104.1 / 234.8 | 6 | {'2': 356, '3': 1384, '4': 282, '5': 38, '6': 15} | -483 / -337 |
| tree_s1.5c3 | top | 376 | 8.66 | 7.1 % | 2109 | 1545 | 530 | 34 | 104.1 / 234.8 | 6 | {'2': 356, '3': 1384, '4': 282, '5': 38, '6': 15} | -483 / -337 |
| tree_s3.5c5 | top | 194 | 8.66 | 41.9 % | 1222 | 603 | 556 | 63 | 104.1 / 234.8 | 7 | {'2': 168, '3': 646, '4': 273, '5': 44, '6': 13, '7': 15} | -487 / -340 |
| v1_s3.5 | top | 210 | 8.66 | 37.5 % | 1336 | 764 | 508 | 64 | 104.1 / 234.8 | 6 | {'2': 183, '3': 772, '4': 256, '5': 26, '6': 35} | -483 / -337 |
| dies81 | top | 91 | 11.54* | 58.6 % | 948 | 90 | 746 | 112 | 104.1 / 159.8 | 7 | {'2': 67, '3': 293, '4': 367, '5': 71, '6': 34, '7': 4} | -548 / -390 |
| land179 | top | 179 | 11.54* | 47.6 % | 1173 | 178 | 801 | 194 | 104.1 / 132.0 | 6 | {'2': 131, '3': 339, '4': 432, '5': 52, '6': 25} | -566 / -406 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| xtier__s_5S_C__s_5N_C__3 | T210 -> T232 | 276 | OFF | nontree (amb 2) | 1102..6767 | FAIL | - / - | 685.6 / -519.3 |
| xtier__s_4S_C__bk_sel__2 | T187 -> T209 | 276 | OFF | nontree (amb 2) | 1020..6521 | FAIL | - / - | 603.1 / -273.4 |
| xtier__bk_sel__s_4S_C__8 | T209 -> T187 | 276 | OFF | nontree (amb 2) | 976..6477 | FAIL | - / - | 559.6 / -229.9 |
| xtier__s_5N_C__s_5S_C__2 | T232 -> T210 | 276 | OFF | nontree (amb 2) | 730..6395 | FAIL | - / - | 313.7 / -147.4 |
| xring__s_3S_C__s_4S_C__0 | T147 -> T148 | 1104 | OFF | nontree (amb 2) | 803..6142 | 8 | -9 / 6 | 386.9 / 105.2 |
| unit__s_7N_LP__seqhost__3 | T213 -> T191 | 604 | OFF | nontree (amb 2) | 1016..6064 | 8 | 4 / 7 | 599.1 / 183.3 |
| tp__bk_sel__s_7S_LP__10 | T213 -> T191 | 276 | OFF | nontree (amb 2) | 1016..6064 | 8 | 4 / 7 | 599.1 / 183.3 |
| hbmrd__phy_hbm__svc_2__0 | T005 -> T017 | 1120 | OFF | nontree (amb 3) | 1022..6022 | 8 | 15 / 5 | 605.3 / 225.7 |
| xtier__bk_sel__seqhost__16 | T089 -> T088 | 276 | OFF | nontree (amb 2) | 1210..6000 | 8 | 15 / 5 | 793.5 / 248.0 |
| unit__s_7N_LP__seqhost__13 | T089 -> T088 | 604 | OFF | nontree (amb 2) | 1210..6000 | 8 | 15 / 5 | 793.5 / 248.0 |
| unit__svc_11__seqhost__2 | T089 -> T088 | 13 | OFF | nontree (amb 2) | 1210..6000 | 8 | 15 / 5 | 793.5 / 248.0 |
| dfi__svc_0__phy_hbm__1 | T004 -> T005 | 1368 | OFF | nontree (amb 3) | 822..5998 | 8 | -5 / 7 | 405.4 / 249.9 |
| xtier__s_7S_C__s_7N_C__3 | T212 -> T234 | 276 | OFF | nontree (amb 2) | 825..5938 | 8 | 8 / 4 | 408.8 / 309.2 |
| xtier__bk_sel__seqhost__8 | T211 -> T189 | 276 | OFF | nontree (amb 2) | 972..5921 | 8 | 3 / 7 | 555.3 / 326.6 |
| xring__s_4S_C__s_3S_C__0 | T148 -> T147 | 1104 | OFF | nontree (amb 2) | 522..5861 | 8 | 19 / 5 | 105.2 / 386.9 |

Per-crossing K/DEPTH/latency/margins: s81_v3_crossings.tsv (all 2109).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
