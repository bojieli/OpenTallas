# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 12:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 1, 'GRT-LABEL': 11, 'YOUNG': 128, 'NO-DATA': 3, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 31}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 15.5 | drt_violations best 110699 last 110699 rows 1 | before-window best 110699, window best 110699 | NO-PROGRESS: drt_violations best 110699 vs 110699 before window: < 2 % in 6 h | CANCELLED |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 15.5 | drt_violations best 102627 last 102627 rows 1 | before-window best 102627, window best 102627 | NO-PROGRESS: drt_violations best 102627 vs 102627 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (308/308 lines) | UNSIGNABLE: 5_1_grt.log latest setup WNS -440.37 ps (< -300, gate TT >= -42); job age 4.4 h  | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 9.0 | last meaningful line 6.6 h ago (249/322 lines) | NO-PROGRESS: no new non-iteration log line for 6.6 h | CANCELLED |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 17.8 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 3.9 | grt rounds 6 overflow 5:1998 -> 10:1858 -> 15:1870 -> 20:1699 -> 25:1717 -> 30:1567 | GRT-LABEL: DESIGN-FAIL: overflow 1858 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 3.8 | grt rounds 2 overflow 5:48999 -> 10:45315 | GRT-LABEL: DESIGN-FAIL: overflow 45315 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | 5_1_grt | 3.8 | grt rounds 6 overflow 5:2979 -> 10:1494 -> 15:71 -> 20:9 -> 25:9 -> 30:11 | GRT-LABEL: DESIGN-FAIL: overflow 1494 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:30456 -> 10:19532 | GRT-LABEL: DESIGN-FAIL: overflow 19532 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 14.3 | grt rounds 3 overflow 5:27316 -> 10:11412 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:50814 -> 10:51002 | GRT-LABEL: DESIGN-FAIL: overflow 51002 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 23.4 | grt rounds 3 overflow 5:48547 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 15.3 | grt rounds 3 overflow 5:46995 -> 10:41355 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 15.3 | grt rounds 2 overflow 5:58470 -> 10:41949 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 10.1 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:10179 -> 20:10000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.1889 last 0.1889 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-1485860 | cbx_q10 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (296/296 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | tt_setup_repair | 0.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 3.0 | last meaningful line 0.8 h ago (199/212 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 14646 last 14646 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 14646 last 14646 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | tt_setup_repair_grt | 3.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.7 | overflow best 0.3756 last 0.3862 rows 12 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-328394 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.7 | overflow best 0.3453 last 0.3526 rows 12 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3860/3860 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3613602 | dsdv_slice_lepw_mu_LP__t2 | 3_3_place_gp | 0.9 | overflow best 0.7038 last 0.7038 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3423/3423 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 1.3 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3402/3402 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-3229485 | ot_s81sl_leaf__t36 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t37-324991 | ot_s81sl_leaf__t37 | 3_3_place_gp | 0.7 | overflow best 0.2128 last 0.2128 rows 42 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-319778 | ot_s81sl_leaf__t5 | 3_3_place_gp | 0.7 | overflow best 0.4854 last 0.4854 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-serdes__t3-2131131 | serdes__t3 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl372cea1c-3342696 | sle_ctl | 3_3_place_gp | 0.9 | overflow best 0.4159 last 0.4159 rows 22 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff-3983509 | sle_ctl | 3_1_place_gp_skip_io | 0.8 | overflow best 0.6981 last 0.7114 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff__padE4-3232565 | sle_ctl | 3_3_place_gp | 1.0 | overflow best 0.1951 last 0.1951 rows 52 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795-3620476 | sle_ctl | 3_1_place_gp_skip_io | 0.9 | overflow best 0.3233 last 0.3233 rows 30 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795__padW5-1501671 | sle_ctl | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (1426/1426 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-4132289 | sle_fw_v1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3347897 | sle_fw_v1 | 3_3_place_gp | 0.9 | last meaningful line -0.0 h ago (274/274 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-3213795 | sle_fw_v2 | 3_4_place_resized | 1.0 | repair_Remaining best 223962 last 223962 rows 69 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-127322 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.138 last 0.138 rows 51 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v2-127583 | sle_sc_v2 | 3_3_place_gp | 0.7 | overflow best 0.2164 last 0.2646 rows 40 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-324034 | sle_st_b_v2 | 3_3_place_gp | 0.7 | overflow best 0.7634 last 0.7634 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1500025 | sle_st_b_v2 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__cl27746664-3856466 | sle_stm_v1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.1751 last 0.1751 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3217716 | sle_stm_v1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3864447 | sle_stm_v2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-3911511 | slice_station__t29 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (218/218 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t40__clc8fb2c8c-3205661 | slice_station__t40 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-315959 | slw_fe_v1 | 3_3_place_gp | 0.7 | overflow best 0.35 last 0.35 rows 25 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3636235 | slw_fe_v1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-1782333 | slw_fe_v2 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (299/299 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-3338635 | slw_fw_v1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-708438 | slw_fw_v1 | 3_3_place_gp | 0.6 | overflow best 0.4175 last 0.4175 rows 18 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4163727 | slw_fw_v2 | 3_3_place_gp | 0.8 | overflow best 0.2604 last 0.2604 rows 33 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-331949 | slw_hc1 | 3_3_place_gp | 0.7 | overflow best 0.6682 last 0.6682 rows 29 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v2-4155454 | slw_sc_v2 | 3_3_place_gp | 0.8 | last meaningful line -0.0 h ago (258/258 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1506133 | slw_st_b_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-3230820 | slw_st_b_v1 | 3_3_place_gp | 1.0 | overflow best 0.2043 last 0.2043 rows 39 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-131605 | slw_st_b_v2 | 3_3_place_gp | 0.7 | overflow best 0.7005 last 0.7005 rows 21 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3566124 | slw_stm_v2 | 3_3_place_gp | 0.9 | overflow best 0.2222 last 0.2222 rows 29 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (448/448 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (227/227 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-1514045-1137 | 1514045 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-1514205-3474 | 1514205 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-367632-348 | 367632 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-369074-32307 | 369074 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-4183100-28822 | 4183100 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 2.4 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 2.0 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (232/256 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 9.0 | drt_violations best 26911 last 26911 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v2--cle0015330-grt-2588261 | kv3-hgi-v2--cle0015330-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (84/84 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (381/381 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (918/918 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 12.8 | drt_violations best 150968 last 150968 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (201/201 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-379194 | hd_serdes | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4762/4762 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-1983684 | kv3_hgi_v2 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | 3_3_place_gp | 1.0 | overflow best 0.6774 last 0.6774 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v1-3573937 | kv3_pv_v1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | 3_3_place_gp | 2.2 | overflow best 0.224 last 0.224 rows 32 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | 3_3_place_gp | 2.2 | overflow best 0.1968 last 0.1968 rows 33 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | 3_3_place_gp | 2.2 | overflow best 0.2343 last 0.2343 rows 29 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | 3_1_place_gp_skip_io | 2.1 | overflow best 0.1026 last 0.1026 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | 3_1_place_gp_skip_io | 2.1 | overflow best 0.2791 last 0.2791 rows 34 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | 3_1_place_gp_skip_io | 2.3 | overflow best 0.2003 last 0.2003 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.9447 last 0.9447 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.9505 last 0.9505 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 3.3 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (531/531 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 3.3 | repair_TNS best 216533 last 216533 rows 23 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t16-3746725 | serdes__t16 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (1140/1140 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (994/1011 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_2_route | 4.0 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | pregrt_ff_hold | 3.2 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 4.0 | last meaningful line 2.4 h ago (213/949 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc7 | phscan-1854121 | phscan | kv3_pc_v3-route-loved-redfish-1034456-1795203695.placed_raw | 4.5 | last meaningful line 0.8 h ago (11/11 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | so_1437304_ff_48902 | so_1437304_ff_48902 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc7 | so_1437304_tt_48902 | so_1437304_tt_48902 | signoff | 0.8 |  | NO-DATA: empty log |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (1641/1641 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (379/379 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 3.8 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 3.9 | last meaningful line 0.5 h ago (248/549 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 3.9 | last meaningful line 2.5 h ago (209/231 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 3.9 | last meaningful line 2.3 h ago (209/232 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1933/1933 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 4.4 | last meaningful line 0.5 h ago (255/256 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | postcts_gate_TT | 3.8 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | stage_odb_cap | 4.3 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | 2_1_floorplan | 0.4 | last meaningful line 0.3 h ago (87/87 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | 3_3_place_gp | 2.3 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-833696 | kv3_sys_c | 3_3_place_gp | 1.2 | overflow best 0.0973 last 0.0973 rows 44 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1706/1706 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-957100 | ot_s81sl_leaf__t33 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1496/1496 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1580/1580 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2007320 | sle_ctl | 3_3_place_gp | 0.6 | overflow best 0.3354 last 0.3354 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 14.6 | last meaningful line 2.0 h ago (217/223 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1604383 | sle_stm_v1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 15.5 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-2060137 | sle_su_c | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 3.8 | last meaningful line 0.4 h ago (259/260 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 15.8 | last meaningful line 0.2 h ago (259/259 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-2982583 | slw_fw_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 16.5 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 16.5 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-2862262 | slw_hc2 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-2927245 | slw_sc_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 16.9 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-429445 | slw_stm_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 1.1 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_091653_2376724-i1-614277 | eco_20261120_091653_2376724-i1 | 5_2_route | 3.2 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | so_915205_ff_21124 | so_915205_ff_21124 | generate_abstract | 1.2 | last meaningful line 1.0 h ago (204/204 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | so_915205_tt_21124 | so_915205_tt_21124 | generate_abstract | 1.2 | last meaningful line 1.0 h ago (204/204 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 2.1 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 25.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 59.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 35.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 36.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 9.7 | last meaningful line 0.2 h ago (1375/1375 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3682/3682 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 25.3 | drt_violations best 20 last 20 rows 51 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 25.3 | drt_violations best 20 last 20 rows 51 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3789/3789 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 25.3 | drt_violations best 20 last 20 rows 51 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3947/3947 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3638/3638 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3739/3739 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3708/3708 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (492/492 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 21.8 | drt_violations best 10168 last 10168 rows 17 | before-window best 11596, window best 10168 | PROGRESS: drt_violations improved 12.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 21.5 | drt_violations best 7619 last 38244 rows 18 | before-window best 8100, window best 7619 | PROGRESS: drt_violations improved 5.9 % in window |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 5_1_grt | 2.6 | repair_TNS best 0 last 0 rows 52 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 7.9 | drt_violations best 76 last 76 rows 9 | before-window best 28098, window best 76 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 22.9 | last meaningful line 0.0 h ago (1367/1367 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | 5_2_route | 18.0 | drt_violations best 35 last 35 rows 38 | before-window best 98, window best 35 | PROGRESS: drt_violations improved 64.3 % in window |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 16.3 | last meaningful line 0.0 h ago (1011/1011 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 9.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 9.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 13.5 | last meaningful line 0.0 h ago (1140/1140 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 16.7 | last meaningful line 0.0 h ago (1068/1068 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 17.1 | last meaningful line 0.0 h ago (1080/1080 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 16.3 | last meaningful line 0.0 h ago (970/970 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 16.0 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
