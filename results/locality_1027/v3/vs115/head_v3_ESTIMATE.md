# 12.14b ESTIMATE v3: head, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81_head/die_plan.json (sha256 7af819954806), 326 partitions, 427 ports; clock wire v = 401.3 ps/mm TT (HEAD measured 335-349 ps/mm (LAND-HEAD-3), upper value x1.15); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map v1_s3.5, feed dme

* 85 regions, max span 3.01 mm, bit-mm inside 57.1 %, 162 crossings (66203 bits), 1 connected component(s), start-tree edges clean 45/84, max path ambiguity 2 cycles.
* **DEPTH4 93, DEPTH8 69 (21079 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 643.6 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 64, '3': 54, '4': 44}; max 4; bit-weighted mean 2.76.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'2': 64, '3': 54, '4': 44}; bit-weighted: {'2': 31942, '3': 18449, '4': 15812}.
* Render: head_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1_s3.5 | dme | 85 | 3.01 | 57.1 % | 162 | 93 | 69 | 0 | 104.1 / 643.6 | 4 | {'2': 64, '3': 54, '4': 44} | -223 / -116 |
| tree_s3.5c5 | dme | 85 | 3.01 | 57.1 % | 162 | 93 | 69 | 0 | 104.1 / 643.6 | 4 | {'2': 64, '3': 54, '4': 44} | -223 / -116 |
| tree_s2c3.5 | fwd | 182 | 2.89 | 26.2 % | 283 | 271 | 12 | 0 | 104.1 / 376.2 | 4 | {'2': 79, '3': 174, '4': 30} | -9199 / -7783 |
| v1_s3.5 | fish | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 207.7 | 5 | {'2': 40, '3': 102, '4': 8, '5': 12} | -1523 / -1231 |
| tree_s3.5c5 | fish | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 207.7 | 5 | {'2': 40, '3': 102, '4': 8, '5': 12} | -1523 / -1231 |
| v1_s3.5 | fwd | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 175.5 | 5 | {'2': 26, '3': 102, '4': 24, '5': 10} | -1787 / -1456 |
| tree_s3.5c5 | fwd | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 175.5 | 5 | {'2': 26, '3': 102, '4': 24, '5': 10} | -1787 / -1456 |
| v1_s3.5 | spine | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 165.7 | 5 | {'2': 21, '3': 113, '4': 16, '5': 12} | -1539 / -1244 |
| tree_s3.5c5 | spine | 85 | 3.01 | 57.1 % | 162 | 150 | 12 | 0 | 104.1 / 165.7 | 5 | {'2': 21, '3': 113, '4': 16, '5': 12} | -1539 / -1244 |
| tree_s2c3.5 | fish | 182 | 2.89 | 26.2 % | 283 | 271 | 12 | 0 | 104.1 / 328.5 | 5 | {'2': 98, '3': 165, '4': 12, '5': 8} | -6747 / -5691 |
| tree_s1.5c3 | fish | 206 | 2.89 | 23.3 % | 307 | 295 | 12 | 0 | 104.1 / 328.5 | 5 | {'2': 102, '3': 185, '4': 12, '5': 8} | -6750 / -5694 |
| tree_s1.5c3 | fwd | 206 | 2.89 | 23.3 % | 307 | 295 | 12 | 0 | 104.1 / 376.2 | 5 | {'2': 79, '3': 202, '4': 18, '5': 8} | -9640 / -8159 |
| tree_s1.5c3 | spine | 206 | 2.89 | 23.3 % | 307 | 295 | 12 | 0 | 104.1 / 310.1 | 5 | {'2': 35, '3': 252, '4': 12, '5': 8} | -6767 / -5707 |
| landpart | fish | 326 | 2.89 | 0.0 % | 427 | 415 | 12 | 0 | 104.1 / 328.5 | 5 | {'2': 222, '3': 185, '4': 12, '5': 8} | -6750 / -5694 |
| landpart | fwd | 326 | 2.89 | 0.0 % | 427 | 415 | 12 | 0 | 104.1 / 376.2 | 5 | {'2': 39, '3': 358, '4': 22, '5': 8} | -11821 / -10021 |
| landpart | spine | 326 | 2.89 | 0.0 % | 427 | 415 | 12 | 0 | 104.1 / 310.1 | 5 | {'2': 30, '3': 377, '4': 12, '5': 8} | -6767 / -5707 |
| tree_s2c3.5 | spine | 182 | 2.89 | 26.2 % | 283 | 271 | 12 | 0 | 104.1 / 310.1 | 6 | {'2': 31, '3': 232, '4': 12, '6': 8} | -6763 / -5705 |
| tree_s2c3.5 | dme | 182 | 2.89 | 26.2 % | 283 | 203 | 68 | 12 | 104.1 / 464.7 | 4 | {'2': 158, '3': 74, '4': 39} | -355 / -226 |
| tree_s1.5c3 | dme | 206 | 2.89 | 23.3 % | 307 | 227 | 68 | 12 | 104.1 / 464.7 | 4 | {'2': 182, '3': 74, '4': 39} | -363 / -232 |
| landpart | dme | 326 | 2.89 | 0.0 % | 427 | 347 | 68 | 12 | 104.1 / 464.7 | 4 | {'2': 290, '3': 93, '4': 32} | -363 / -232 |
| v1_s3.5 | top | 85 | 3.01 | 57.1 % | 162 | 129 | 33 | 0 | 104.1 / 737.6 | 4 | {'2': 91, '3': 49, '4': 22} | -119 / -33 |
| tree_s3.5c5 | top | 85 | 3.01 | 57.1 % | 162 | 129 | 33 | 0 | 104.1 / 737.6 | 4 | {'2': 91, '3': 49, '4': 22} | -119 / -33 |
| tree_s2c3.5 | top | 182 | 2.89 | 26.2 % | 283 | 233 | 50 | 0 | 104.1 / 736.2 | 4 | {'2': 204, '3': 49, '4': 30} | -120 / -34 |
| tree_s1.5c3 | top | 206 | 2.89 | 23.3 % | 307 | 269 | 38 | 0 | 104.1 / 707.8 | 6 | {'2': 237, '3': 46, '4': 18, '6': 6} | -134 / -45 |
| landpart | top | 326 | 2.89 | 0.0 % | 427 | 389 | 38 | 0 | 104.1 / 707.8 | 6 | {'2': 357, '3': 47, '4': 17, '6': 6} | -133 / -45 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| chE3_o6__0 | R041 -> R037 | 565 | OFF | nontree (amb 2) | 922..4076 | 8 | 4 / 4 | 505.8 / 2171.8 |
| chW3_o6__0 | R038 -> R031 | 565 | OFF | nontree (amb 2) | 922..4076 | 8 | 4 / 4 | 505.8 / 2171.8 |
| chE2_b3__0 | R048 -> R047 | 565 | OFF | nontree (amb 2) | 980..4018 | 8 | 4 / 4 | 563.8 / 2229.8 |
| chW2_b3__0 | R042 -> R043 | 565 | OFF | nontree (amb 2) | 980..4018 | 8 | 4 / 4 | 563.8 / 2229.8 |
| chE1_o6__0 | R063 -> R059 | 565 | OFF | nontree (amb 2) | 1039..3959 | 8 | 4 / 4 | 622.3 / 2288.3 |
| chW1_o6__0 | R060 -> R053 | 565 | OFF | nontree (amb 2) | 1039..3959 | 8 | 4 / 4 | 622.3 / 2288.3 |
| chE4_o6__0 | R030 -> R026 | 565 | OFF | nontree (amb 2) | 1039..3959 | 8 | 4 / 4 | 622.3 / 2288.3 |
| chW4_o6__0 | R027 -> R020 | 565 | OFF | nontree (amb 2) | 1039..3959 | 8 | 4 / 4 | 622.3 / 2288.3 |
| chE0_o6__0 | R074 -> R070 | 565 | OFF | nontree (amb 2) | 1097..3901 | 8 | 4 / 4 | 680.3 / 2346.3 |
| chW0_o6__0 | R071 -> R064 | 565 | OFF | nontree (amb 2) | 1097..3901 | 8 | 4 / 4 | 680.3 / 2346.3 |
| chE5_o6__0 | R019 -> R015 | 565 | OFF | nontree (amb 2) | 1097..3901 | 8 | 4 / 4 | 680.3 / 2346.3 |
| chW5_o6__0 | R016 -> R009 | 565 | OFF | nontree (amb 2) | 1097..3901 | 8 | 4 / 4 | 680.3 / 2346.3 |
| sp_x3__0 | R045 -> R034 | 565 | on | nontree (amb 1) | 975..3190 | 8 | 4 / 4 | 558.5 / 3057.5 |
| sp_b3__0 | R034 -> R045 | 565 | on | nontree (amb 1) | 975..3190 | 8 | 3 / 3 | 558.5 / 3057.5 |
| sp_x4__0 | R034 -> R023 | 565 | on | nontree (amb 1) | 975..3190 | 8 | 4 / 4 | 558.5 / 3057.5 |

Per-crossing K/DEPTH/latency/margins: head_v3_crossings.tsv (all 162).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
