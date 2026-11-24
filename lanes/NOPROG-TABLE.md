# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 03:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'GRT-LABEL': 1, 'YOUNG': 34, 'NO-DATA': 4, 'PROGRESS': 16}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 9.6 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 9.3 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-3935497-15976 | 3935497 | 5_1_grt | 0.7 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-serdes__t12-2097905 | serdes__t12 | 3_3_place_gp | 0.6 | overflow best 0.4687 last 0.4687 rows 87 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-serdes__t2-2141379 | serdes__t2 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.3351 last 0.3351 rows 40 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2-336844 | eco_20261123_102841_2122262-i2 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_2_route | 3.4 | drt_violations best 130 last 130 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-217815 | hd_lep0N_w | rtl_lint | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | postcts_gate_TT | 4.1 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5771/5771 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-3573304 | sle_sc_v3 | tt_setup_repair | 0.6 | repair_Viol best 48 last 48 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | tt_setup_repair_grt | 4.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4453/4453 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | pregrt_ff_hold | 0.7 | repair_TNS best 10772.3 last 10772.3 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | postcts_gate_TT | 4.3 | last meaningful line 0.0 h ago (2065/2065 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4273/4273 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | tt_setup_repair_grt | 4.5 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4756/4756 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2-4134013 | eco_20261123_171023_3055226-i2 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 9.2 | repair_Viol best 709 last 709 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | postcts_gate_FF | 6.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | postcts_gate_FF | 7.8 | last meaningful line -0.0 h ago (68204/68204 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-1286351 | slw_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1359921-17304 | 1359921 | postcts_gate_FF | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 2.9 | drt_violations best 16 last 16 rows 14 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_2_route | 2.0 | drt_violations best 41919 last 41919 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-1900737-27685 | 1900737 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1985823-6991 | 1985823 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-1998099-14929 | 1998099 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-2658135 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3t-46390 | eco_20261123_190031_3093983-i3t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2-702588 | eco_20261123_224216_149959-i2 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2t-283529 | eco_20261124_010152_2867084-i2t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 3.0 |  | NO-DATA: no log found |  |
| intel1 | otc-3913441-3537 | 3913441 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3821/3821 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-933055 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-931660 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 2.9 | drt_violations best 20278 last 20278 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 30.8 | drt_violations best 783 last 783 rows 32 | before-window best 2455, window best 783 | PROGRESS: drt_violations improved 68.1 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 9.5 | last meaningful line 1.5 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 4.1 | repair_Violations best 63712 last 63719 rows 96 | before-window best 399712, window best 63712 | PROGRESS: repair_Violations improved 84.1 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 26.1 | drt_violations best 22423 last 22423 rows 11 | before-window best 49689, window best 22423 | PROGRESS: drt_violations improved 54.9 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 19.4 | drt_violations best 39072 last 39072 rows 10 | before-window best 95242, window best 39072 | PROGRESS: drt_violations improved 59.0 % in window |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3401719 | sle_su_l1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 33.4 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-16187-7415 | 16187 | 4_1_cts | 1.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 33.6 | drt_violations best 76746 last 76746 rows 14 | before-window best 78971, window best 76746 | PROGRESS: drt_violations improved 2.8 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 11.7 | last meaningful line 0.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 15.4 | last meaningful line 0.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 2.4 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
