# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 03:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 1, 'GRT-LABEL': 2, 'YOUNG': 35, 'NO-DATA': 6, 'PROGRESS': 15}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 9.4 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 9.1 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-coll_core-1578986 | coll_core | tt_setup_repair_grt | 5.7 | repair_Remaining best 136226 last 136226 rows 325 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -382.37 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:91995 -> 10:83281 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | otc-3935497-15976 | 3935497 | 5_1_grt | 0.5 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-serdes__t12-2097905 | serdes__t12 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t2-2141379 | serdes__t2 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | pregrt_ff_hold | 2.5 | repair_TNS best 205931 last 205931 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2-336844 | eco_20261123_102841_2122262-i2 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_2_route | 3.2 | drt_violations best 130 last 130 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | tt_setup_repair_grt | 3.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-3573304 | sle_sc_v3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3902/3902 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (1002/1008 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_2_route | 4.4 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4601/4601 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3401719 | sle_su_l1 | tt_setup_repair | 0.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | postcts_gate_TT | 4.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4211/4212 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_1_grt | 4.3 | last meaningful line 0.1 h ago (1014/1029 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4643/4644 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-4052233-27242 | 4052233 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (944/944 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | postcts_gate_FF | 7.6 | last meaningful line 0.0 h ago (1687/1687 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 2.7 | drt_violations best 827 last 827 rows 4 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (297/298 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-fin-662867 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (596/596 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1280055-22679 | 1280055 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-1376256-19607 | 1376256 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (240676/240676 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1386730-3351 | 1386730 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-1548901-2595 | 1548901 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3t-46390 | eco_20261123_190031_3093983-i3t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2-702588 | eco_20261123_224216_149959-i2 | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (237/1370 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_2_route | 2.8 | drt_violations best 559 last 559 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2t-283529 | eco_20261124_010152_2867084-i2t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 2.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3467627-16977 | 3467627 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (3987/3987 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-3620687-32261 | 3620687 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3848/3848 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3657120-29357 | 3657120 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3864/3864 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3913441-3537 | 3913441 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3525/3525 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-933055 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.396 last 17.396 rows 8 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2098551 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-931660 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 2.7 | drt_violations best 20278 last 20278 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | so_2527291_ff_85727 | so_2527291_ff_85727 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_2527291_tt_85727 | so_2527291_tt_85727 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 30.6 | drt_violations best 783 last 783 rows 32 | before-window best 2455, window best 783 | PROGRESS: drt_violations improved 68.1 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 9.2 | last meaningful line 1.3 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 3.8 | repair_Violations best 63832 last 63832 rows 61 | before-window best 399712, window best 63832 | PROGRESS: repair_Violations improved 84.0 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 25.8 | drt_violations best 22423 last 22423 rows 11 | before-window best 49689, window best 22423 | PROGRESS: drt_violations improved 54.9 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 19.1 | drt_violations best 39072 last 39072 rows 10 | before-window best 95242, window best 39072 | PROGRESS: drt_violations improved 59.0 % in window |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 4.5 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 33.2 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-16187-7415 | 16187 | 4_1_cts | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 33.4 | drt_violations best 76746 last 76746 rows 14 | before-window best 78971, window best 76746 | PROGRESS: drt_violations improved 2.8 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 11.4 | last meaningful line 0.6 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 15.2 | last meaningful line 0.6 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 2.2 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
