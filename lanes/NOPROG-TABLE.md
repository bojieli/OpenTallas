# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 04:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'GRT-LABEL': 1, 'YOUNG': 37, 'NO-DATA': 3, 'PROGRESS': 18}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 10.4 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 10.1 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3401719 | sle_su_l1 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:6262 -> 10:2003 | GRT-LABEL: DESIGN-FAIL: overflow 2003 at round 10 > 1000 |  |
| epyc10 | ctb_rg_dsfd_node_LLd_FF_3918171 | ctb_rg_dsfd_node_LLd_FF_3918171 | regen_FF | 0.0 | last meaningful line -0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ctb_rg_qfd_qc_su_lane_w_l2_TT_3918179 | ctb_rg_qfd_qc_su_lane_w_l2_TT_3918179 | regen_TT | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ctb_rg_qfd_qc_su_lane_w_l3_TT_3918181 | ctb_rg_qfd_qc_su_lane_w_l3_TT_3918181 | regen_TT | 0.0 | last meaningful line -0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ctb_rg_qfd_qc_su_lane_w_l6_TT_3918183 | ctb_rg_qfd_qc_su_lane_w_l6_TT_3918183 | regen_TT | 0.0 | last meaningful line -0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ctb_rg_qfd_qc_su_lane_w_l7_TT_3918185 | ctb_rg_qfd_qc_su_lane_w_l7_TT_3918185 | regen_TT | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ctb_rg_qfd_tile_nl_a0c_TT_3918186 | ctb_rg_qfd_tile_nl_a0c_TT_3918186 | regen_TT | 0.0 | last meaningful line -0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ctb_rg_sta_region_nb0_h15_n_TT_3918189 | ctb_rg_sta_region_nb0_h15_n_TT_3918189 | regen_FF | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | ctb_rg_sta_region_nb0_h17_n_TT_3918191 | ctb_rg_sta_region_nb0_h17_n_TT_3918191 | regen_TT | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3703000-1555 | 3703000 | eq2 | 0.2 | last meaningful line 0.0 h ago (630037/630037 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | eco-abs-3459830 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-fin-336844 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1070/1070 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (146/146 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-glue-2294683 | glue | 5_1_grt | 5.3 | last meaningful line 0.2 h ago (280/895 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3209/3209 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | tt_setup_repair_grt | 5.5 | last meaningful line 0.0 h ago (602/602 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | postcts_gate_TT | 4.9 | last meaningful line -0.0 h ago (21543/21543 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | postcts_gate_TT | 5.0 | last meaningful line -0.0 h ago (85675/85675 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (4941/4941 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_2_route | 5.4 | drt_violations best 90161 last 90161 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 5.1 | last meaningful line 0.0 h ago (42/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | postcts_gate_TT | 5.3 | last meaningful line -0.0 h ago (82567/82567 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | pregrt_ff_hold | 1.2 | repair_TNS best 22933.3 last 22933.3 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-813892 | slw_stm_v2 | 3_3_place_gp | 0.3 | overflow best 0.5148 last 0.5148 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2-4134013 | eco_20261123_171023_3055226-i2 | 5_1_grt | 1.0 | last meaningful line 0.6 h ago (236/1306 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 10.0 | repair_Violations best 5 last 8 rows 64 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 3.7 | drt_violations best 11 last 55 rows 28 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_2_route | 2.7 | drt_violations best 41919 last 41919 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | otc-2531283-11455 | 2531283 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-2619226-24789 | 2619226 | eq_out | 0.2 | last meaningful line -0.0 h ago (384885/384885 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3t-46390 | eco_20261123_190031_3093983-i3t | 5_2_route | 2.3 | drt_violations best 174 last 174 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2-702588 | eco_20261123_224216_149959-i2 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2-2527977 | eco_20261123_224647_4153453-i2 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (174/174 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2t-283529 | eco_20261124_010152_2867084-i2t | 5_2_route | 2.1 | drt_violations best 3161 last 3161 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_2_route | 3.6 | drt_violations best 20 last 20 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-933055 | coll_ftm | 5_2_route | 1.7 | drt_violations best 10185 last 10185 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-4110913 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3148810 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 3.7 | drt_violations best 20278 last 20278 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 31.6 | drt_violations best 779 last 3069 rows 34 | before-window best 1939, window best 779 | PROGRESS: drt_violations improved 59.8 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 10.2 | last meaningful line 2.3 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-serdes__t12-3207547 | serdes__t12 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-serdes__t2-3395720 | serdes__t2 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 26.8 | drt_violations best 22423 last 22423 rows 11 | before-window best 39904, window best 22423 | PROGRESS: drt_violations improved 43.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 20.1 | drt_violations best 32431 last 32431 rows 11 | before-window best 55825, window best 32431 | PROGRESS: drt_violations improved 41.9 % in window |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v3-3573304 | sle_sc_v3 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 34.2 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 34.4 | drt_violations best 76746 last 76746 rows 14 | before-window best 78971, window best 76746 | PROGRESS: drt_violations improved 2.8 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 12.4 | last meaningful line 1.6 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 16.2 | last meaningful line 1.6 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 3.2 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-kv3_io_ft-4110971 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
