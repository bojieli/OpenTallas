# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 12:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 8, 'GRT-LABEL': 1, 'YOUNG': 24, 'NO-DATA': 1, 'PROGRESS': 1}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 17.8 | last meaningful line 15.8 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 15.8 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 11.3 | last meaningful line 10.5 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 35.4 | drt_violations best 387 last 387 rows 44 | before-window best 387, window best 387 | NO-PROGRESS: drt_violations best 387 vs 387 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 14.6 | last meaningful line 13.8 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 13.8 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 13.3 | drt_violations best 7 last 62 rows 42 | before-window best 7, window best 7 | NO-PROGRESS: drt_violations best 7 vs 7 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 52.4 | drt_violations best 9 last 9 rows 60 | before-window best 9, window best 9 | NO-PROGRESS: drt_violations best 9 vs 9 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 47.6 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 17.7 | last meaningful line 14.0 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 14.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | dpkit-hd_serdes-1897308 | hd_serdes | 5_1_grt | 0.6 | grt rounds 1 overflow 5:10167 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-hd_host_w-1637183 | hd_host_w | 3_3_place_gp | 0.1 | overflow best 0.6488 last 0.6488 rows 23 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-2048145 | kv3_pc_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.3 h ago (32/32 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r817e6c402-652325 | kv3_pc_v1 | 3_5_place_dp | 2.3 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8b2213035-2044496 | kv3_pc_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.2 h ago (32/32 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-hd_st_n3_transit-1894912 | hd_st_n3_transit | abstract_exact | 1.8 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | eco-abs-2915881 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (31/31 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i2t-2681303 | eco_20261126_033735_1990069-i2t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_str-463564 | hd_st_str | 5_2_route | 1.6 | drt_violations best 9349 last 9349 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2234926 | slw_fe_v1 | 3_3_place_gp | 0.3 | overflow best 0.456 last 0.456 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | lecr2-hc0-1120 | lecr2-hc0 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-677114-26300 | 677114 | drc_merged | 1.5 | last meaningful line 0.0 h ago (542/542 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-fin-3168523 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-bk_sel__t2-2622147 | bk_sel__t2 | 5_1_grt | 3.1 | repair_Remaining best 230158 last 230158 rows 70 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-3465321 | sle_su_l1 | 5_2_route | 2.8 | drt_violations best 82264 last 82264 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t38-739500 | slice_station__t38 | 5_2_route | 3.7 | drt_violations best 43279 last 43279 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i3-1849399 | eco_20261126_124723_1617778-i3 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-hd_st_n3_turn-2203112 | hd_st_n3_turn | abstract_exact | 1.8 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | postcts_gate_TT | 4.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v12e-2085434 | kv3_pv_v12e | 3_3_place_gp | 0.8 | overflow best 0.2383 last 0.2383 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v3-2110462 | kv3_pv_v3 | 3_3_place_gp | 0.8 | overflow best 0.3657 last 0.3657 rows 22 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v3n-1836637 | kv3_pv_v3n | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (379/379 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v3ne-1932656 | kv3_pv_v3ne | 3_3_place_gp | 0.8 | overflow best 0.0987 last 0.0987 rows 44 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v5e-1700011 | kv3_pv_v5e | 3_3_place_gp | 0.9 | overflow best 0.0995 last 0.0995 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v6n-4016509 | kv3_pv_v6n | 3_5_place_dp | 1.3 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7-1467641 | kv3_pv_v7 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (311/311 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 26.0 | drt_violations best 4 last 4 rows 52 | before-window best 5, window best 4 | PROGRESS: drt_violations improved 20.0 % in window |  |
