# 12.14b ESTIMATE v3: hbm, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/die-hbm-1027/c20/die_plan.json (sha256 c9dbfc156c28), 88 partitions, 629 ports; clock wire v = 366.4 ps/mm TT (single-map score x1.05 spice); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map t63c20, feed fish

* 63 regions, max span 8.80 mm, bit-mm inside 8.4 %, 519 crossings (463923 bits), 1 connected component(s), start-tree edges clean 38/60, max path ambiguity 5 cycles.
* **DEPTH4 466, DEPTH8 44 (31798 bits), FAIL even at DEPTH8 9 (12168 bits)**; worst margin low 104.1 ps / high 128.9 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 28, '3': 360, '4': 109, '5': 12, '6': 1}; max 6; bit-weighted mean 2.59.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-1': 15, '0': 28, '1': 88, '2': 159, '3': 108, '4': 31, '5': 35, '6': 23, '7': 19, '8': 4}; bit-weighted: {'-1': 14662, '0': 28710, '1': 62299, '2': 156475, '3': 118171, '4': 23710, '5': 21989, '6': 13127, '7': 12058, '8': 554}.
* Render:  (VIEWED).

Hop chains (12.13c) ONLY for the 9 D8-fail crossings: 9 chains (0 already on-feed, cannot be chained), max 9 hops, 86112 extra bit-hops, 0 synthetic feed-edge crossings; after re-timing: D4 466, D8 44, FAIL 0; chain latency (cycles: chains) {'32': 6, '45': 3} (landing cycles only, intra-region transit not counted).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 8.8 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| t63c20 | fish | 63 | 8.80 | 8.4 % | 519 | 466 | 44 | 9 | 104.1 / 128.9 | 6 | {'2': 28, '3': 360, '4': 109, '5': 12, '6': 1} | -6722 / -5662 |
| v1_s3.5 | fish | 63 | 8.80 | 8.4 % | 519 | 466 | 44 | 9 | 104.1 / 128.9 | 6 | {'2': 28, '3': 360, '4': 109, '5': 12, '6': 1} | -6722 / -5662 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| L8_5 | T059 -> T060 | 2456 | OFF | nontree (amb 5) | 882..6951 | FAIL | - / - | 465.7 / -703.9 |
| L114_3 | T054 -> T010 | 16 | OFF | nontree (amb 4) | 1087..6622 | FAIL | - / - | 670.5 / -374.6 |
| L114m_3 | T054 -> T010 | 16 | OFF | nontree (amb 4) | 1087..6622 | FAIL | - / - | 670.5 / -374.6 |
| L21_0 | T060 -> T059 | 2048 | OFF | nontree (amb 5) | 546..6615 | FAIL | - / - | 129.1 / -367.3 |
| L22_0 | T060 -> T059 | 2048 | OFF | nontree (amb 5) | 546..6615 | FAIL | - / - | 129.1 / -367.3 |
| L9_1 | T010 -> T054 | 2456 | OFF | nontree (amb 4) | 875..6410 | FAIL | - / - | 458.4 / -162.5 |
| L9m_1 | T010 -> T054 | 2456 | OFF | nontree (amb 4) | 875..6410 | FAIL | - / - | 458.4 / -162.5 |
| L63_1 | T010 -> T054 | 336 | OFF | nontree (amb 4) | 875..6410 | FAIL | - / - | 458.4 / -162.5 |
| L63m_1 | T010 -> T054 | 336 | OFF | nontree (amb 4) | 875..6410 | FAIL | - / - | 458.4 / -162.5 |
| L78m_0 | T047 -> T052 | 173 | OFF | nontree (amb 3) | 1216..4688 | 8 | 4 / 6 | 799.1 / 1559.1 |
| L76_0 | T007 -> T002 | 173 | OFF | nontree (amb 2) | 1351..4234 | 8 | 2 / 5 | 934.2 / 2013.1 |
| L48_6 | T007 -> T013 | 634 | OFF | nontree (amb 2) | 1222..3778 | 8 | 7 / 5 | 805.5 / 2469.5 |
| L48m_6 | T009 -> T016 | 634 | OFF | nontree (amb 2) | 1222..3778 | 8 | 7 / 5 | 805.5 / 2469.5 |
| L117_3 | T007 -> T013 | 11 | OFF | nontree (amb 2) | 1222..3778 | 8 | 7 / 5 | 805.5 / 2469.5 |
| L117m_3 | T009 -> T016 | 11 | OFF | nontree (amb 2) | 1222..3778 | 8 | 7 / 5 | 805.5 / 2469.5 |

Per-crossing K/DEPTH/latency/margins: hbm_v3_crossings.tsv (all 519).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
