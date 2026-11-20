# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 13:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 1, 'GRT-LABEL': 9, 'NO-DATA': 5, 'YOUNG': 102, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 13.3 | drt_violations best 150968 last 150968 rows 1 | before-window best 150968, window best 150968 | NO-PROGRESS: drt_violations best 150968 vs 150968 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 4.4 | repair_Viol best 1076 last 1076 rows 115 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -355.65 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 18.3 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 4.3 | grt rounds 2 overflow 5:48999 -> 10:45315 | GRT-LABEL: DESIGN-FAIL: overflow 45315 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:30456 -> 10:19532 | GRT-LABEL: DESIGN-FAIL: overflow 19532 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 14.8 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:50814 -> 10:51002 | GRT-LABEL: DESIGN-FAIL: overflow 51002 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 23.9 | grt rounds 3 overflow 5:48547 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 15.8 | grt rounds 3 overflow 5:43280 -> 10:41355 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 15.8 | grt rounds 3 overflow 5:58470 -> 10:41949 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 10.6 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:10000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | ap-ageom-kw-col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt-684180 | col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t5-grt-387776 | ot-s81sl-leaf--t5-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-sle-fw-v2--cl6740750e-grt-388671 | sle-fw-v2--cl6740750e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-slw-sc-v1--cl64543eaf--cl5e017c6f-grt-385913 | slw-sc-v1--cl64543eaf--cl5e017c6f-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | 5_1_grt | 3.7 | repair_Viol best 505 last 505 rows 7 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 32133.1 last 32133.1 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 3.7 | last meaningful line 1.5 h ago (199/219 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 3.7 | last meaningful line 0.0 h ago (245/245 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 1.2 | repair_Remaining best 99950 last 99950 rows 246 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-3398365 | iqf__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | 3_3_place_gp | 2.5 | overflow best 0.1168 last 0.1168 rows 41 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.1 | last meaningful line 0.0 h ago (214/214 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (242/242 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-3394778 | ot_s81sl_leaf__t57 | 3_3_place_gp | 0.5 | overflow best 0.5637 last 0.5637 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl372cea1c-3342696 | sle_ctl | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795__padW5-1501671 | sle_ctl | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-4132289 | sle_fw_v1 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3347897 | sle_fw_v1 | 3_4_place_resized | 1.7 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-127322 | sle_sc_v1 | 3_4_place_resized | 1.5 | last meaningful line -0.0 h ago (378/378 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl7479a5ec-2924472 | sle_sc_v1 | 3_3_place_gp | 0.7 | overflow best 0.1617 last 0.1889 rows 34 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-4038564 | sle_st_b_v1 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-324034 | sle_st_b_v2 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1500025 | sle_st_b_v2 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__cl27746664-3856466 | sle_stm_v1 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-2891222 | sle_stm_v2 | 3_3_place_gp | 0.7 | overflow best 0.1118 last 0.1118 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | 6_report | 7.7 | last meaningful line -0.0 h ago (780/780 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-3911511 | slice_station__t29 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-315959 | slw_fe_v1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-164358 | slw_fe_v1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4163727 | slw_fw_v2 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (292/292 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4043558 | slw_sc_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (361/361 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v2-4155454 | slw_sc_v2 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1506133 | slw_st_b_v1 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3486824 | slw_stm_v2 | 3_3_place_gp | 0.5 | overflow best 0.4899 last 0.4899 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 2.3 | last meaningful line 0.5 h ago (484/484 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (436/436 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | otc-1514045-1137 | 1514045 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | otc-1514205-3474 | 1514205 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | otc-3492910-9967 | 3492910 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 3.1 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 2.7 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 9.8 | drt_violations best 26911 last 26911 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (655/655 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (1106/1106 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (10446/10446 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-379194 | hd_serdes | pregrt_ff_hold | 1.9 | repair_TNS best 285499 last 285499 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-3573937 | kv3_pv_v1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | 3_3_place_gp | 2.7 | overflow best 0.0996 last 0.0996 rows 43 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | 3_3_place_gp | 2.4 | overflow best 0.2038 last 0.2038 rows 31 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | 3_3_place_gp | 2.6 | overflow best 0.1342 last 0.1342 rows 39 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | 3_3_place_gp | 2.6 | overflow best 0.6271 last 0.6289 rows 10 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (184/184 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 3_3_place_gp | 1.1 | overflow best 0.6406 last 0.6406 rows 13 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 3_3_place_gp | 1.1 | overflow best 0.6362 last 0.6362 rows 14 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 3.8 | last meaningful line 0.2 h ago (15091/15091 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | tt_setup_repair | 1.6 | repair_Viol best 4103 last 4103 rows 249 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 3.8 | repair_TNS best 208046 last 208046 rows 32 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | postcts_gate_TT | 4.5 | last meaningful line 0.0 h ago (369/369 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_2_route | 4.5 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (1369/1369 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 4.5 | last meaningful line 2.9 h ago (213/979 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-3533052 | cbf_q00 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | tt_setup_repair_grt | 4.4 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (1941/1941 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 4.3 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | 5_1_grt | 1.2 | last meaningful line 0.3 h ago (207/210 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 4.4 | last meaningful line 0.1 h ago (432/438 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | 5_1_grt | 4.4 | last meaningful line 0.5 h ago (235/319 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.3 h ago (261/262 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | 5_2_route | 4.3 | last meaningful line 0.0 h ago (242/242 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | 2_1_floorplan | 0.9 | last meaningful line 0.8 h ago (87/87 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (1839/1839 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2006/2006 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | pregrt_ff_hold | 4.3 | repair_Violations best 511 last 511 rows 62 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | pregrt_ff_hold | 4.4 | repair_Violations best 6182 last 6186 rows 94 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t58-371134 | ot_s81sl_leaf__t58 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2007320 | sle_ctl | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 15.1 | last meaningful line 2.5 h ago (217/225 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1604383 | sle_stm_v1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 16.0 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 4.3 | last meaningful line 0.4 h ago (263/264 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-381736 | slice_station__t52 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 16.3 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-2982583 | slw_fw_v1 | 3_3_place_gp | 0.7 | overflow best 0.3681 last 0.3722 rows 15 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 17.0 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 17.0 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-2862262 | slw_hc2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-2927245 | slw_sc_v1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 17.4 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 1.1 | last meaningful line 0.1 h ago (192/194 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-fin-614277 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | 5_2_route | 16.6 | drt_violations best 85180 last 85180 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 26.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 60.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 36.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 37.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 10.5 | last meaningful line 0.9 h ago (1375/1375 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (4122/4122 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 26.1 | drt_violations best 20 last 20 rows 51 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 26.1 | drt_violations best 20 last 20 rows 51 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (4229/4229 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 26.1 | drt_violations best 20 last 20 rows 53 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4387/4387 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (4088/4088 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (4189/4189 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4310/4310 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (3863/3863 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4158/4158 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 22.3 | drt_violations best 10168 last 49296 rows 18 | before-window best 11104, window best 10168 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 22.0 | drt_violations best 7619 last 38244 rows 18 | before-window best 8100, window best 7619 | PROGRESS: drt_violations improved 5.9 % in window |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 5_1_grt | 3.1 | repair_TNS best 0 last 0 rows 61 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 8.4 | drt_violations best 75 last 75 rows 10 | before-window best 28098, window best 75 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 4.4 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 23.4 | last meaningful line 0.0 h ago (1397/1397 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 18.5 | last meaningful line 0.0 h ago (1118/1118 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 16.8 | last meaningful line 0.0 h ago (1041/1041 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 10.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 10.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 14.0 | last meaningful line 0.0 h ago (1170/1170 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 16.6 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 17.2 | last meaningful line 0.0 h ago (1098/1098 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 16.6 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 16.6 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 16.6 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 17.6 | last meaningful line 0.0 h ago (1110/1110 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 16.8 | last meaningful line 0.0 h ago (1000/1000 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 16.6 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 16.5 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
