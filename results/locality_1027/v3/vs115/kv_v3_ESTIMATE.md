# 12.14b ESTIMATE v3: kv, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_kvsys/die_plan.json (sha256 59a8a3ebb4d5), 160 partitions, 3939 ports; clock wire v = 369.1 ps/mm TT (KV measured 321 ps/mm x1.15); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map land128, feed fish

* 128 regions, max span 2.16 mm, bit-mm inside 8.9 %, 3619 crossings (536055 bits), 1 connected component(s), start-tree edges clean 127/127, max path ambiguity 0 cycles.
* **DEPTH4 3357, DEPTH8 262 (16804 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 137.6 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 43, '3': 3327, '4': 193, '5': 56}; max 5; bit-weighted mean 2.51.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-10': 16, '-9': 10, '-7': 24, '-6': 4, '-5': 2, '-4': 2, '-3': 2, '-2': 2, '-1': 2, '0': 18, '1': 70, '2': 1818, '3': 1389, '4': 6, '5': 32, '6': 4, '8': 4, '9': 4, '10': 4, '12': 4, '13': 5, '15': 170, '16': 11, '17': 16}; bit-weighted: {'-10': 2079, '-9': 653, '-7': 2639, '-6': 2624, '-5': 2112, '-4': 2112, '-3': 2112, '-2': 2112, '-1': 2112, '0': 4407, '1': 10160, '2': 220222, '3': 266357, '4': 6336, '5': 3193, '6': 32, '8': 32, '9': 32, '10': 32, '12': 32, '13': 554, '15': 3736, '16': 1329, '17': 1046}.
* Render: kv_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| land128 | fish | 128 | 2.16 | 8.9 % | 3619 | 3357 | 262 | 0 | 104.1 / 137.6 | 5 | {'2': 43, '3': 3327, '4': 193, '5': 56} | -12260 / -10389 |
| tree_s1.5c3 | fish | 158 | 2.36 | 0.7 % | 3905 | 3643 | 262 | 0 | 104.1 / 137.6 | 5 | {'2': 34, '3': 3630, '4': 185, '5': 56} | -12260 / -10389 |
| land128 | spine | 128 | 2.16 | 8.9 % | 3619 | 3357 | 262 | 0 | 104.1 / 116.1 | 6 | {'2': 18, '3': 3352, '4': 193, '5': 44, '6': 12} | -12273 / -10400 |
| tree_s1.5c3 | spine | 158 | 2.36 | 0.7 % | 3905 | 3643 | 262 | 0 | 104.1 / 116.1 | 6 | {'2': 5, '3': 3659, '4': 185, '5': 55, '6': 1} | -12273 / -10400 |
| tree_s3.5c5 | fish | 39 | 4.72 | 59.7 % | 1621 | 1317 | 265 | 39 | 104.1 / 144.8 | 7 | {'2': 8, '3': 1012, '4': 502, '5': 48, '6': 8, '7': 4} | -7399 / -6243 |
| tree_s3.5c5 | fwd | 39 | 4.72 | 59.7 % | 1621 | 1267 | 278 | 76 | 104.1 / 129.6 | 7 | {'2': 36, '3': 672, '4': 726, '5': 92, '6': 17, '7': 2} | -13279 / -11262 |
| tree_s3.5c5 | spine | 39 | 4.72 | 59.7 % | 1621 | 1124 | 421 | 76 | 104.1 / 156.3 | 7 | {'2': 7, '3': 678, '4': 712, '5': 133, '6': 14, '7': 1} | -7429 / -6267 |
| tree_s2c3.5 | fish | 72 | 3.18 | 38.0 % | 2553 | 2072 | 396 | 85 | 104.1 / 105.5 | 8 | {'2': 20, '3': 1818, '4': 548, '5': 63, '6': 7, '7': 11, '8': 1} | -9893 / -8370 |
| tree_s3.5c5 | dme | 39 | 4.72 | 59.7 % | 1621 | 229 | 1234 | 158 | 104.1 / 285.8 | 6 | {'2': 53, '3': 506, '4': 822, '5': 66, '6': 16} | -577 / -403 |
| tree_s1.5c3 | fwd | 158 | 2.36 | 0.7 % | 3905 | 3590 | 157 | 158 | 104.1 / 123.2 | 6 | {'2': 315, '3': 3180, '4': 143, '5': 101, '6': 8} | -18284 / -15528 |
| land128 | fwd | 128 | 2.16 | 8.9 % | 3619 | 3298 | 155 | 166 | 104.1 / 134.9 | 6 | {'2': 325, '3': 2785, '4': 243, '5': 96, '6': 4} | -17989 / -15276 |
| tree_s2c3.5 | spine | 72 | 3.18 | 38.0 % | 2553 | 2060 | 327 | 166 | 104.1 / 107.3 | 8 | {'2': 9, '3': 1751, '4': 501, '5': 102, '6': 11, '7': 12, '8': 1} | -9912 / -8386 |
| tree_s2c3.5 | fwd | 72 | 3.18 | 38.0 % | 2553 | 1919 | 369 | 265 | 104.1 / 108.8 | 8 | {'2': 82, '3': 1608, '4': 568, '5': 11, '6': 15, '7': 2, '8': 2} | -13896 / -11783 |
| v1_s3.5 | fish | 50 | 3.44 | 53.6 % | 1885 | 1326 | 284 | 275 | 104.1 / 266.6 | 7 | {'2': 7, '3': 1042, '4': 412, '5': 136, '6': 7, '7': 6} | -13813 / -11713 |
| v1_s3.5 | fwd | 50 | 3.44 | 53.6 % | 1885 | 1221 | 382 | 282 | 104.1 / 141.7 | 8 | {'2': 69, '3': 683, '4': 705, '5': 120, '6': 22, '7': 3, '8': 1} | -18942 / -16088 |
| v1_s3.5 | spine | 50 | 3.44 | 53.6 % | 1885 | 1287 | 309 | 289 | 104.1 / 156.1 | 7 | {'2': 5, '3': 843, '4': 590, '5': 146, '6': 8, '7': 4} | -13826 / -11724 |
| tree_s2c3.5 | dme | 72 | 3.18 | 38.0 % | 2553 | 1062 | 1128 | 363 | 104.1 / 122.8 | 7 | {'2': 498, '3': 861, '4': 752, '5': 63, '6': 12, '7': 4} | -794 / -581 |
| v1_s3.5 | dme | 50 | 3.44 | 53.6 % | 1885 | 429 | 1049 | 407 | 104.1 / 221.7 | 7 | {'2': 177, '3': 503, '4': 675, '5': 93, '6': 26, '7': 4} | -884 / -656 |
| tree_s1.5c3 | dme | 158 | 2.36 | 0.7 % | 3905 | 1659 | 1789 | 457 | 104.1 / 142.9 | 6 | {'2': 968, '3': 1083, '4': 1091, '5': 295, '6': 11} | -704 / -507 |
| land128 | dme | 128 | 2.16 | 8.9 % | 3619 | 1350 | 1804 | 465 | 104.1 / 120.6 | 6 | {'2': 653, '3': 1089, '4': 1114, '5': 287, '6': 11} | -722 / -521 |
| land128 | top | 128 | 2.16 | 8.9 % | 3619 | 3103 | 516 | 0 | 104.1 / 742.1 | 4 | {'2': 2296, '3': 1101, '4': 222} | -113 / -28 |
| tree_s2c3.5 | top | 72 | 3.18 | 38.0 % | 2553 | 1870 | 683 | 0 | 104.1 / 698.1 | 5 | {'2': 933, '3': 1168, '4': 368, '5': 84} | -148 / -57 |
| tree_s1.5c3 | top | 158 | 2.36 | 0.7 % | 3905 | 3235 | 670 | 0 | 104.1 / 715.2 | 5 | {'2': 2239, '3': 1223, '4': 362, '5': 81} | -130 / -42 |
| v1_s3.5 | top | 50 | 3.44 | 53.6 % | 1885 | 1194 | 691 | 0 | 104.1 / 720.8 | 6 | {'2': 416, '3': 1041, '4': 296, '5': 56, '6': 76} | -140 / -49 |
| tree_s3.5c5 | top | 39 | 4.72 | 59.7 % | 1621 | 585 | 926 | 110 | 104.1 / 533.9 | 6 | {'2': 37, '3': 949, '4': 382, '5': 6, '6': 137} | -195 / -95 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L668_0 | hroot_WS -> phy_WS_7 | 1 | OFF | nontree (amb 0) | 1210..4216 | 8 | -7 / 5 | 793.5 / 2031.5 |
| L503_1 | hroot_WS -> phy_WS_7 | 13 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L638_1 | hroot_WS -> phy_WS_7 | 1 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L650_2 | hroot_WS -> phy_WS_7 | 291 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L669_0 | hroot_WS -> phy_WS_7 | 1 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L711_1 | hroot_WS -> phy_WS_7 | 1 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L1102_0 | hroot_WS -> phy_WS_7 | 2 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L1142_0 | hroot_WS -> phy_WS_7 | 33 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L1457_1 | hroot_WS -> phy_WS_7 | 16 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L1491_1 | hroot_WS -> phy_WS_7 | 18 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L1594_0 | hroot_WS -> phy_WS_7 | 271 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L1605_0 | hroot_WS -> phy_WS_7 | 780 | OFF | nontree (amb 0) | 1214..4210 | 8 | -7 / 5 | 797.9 / 2037.1 |
| L333_0 | hub_Wo -> hg_WS_7 | 572 | OFF | nontree (amb 0) | 1270..4142 | 8 | -7 / 5 | 853.4 / 2105.1 |
| L1419_0 | hub_Wo -> hg_WS_7 | 16 | OFF | nontree (amb 0) | 1270..4142 | 8 | -7 / 5 | 853.4 / 2105.1 |
| L1586_1 | hub_Wo -> hg_WS_7 | 40 | OFF | nontree (amb 0) | 1270..4142 | 8 | -7 / 5 | 853.4 / 2105.1 |

Per-crossing K/DEPTH/latency/margins: kv_v3_crossings.tsv (all 3619).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
