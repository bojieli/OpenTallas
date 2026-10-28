# 12.14b ESTIMATE v3: qc, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/wt/qc-smallreg-1027/physical/die_plan/qwen_compute/die_plan_sliceclk.json (sha256 5545cbfca017), 377 partitions, 3005 ports; clock wire v = 334 ps/mm TT (334 ps/mm routed; count_align_plan @32e8cbb16; spice x1.0485 TT / x1.0552 FF); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map row, feed fish

* 221 regions, max span 2.68 mm, bit-mm inside 14.0 %, 2414 crossings (990900 bits), 1 connected component(s), start-tree edges clean 194/220, max path ambiguity 1 cycles.
* **DEPTH4 2409, DEPTH8 5 (1197 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 111.0 ps / high 190.0 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 274, '3': 2057, '4': 83}; max 4; bit-weighted mean 2.40.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'1': 581, '2': 770, '3': 851, '4': 147, '5': 65}; bit-weighted: {'1': 301222, '2': 337197, '3': 269359, '4': 54555, '5': 28567}.
* Render:  (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| row | fish | 221 | 2.68 | 14.0 % | 2414 | 2409 | 5 | 0 | 111.0 / 190.0 | 4 | {'2': 274, '3': 2057, '4': 83} | -1455 / -1177 |
| v1_s0.1 | fish | 377 | 2.62 | 0.0 % | 3005 | 2841 | 164 | 0 | 111.0 / 257.9 | 6 | {'2': 1010, '3': 1821, '4': 81, '5': 70, '6': 23} | -6994 / -5899 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| coll_s__serdes_tx_tx_flit_2__0 | coll_s -> crow_W5_bf_0 | 597 | OFF | nontree (amb 1) | 1343..3514 | 8 | 2 / 4 | 926.7 / 2733.2 |
| coll_s__serdes_tx_valid_tx_v_2__0 | coll_s -> crow_W5_bf_0 | 1 | OFF | nontree (amb 1) | 1343..3514 | 8 | 2 / 4 | 926.7 / 2733.2 |
| io_serdes_2__rx_flit_serdes_rx__2 | crow_W5_bf_0 -> coll_s | 597 | OFF | nontree (amb 1) | 651..2822 | 8 | 5 / 4 | 234.2 / 3425.7 |
| io_serdes_2__rx_v_serdes_rx_valid__2 | crow_W5_bf_0 -> coll_s | 1 | OFF | nontree (amb 1) | 651..2822 | 8 | 5 / 4 | 234.2 / 3425.7 |
| io_serdes_2__tx_up_serdes_up__2 | crow_W5_bf_0 -> coll_s | 1 | OFF | nontree (amb 1) | 651..2822 | 8 | 5 / 4 | 234.2 / 3425.7 |
| sl_W0_hc3__cwn3__0 | sl_W0_st_b -> crow_W0_tn_0 | 516 | OFF | nontree (amb 1) | 1081..2726 | 4 | 1 / 3 | 664.8 / 190.0 |
| sl_E0_hc3__cwn3__0 | sl_E0_st_b -> crow_E0_tn_0 | 516 | OFF | nontree (amb 1) | 1081..2726 | 4 | 1 / 3 | 664.8 / 190.0 |
| sl_E1_hc3__cwn3__0 | sl_E1_st_b -> crow_E1_tn_0 | 516 | OFF | nontree (amb 1) | 1081..2726 | 4 | 1 / 3 | 664.8 / 190.0 |
| sl_E2_hc3__cwn3__0 | sl_E2_st_b -> crow_E2_tn_0 | 516 | OFF | nontree (amb 1) | 1081..2726 | 4 | 1 / 3 | 664.8 / 190.0 |
| sl_E3_hc3__cwn3__0 | sl_E3_st_b -> crow_E3_tn_0 | 516 | OFF | nontree (amb 1) | 1081..2726 | 4 | 1 / 3 | 664.8 / 190.0 |
| sl_E4_hc3__cwn3__0 | sl_E4_st_b -> crow_E4_tn_0 | 516 | OFF | nontree (amb 1) | 1081..2726 | 4 | 1 / 3 | 664.8 / 190.0 |
| sl_E5_hc3__cwn3__0 | sl_E5_st_b -> crow_E5_tn_0 | 516 | OFF | nontree (amb 1) | 1081..2726 | 4 | 1 / 3 | 664.8 / 190.0 |
| sl_W5_hc2__cwn2__0 | sl_W5_hc2 -> crow_W5_tn_0 | 516 | OFF | nontree (amb 1) | 1085..2675 | 4 | 2 / 4 | 668.5 / 240.5 |
| sl_W4_hc2__cwn2__0 | sl_W4_hc2 -> crow_W4_tn_0 | 516 | OFF | nontree (amb 1) | 1085..2675 | 4 | 2 / 4 | 668.5 / 240.5 |
| sl_W3_hc2__cwn2__0 | sl_W3_hc2 -> crow_W3_tn_0 | 516 | OFF | nontree (amb 1) | 1085..2675 | 4 | 2 / 4 | 668.5 / 240.5 |

Per-crossing K/DEPTH/latency/margins: qc_v3_crossings.tsv (all 2414).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
