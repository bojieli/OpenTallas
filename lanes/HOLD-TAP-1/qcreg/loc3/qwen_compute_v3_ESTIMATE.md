# 12.14b ESTIMATE v3: qwen_compute, adopted count-aligned ring (LOCALITY-SCORE-3, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch3/claude/wt/qc-clkgate-1/physical/die_plan/qwen_compute/plan_of_record/zz_gates_ev2st.json (sha256 736058c458ee), 377 partitions, 2993 ports; clock wire v = 290 ps/mm TT (H-tree trunk of the s28 gate run, 8W NDR M8/M9); T = 833 ps.
Crossing form = MESO-COUNT-1 count-aligned ring (ot_dp_clk_landing_ca, COORD 20:35 adopted): reads by count; K and DEPTH (4 or 8) fixed per crossing at design time, jointly for TT+FF (no per-chip training); window (DEPTH-1)T; derated lag L inside [(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8, >= 100 ps both sides.  Math = tools/die_plan/count_align_plan.py unchanged (Kruskal start tree on clean edges, path ambiguity on loop crossings), fed with this tool's modelled d / p_up / p_dn (shared derate: clk_aocv g021 + droop regions + core latency class B).  Latency = logical crossing latency in cycles (K + 1 + nominal origin difference).

## Best (no hop chains): map tree_s3.5c5, feed fish

* 125 regions, max span 4.79 mm, bit-mm inside 40.8 %, 1288 crossings (566831 bits), 1 connected component(s), start-tree edges clean 112/124, max path ambiguity 1 cycles.
* **DEPTH4 1288, DEPTH8 0 (0 bits), FAIL even at DEPTH8 0 (0 bits)**; worst margin low 109.4 ps / high 263.5 ps (passing crossings; gate >= 100).
* **Physical latency per crossing** (write -> read incl. RDREG, ceil(L/T + 1) = ceil(lat + d/T); skew-free, sums around any closed dataflow loop = the loop's cost -> use for TOK pricing; cycles: crossings): {'2': 509, '3': 660, '4': 119}; max 4; bit-weighted mean 2.21.
* Schedule constant per crossing (logical latency in the die-wide count, K + 1 + origin difference; carries the clock-arrival offset d/T, so it can be < 1 or negative; cycles: crossings): {'1': 615, '2': 95, '3': 405, '4': 56, '5': 117}; bit-weighted: {'1': 326326, '2': 47943, '3': 140262, '4': 23085, '5': 29215}.
* Render:  (VIEWED).

Hop chains: none needed (0 crossings fail at DEPTH 8).

## All maps x feeds (adopted CA ring, no hop chains), best first

Ranking: 12.13 first (feed 'top' = die-wide release clock, listed for reference only; max region span <= 5.0 mm = max(5 mm, largest partition side), else '*' after the span), then FAIL@D8, max physical latency, physical bit-cycles, D8 count.

| map | feed | regions | max span mm | bit-mm in | crossings | D4 | D8 | FAIL@D8 | worst lo / hi ps | max phys lat | phys latency hist | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree_s3.5c5 | fish | 125 | 4.79 | 40.8 % | 1288 | 1288 | 0 | 0 | 109.4 / 263.5 | 4 | {'2': 509, '3': 660, '4': 119} | -1000 / -789 |
| v1_s3.5 | fish | 131 | 3.28 | 39.8 % | 1349 | 1349 | 0 | 0 | 109.4 / 138.7 | 4 | {'2': 528, '3': 701, '4': 120} | -2205 / -1816 |
| v1_s3.5 | spine | 131 | 3.28 | 39.8 % | 1349 | 1345 | 4 | 0 | 124.9 / 328.1 | 4 | {'2': 39, '3': 1185, '4': 125} | -2238 / -1843 |
| tree_s3.5c5 | spine | 125 | 4.79 | 40.8 % | 1288 | 1282 | 6 | 0 | 124.9 / 229.6 | 5 | {'2': 24, '3': 1130, '4': 130, '5': 4} | -1213 / -969 |
| v1_s3.5 | fwd | 131 | 3.28 | 39.8 % | 1349 | 1341 | 8 | 0 | 109.4 / 350.9 | 5 | {'2': 78, '3': 1026, '4': 243, '5': 2} | -2631 / -2179 |
| tree_s2c3.5 | fish | 248 | 3.23 | 25.9 % | 1675 | 1669 | 6 | 0 | 107.6 / 140.3 | 5 | {'2': 581, '3': 959, '4': 133, '5': 2} | -5563 / -4680 |
| tree_s2c3.5 | fwd | 248 | 3.23 | 25.9 % | 1675 | 1667 | 8 | 0 | 106.8 / 106.8 | 5 | {'2': 253, '3': 1351, '4': 67, '5': 4} | -7228 / -6100 |
| tree_s3.5c5 | dme | 125 | 4.79 | 40.8 % | 1288 | 630 | 658 | 0 | 110.7 / 241.3 | 5 | {'2': 209, '3': 633, '4': 337, '5': 109} | -380 / -254 |
| v1_s3.5 | dme | 131 | 3.28 | 39.8 % | 1349 | 637 | 712 | 0 | 106.9 / 251.8 | 5 | {'2': 212, '3': 633, '4': 363, '5': 141} | -367 / -243 |
| tree_s2c3.5 | spine | 248 | 3.23 | 25.9 % | 1675 | 1665 | 10 | 0 | 104.7 / 164.2 | 5 | {'2': 80, '3': 1403, '4': 188, '5': 4} | -5570 / -4686 |
| plain | fish | 313 | 3.13 | 8.7 % | 2525 | 2433 | 92 | 0 | 119.0 / 125.6 | 5 | {'2': 574, '3': 1802, '4': 82, '5': 67} | -5843 / -4918 |
| plain | spine | 313 | 3.13 | 8.7 % | 2525 | 2410 | 115 | 0 | 116.9 / 219.9 | 5 | {'2': 276, '3': 2069, '4': 113, '5': 67} | -5850 / -4925 |
| plain | fwd | 313 | 3.13 | 8.7 % | 2525 | 2372 | 153 | 0 | 107.1 / 112.4 | 5 | {'2': 413, '3': 1909, '4': 158, '5': 45} | -7673 / -6480 |
| tree_s3.5c5 | fwd | 125 | 4.79 | 40.8 % | 1288 | 1283 | 5 | 0 | 117.3 / 306.9 | 6 | {'2': 64, '3': 957, '4': 264, '6': 3} | -1280 / -1028 |
| tree_s2c3.5 | dme | 248 | 3.23 | 25.9 % | 1675 | 926 | 737 | 12 | 106.1 / 210.9 | 5 | {'2': 337, '3': 785, '4': 345, '5': 196} | -516 / -359 |
| plain | dme | 313 | 3.13 | 8.7 % | 2525 | 670 | 1678 | 177 | 116.3 / 254.3 | 6 | {'2': 298, '3': 718, '4': 885, '5': 439, '6': 8} | -371 / -246 |
| tree_s3.5c5 | top | 125 | 4.79 | 40.8 % | 1288 | 977 | 311 | 0 | 137.1 / 755.0 | 4 | {'2': 290, '3': 820, '4': 178} | -214 / -113 |
| v1_s3.5 | top | 131 | 3.28 | 39.8 % | 1349 | 1035 | 314 | 0 | 147.1 / 761.8 | 4 | {'2': 319, '3': 857, '4': 173} | -217 / -115 |
| tree_s2c3.5 | top | 248 | 3.23 | 25.9 % | 1675 | 1268 | 407 | 0 | 141.3 / 757.5 | 4 | {'2': 644, '3': 807, '4': 224} | -226 / -122 |
| plain | top | 313 | 3.13 | 8.7 % | 2525 | 2076 | 449 | 0 | 107.5 / 773.7 | 4 | {'2': 1675, '3': 565, '4': 285} | -207 / -107 |

## Worst crossings of the best form (FAIL first, then highest L_hi)

| crossing | src -> dst region | bits | on feed | kind | L lo..hi ps | DEPTH | lat (sched / phys) | margin lo / hi |
|---|---|---|---|---|---|---|---|---|
| coll_s__serdes_tx_tx_flit_2__0 | T012 -> T013 | 597 | OFF | nontree (amb 1) | 821..2652 | 4 | 4 / 4 | 404.1 / 263.5 |
| coll_s__serdes_tx_valid_tx_v_2__0 | T012 -> T013 | 1 | OFF | nontree (amb 1) | 821..2652 | 4 | 4 / 4 | 404.1 / 263.5 |
| io_serdes_2__rx_flit_serdes_rx__2 | T013 -> T012 | 597 | OFF | nontree (amb 1) | 680..2511 | 4 | 2 / 3 | 263.5 / 404.1 |
| io_serdes_2__rx_v_serdes_rx_valid__2 | T013 -> T012 | 1 | OFF | nontree (amb 1) | 680..2511 | 4 | 2 / 3 | 263.5 / 404.1 |
| io_serdes_2__tx_up_serdes_up__2 | T013 -> T012 | 1 | OFF | nontree (amb 1) | 680..2511 | 4 | 2 / 3 | 263.5 / 404.1 |
| sl_E0_fw__ag_eo_ag_ei__0 | T070 -> T069 | 10 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__ard_eo_ard_ei__0 | T070 -> T069 | 512 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__arl_eo_arl_ei__0 | T070 -> T069 | 1 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__arm_eo_arm_ei__0 | T070 -> T069 | 1 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__art_eo_art_ei__0 | T070 -> T069 | 32 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__arv_eo_arv_ei__0 | T070 -> T069 | 1 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__dd_eo_dd_ei__0 | T070 -> T069 | 548 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__sc_eo_sc_ei__0 | T070 -> T069 | 48 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E0_fw__st_eo_st_ei__0 | T070 -> T069 | 1087 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |
| sl_E1_fw__ag_eo_ag_wi__0 | T071 -> T070 | 10 | on | nontree (amb 1) | 1246..2493 | 4 | 5 / 4 | 829.7 / 422.2 |

Per-crossing K/DEPTH/latency/margins: qwen_compute_v3_crossings.tsv (all 1288).

Verdict rule (12.14b): build only a form whose every crossing fits (DEPTH 4/8, >= 100 ps both sides); estimate only (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored here: intra-region related pairs (large regions) -> die STA.
