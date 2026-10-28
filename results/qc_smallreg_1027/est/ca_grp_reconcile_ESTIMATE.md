# 12.14b ESTIMATE v3: qc, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/wt/qc-smallreg-1027/physical/die_plan/qwen_compute/die_plan_sliceclk.json (sha256 5545cbfca017), 377 partitions, 3005 ports; clock wire v = 334 ps/mm TT (334 ps/mm routed; count_align_plan @32e8cbb16; spice x1.0485 TT / x1.0552 FF); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map grp, feed fish

* 317 regions, max span 2.68 mm, bit-mm inside 9.2 %, 2558 crossings (1064916 bits), 1 connected component(s), start-tree edges clean 267/316, max path ambiguity 3 cycles.
* **DEPTH4 2399, DEPTH8 159 (81904 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 111.0 ps / high 257.9 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 497, '3': 1866, '4': 102, '5': 75, '6': 18}; max 6; bit-weighted mean 2.50.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'-5': 24, '-4': 6, '-3': 19, '-2': 23, '0': 24, '1': 308, '2': 755, '3': 1122, '4': 158, '5': 71, '8': 2, '9': 46}; bit-weighted: {'-5': 12384, '-4': 3096, '-3': 9802, '-2': 11822, '0': 12336, '1': 160546, '2': 329457, '3': 407906, '4': 60209, '5': 32686, '8': 1028, '9': 23644}.
* Render:  (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grp | fish | 317 | 2.68 | 9.2 % | 2558 | 2399 | 159 | 0 | 111.0 / 257.9 | 6 | {'2': 497, '3': 1866, '4': 102, '5': 75, '6': 18} | -6972 / -5880 |
| v1_s0.1 | fish | 377 | 2.62 | 0.0 % | 3005 | 2841 | 164 | 0 | 111.0 / 257.9 | 6 | {'2': 1010, '3': 1821, '4': 81, '5': 70, '6': 23} | -6994 / -5899 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| sl_W0_hc3__cwn3__0 | sl_W0_st_b -> c_W0_tn_10 | 516 | OFF | nontree (amb 2) | 1233..5466 | 8 | -3 / 6 | 816.3 / 781.7 |
| sl_E0_hc3__cwn3__0 | sl_E0_st_b -> c_E0_tn_10 | 516 | OFF | nontree (amb 2) | 1233..5466 | 8 | -3 / 6 | 816.3 / 781.7 |
| sl_E1_hc3__cwn3__0 | sl_E1_st_b -> c_E1_tn_10 | 516 | OFF | nontree (amb 2) | 1233..5466 | 8 | -3 / 6 | 816.3 / 781.7 |
| sl_E2_hc3__cwn3__0 | sl_E2_st_b -> c_E2_tn_10 | 516 | OFF | nontree (amb 2) | 1233..5466 | 8 | -3 / 6 | 816.3 / 781.7 |
| sl_E3_hc3__cwn3__0 | sl_E3_st_b -> c_E3_tn_10 | 516 | OFF | nontree (amb 2) | 1233..5466 | 8 | -3 / 6 | 816.3 / 781.7 |
| sl_E4_hc3__cwn3__0 | sl_E4_st_b -> c_E4_tn_10 | 516 | OFF | nontree (amb 2) | 1233..5466 | 8 | -3 / 6 | 816.3 / 781.7 |
| sl_E5_hc3__cwn3__0 | sl_E5_st_b -> c_E5_tn_10 | 516 | OFF | nontree (amb 2) | 1233..5466 | 8 | -3 / 6 | 816.3 / 781.7 |
| sl_W5_hc3__cws3__3 | sl_W5_su_l0 -> c_W5_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |
| sl_W4_hc3__cws3__3 | sl_W4_su_l0 -> c_W4_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |
| sl_W3_hc3__cws3__3 | sl_W3_su_l0 -> c_W3_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |
| sl_W2_hc3__cws3__3 | sl_W2_su_l0 -> c_W2_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |
| sl_W1_hc3__cws3__3 | sl_W1_su_l0 -> c_W1_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |
| sl_E0_hc3__cws3__3 | sl_E0_su_l0 -> c_E0_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |
| sl_E1_hc3__cws3__3 | sl_E1_su_l0 -> c_E1_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |
| sl_E2_hc3__cws3__3 | sl_E2_su_l0 -> c_E2_bn_10 | 516 | OFF | nontree (amb 2) | 1293..5398 | 8 | -3 / 6 | 876.3 / 849.5 |

Per-crossing K/DEPTH/latency/margins: qc_v3_crossings.tsv (all 2558).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
