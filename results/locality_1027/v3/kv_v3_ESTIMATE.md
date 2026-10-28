# 12.14b ESTIMATE v3: kv, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_kvsys/die_plan.json (sha256 59a8a3ebb4d5), 160 partitions, 3939 ports; clock wire v = 321 ps/mm TT (KV measured 321 ps/mm x1.0); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map land128, feed fish

* 128 regions, max span 2.16 mm, bit-mm inside 8.9 %, 3619 crossings (536055 bits), 1 connected component(s), start-tree edges clean 127/127, max path ambiguity 0 cycles.
* **DEPTH4 3357, DEPTH8 262 (16804 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 188.6 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 11, '3': 3510, '4': 44, '5': 54}; max 5; bit-weighted mean 2.53.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-8': 16, '-7': 10, '-6': 24, '-5': 4, '-4': 2, '-3': 2, '-2': 2, '-1': 2, '0': 2, '1': 52, '2': 1854, '3': 1389, '4': 25, '5': 13, '6': 4, '7': 4, '8': 4, '9': 4, '11': 4, '12': 5, '13': 158, '14': 23, '15': 16}; bit-weighted: {'-8': 2079, '-7': 653, '-6': 2639, '-5': 2624, '-4': 2112, '-3': 2112, '-2': 2112, '-1': 2112, '0': 2112, '1': 8616, '2': 226173, '3': 266357, '4': 8350, '5': 1179, '6': 32, '7': 32, '8': 32, '9': 32, '11': 32, '12': 554, '13': 3097, '14': 1968, '15': 1046}.
* Render: kv_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| land128 | fish | 128 | 2.16 | 8.9 % | 3619 | 3357 | 262 | 0 | 104.1 / 188.6 | 5 | {'2': 11, '3': 3510, '4': 44, '5': 54} | -10617 / -8988 |
| tree_s1.5c3 | fish | 158 | 2.36 | 0.7 % | 3905 | 3643 | 262 | 0 | 104.1 / 188.6 | 5 | {'2': 9, '3': 3703, '4': 138, '5': 55} | -10617 / -8988 |
| land128 | spine | 128 | 2.16 | 8.9 % | 3619 | 3312 | 307 | 0 | 104.1 / 118.0 | 7 | {'2': 11, '3': 3372, '4': 146, '5': 36, '6': 28, '7': 26} | -10628 / -8997 |
| tree_s1.5c3 | spine | 158 | 2.36 | 0.7 % | 3905 | 3598 | 307 | 0 | 104.1 / 110.0 | 7 | {'2': 9, '3': 3658, '4': 67, '5': 116, '6': 29, '7': 26} | -10628 / -8997 |
| tree_s2c3.5 | fish | 72 | 3.18 | 38.0 % | 2553 | 2164 | 365 | 24 | 104.1 / 105.7 | 7 | {'2': 11, '3': 2023, '4': 306, '5': 76, '6': 106, '7': 7} | -8558 / -7231 |
| land128 | fwd | 128 | 2.16 | 8.9 % | 3619 | 3323 | 264 | 32 | 104.1 / 159.7 | 7 | {'2': 325, '3': 2867, '4': 339, '5': 16, '6': 18, '7': 22} | -15600 / -13238 |
| tree_s1.5c3 | fwd | 158 | 2.36 | 0.7 % | 3905 | 3609 | 264 | 32 | 104.1 / 159.7 | 7 | {'2': 250, '3': 3293, '4': 274, '5': 16, '6': 14, '7': 26} | -15857 / -13457 |
| tree_s3.5c5 | fwd | 39 | 4.72 | 59.7 % | 1621 | 1125 | 457 | 39 | 104.1 / 105.3 | 7 | {'2': 6, '3': 791, '4': 573, '5': 185, '6': 23, '7': 4} | -11503 / -9746 |
| v1_s3.5 | fish | 50 | 3.44 | 53.6 % | 1885 | 1273 | 559 | 53 | 104.1 / 104.9 | 7 | {'2': 36, '3': 1051, '4': 575, '5': 74, '6': 81, '7': 15} | -11968 / -10139 |
| tree_s3.5c5 | fish | 39 | 4.72 | 59.7 % | 1621 | 1359 | 204 | 58 | 104.1 / 150.0 | 6 | {'2': 44, '3': 832, '4': 641, '5': 40, '6': 6} | -6389 / -5381 |
| tree_s3.5c5 | spine | 39 | 4.72 | 59.7 % | 1621 | 1186 | 353 | 82 | 104.1 / 186.3 | 6 | {'2': 3, '3': 545, '4': 813, '5': 164, '6': 14} | -6415 / -5403 |
| tree_s3.5c5 | dme | 39 | 4.72 | 59.7 % | 1621 | 229 | 1310 | 82 | 104.1 / 438.6 | 6 | {'2': 58, '3': 554, '4': 807, '5': 104, '6': 16} | -458 / -304 |
| v1_s3.5 | fwd | 50 | 3.44 | 53.6 % | 1885 | 1317 | 423 | 145 | 104.1 / 201.5 | 8 | {'2': 8, '3': 1261, '4': 369, '5': 75, '6': 10, '7': 14, '8': 3} | -16429 / -13944 |
| tree_s2c3.5 | fwd | 72 | 3.18 | 38.0 % | 2553 | 2083 | 319 | 151 | 104.1 / 118.5 | 8 | {'2': 239, '3': 1674, '4': 446, '5': 16, '6': 8, '7': 18, '8': 1} | -12042 / -10200 |
| tree_s2c3.5 | spine | 72 | 3.18 | 38.0 % | 2553 | 2050 | 337 | 166 | 104.1 / 122.3 | 7 | {'2': 11, '3': 1883, '4': 401, '5': 86, '6': 2, '7': 4} | -8575 / -7245 |
| v1_s3.5 | spine | 50 | 3.44 | 53.6 % | 1885 | 1226 | 407 | 252 | 104.1 / 157.1 | 7 | {'2': 12, '3': 956, '4': 510, '5': 114, '6': 38, '7': 3} | -11979 / -10148 |
| tree_s2c3.5 | dme | 72 | 3.18 | 38.0 % | 2553 | 1222 | 1020 | 311 | 104.1 / 214.0 | 7 | {'2': 710, '3': 774, '4': 671, '5': 65, '6': 18, '7': 4} | -648 / -461 |
| tree_s1.5c3 | dme | 158 | 2.36 | 0.7 % | 3905 | 1850 | 1730 | 325 | 104.1 / 314.3 | 7 | {'2': 1173, '3': 1107, '4': 962, '5': 324, '6': 12, '7': 2} | -570 / -395 |
| land128 | dme | 128 | 2.16 | 8.9 % | 3619 | 1541 | 1745 | 333 | 104.1 / 294.9 | 7 | {'2': 863, '3': 1108, '4': 981, '5': 320, '6': 12, '7': 2} | -585 / -408 |
| v1_s3.5 | dme | 50 | 3.44 | 53.6 % | 1885 | 510 | 1020 | 355 | 104.1 / 113.6 | 7 | {'2': 181, '3': 583, '4': 657, '5': 85, '6': 20, '7': 4} | -727 / -526 |
| v1_s3.5 | top | 50 | 3.44 | 53.6 % | 1885 | 1340 | 545 | 0 | 104.1 / 816.8 | 4 | {'2': 548, '3': 1036, '4': 301} | -76 / 5 |
| tree_s2c3.5 | top | 72 | 3.18 | 38.0 % | 2553 | 2023 | 530 | 0 | 104.1 / 797.1 | 4 | {'2': 1191, '3': 1062, '4': 300} | -84 / -2 |
| land128 | top | 128 | 2.16 | 8.9 % | 3619 | 3103 | 516 | 0 | 104.1 / 835.4 | 4 | {'2': 2297, '3': 1100, '4': 222} | -52 / 24 |
| tree_s1.5c3 | top | 158 | 2.36 | 0.7 % | 3905 | 3389 | 516 | 0 | 104.1 / 811.9 | 4 | {'2': 2582, '3': 1029, '4': 294} | -68 / 11 |
| tree_s3.5c5 | top | 39 | 4.72 | 59.7 % | 1621 | 949 | 672 | 0 | 104.1 / 757.7 | 6 | {'2': 119, '3': 1078, '4': 259, '5': 137, '6': 28} | -124 / -35 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L589_7 | phy_WS_7 -> hroot_WS | 1 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1021_0 | phy_WS_7 -> hroot_WS | 32 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1022_0 | phy_WS_7 -> hroot_WS | 32 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1023_0 | phy_WS_7 -> hroot_WS | 1 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1024_0 | phy_WS_7 -> hroot_WS | 32 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1025_0 | phy_WS_7 -> hroot_WS | 32 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1026_0 | phy_WS_7 -> hroot_WS | 32 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1027_0 | phy_WS_7 -> hroot_WS | 32 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1376_0 | phy_WS_7 -> hroot_WS | 299 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L1377_0 | phy_WS_7 -> hroot_WS | 1 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L2203_0 | phy_WS_7 -> hroot_WS | 1 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L2205_0 | phy_WS_7 -> hroot_WS | 144 | OFF | nontree (amb 0) | 1348..3999 | 8 | 14 / 4 | 931.6 / 2248.9 |
| L668_0 | hroot_WS -> phy_WS_7 | 1 | OFF | nontree (amb 0) | 996..3654 | 8 | -6 / 5 | 579.5 / 2593.2 |
| L503_1 | hroot_WS -> phy_WS_7 | 13 | OFF | nontree (amb 0) | 999..3650 | 8 | -6 / 5 | 582.9 / 2597.6 |
| L638_1 | hroot_WS -> phy_WS_7 | 1 | OFF | nontree (amb 0) | 999..3650 | 8 | -6 / 5 | 582.9 / 2597.6 |

Per-crossing K/DEPTH/latency/margins: kv_v3_crossings.tsv (all 3619).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
