# 12.14b ESTIMATE v3: hbm, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/die-hbm-1027/c20/die_plan.json (sha256 c9dbfc156c28), 88 partitions, 629 ports; clock wire v = 401.4 ps/mm TT (single-map score x1.05 spice); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map t82c20, feed fish

* 82 regions, max span 8.80 mm, bit-mm inside 1.4 %, 609 crossings (532783 bits), 1 connected component(s), start-tree edges clean 69/79, max path ambiguity 4 cycles.
* **DEPTH4 564, DEPTH8 42 (24229 bits), FAIL even at DEPTH8 3 (6552 bits)**; worst margin low 104.1 ps / high 116.5 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 45, '3': 505, '4': 49, '5': 7}; max 5; bit-weighted mean 2.48.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-3': 4, '-2': 1, '-1': 17, '0': 15, '1': 71, '2': 239, '3': 188, '4': 38, '5': 3, '6': 14, '7': 7, '8': 7, '12': 2}; bit-weighted: {'-3': 5584, '-2': 2628, '-1': 15854, '0': 16472, '1': 53493, '2': 236265, '3': 154230, '4': 25128, '5': 43, '6': 10744, '7': 2620, '8': 3138, '12': 32}.
* Render:  (VIEWED).

Hop chains (12.13c) ONLY for the 3 D8-fail crossings: 3 chains (0 already on-feed, cannot be chained), max 13 hops, 78624 extra bit-hops, 0 synthetic feed-edge crossings; after re-timing: D4 564, D8 42, FAIL 0; chain latency (cycles: chains) {'49': 3} (landing cycles only, intra-region transit not counted).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.8 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| t82c20 | fish | 82 | 8.80 | 1.4 % | 609 | 564 | 42 | 3 | 104.1 / 116.5 | 5 | {'2': 45, '3': 505, '4': 49, '5': 7} | -6616 / -5571 |
| v1_s3.5 | fish | 82 | 8.80 | 1.4 % | 609 | 564 | 42 | 3 | 104.1 / 116.5 | 5 | {'2': 45, '3': 505, '4': 49, '5': 7} | -6616 / -5571 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L21_0 | T079 -> T078 | 2048 | OFF | nontree (amb 4) | 1139..6432 | FAIL | - / - | 722.1 / -184.9 |
| L22_0 | T079 -> T078 | 2048 | OFF | nontree (amb 4) | 1139..6432 | FAIL | - / - | 722.1 / -184.9 |
| L8_5 | T078 -> T079 | 2456 | OFF | nontree (amb 4) | 1065..6358 | FAIL | - / - | 648.1 / -110.9 |
| L114_3 | T070 -> T013 | 16 | OFF | nontree (amb 2) | 1193..5072 | 8 | 12 / 5 | 776.8 / 1175.4 |
| L114m_3 | T070 -> T013 | 16 | OFF | nontree (amb 2) | 1193..5072 | 8 | 12 / 5 | 776.8 / 1175.4 |
| L9_1 | T013 -> T070 | 2456 | OFF | nontree (amb 2) | 759..4638 | 8 | -3 / 5 | 342.4 / 1609.8 |
| L9m_1 | T013 -> T070 | 2456 | OFF | nontree (amb 2) | 759..4638 | 8 | -3 / 5 | 342.4 / 1609.8 |
| L63_1 | T013 -> T070 | 336 | OFF | nontree (amb 2) | 759..4638 | 8 | -3 / 5 | 342.4 / 1609.8 |
| L63m_1 | T013 -> T070 | 336 | OFF | nontree (amb 2) | 759..4638 | 8 | -3 / 5 | 342.4 / 1609.8 |
| L77_0 | T065 -> T064 | 173 | OFF | nontree (amb 2) | 1013..4026 | 8 | -1 / 4 | 596.8 / 2221.8 |
| L77m_0 | T068 -> T069 | 173 | OFF | nontree (amb 2) | 1013..4026 | 8 | -1 / 4 | 596.8 / 2221.8 |
| L70_0 | T002 -> T019 | 268 | OFF | nontree (amb 1) | 1208..3202 | 8 | 7 / 4 | 791.2 / 3045.7 |
| L70m_0 | T004 -> T024 | 268 | OFF | nontree (amb 1) | 1208..3202 | 8 | 7 / 4 | 791.2 / 3045.7 |
| L123_0 | T002 -> T019 | 9 | OFF | nontree (amb 1) | 1208..3202 | 8 | 7 / 4 | 791.2 / 3045.7 |
| L123m_0 | T004 -> T024 | 9 | OFF | nontree (amb 1) | 1208..3202 | 8 | 7 / 4 | 791.2 / 3045.7 |

Per-crossing K/DEPTH/latency/margins: hbm_v3_crossings.tsv (all 609).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
