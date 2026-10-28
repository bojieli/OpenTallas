# 12.14b ESTIMATE v3: hbm, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/die-hbm-1027/c20/die_plan.json (sha256 c9dbfc156c28), 88 partitions, 629 ports; clock wire v = 366.4 ps/mm TT (single-map score x1.05 spice); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map quad, feed fish

* 4 regions, max span 28.40 mm, bit-mm inside 86.2 %, 60 crossings (53841 bits), 1 connected component(s), start-tree edges clean 0/3, max path ambiguity 2 cycles.
* **DEPTH4 14, DEPTH8 46 (42344 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 104.1 ps / high 213.2 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'3': 16, '4': 26, '5': 15, '6': 3}; max 6; bit-weighted mean 3.67.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-3': 11, '-2': 2, '1': 7, '2': 8, '3': 1, '4': 3, '5': 13, '10': 12, '12': 3}; bit-weighted: {'-3': 12474, '-2': 36, '1': 5649, '2': 6796, '3': 16, '4': 4236, '5': 9904, '10': 10494, '12': 4236}.
* Render:  (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.8 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quad | fish | 4 | 28.40* | 86.2 % | 60 | 14 | 46 | 0 | 104.1 / 213.2 | 6 | {'3': 16, '4': 26, '5': 15, '6': 3} | -5625 / -4734 |
| v1_s3.5 | fish | 4 | 28.40* | 86.2 % | 60 | 14 | 46 | 0 | 104.1 / 213.2 | 6 | {'3': 16, '4': 26, '5': 15, '6': 3} | -5625 / -4734 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L21_1 | TOP -> NW | 2048 | OFF | nontree (amb 2) | 1332..4846 | 8 | 4 / 5 | 916.0 / 1402.0 |
| L22_1 | TOP -> NW | 2048 | OFF | nontree (amb 2) | 1332..4846 | 8 | 4 / 5 | 916.0 / 1402.0 |
| L82_0 | TOP -> NW | 140 | OFF | nontree (amb 2) | 1332..4846 | 8 | 4 / 5 | 916.0 / 1402.0 |
| L21m_1 | TOP -> NE | 2048 | on | nontree (amb 2) | 1352..4538 | 8 | 12 / 6 | 935.3 / 1709.7 |
| L22m_1 | TOP -> NE | 2048 | on | nontree (amb 2) | 1352..4538 | 8 | 12 / 6 | 935.3 / 1709.7 |
| L82m_0 | TOP -> NE | 140 | on | nontree (amb 2) | 1352..4538 | 8 | 12 / 6 | 935.3 / 1709.7 |
| L8_4 | NW -> TOP | 2456 | OFF | nontree (amb 2) | 986..4498 | 8 | 5 / 5 | 569.0 / 1749.0 |
| L66_4 | NW -> TOP | 268 | OFF | nontree (amb 2) | 986..4498 | 8 | 5 / 5 | 569.0 / 1749.0 |
| L79_4 | NW -> TOP | 172 | OFF | nontree (amb 2) | 986..4498 | 8 | 5 / 5 | 569.0 / 1749.0 |
| L8m_4 | NE -> TOP | 2456 | on | nontree (amb 2) | 1293..4479 | 8 | -3 / 4 | 876.7 / 1768.3 |
| L66m_4 | NE -> TOP | 268 | on | nontree (amb 2) | 1293..4479 | 8 | -3 / 4 | 876.7 / 1768.3 |
| L79m_4 | NE -> TOP | 172 | on | nontree (amb 2) | 1293..4479 | 8 | -3 / 4 | 876.7 / 1768.3 |
| L106_0 | ROOT -> NW | 20 | on | nontree (amb 1) | 1339..3755 | 8 | -2 / 4 | 922.5 / 2492.9 |
| L114_4 | ROOT -> NW | 16 | on | nontree (amb 1) | 1339..3755 | 8 | -2 / 4 | 922.5 / 2492.9 |
| L125_7 | NW -> ROOT | 7 | on | nontree (amb 1) | 1243..3659 | 8 | 10 / 5 | 826.9 / 2588.5 |

Per-crossing K/DEPTH/latency/margins: hbm_v3_crossings.tsv (all 60).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
