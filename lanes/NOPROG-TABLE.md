# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 04:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'YOUNG': 47, 'NO-DATA': 2, 'PROGRESS': 16}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 10.6 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 10.3 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | ctb_ph_slw_sc_v3_new_4086867 | ctb_ph_slw_sc_v3_new_4086867 | hold_new | 0.1 | last meaningful line 0.0 h ago (566/566 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-3703000-1555 | 3703000 | cex | 0.4 | last meaningful line -0.0 h ago (601161/601161 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-4085056-26666 | 4085056 | eq2 | 0.2 | last meaningful line -0.0 h ago (630982/630982 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-4085482-21038 | 4085482 | cex | 0.2 | last meaningful line -0.0 h ago (602364/602364 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | tt_setup_repair_grt | 0.1 | repair_Viol best 17 last 17 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-serdes__t12-3207547 | serdes__t12 | pregrt_ff_hold | 0.6 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | eco-abs-3459830 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | eco-abs-3806152 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (279/281 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-glue-2294683 | glue | 5_1_grt | 5.5 | last meaningful line 0.1 h ago (988/994 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | postcts_gate_FF | 5.7 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | postcts_gate_FF | 5.1 | last meaningful line 0.0 h ago (977/977 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-3573304 | sle_sc_v3 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-1581596 | sle_st_a_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1570738 | sle_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.3657 last 0.3806 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1728588 | sle_st_a_v1 | 2_1_floorplan | 0.1 | repair_Viol best 2328 last 2328 rows 1042 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-1471188 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.1997 last 0.1997 rows 43 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1467684 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.2393 last 0.2393 rows 42 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-1492153 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.3008 last 0.3008 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | postcts_gate_FF | 5.2 | last meaningful line 0.0 h ago (1691/1691 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | pregrt_ff_hold | 1.1 | repair_TNS best 8353.2 last 8353.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_2_route | 5.7 | drt_violations best 90161 last 90161 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (168/168 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 5.3 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clb036e152-1590097 | slw_st_a_v1 | 3_3_place_gp | 0.2 | last meaningful line -0.0 h ago (196/196 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1591840 | slw_st_a_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1593287 | slw_st_a_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-1734717 | slw_st_a_v2 | 2_1_floorplan | 0.1 | repair_Viol best 2348 last 2348 rows 1184 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-1707882 | slw_st_a_v2 | 2_3_floorplan_tapcell | 0.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | postcts_gate_FF | 5.5 | last meaningful line 0.0 h ago (1368/1368 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-813892 | slw_stm_v2 | 3_3_place_gp | 0.6 | overflow best 0.155 last 0.155 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2-4134013 | eco_20261123_171023_3055226-i2 | 5_1_grt | 1.2 | last meaningful line 0.8 h ago (236/1366 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 10.2 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (173/173 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 3.9 | drt_violations best 11 last 50 rows 29 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_2_route | 3.0 | drt_violations best 112 last 112 rows 6 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5450/5450 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-3094879-23879 | 3094879 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | phscan-3127676 | phscan | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (5450/5450 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3t-46390 | eco_20261123_190031_3093983-i3t | 5_2_route | 2.5 | drt_violations best 174 last 174 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2-702588 | eco_20261123_224216_149959-i2 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2-2527977 | eco_20261123_224647_4153453-i2 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (237/1303 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2t-283529 | eco_20261124_010152_2867084-i2t | 5_2_route | 2.4 | drt_violations best 3161 last 3161 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 4.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_2_route | 3.9 | drt_violations best 20 last 20 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-933055 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10185 last 10185 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3148810 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 3.9 | drt_violations best 20278 last 20278 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 31.8 | drt_violations best 779 last 1754 rows 35 | before-window best 1392, window best 779 | PROGRESS: drt_violations improved 44.0 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 10.5 | last meaningful line 2.5 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-serdes__t2-3395720 | serdes__t2 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 27.1 | drt_violations best 19595 last 19595 rows 12 | before-window best 39904, window best 19595 | PROGRESS: drt_violations improved 50.9 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 20.4 | drt_violations best 32431 last 32431 rows 11 | before-window best 49025, window best 32431 | PROGRESS: drt_violations improved 33.8 % in window |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 34.4 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 34.6 | drt_violations best 74496 last 74496 rows 15 | before-window best 78971, window best 74496 | PROGRESS: drt_violations improved 5.7 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 12.7 | last meaningful line 1.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 16.4 | last meaningful line 1.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 3.4 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-kv3_io_ft-4110971 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
