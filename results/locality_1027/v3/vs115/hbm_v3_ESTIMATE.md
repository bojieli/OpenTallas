# 12.14b ESTIMATE v3: hbm, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json (sha256 6a711a87b7e7), 88 partitions, 631 ports; clock wire v = 401.3 ps/mm TT (HBM not measured: conservative = highest measured die (HEAD 349) x1.15); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map v1_s3.5, feed fish

* 66 regions, max span 8.80 mm, bit-mm inside 8.2 %, 527 crossings (470002 bits), 1 connected component(s), start-tree edges clean 48/63, max path ambiguity 2 cycles.
* **DEPTH4 472, DEPTH8 55 (36426 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 120.7 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 46, '3': 370, '4': 97, '5': 10, '6': 4}; max 6; bit-weighted mean 2.60.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-4': 4, '-2': 1, '-1': 23, '0': 21, '1': 96, '2': 158, '3': 115, '4': 35, '5': 33, '6': 15, '7': 13, '8': 7, '9': 4, '13': 2}; bit-weighted: {'-4': 5584, '-2': 2628, '-1': 19474, '0': 27302, '1': 65161, '2': 158345, '3': 118653, '4': 30243, '5': 22223, '6': 12361, '7': 4304, '8': 3138, '9': 554, '13': 32}.
* Render: hbm_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.8 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1_s3.5 | fish | 66 | 8.80 | 8.2 % | 527 | 472 | 55 | 0 | 104.1 / 120.7 | 6 | {'2': 46, '3': 370, '4': 97, '5': 10, '6': 4} | -6629 / -5582 |
| tree_s3.5c5 | fish | 63 | 8.80 | 9.0 % | 519 | 454 | 65 | 0 | 104.1 / 120.5 | 7 | {'2': 44, '3': 346, '4': 112, '5': 12, '6': 1, '7': 4} | -7396 / -6236 |
| tree_s2c3.5 | fish | 82 | 8.80 | 1.4 % | 611 | 565 | 43 | 3 | 104.1 / 142.0 | 5 | {'2': 45, '3': 507, '4': 48, '5': 8} | -6629 / -5582 |
| tree_s1.5c3 | fish | 88 | 8.80 | 0.0 % | 631 | 585 | 43 | 3 | 104.1 / 142.0 | 5 | {'2': 51, '3': 523, '4': 46, '5': 8} | -6629 / -5582 |
| v1_s3.5 | spine | 66 | 8.80 | 8.2 % | 527 | 342 | 176 | 9 | 104.1 / 119.3 | 8 | {'2': 17, '3': 293, '4': 162, '5': 42, '7': 2, '8': 2} | -6655 / -5604 |
| tree_s3.5c5 | spine | 63 | 8.80 | 9.0 % | 519 | 323 | 183 | 13 | 104.1 / 119.3 | 8 | {'2': 17, '3': 268, '4': 172, '5': 41, '6': 4, '7': 2, '8': 2} | -7421 / -6257 |
| tree_s2c3.5 | spine | 82 | 8.80 | 1.4 % | 611 | 505 | 91 | 15 | 104.1 / 125.9 | 7 | {'2': 13, '3': 403, '4': 152, '5': 24, '6': 2, '7': 2} | -6655 / -5604 |
| tree_s1.5c3 | spine | 88 | 8.80 | 0.0 % | 631 | 505 | 111 | 15 | 104.1 / 110.1 | 7 | {'2': 15, '3': 408, '4': 163, '5': 28, '7': 2} | -6655 / -5604 |
| v1_s3.5 | fwd | 66 | 8.80 | 8.2 % | 527 | 430 | 80 | 17 | 104.1 / 104.2 | 5 | {'2': 9, '3': 344, '4': 133, '5': 24} | -16411 / -13931 |
| tree_s2c3.5 | fwd | 82 | 8.80 | 1.4 % | 611 | 526 | 68 | 17 | 104.1 / 104.2 | 5 | {'2': 32, '3': 430, '4': 116, '5': 16} | -17504 / -14863 |
| tree_s1.5c3 | fwd | 88 | 8.80 | 0.0 % | 631 | 546 | 68 | 17 | 104.1 / 104.2 | 5 | {'2': 34, '3': 448, '4': 114, '5': 18} | -17504 / -14863 |
| tree_s3.5c5 | fwd | 63 | 8.80 | 9.0 % | 519 | 418 | 84 | 17 | 104.1 / 104.2 | 6 | {'2': 11, '3': 330, '4': 142, '5': 18, '6': 1} | -17015 / -14446 |
| tree_s3.5c5 | dme | 63 | 8.80 | 9.0 % | 519 | 209 | 290 | 20 | 104.1 / 258.8 | 5 | {'2': 134, '3': 148, '4': 183, '5': 34} | -640 / -450 |
| v1_s3.5 | dme | 66 | 8.80 | 8.2 % | 527 | 209 | 297 | 21 | 104.1 / 263.1 | 5 | {'2': 136, '3': 145, '4': 183, '5': 42} | -629 / -442 |
| tree_s2c3.5 | dme | 82 | 8.80 | 1.4 % | 611 | 257 | 327 | 27 | 104.1 / 274.6 | 5 | {'2': 171, '3': 178, '4': 199, '5': 36} | -629 / -442 |
| tree_s1.5c3 | dme | 88 | 8.80 | 0.0 % | 631 | 285 | 317 | 29 | 104.1 / 274.6 | 5 | {'2': 185, '3': 185, '4': 194, '5': 38} | -629 / -442 |
| c18quad | fish | 4 | 28.40* | 86.2 % | 60 | 11 | 43 | 6 | 104.1 / 152.0 | 5 | {'3': 9, '4': 27, '5': 18} | -6210 / -5233 |
| c18quad | dme | 4 | 28.40* | 86.2 % | 60 | 3 | 45 | 12 | 104.1 / 170.4 | 4 | {'3': 12, '4': 36} | -716 / -513 |
| c18quad | fwd | 4 | 28.40* | 86.2 % | 60 | 3 | 45 | 12 | 104.1 / 236.9 | 6 | {'3': 3, '4': 22, '5': 8, '6': 15} | -9655 / -8174 |
| c18quad | spine | 4 | 28.40* | 86.2 % | 60 | 3 | 40 | 17 | 104.1 / 170.4 | 5 | {'3': 1, '4': 21, '5': 21} | -7282 / -6141 |
| tree_s2c3.5 | top | 82 | 8.80 | 1.4 % | 611 | 223 | 285 | 103 | 104.1 / 299.6 | 6 | {'2': 70, '3': 261, '4': 135, '5': 37, '6': 5} | -454 / -310 |
| tree_s1.5c3 | top | 88 | 8.80 | 0.0 % | 631 | 243 | 285 | 103 | 104.1 / 299.6 | 6 | {'2': 76, '3': 275, '4': 135, '5': 37, '6': 5} | -454 / -310 |
| tree_s3.5c5 | top | 63 | 8.80 | 9.0 % | 519 | 176 | 224 | 119 | 104.1 / 328.3 | 6 | {'2': 50, '3': 225, '4': 98, '5': 22, '6': 5} | -444 / -302 |
| v1_s3.5 | top | 66 | 8.80 | 8.2 % | 527 | 180 | 228 | 119 | 104.1 / 328.3 | 6 | {'2': 54, '3': 227, '4': 97, '5': 25, '6': 5} | -444 / -302 |
| c18quad | top | 4 | 28.40* | 86.2 % | 60 | 3 | 57 | 0 | 104.1 / 226.0 | 5 | {'3': 11, '4': 40, '5': 9} | -503 / -345 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L114_3 | R057 -> R010 | 16 | OFF | nontree (amb 2) | 1180..5062 | 8 | 13 / 6 | 763.8 / 1185.6 |
| L114m_3 | R057 -> R010 | 16 | OFF | nontree (amb 2) | 1180..5062 | 8 | 13 / 6 | 763.8 / 1185.6 |
| L21_0 | R063 -> R062 | 2048 | OFF | nontree (amb 2) | 1137..4768 | 8 | 5 / 6 | 720.6 / 1479.9 |
| L22_0 | R063 -> R062 | 2048 | OFF | nontree (amb 2) | 1137..4768 | 8 | 5 / 6 | 720.6 / 1479.9 |
| L8_5 | R062 -> R063 | 2456 | OFF | nontree (amb 2) | 1063..4694 | 8 | 4 / 4 | 646.9 / 1553.6 |
| L9_1 | R010 -> R057 | 2456 | OFF | nontree (amb 2) | 769..4651 | 8 | -4 / 4 | 352.6 / 1596.8 |
| L9m_1 | R010 -> R057 | 2456 | OFF | nontree (amb 2) | 769..4651 | 8 | -4 / 4 | 352.6 / 1596.8 |
| L63_1 | R010 -> R057 | 336 | OFF | nontree (amb 2) | 769..4651 | 8 | -4 / 4 | 352.6 / 1596.8 |
| L63m_1 | R010 -> R057 | 336 | OFF | nontree (amb 2) | 769..4651 | 8 | -4 / 4 | 352.6 / 1596.8 |
| L70_0 | R002 -> R013 | 268 | OFF | nontree (amb 2) | 1157..4093 | 8 | 9 / 5 | 740.9 / 2154.5 |
| L70m_0 | R004 -> R016 | 268 | OFF | nontree (amb 2) | 1157..4093 | 8 | 9 / 5 | 740.9 / 2154.5 |
| L123_0 | R002 -> R013 | 9 | OFF | nontree (amb 2) | 1157..4093 | 8 | 9 / 5 | 740.9 / 2154.5 |
| L123m_0 | R004 -> R016 | 9 | OFF | nontree (amb 2) | 1157..4093 | 8 | 9 / 5 | 740.9 / 2154.5 |
| L77_0 | R042 -> R053 | 173 | OFF | nontree (amb 2) | 994..4004 | 8 | -1 / 4 | 578.0 / 2243.8 |
| L77m_0 | R049 -> R056 | 173 | OFF | nontree (amb 2) | 994..4004 | 8 | -1 / 4 | 578.0 / 2243.8 |

Per-crossing K/DEPTH/latency/margins: hbm_v3_crossings.tsv (all 527).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
