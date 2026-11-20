# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 12:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 2, 'GRT-LABEL': 11, 'YOUNG': 128, 'NO-DATA': 4, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 15.3 | drt_violations best 110699 last 110699 rows 1 | before-window best 110699, window best 110699 | NO-PROGRESS: drt_violations best 110699 vs 110699 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 15.3 | drt_violations best 102627 last 102627 rows 1 | before-window best 102627, window best 102627 | NO-PROGRESS: drt_violations best 102627 vs 102627 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (293/293 lines) | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -397.37 ps (< -300, gate TT >= -42); job age 4. | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | tt_setup_repair | 3.5 | repair_Violations best 595 last 595 rows 36 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -499.03 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 8.7 | last meaningful line 6.4 h ago (249/322 lines) | NO-PROGRESS: no new non-iteration log line for 6.4 h | REPORTED (cancel next pass) |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 17.6 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 3.7 | grt rounds 6 overflow 5:1998 -> 10:1858 -> 15:1870 -> 20:1699 -> 25:1717 -> 30:1567 | GRT-LABEL: DESIGN-FAIL: overflow 1858 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 3.5 | grt rounds 2 overflow 5:48999 -> 10:45315 | GRT-LABEL: DESIGN-FAIL: overflow 45315 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | 5_1_grt | 3.5 | grt rounds 4 overflow 5:2979 -> 10:1494 -> 15:71 -> 20:9 | GRT-LABEL: DESIGN-FAIL: overflow 1494 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:30456 -> 10:19532 | GRT-LABEL: DESIGN-FAIL: overflow 19532 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 14.0 | grt rounds 3 overflow 5:27316 -> 10:11412 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:50814 -> 10:51002 | GRT-LABEL: DESIGN-FAIL: overflow 51002 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 23.1 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 15.0 | grt rounds 3 overflow 5:46995 -> 10:41355 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 15.0 | grt rounds 2 overflow 5:58470 -> 10:41949 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 9.8 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:10179 -> 20:10000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-1485860 | cbx_q10 | 2_1_floorplan | 0.1 | repair_Viol best 847 last 847 rows 304 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3130/3130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 2.7 | last meaningful line 0.5 h ago (199/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3509/3509 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-328394 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3203 last 0.3203 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3710/3710 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3613602 | dsdv_slice_lepw_mu_LP__t2 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3273/3273 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3558/3558 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 1.1 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-3229485 | ot_s81sl_leaf__t36 | 3_3_place_gp | 0.7 | overflow best 0.4972 last 0.5152 rows 30 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t37-324991 | ot_s81sl_leaf__t37 | 3_3_place_gp | 0.4 | overflow best 0.6401 last 0.6401 rows 2 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-319778 | ot_s81sl_leaf__t5 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t3-2131131 | serdes__t3 | 3_5_place_dp | 1.9 | repair_Violations best 757 last 757 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl372cea1c-3342696 | sle_ctl | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff-3983509 | sle_ctl | 3_1_place_gp_skip_io | 0.6 | overflow best 0.864 last 0.864 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff__padE4-3232565 | sle_ctl | 3_3_place_gp | 0.7 | overflow best 0.3046 last 0.3074 rows 16 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795-3620476 | sle_ctl | 3_1_place_gp_skip_io | 0.6 | overflow best 0.7972 last 0.7972 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795__padW5-1501671 | sle_ctl | 2_1_floorplan | 0.1 | repair_Viol best 2866 last 2866 rows 123 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-4132289 | sle_fw_v1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3347897 | sle_fw_v1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-3213795 | sle_fw_v2 | 3_3_place_gp | 0.7 | overflow best 0.2158 last 0.2158 rows 35 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-127322 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8096 last 0.8096 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v2-127583 | sle_sc_v2 | 3_3_place_gp | 0.5 | overflow best 0.4058 last 0.4058 rows 11 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-324034 | sle_st_b_v2 | 3_1_place_gp_skip_io | 0.4 | last meaningful line -0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1500025 | sle_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (352/352 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__cl27746664-3856466 | sle_stm_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8858 last 0.8858 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3217716 | sle_stm_v1 | 3_3_place_gp | 0.7 | overflow best 0.3489 last 0.3489 rows 25 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3864447 | sle_stm_v2 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-319437 | slice_station__t24 | 3_3_place_gp | 0.4 | overflow best 0.3334 last 0.3484 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-3911511 | slice_station__t29 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t40__clc8fb2c8c-3205661 | slice_station__t40 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-315959 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.5589 last 0.5589 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3636235 | slw_fe_v1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-1782333 | slw_fe_v2 | 3_3_place_gp | 1.1 | overflow best 0.2871 last 0.2871 rows 31 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-3338635 | slw_fw_v1 | 3_3_place_gp | 0.7 | overflow best 0.3956 last 0.3956 rows 22 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-708438 | slw_fw_v1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4163727 | slw_fw_v2 | 3_3_place_gp | 0.5 | overflow best 0.3564 last 0.3564 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3-1780248 | slw_hc0 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-331949 | slw_hc1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (378/378 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v2-4155454 | slw_sc_v2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.6424 last 0.6424 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1506133 | slw_st_b_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-3230820 | slw_st_b_v1 | 3_3_place_gp | 0.7 | overflow best 0.7602 last 0.7602 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-131605 | slw_st_b_v2 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (283/283 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3566124 | slw_stm_v2 | 3_3_place_gp | 0.7 | overflow best 0.4871 last 0.4871 rows 5 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-4136362 | slw_su_l1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 1.3 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-1514045-1137 | 1514045 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-1514205-3474 | 1514205 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-367632-348 | 367632 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-369074-32307 | 369074 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-4183100-28822 | 4183100 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 2.1 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 1.7 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 8.8 | drt_violations best 26911 last 26911 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (833/833 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 12.6 | drt_violations best 150968 last 150968 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 3_4_place_resized | 1.7 | repair_Remaining best 261343 last 261343 rows 84 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-hd_serdes-379194 | hd_serdes | 3_3_place_gp | 1.2 | overflow best 0.2491 last 0.2491 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-1983684 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.6904 last 0.7282 rows 19 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-1708790 | kv3_hgi_v2 | 3_3_place_gp | 0.4 | overflow best 0.3586 last 0.3768 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-3573937 | kv3_pv_v1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | 3_3_place_gp | 1.9 | overflow best 0.6973 last 0.6973 rows 14 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | 3_3_place_gp | 1.9 | overflow best 0.6451 last 0.6451 rows 17 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | 3_3_place_gp | 2.0 | overflow best 0.6324 last 0.6324 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | 3_1_place_gp_skip_io | 1.8 | overflow best 0.7735 last 0.7735 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | 3_1_place_gp_skip_io | 1.9 | overflow best 0.8609 last 0.8609 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v6n-2561884 | kv3_pv_v6n | 3_3_place_gp | 2.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | 3_1_place_gp_skip_io | 2.0 | overflow best 0.8695 last 0.8695 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 2_2_floorplan_macro | 0.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 2_1_floorplan | 0.4 | last meaningful line 0.1 h ago (384/384 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 3_5_place_dp | 3.1 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 3.1 | repair_TNS best 220427 last 220427 rows 19 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t16-3746725 | serdes__t16 | 4_1_cts | 3.7 | repair_Violations best 13 last 16 rows 14 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_2_route | 3.7 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | 4_1_cts | 3.0 | last meaningful line 0.0 h ago (5537/5537 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-2036208-3288 | 2036208 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | phscan-1854121 | phscan | kv3_pc_v3-route-loved-redfish-1034456-1795203695.placed_raw | 4.2 | last meaningful line 0.5 h ago (11/11 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_1437304_ff_48902 | so_1437304_ff_48902 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_1437304_tt_48902 | so_1437304_tt_48902 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | 2_1_floorplan | 0.5 | last meaningful line 0.0 h ago (1431/1431 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (1491/1491 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (364/364 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 3.5 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 3.7 | last meaningful line 0.2 h ago (248/398 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 3.7 | last meaningful line 2.2 h ago (209/229 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 3.7 | last meaningful line 2.0 h ago (209/229 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (1783/1783 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 4.1 | last meaningful line 0.2 h ago (255/256 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | tt_setup_repair_grt | 3.5 | repair_Viol best 1455 last 1455 rows 23 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | 3_1_place_gp_skip_io | 4.0 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (87/87 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-833696 | kv3_sys_c | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1556/1556 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-957100 | ot_s81sl_leaf__t33 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (1430/1430 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2007320 | sle_ctl | 2_1_floorplan | 0.4 | last meaningful line 0.1 h ago (1426/1426 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 14.4 | last meaningful line 1.7 h ago (217/223 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1604383 | sle_stm_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.6704 last 0.6704 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 15.3 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-2060137 | sle_su_c | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9276 last 0.9276 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 3.5 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 15.6 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 16.3 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 16.3 | last meaningful line 0.4 h ago (271/272 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-2862262 | slw_hc2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-2927245 | slw_sc_v1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (188/188 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 16.7 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-429445 | slw_stm_v1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261120_091653_2376724-i1-614277 | eco_20261120_091653_2376724-i1 | 5_2_route | 2.9 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | so_915205_ff_21124 | so_915205_ff_21124 | generate_abstract | 0.9 | last meaningful line 0.7 h ago (204/204 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | so_915205_tt_21124 | so_915205_tt_21124 | generate_abstract | 0.9 | last meaningful line 0.7 h ago (204/204 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | 5_1_grt | 16.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 25.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 59.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 35.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 36.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 9.5 | last meaningful line 1.6 h ago (1373/1373 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3532/3532 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 25.1 | drt_violations best 20 last 20 rows 51 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 25.1 | drt_violations best 20 last 20 rows 51 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3639/3639 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 25.1 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3797/3797 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_1_grt | 2.7 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3488/3488 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3589/3589 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-serdes__t1__clb45db5be-2837229 | serdes__t1 | 3_5_place_dp | 1.7 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (476/476 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_1_grt | 3.7 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 3.7 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 21.6 | drt_violations best 10389 last 10389 rows 16 | before-window best 11596, window best 10389 | PROGRESS: drt_violations improved 10.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 21.3 | drt_violations best 7619 last 38244 rows 18 | before-window best 8100, window best 7619 | PROGRESS: drt_violations improved 5.9 % in window |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 160 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 7.6 | drt_violations best 413 last 413 rows 4 | before-window best 28098, window best 413 | PROGRESS: drt_violations improved 98.5 % in window |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 22.7 | last meaningful line 0.0 h ago (1352/1352 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 17.7 | last meaningful line 0.0 h ago (1073/1073 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 9.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 9.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1125/1125 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (941/941 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 16.4 | last meaningful line 0.0 h ago (1053/1053 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (941/941 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (941/941 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (941/941 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 16.9 | last meaningful line 0.0 h ago (1066/1066 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 16.0 | last meaningful line 0.0 h ago (956/956 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (941/941 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (941/941 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (941/941 lines) | PROGRESS: log still growing |  |
