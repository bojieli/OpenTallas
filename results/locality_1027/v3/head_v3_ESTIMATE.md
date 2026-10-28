# 12.14b ESTIMATE v3: head, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81_head/die_plan.json (sha256 7af819954806), 326 partitions, 427 ports; clock wire v = 349 ps/mm TT (HEAD measured 335-349 ps/mm (LAND-HEAD-3), upper value x1.0); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map v1_s3.5, feed fish

* 85 regions, max span 3.01 mm, bit-mm inside 57.1 %, 162 crossings (66203 bits), 1 connected component(s), start-tree edges clean 84/84, max path ambiguity 0 cycles.
* **DEPTH4 162, DEPTH8 0 (0 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 1117.0 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 37, '3': 125}; max 3; bit-weighted mean 2.21.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'0': 4, '1': 50, '2': 27, '3': 60, '4': 21}; bit-weighted: {'0': 2048, '1': 25220, '2': 5821, '3': 23058, '4': 10056}.
* Render: head_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1_s3.5 | fish | 85 | 3.01 | 57.1 % | 162 | 162 | 0 | 0 | 104.1 / 1117.0 | 3 | {'2': 37, '3': 125} | -1278 / -1022 |
| tree_s3.5c5 | fish | 85 | 3.01 | 57.1 % | 162 | 162 | 0 | 0 | 104.1 / 1117.0 | 3 | {'2': 37, '3': 125} | -1278 / -1022 |
| v1_s3.5 | spine | 85 | 3.01 | 57.1 % | 162 | 162 | 0 | 0 | 104.1 / 244.4 | 4 | {'2': 28, '3': 119, '4': 15} | -1291 / -1033 |
| tree_s3.5c5 | spine | 85 | 3.01 | 57.1 % | 162 | 162 | 0 | 0 | 104.1 / 244.4 | 4 | {'2': 28, '3': 119, '4': 15} | -1291 / -1033 |
| v1_s3.5 | fwd | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 208.0 | 4 | {'2': 22, '3': 123, '4': 17} | -1507 / -1217 |
| tree_s3.5c5 | fwd | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 208.0 | 4 | {'2': 22, '3': 123, '4': 17} | -1507 / -1217 |
| v1_s3.5 | dme | 85 | 3.01 | 57.1 % | 162 | 93 | 69 | 0 | 104.1 / 749.7 | 4 | {'2': 74, '3': 44, '4': 44} | -149 / -54 |
| tree_s3.5c5 | dme | 85 | 3.01 | 57.1 % | 162 | 93 | 69 | 0 | 104.1 / 749.7 | 4 | {'2': 74, '3': 44, '4': 44} | -149 / -54 |
| tree_s2c3.5 | fwd | 182 | 2.89 | 26.2 % | 283 | 283 | 0 | 0 | 104.1 / 155.1 | 4 | {'2': 64, '3': 209, '4': 10} | -7954 / -6721 |
| tree_s2c3.5 | fish | 182 | 2.89 | 26.2 % | 283 | 283 | 0 | 0 | 104.1 / 144.0 | 4 | {'2': 44, '3': 231, '4': 8} | -5821 / -4901 |
| tree_s2c3.5 | spine | 182 | 2.89 | 26.2 % | 283 | 283 | 0 | 0 | 104.1 / 132.1 | 4 | {'2': 28, '3': 241, '4': 14} | -5835 / -4913 |
| tree_s1.5c3 | fwd | 206 | 2.89 | 23.3 % | 307 | 295 | 12 | 0 | 104.1 / 408.4 | 4 | {'2': 68, '3': 225, '4': 14} | -8337 / -7048 |
| tree_s1.5c3 | fish | 206 | 2.89 | 23.3 % | 307 | 307 | 0 | 0 | 104.1 / 141.8 | 4 | {'2': 40, '3': 259, '4': 8} | -5824 / -4903 |
| tree_s1.5c3 | spine | 206 | 2.89 | 23.3 % | 307 | 307 | 0 | 0 | 104.1 / 129.8 | 4 | {'2': 28, '3': 265, '4': 14} | -5838 / -4915 |
| landpart | fish | 326 | 2.89 | 0.0 % | 427 | 427 | 0 | 0 | 104.1 / 141.8 | 4 | {'2': 199, '3': 220, '4': 8} | -5824 / -4903 |
| landpart | spine | 326 | 2.89 | 0.0 % | 427 | 427 | 0 | 0 | 104.1 / 129.8 | 4 | {'2': 187, '3': 226, '4': 14} | -5838 / -4915 |
| landpart | fwd | 326 | 2.89 | 0.0 % | 427 | 415 | 12 | 0 | 104.1 / 408.4 | 5 | {'2': 28, '3': 389, '4': 2, '5': 8} | -10235 / -8667 |
| tree_s2c3.5 | dme | 182 | 2.89 | 26.2 % | 283 | 209 | 62 | 12 | 104.1 / 594.2 | 4 | {'2': 170, '3': 66, '4': 35} | -264 / -150 |
| tree_s1.5c3 | dme | 206 | 2.89 | 23.3 % | 307 | 233 | 62 | 12 | 104.1 / 594.2 | 4 | {'2': 194, '3': 66, '4': 35} | -272 / -155 |
| landpart | dme | 326 | 2.89 | 0.0 % | 427 | 353 | 62 | 12 | 104.1 / 594.2 | 4 | {'2': 314, '3': 73, '4': 28} | -272 / -155 |
| v1_s3.5 | top | 85 | 3.01 | 57.1 % | 162 | 143 | 19 | 0 | 104.1 / 831.5 | 4 | {'2': 117, '3': 31, '4': 14} | -59 / 19 |
| tree_s3.5c5 | top | 85 | 3.01 | 57.1 % | 162 | 143 | 19 | 0 | 104.1 / 831.5 | 4 | {'2': 117, '3': 31, '4': 14} | -59 / 19 |
| tree_s2c3.5 | top | 182 | 2.89 | 26.2 % | 283 | 247 | 36 | 0 | 104.1 / 830.3 | 4 | {'2': 218, '3': 43, '4': 22} | -59 / 18 |
| tree_s1.5c3 | top | 206 | 2.89 | 23.3 % | 307 | 283 | 24 | 0 | 104.1 / 805.5 | 4 | {'2': 247, '3': 44, '4': 16} | -71 / 8 |
| landpart | top | 326 | 2.89 | 0.0 % | 427 | 403 | 24 | 0 | 104.1 / 805.5 | 4 | {'2': 367, '3': 45, '4': 15} | -71 / 8 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| chE0_o6__0 | R074 -> R070 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chW0_o6__0 | R071 -> R064 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chE1_o6__0 | R063 -> R059 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chW1_o6__0 | R060 -> R053 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chE3_o6__0 | R041 -> R037 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chW3_o6__0 | R038 -> R031 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chE4_o6__0 | R030 -> R026 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chW4_o6__0 | R027 -> R020 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chE5_o6__0 | R019 -> R015 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| chW5_o6__0 | R016 -> R009 | 565 | OFF | nontree (amb 0) | 900..1798 | 4 | 1 / 3 | 483.5 / 1117.0 |
| coll_WN1_u__2 | R077 -> R078 | 514 | on | nontree (amb 0) | 1300..1791 | 4 | 4 / 3 | 883.5 / 1124.6 |
| coll_WN2_u__4 | R077 -> R078 | 514 | on | nontree (amb 0) | 1300..1791 | 4 | 4 / 3 | 883.5 / 1124.6 |
| sp_b1__0 | R056 -> R067 | 565 | on | nontree (amb 0) | 1305..1734 | 4 | 2 / 3 | 888.4 / 1181.7 |
| sp_b2__0 | R045 -> R056 | 565 | on | nontree (amb 0) | 1305..1734 | 4 | 2 / 3 | 888.4 / 1181.7 |
| sp_b3__0 | R034 -> R045 | 565 | on | nontree (amb 0) | 1305..1734 | 4 | 2 / 3 | 888.4 / 1181.7 |

Per-crossing K/DEPTH/latency/margins: head_v3_crossings.tsv (all 162).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
