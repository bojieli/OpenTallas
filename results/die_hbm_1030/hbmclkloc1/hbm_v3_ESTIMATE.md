# 12.14b ESTIMATE v3: hbm, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/die-hbm-45/plan/d44f/die_plan.json (sha256 a6402d40d1a2), 90 partitions, 900 ports; clock wire v = 280 ps/mm TT (d44f B routed street_body tree: late/path 270-300 ps/mm inv2 1x (regB.json)); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map tree_s3.5c5, feed fish

* 66 regions, max span 8.22 mm, bit-mm inside 7.9 %, 752 crossings (630250 bits), 1 connected component(s), start-tree edges clean 58/63, max path ambiguity 1 cycles.
* **DEPTH4 752, DEPTH8 0 (0 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 117.4 ps / high 132.2 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 155, '3': 539, '4': 58}; max 4; bit-weighted mean 2.36.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'0': 12, '1': 145, '2': 356, '3': 154, '4': 34, '5': 51}; bit-weighted: {'0': 8926, '1': 134512, '2': 346420, '3': 89329, '4': 18494, '5': 32569}.
* Render: hbm_v3_best_cap.png (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.22 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree_s3.5c5 | fish | 66 | 8.22 | 7.9 % | 752 | 752 | 0 | 0 | 117.4 / 132.2 | 4 | {'2': 155, '3': 539, '4': 58} | -2695 / -2235 |
| v1_s3.5 | fish | 70 | 8.22 | 6.2 % | 776 | 776 | 0 | 0 | 117.4 / 132.2 | 4 | {'2': 155, '3': 563, '4': 58} | -2695 / -2235 |
| tree_s2c3.5 | fish | 82 | 8.22 | 2.1 % | 858 | 858 | 0 | 0 | 108.3 / 185.8 | 4 | {'2': 116, '3': 692, '4': 50} | -2272 / -1873 |
| tree_s3.5c5 | fwd | 66 | 8.22 | 7.9 % | 752 | 695 | 57 | 0 | 110.7 / 131.1 | 5 | {'2': 178, '3': 438, '4': 132, '5': 4} | -3955 / -3304 |
| v1_s3.5 | fwd | 70 | 8.22 | 6.2 % | 776 | 711 | 65 | 0 | 106.8 / 131.1 | 5 | {'2': 208, '3': 432, '4': 132, '5': 4} | -3955 / -3304 |
| tree_s3.5c5 | spine | 66 | 8.22 | 7.9 % | 752 | 694 | 58 | 0 | 104.6 / 115.3 | 5 | {'2': 73, '3': 575, '4': 76, '5': 28} | -2711 / -2248 |
| v1_s3.5 | spine | 70 | 8.22 | 6.2 % | 776 | 728 | 48 | 0 | 104.6 / 179.6 | 5 | {'2': 81, '3': 583, '4': 88, '5': 24} | -2711 / -2248 |
| tree_s2c3.5 | fwd | 82 | 8.22 | 2.1 % | 858 | 801 | 57 | 0 | 106.8 / 166.0 | 5 | {'2': 214, '3': 545, '4': 93, '5': 6} | -4151 / -3472 |
| tree_s2c3.5 | spine | 82 | 8.22 | 2.1 % | 858 | 812 | 46 | 0 | 110.5 / 179.6 | 5 | {'2': 70, '3': 716, '4': 52, '5': 20} | -2288 / -1886 |
| part | fish | 90 | 8.22 | 0.0 % | 900 | 881 | 19 | 0 | 117.4 / 185.8 | 5 | {'2': 141, '3': 700, '4': 57, '5': 2} | -2921 / -2424 |
| part | fwd | 90 | 8.22 | 0.0 % | 900 | 849 | 51 | 0 | 104.6 / 104.6 | 5 | {'2': 210, '3': 575, '4': 104, '5': 11} | -4861 / -4080 |
| part | spine | 90 | 8.22 | 0.0 % | 900 | 841 | 59 | 0 | 112.4 / 123.4 | 5 | {'2': 82, '3': 745, '4': 47, '5': 26} | -3142 / -2613 |
| tree_s3.5c5 | dme | 66 | 8.22 | 7.9 % | 752 | 390 | 362 | 0 | 135.4 / 782.2 | 5 | {'2': 262, '3': 253, '4': 223, '5': 14} | -151 / -56 |
| v1_s3.5 | dme | 70 | 8.22 | 6.2 % | 776 | 376 | 400 | 0 | 135.4 / 782.2 | 5 | {'2': 262, '3': 257, '4': 239, '5': 18} | -151 / -56 |
| tree_s2c3.5 | dme | 82 | 8.22 | 2.1 % | 858 | 464 | 394 | 0 | 116.1 / 782.2 | 5 | {'2': 312, '3': 285, '4': 239, '5': 22} | -122 / -32 |
| part | dme | 90 | 8.22 | 0.0 % | 900 | 496 | 404 | 0 | 116.1 / 782.2 | 5 | {'2': 356, '3': 271, '4': 251, '5': 22} | -140 / -45 |
| sb63 | fish | 63 | 8.80* | 7.1 % | 773 | 762 | 11 | 0 | 117.4 / 132.2 | 5 | {'2': 178, '3': 531, '4': 60, '5': 4} | -2679 / -2220 |
| sb63 | dme | 63 | 8.80* | 7.1 % | 773 | 415 | 358 | 0 | 116.1 / 673.3 | 5 | {'2': 262, '3': 270, '4': 218, '5': 23} | -219 / -108 |
| sb63 | fwd | 63 | 8.80* | 7.1 % | 773 | 632 | 141 | 0 | 108.2 / 108.2 | 6 | {'2': 172, '3': 395, '4': 176, '5': 23, '6': 7} | -3955 / -3304 |
| sb63 | spine | 63 | 8.80* | 7.1 % | 773 | 705 | 68 | 0 | 104.6 / 115.3 | 6 | {'2': 69, '3': 581, '4': 94, '5': 23, '6': 6} | -2734 / -2267 |
| tree_s3.5c5 | top | 66 | 8.22 | 7.9 % | 752 | 393 | 359 | 0 | 115.3 / 614.9 | 5 | {'2': 164, '3': 368, '4': 211, '5': 9} | -190 / -90 |
| v1_s3.5 | top | 70 | 8.22 | 6.2 % | 776 | 417 | 359 | 0 | 115.3 / 614.9 | 5 | {'2': 164, '3': 392, '4': 211, '5': 9} | -190 / -90 |
| tree_s2c3.5 | top | 82 | 8.22 | 2.1 % | 858 | 524 | 334 | 0 | 113.2 / 611.1 | 5 | {'2': 170, '3': 495, '4': 187, '5': 6} | -197 / -96 |
| part | top | 90 | 8.22 | 0.0 % | 900 | 566 | 334 | 0 | 114.2 / 792.8 | 5 | {'2': 188, '3': 523, '4': 187, '5': 2} | -197 / -96 |
| sb63 | top | 63 | 8.80* | 7.1 % | 773 | 416 | 357 | 0 | 115.3 / 625.4 | 5 | {'2': 162, '3': 377, '4': 210, '5': 24} | -207 / -103 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L33_2 | T007 -> T000 | 1615 | on | nontree (amb 1) | 1048..2783 | 4 | 1 / 4 | 631.0 / 132.2 |
| L33m_2 | T009 -> T006 | 1615 | on | nontree (amb 1) | 1048..2783 | 4 | 1 / 4 | 631.0 / 132.2 |
| L75_0 | T007 -> T000 | 173 | on | nontree (amb 1) | 1048..2783 | 4 | 1 / 4 | 631.0 / 132.2 |
| L75m_0 | T009 -> T006 | 173 | on | nontree (amb 1) | 1048..2783 | 4 | 1 / 4 | 631.0 / 132.2 |
| L99_1 | T007 -> T000 | 22 | on | nontree (amb 1) | 1043..2745 | 4 | 1 / 4 | 626.5 / 170.1 |
| L99m_1 | T009 -> T006 | 22 | on | nontree (amb 1) | 1043..2745 | 4 | 1 / 4 | 626.5 / 170.1 |
| L106_0 | T010 -> T044 | 20 | OFF | nontree (amb 1) | 822..2715 | 4 | 1 / 4 | 405.4 / 200.9 |
| L106m_0 | T010 -> T045 | 20 | OFF | nontree (amb 1) | 822..2715 | 4 | 1 / 4 | 405.4 / 200.9 |
| L114_4 | T010 -> T044 | 6 | OFF | nontree (amb 1) | 822..2715 | 4 | 1 / 4 | 405.4 / 200.9 |
| L114m_4 | T010 -> T045 | 6 | OFF | nontree (amb 1) | 822..2715 | 4 | 1 / 4 | 405.4 / 200.9 |
| L700_2 | T010 -> T044 | 2807 | OFF | nontree (amb 1) | 822..2715 | 4 | 1 / 4 | 405.4 / 200.9 |
| L701_2 | T010 -> T045 | 2762 | OFF | nontree (amb 1) | 822..2715 | 4 | 1 / 4 | 405.4 / 200.9 |
| L12_0 | T010 -> T014 | 1980 | OFF | nontree (amb 1) | 818..2709 | 4 | 1 / 4 | 401.6 / 206.2 |
| L12m_0 | T010 -> T015 | 1980 | OFF | nontree (amb 1) | 818..2709 | 4 | 1 / 4 | 401.6 / 206.2 |
| L53_0 | T010 -> T014 | 612 | OFF | nontree (amb 1) | 818..2709 | 4 | 1 / 4 | 401.6 / 206.2 |

Per-crossing K/DEPTH/latency/margins: hbm_v3_crossings.tsv (all 752).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
