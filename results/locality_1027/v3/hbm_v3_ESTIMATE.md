# 12.14b ESTIMATE v3: hbm, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json (sha256 6a711a87b7e7), 88 partitions, 631 ports; clock wire v = 349 ps/mm TT (HBM not measured: conservative = highest measured die (HEAD 349) x1.0); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map tree_s3.5c5, feed fish

* 63 regions, max span 8.80 mm, bit-mm inside 9.0 %, 519 crossings (463923 bits), 1 connected component(s), start-tree edges clean 50/60, max path ambiguity 2 cycles.
* **DEPTH4 499, DEPTH8 20 (17262 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 134.2 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 46, '3': 410, '4': 60, '5': 3}; max 5; bit-weighted mean 2.51.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-4': 4, '-1': 18, '0': 19, '1': 87, '2': 188, '3': 98, '4': 55, '5': 20, '6': 12, '7': 16, '11': 2}; bit-weighted: {'-4': 5584, '-1': 20136, '0': 18337, '1': 70511, '2': 188860, '3': 89035, '4': 45746, '5': 9153, '6': 3181, '7': 13348, '11': 32}.
* Render: hbm_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.8 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree_s3.5c5 | fish | 63 | 8.80 | 9.0 % | 519 | 499 | 20 | 0 | 104.1 / 134.2 | 5 | {'2': 46, '3': 410, '4': 60, '5': 3} | -6387 / -5376 |
| tree_s2c3.5 | fish | 82 | 8.80 | 1.4 % | 611 | 592 | 19 | 0 | 104.1 / 119.0 | 5 | {'2': 40, '3': 529, '4': 37, '5': 5} | -5720 / -4807 |
| tree_s1.5c3 | fish | 88 | 8.80 | 0.0 % | 631 | 613 | 18 | 0 | 104.1 / 136.2 | 5 | {'2': 56, '3': 533, '4': 37, '5': 5} | -5720 / -4807 |
| v1_s3.5 | fish | 66 | 8.80 | 8.2 % | 527 | 497 | 27 | 3 | 104.1 / 134.2 | 6 | {'2': 49, '3': 406, '4': 63, '5': 4, '6': 2} | -5720 / -4807 |
| tree_s3.5c5 | fwd | 63 | 8.80 | 9.0 % | 519 | 414 | 102 | 3 | 104.1 / 112.9 | 6 | {'2': 58, '3': 313, '4': 116, '5': 25, '6': 4} | -14754 / -12517 |
| v1_s3.5 | fwd | 66 | 8.80 | 8.2 % | 527 | 443 | 75 | 9 | 104.1 / 112.9 | 5 | {'2': 62, '3': 337, '4': 110, '5': 9} | -14228 / -12069 |
| tree_s2c3.5 | fwd | 82 | 8.80 | 1.4 % | 611 | 545 | 57 | 9 | 104.1 / 124.2 | 5 | {'2': 118, '3': 414, '4': 62, '5': 8} | -15178 / -12880 |
| tree_s1.5c3 | fwd | 88 | 8.80 | 0.0 % | 631 | 567 | 55 | 9 | 104.1 / 124.1 | 5 | {'2': 124, '3': 426, '4': 62, '5': 10} | -15178 / -12880 |
| tree_s3.5c5 | dme | 63 | 8.80 | 9.0 % | 519 | 238 | 272 | 9 | 104.1 / 351.6 | 5 | {'2': 158, '3': 173, '4': 162, '5': 17} | -513 / -346 |
| v1_s3.5 | dme | 66 | 8.80 | 8.2 % | 527 | 238 | 280 | 9 | 104.1 / 428.8 | 5 | {'2': 160, '3': 177, '4': 169, '5': 12} | -504 / -339 |
| tree_s2c3.5 | spine | 82 | 8.80 | 1.4 % | 611 | 529 | 73 | 9 | 104.1 / 137.2 | 5 | {'2': 12, '3': 440, '4': 121, '5': 29} | -5742 / -4826 |
| tree_s1.5c3 | spine | 88 | 8.80 | 0.0 % | 631 | 553 | 69 | 9 | 104.1 / 179.4 | 5 | {'2': 14, '3': 472, '4': 111, '5': 25} | -5742 / -4826 |
| tree_s2c3.5 | dme | 82 | 8.80 | 1.4 % | 611 | 268 | 334 | 9 | 104.1 / 371.3 | 5 | {'2': 200, '3': 200, '4': 186, '5': 16} | -504 / -339 |
| tree_s1.5c3 | dme | 88 | 8.80 | 0.0 % | 631 | 312 | 310 | 9 | 104.1 / 371.3 | 5 | {'2': 226, '3': 202, '4': 182, '5': 12} | -504 / -339 |
| v1_s3.5 | spine | 66 | 8.80 | 8.2 % | 527 | 449 | 69 | 9 | 104.1 / 117.9 | 7 | {'2': 17, '3': 334, '4': 145, '5': 20, '7': 2} | -5742 / -4826 |
| tree_s3.5c5 | spine | 63 | 8.80 | 9.0 % | 519 | 390 | 120 | 9 | 104.1 / 208.9 | 7 | {'2': 12, '3': 299, '4': 152, '5': 40, '6': 5, '7': 2} | -6409 / -5395 |
| c18quad | fish | 4 | 28.40* | 86.2 % | 60 | 14 | 46 | 0 | 104.1 / 294.3 | 6 | {'2': 1, '3': 11, '4': 29, '5': 16, '6': 3} | -5353 / -4502 |
| c18quad | dme | 4 | 28.40* | 86.2 % | 60 | 3 | 51 | 6 | 104.1 / 222.7 | 5 | {'3': 12, '4': 36, '5': 6} | -580 / -401 |
| c18quad | fwd | 4 | 28.40* | 86.2 % | 60 | 3 | 51 | 6 | 104.1 / 170.6 | 6 | {'3': 2, '4': 32, '5': 9, '6': 11} | -8350 / -7060 |
| c18quad | spine | 4 | 28.40* | 86.2 % | 60 | 3 | 45 | 12 | 104.1 / 338.2 | 5 | {'3': 2, '4': 32, '5': 14} | -6289 / -5294 |
| tree_s2c3.5 | top | 82 | 8.80 | 1.4 % | 611 | 293 | 275 | 43 | 104.1 / 462.4 | 7 | {'2': 94, '3': 315, '4': 115, '5': 22, '6': 12, '7': 10} | -352 / -224 |
| tree_s1.5c3 | top | 88 | 8.80 | 0.0 % | 631 | 313 | 275 | 43 | 104.1 / 462.4 | 7 | {'2': 100, '3': 329, '4': 115, '5': 22, '6': 12, '7': 10} | -352 / -224 |
| tree_s3.5c5 | top | 63 | 8.80 | 9.0 % | 519 | 188 | 212 | 119 | 104.1 / 475.5 | 6 | {'2': 75, '3': 212, '4': 86, '5': 22, '6': 5} | -343 / -216 |
| v1_s3.5 | top | 66 | 8.80 | 8.2 % | 527 | 196 | 212 | 119 | 104.1 / 475.5 | 6 | {'2': 78, '3': 217, '4': 85, '5': 23, '6': 5} | -343 / -216 |
| c18quad | top | 4 | 28.40* | 86.2 % | 60 | 3 | 57 | 0 | 104.1 / 475.5 | 5 | {'3': 15, '4': 42, '5': 3} | -394 / -254 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L8_5 | T059 -> T060 | 2456 | OFF | nontree (amb 2) | 910..4408 | 8 | 4 / 5 | 493.8 / 1839.2 |
| L21_0 | T060 -> T059 | 2048 | OFF | nontree (amb 2) | 590..4088 | 8 | 4 / 4 | 173.2 / 2159.8 |
| L22_0 | T060 -> T059 | 2048 | OFF | nontree (amb 2) | 590..4088 | 8 | 4 / 4 | 173.2 / 2159.8 |
| L9_1 | T010 -> T054 | 2456 | OFF | nontree (amb 1) | 628..3575 | 8 | -4 / 4 | 211.7 / 2672.3 |
| L9m_1 | T010 -> T054 | 2456 | OFF | nontree (amb 1) | 628..3575 | 8 | -4 / 4 | 211.7 / 2672.3 |
| L63_1 | T010 -> T054 | 336 | OFF | nontree (amb 1) | 628..3575 | 8 | -4 / 4 | 211.7 / 2672.3 |
| L63m_1 | T010 -> T054 | 336 | OFF | nontree (amb 1) | 628..3575 | 8 | -4 / 4 | 211.7 / 2672.3 |
| L114_3 | T054 -> T010 | 16 | OFF | nontree (amb 1) | 590..3537 | 8 | 11 / 4 | 173.3 / 2710.7 |
| L114m_3 | T054 -> T010 | 16 | OFF | nontree (amb 1) | 590..3537 | 8 | 11 / 4 | 173.3 / 2710.7 |
| L12_0 | T010 -> T014 | 2996 | OFF | nontree (amb 1) | 1339..3260 | 8 | 0 / 4 | 922.8 / 2987.5 |
| L53_0 | T010 -> T014 | 612 | OFF | nontree (amb 1) | 1339..3260 | 8 | 0 / 4 | 922.8 / 2987.5 |
| L80_0 | T010 -> T014 | 171 | OFF | nontree (amb 1) | 1339..3260 | 8 | 0 / 4 | 922.8 / 2987.5 |
| L124_0 | T010 -> T014 | 9 | OFF | nontree (amb 1) | 1339..3260 | 8 | 0 / 4 | 922.8 / 2987.5 |
| L76_0 | T007 -> T002 | 173 | OFF | nontree (amb 1) | 1215..3206 | 8 | 2 / 5 | 798.9 / 3041.6 |
| L76m_0 | T009 -> T004 | 173 | OFF | nontree (amb 1) | 1194..3182 | 8 | 2 / 5 | 778.0 / 3066.0 |

Per-crossing K/DEPTH/latency/margins: hbm_v3_crossings.tsv (all 519).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
