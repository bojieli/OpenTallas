# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 12:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 4, 'GRT-LABEL': 11, 'NO-DATA': 10, 'YOUNG': 141, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 15.0 | drt_violations best 110699 last 110699 rows 1 | before-window best 110699, window best 110699 | NO-PROGRESS: drt_violations best 110699 vs 110699 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 11.9 | drt_violations best 133408 last 133408 rows 1 | before-window best 133408, window best 133408 | NO-PROGRESS: drt_violations best 133408 vs 133408 before window: < 2 % in 6 h | CANCELLED |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 11.9 | drt_violations best 132897 last 132897 rows 1 | before-window best 132897, window best 132897 | NO-PROGRESS: drt_violations best 132897 vs 132897 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1341/1341 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -775.63 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (278/278 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -385.89 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | tt_setup_repair | 3.3 | repair_Viol best 310 last 310 rows 16 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -454.43 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | tt_setup_repair | 3.4 | repair_Violations best 146 last 226 rows 57 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -313.34 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 8.5 | last meaningful line 6.1 h ago (249/322 lines) | NO-PROGRESS: no new non-iteration log line for 6.1 h | REPORTED (cancel next pass) |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 17.3 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 3.4 | grt rounds 6 overflow 5:1998 -> 10:1858 -> 15:1870 -> 20:1699 -> 25:1717 -> 30:1567 | GRT-LABEL: DESIGN-FAIL: overflow 1858 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 3.3 | grt rounds 2 overflow 5:48999 -> 10:45315 | GRT-LABEL: DESIGN-FAIL: overflow 45315 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:2979 -> 10:1494 | GRT-LABEL: DESIGN-FAIL: overflow 1494 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:30456 -> 10:19532 | GRT-LABEL: DESIGN-FAIL: overflow 19532 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 13.8 | grt rounds 3 overflow 5:27316 -> 10:11412 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:50814 -> 10:51002 | GRT-LABEL: DESIGN-FAIL: overflow 51002 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 22.9 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 14.8 | grt rounds 3 overflow 5:46995 -> 10:41355 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: overflow 41355 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 14.8 | grt rounds 2 overflow 5:58470 -> 10:41949 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 9.3 | grt rounds 4 overflow 5:13197 -> 10:11192 -> 15:10179 -> 20:10000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t36-grt-785951 | ot-s81sl-leaf--t36-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t56-grt-626773 | ot-s81sl-leaf--t56-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t72-grt-847111 | ot-s81sl-leaf--t72-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-serdes--t14-grt-896578 | serdes--t14-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (213/213 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 2_1_floorplan | 0.2 | repair_Viol best 1128 last 1128 rows 392 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (199/205 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 4_1_cts | 0.2 | repair_Violations best 60 last 239 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 4_1_cts | 0.2 | repair_Violations best 60 last 97 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (3489/3489 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (3647/3647 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9715 last 0.9715 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-328394 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (3560/3560 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3613602 | dsdv_slice_lepw_mu_LP__t2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7018 last 0.835 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v1__cl141fc26e-1783065 | kv3_hgi_v1 | 3_3_place_gp | 0.8 | overflow best 0.1926 last 0.1926 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (3123/3123 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (3418/3418 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | 2_4_floorplan_pdn | 1.3 | last meaningful line 0.3 h ago (93/93 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-3229485 | ot_s81sl_leaf__t36 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t37-324991 | ot_s81sl_leaf__t37 | stage_odb_cap | 0.2 | last meaningful line 0.0 h ago (8/8 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-319778 | ot_s81sl_leaf__t5 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7646 last 0.829 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-serdes__t1__clb45db5be-2837229 | serdes__t1 | 3_3_place_gp | 1.5 | overflow best 0.1987 last 0.1987 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-serdes__t3-2131131 | serdes__t3 | 3_3_place_gp | 1.6 | overflow best 0.2 last 0.2 rows 42 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl372cea1c-3342696 | sle_ctl | 2_1_floorplan | 0.4 | last meaningful line 0.1 h ago (1426/1426 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff-3983509 | sle_ctl | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (1422/1422 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff__padE4-3232565 | sle_ctl | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795-3620476 | sle_ctl | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (1426/1426 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-1703862 | sle_ctl | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-4132289 | sle_fw_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3347897 | sle_fw_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9984 last 0.9984 rows 12 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-3213795 | sle_fw_v2 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-127322 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9944 last 0.9944 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v2-127583 | sle_sc_v2 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-324034 | sle_st_b_v2 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (397/397 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__cl27746664-3856466 | sle_stm_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3217716 | sle_stm_v1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3864447 | sle_stm_v2 | 3_3_place_gp | 0.3 | last meaningful line -0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (462/462 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-319437 | slice_station__t24 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.993 last 0.993 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-3911511 | slice_station__t29 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t40__clc8fb2c8c-3205661 | slice_station__t40 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-315959 | slw_fe_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3636235 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.5568 last 0.5568 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-1782333 | slw_fe_v2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-3338635 | slw_fw_v1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (473/473 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-708438 | slw_fw_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 15.0 | drt_violations best 102627 last 102627 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4163727 | slw_fw_v2 | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-1772497 | slw_hc0 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3-1780248 | slw_hc0 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-331949 | slw_hc1 | 1_synth | 0.2 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-1301687 | slw_hc2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-120113 | slw_sc_v1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v2-4155454 | slw_sc_v2 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__cl9f076a5c-327381 | slw_st_a_v2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9773 last 0.9773 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-3230820 | slw_st_b_v1 | 3_3_place_gp | 0.5 | last meaningful line -0.0 h ago (238/238 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-131605 | slw_st_b_v2 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (3615/3615 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3566124 | slw_stm_v2 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-4136362 | slw_su_l1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 1.1 | last meaningful line 0.0 h ago (303/303 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-367632-348 | 367632 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-369074-32307 | 369074 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-4183100-28822 | 4183100 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 1.9 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 1.5 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (141/141 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 8.5 | drt_violations best 26911 last 26911 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbn-q11--cl49ae4555-grt-1099269 | cbn-q11--cl49ae4555-grt | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (360/360 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v3-grt-990822 | kv3-hgi-v3-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v5-grt-833678 | kv3-hgi-v5-grt | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (272/272 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v6-grt-959272 | kv3-hgi-v6-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v7-grt-953196 | kv3-hgi-v7-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (284/284 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-render-8d4eb8ecc54d-1089232 | ap-render-8d4eb8ecc54d | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 11.8 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-379194 | hd_serdes | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-2263912 | kv3_hgi_v8 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (495/495 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-3573937 | kv3_pv_v1 | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-3098388 | kv3_pv_v12 | 2_1_floorplan | 1.2 | last meaningful line 1.0 h ago (144/144 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-3603774 | kv3_pv_v12 | 2_1_floorplan | 1.0 | last meaningful line 0.8 h ago (145/145 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | 2_4_floorplan_pdn | 1.2 | last meaningful line 0.2 h ago (91/91 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | 3_1_place_gp_skip_io | 1.2 | overflow best 0.8583 last 0.8583 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | 3_1_place_gp_skip_io | 1.2 | overflow best 0.9346 last 0.9346 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | 2_1_floorplan | 0.9 | last meaningful line 0.2 h ago (1263/1263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | 2_1_floorplan | 1.1 | last meaningful line 0.8 h ago (107/107 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | 2_1_floorplan | 1.1 | last meaningful line 0.3 h ago (1417/1417 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | 2_1_floorplan | 1.1 | last meaningful line 0.3 h ago (1419/1419 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v6n-2561884 | kv3_pv_v6n | 2_4_floorplan_pdn | 1.4 | last meaningful line -0.0 h ago (55/55 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | 2_1_floorplan | 1.3 | last meaningful line 0.5 h ago (1299/1299 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 3_5_place_dp | 2.3 | last meaningful line 0.1 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t36-216377 | ot_s81sl_leaf__t36 | 3_5_place_dp | 0.5 | last meaningful line -0.0 h ago (38/38 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-3458307 | ot_s81sl_leaf__t56 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 2.3 | repair_TNS best 231303 last 231303 rows 3 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-serdes__t14-2640585 | serdes__t14 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t16-3746725 | serdes__t16 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (662/662 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cl503337ff__padE0-3721260 | sle_ctl | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | postcts_gate_TT | 3.0 | last meaningful line 0.2 h ago (23/23 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | 4_1_cts | 2.2 | last meaningful line -0.0 h ago (5364/5365 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 3.0 | last meaningful line 1.4 h ago (213/892 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2569223 | slw_fw_v1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3178434 | slw_fw_v2 | stage_odb_cap | 1.2 | last meaningful line -0.0 h ago (212/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | generate_abstract | 19.3 | last meaningful line 0.0 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | 6_report | 12.5 | last meaningful line -0.0 h ago (948/948 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ffkpvr2-grt-v8j_it0-1085144 | ffkpvr2-grt-v8j_it0 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 4_1_cts | 1.6 | repair_Viol best 374 last 374 rows 63 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264-lec | dsdv_bksel_c_rfda3p | 4_1_cts | 1.4 | repair_Viol best 374 last 374 rows 62 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | phscan-1854121 | phscan | sle_sc_v1__cl115da35f-route-loved-redfish-922528-1795195795.placed_raw | 3.5 | last meaningful line 0.1 h ago (11/11 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 6.9 | drt_violations best 28098 last 28098 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | ap-ageom-kw-cbf-q00--cl870de686-grt-2066129 | cbf-q00--cl870de686-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-sle-ctl--cl372cea1c-grt-2309849 | sle-ctl--cl372cea1c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-slw-fe-v2--clf110fab2-grt-2061145 | slw-fe-v2--clf110fab2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | 2_1_floorplan | 0.2 | repair_Viol best 1128 last 1128 rows 381 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (349/349 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 3.3 | last meaningful line 0.3 h ago (259/260 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 3.4 | last meaningful line 2.0 h ago (209/224 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 3.4 | last meaningful line 2.0 h ago (209/226 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 3.4 | last meaningful line 1.8 h ago (209/226 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 3.9 | last meaningful line 0.3 h ago (253/254 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | tt_setup_repair_grt | 3.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | stage_odb_cap | 1.8 | last meaningful line 0.1 h ago (20/20 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-833696 | kv3_sys_c | 3_3_place_gp | 0.7 | overflow best 0.7984 last 0.7984 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1406/1406 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-957100 | ot_s81sl_leaf__t33 | 3_3_place_gp | 0.7 | overflow best 0.529 last 0.5361 rows 15 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2007320 | sle_ctl | 2_1_floorplan | 0.1 | repair_Viol best 2866 last 2866 rows 234 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 14.1 | last meaningful line 1.5 h ago (217/223 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1604383 | sle_stm_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 15.0 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-2060137 | sle_su_c | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 3.3 | last meaningful line 0.5 h ago (255/256 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 15.3 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 16.0 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 16.0 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-1851744 | slw_sc_v1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 16.4 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-429445 | slw_stm_v1 | 3_3_place_gp | 0.9 | overflow best 0.1624 last 0.1624 rows 38 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | tt_setup_repair | 0.1 | repair_Remaining best 167271 last 167271 rows 210 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 0.6 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_091653_2376724-i1-614277 | eco_20261120_091653_2376724-i1 | 5_2_route | 2.7 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | so_915205_ff_21124 | so_915205_ff_21124 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (204/204 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | so_915205_tt_21124 | so_915205_tt_21124 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (204/204 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (236/975 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 24.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 59.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 35.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 35.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 9.2 | last meaningful line 1.4 h ago (1373/1373 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (3382/3382 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 24.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 24.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 24.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_1_grt | 2.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (3348/3348 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (3449/3449 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 20.8 | drt_violations best 10389 last 10389 rows 16 | before-window best 13349, window best 10389 | PROGRESS: drt_violations improved 22.2 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 20.5 | drt_violations best 7619 last 38244 rows 18 | before-window best 8483, window best 7619 | PROGRESS: drt_violations improved 10.2 % in window |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 12.6 | last meaningful line 0.0 h ago (7078/7078 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | 5_2_route | 22.2 | drt_violations best 28 last 28 rows 48 | before-window best 131, window best 28 | PROGRESS: drt_violations improved 78.6 % in window |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 17.2 | last meaningful line 0.0 h ago (1044/1044 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 15.5 | last meaningful line 0.0 h ago (966/966 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 9.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 9.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1095/1095 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (912/912 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 15.9 | last meaningful line 0.0 h ago (1023/1023 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (911/911 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (911/911 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (911/911 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 16.4 | last meaningful line 0.0 h ago (1036/1036 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 15.5 | last meaningful line 0.0 h ago (926/926 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (911/911 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (911/911 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (911/911 lines) | PROGRESS: log still growing |  |
