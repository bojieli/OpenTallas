# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 11:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 16, 'NO-PROGRESS': 6, 'GRT-LABEL': 10, 'NO-DATA': 5, 'YOUNG': 142, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (1858/1858 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -384.44 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 13.0 | last meaningful line 0.0 h ago (193/195 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1734.56 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 13.0 | repair_Viol best 222 last 222 rows 114 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -843.81 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2455/2455 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -509.62 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 12.6 | grt rounds 3 overflow 5:43291 -> 10:27555 -> 15:25376 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -634.17 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_2_route | 10.9 | drt_violations best 97439 last 97439 rows 1 | before-window best 97439, window best 97439 | NO-PROGRESS: drt_violations best 97439 vs 97439 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_2_route | 10.9 | drt_violations best 97026 last 97026 rows 1 | before-window best 97026, window best 97026 | NO-PROGRESS: drt_violations best 97026 vs 97026 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 13.3 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1106.94 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 5_1_grt | 12.9 | grt rounds 3 overflow 5:14481 -> 10:8943 -> 15:10176 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1357.30 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 12.9 | drt_violations best 84302 last 84302 rows 1 | before-window best 84302, window best 84302 | NO-PROGRESS: drt_violations best 84302 vs 84302 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 13.1 | drt_violations best 81753 last 81753 rows 1 | before-window best 81753, window best 81753 | NO-PROGRESS: drt_violations best 81753 vs 81753 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 136.7 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -651.19 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 136.7 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -568.86 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | tt_setup_repair | 12.7 | repair_Viol best 161 last 161 rows 272 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -511.24 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 13.1 | grt rounds 3 overflow 5:27801 -> 10:25683 -> 15:21143 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -494.61 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | 5_1_grt | 12.5 | repair_Viol best 95 last 95 rows 5 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -404.82 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 7.3 | last meaningful line 6.1 h ago (249/308 lines) | NO-PROGRESS: no new non-iteration log line for 6.1 h | REPORTED (cancel next pass) |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 7.3 | last meaningful line 6.1 h ago (249/351 lines) | NO-PROGRESS: no new non-iteration log line for 6.1 h | REPORTED (cancel next pass) |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 14.2 | last meaningful line 0.0 h ago (843/843 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -538.38 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1000/1000 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1301.87 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (988/988 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -871.32 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (956/956 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -348.88 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | 5_1_grt | 5.3 | grt rounds 3 overflow 5:3019 -> 10:1337 -> 15:1194 | GRT-LABEL: DESIGN-FAIL: overflow 1337 at round 10 > 1000 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 16.1 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 2.2 | grt rounds 6 overflow 5:1998 -> 10:1858 -> 15:1870 -> 20:1699 -> 25:1717 -> 30:1567 | GRT-LABEL: DESIGN-FAIL: overflow 1858 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:30456 -> 10:21585 | GRT-LABEL: DESIGN-FAIL: overflow 21585 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 12.5 | grt rounds 3 overflow 5:27112 -> 10:12039 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:51746 -> 10:53387 | GRT-LABEL: DESIGN-FAIL: overflow 53387 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 21.7 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 13.5 | grt rounds 2 overflow 5:46995 -> 10:41355 | GRT-LABEL: DESIGN-FAIL: overflow 41355 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 13.5 | grt rounds 2 overflow 5:58470 -> 10:41949 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:11862 -> 10:11192 -> 15:10179 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t21-dump-1035189 | ot-s81sl-leaf--t21-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t21-grt-1035189 | ot-s81sl-leaf--t21-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-1944187 | cbn_q00 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8507 last 0.8833 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551-2785777 | cbx_q10 | 3_3_place_gp | 0.5 | overflow best 0.5901 last 0.5901 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3989312 | col_h10_r1__t1 | 5_1_grt | 5.3 | last meaningful line 3.0 h ago (199/229 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2829/2829 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (2927/2927 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2830/2830 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2889/2889 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (3047/3047 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-321559 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.2998 last 0.3078 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_1_grt | 1.5 | repair_Remaining best 60727 last 60727 rows 28 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2748/2748 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | 5_2_route | 5.3 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (2960/2960 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_LP__t2-2817595 | dsdv_slice_lepe_mu_LP__t2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3307 last 0.3307 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2523/2523 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (2818/2818 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | 2_1_floorplan | 0.3 | last meaningful line 0.2 h ago (108/108 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1758359 | ot_s81sl_leaf__t32 | 3_3_place_gp | 0.7 | overflow best 0.4552 last 0.4863 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-3852983 | ot_s81sl_leaf__t60 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t66-2986632 | ot_s81sl_leaf__t66 | 3_3_place_gp | 0.5 | overflow best 0.6073 last 0.6073 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2976011 | ot_s81sl_leaf__t72 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t1__clb45db5be-2837229 | serdes__t1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t3-2131131 | serdes__t3 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff__padE4-1960211 | sle_ctl | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795-1955098 | sle_ctl | 3_1_place_gp_skip_io | 0.6 | overflow best 0.6504 last 0.6504 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-1703862 | sle_ctl | 3_3_place_gp | 0.7 | overflow best 0.4977 last 0.4977 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2594730 | sle_fw_v1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (276/276 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2604299 | sle_fw_v1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-120949 | sle_hc0 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-2069867 | sle_st_b_v2 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (402/402 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-3911511 | slice_station__t29 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 14.0 | drt_violations best 110699 last 110699 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 14.0 | drt_violations best 102627 last 102627 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl3449ea95-4077810 | slw_hc1 | 2_3_floorplan_tapcell | 0.3 | last meaningful line -0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-120113 | slw_sc_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-3763698 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (924/924 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (142/142 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 7.5 | drt_violations best 26911 last 26911 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q11__cl49ae4555-1386485 | cbn_q11 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q11__cl5cc92dfe-1384941 | cbn_q11 | 3_3_place_gp | 1.0 | overflow best 0.2207 last 0.2207 rows 34 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3036085 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9205 last 0.9229 rows 10 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 10.8 | last meaningful line 1.2 h ago (278/279 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2720405 | col_h9_r0_p1__t1 | 3_2_place_iop | 0.4 | last meaningful line -0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 10.9 | last meaningful line 0.7 h ago (289/290 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 10.9 | last meaningful line 0.7 h ago (289/290 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-3040432 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v3-1774449 | kv3_hgi_v3 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v5-1793341 | kv3_hgi_v5 | 3_2_place_iop | 0.8 | last meaningful line -0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v6-1768022 | kv3_hgi_v6 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v7-1783245 | kv3_hgi_v7 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.1152 last 0.1152 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v8-2263912 | kv3_hgi_v8 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8999 last 0.8999 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-3521074 | kv3_pc | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (359/359 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-3573937 | kv3_pv_v1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-3098388 | kv3_pv_v12 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-3603774 | kv3_pv_v12 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | 2_1_floorplan | 0.2 | last meaningful line -0.0 h ago (10/10 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (105/105 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | 1_synth | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (342/342 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | reg_fanout | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-kv3_pv_v6n-2561884 | kv3_pv_v6n | 2_1_floorplan | 0.4 | last meaningful line 0.1 h ago (767/767 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | 2_1_floorplan | 0.3 | repair_Viol best 1091 last 1091 rows 276 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 3_3_place_gp | 1.3 | overflow best 0.7094 last 0.7133 rows 5 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2490765 | ot_s81sl_kv_leaf__t1 | 2_1_floorplan | 0.5 | repair_Viol best 1304 last 1304 rows 976 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-3249047 | ot_s81sl_leaf__t22 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9102 last 0.9517 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t26-3271279 | ot_s81sl_leaf__t26 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.4715 last 0.4715 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t52-3274743 | ot_s81sl_leaf__t52 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8937 last 0.9154 rows 10 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3263130 | ot_s81sl_leaf__t55 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8708 last 0.8853 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-3458307 | ot_s81sl_leaf__t56 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t14-2640585 | serdes__t14 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t16-3746725 | serdes__t16 | 3_3_place_gp | 2.0 | last meaningful line 0.0 h ago (102/102 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl69f5e854-893019 | sle_fw_v2 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_1_grt | 2.0 | last meaningful line 0.5 h ago (215/789 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_1_grt | 2.0 | repair_TNS best 502.606 last 502.606 rows 4 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2322694 | sle_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.6474 last 0.6474 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 2.0 | last meaningful line 0.4 h ago (213/839 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-1993703 | sle_stm_v1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v2__cl55be2264-1248458 | sle_stm_v2 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (335/335 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v2__cl7b3062fa-1170508 | sle_stm_v2 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1884728 | slw_fe_v1 | 3_3_place_gp | 0.7 | overflow best 0.3214 last 0.3214 rows 26 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-1219784 | slw_fe_v1 | 3_4_place_resized | 1.0 | last meaningful line -0.0 h ago (320/320 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__cl51d45468-869460 | slw_fw_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2569223 | slw_fw_v1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (357/357 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3178434 | slw_fw_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8f84514c-1131126 | slw_fw_v2 | 3_4_place_resized | 1.1 | repair_Remaining best 279659 last 279659 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v3-1220049 | slw_fw_v3 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 17.6 | drt_violations best 100464 last 100464 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cl6bcaba89-2131191 | slw_hc2 | 3_3_place_gp | 0.6 | overflow best 0.7624 last 0.7624 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-2320085 | slw_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.641 last 0.641 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-1508321 | slw_st_b_v1 | 3_3_place_gp | 0.9 | overflow best 0.3932 last 0.3932 rows 32 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1507079 | slw_st_b_v2 | 3_3_place_gp | 0.9 | overflow best 0.6462 last 0.6462 rows 24 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-2198579 | slw_stm_v2 | 3_3_place_gp | 0.6 | overflow best 0.488 last 0.488 rows 9 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-tt_ctlm-1620401 | tt_ctlm | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 3_3_place_gp | 0.6 | overflow best 0.3265 last 0.4614 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264-lec | dsdv_bksel_c_rfda3p | 3_3_place_gp | 0.4 | overflow best 0.3265 last 0.4614 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | otc-2848231-29567 | 2848231 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc7 | phscan-1854121 | phscan | 5_2_route | 2.5 | drt_violations best 100464 last 100464 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 5.9 | drt_violations best 28098 last 28098 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_161628_1023465-i1t-2964619 | eco_20261120_161628_1023465-i1t | 5_2_route | 2.4 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-3269452 | cbf_q00 | 3_3_place_gp | 2.1 | overflow best 0.0975 last 0.0975 rows 37 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-cbf_q00_s2-1902764 | cbf_q00_s2 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-3325897 | cbx_q10 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | tt_setup_repair | 2.2 | repair_Violations best 618 last 704 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 2.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 2.2 | last meaningful line 0.8 h ago (209/215 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 2.2 | last meaningful line 0.8 h ago (209/214 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (209/215 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (895/895 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | tt_setup_repair_grt | 2.6 | repair_Viol best 343 last 343 rows 27 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-1885956 | col_h9_r2__t1 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (196/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.5 h ago (235/392 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-coll_core-1983638 | coll_core | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 0.5 h ago (127/127 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 2.0 | last meaningful line 1.3 h ago (203/211 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-2201770 | kv3_hgi_v1 | 3_4_place_resized | 0.9 | repair_Remaining best 49926 last 49926 rows 44 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_hub_Wo-1210047 | kv3_hub_Wo | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (632/632 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (519/519 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | 2_1_floorplan | 0.6 | repair_Viol best 1055 last 1055 rows 978 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (668/668 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (526/526 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-2518275 | sle_ctl | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 12.9 | last meaningful line 0.3 h ago (217/219 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 13.8 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | postcts_gate_TT | 2.0 | last meaningful line 0.0 h ago (1001/1001 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | postcts_gate_FF | 14.1 | last meaningful line 0.3 h ago (852/852 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8537f156-3287968 | slw_fw_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | postcts_gate_FF | 14.8 | last meaningful line 0.1 h ago (851/851 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 14.8 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 15.2 | last meaningful line 0.2 h ago (136/136 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2118342 | slw_st_b_v2 | 3_3_place_gp | 0.9 | overflow best 0.2099 last 0.2099 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | prd-eco_20261120_091653_2376724-i1-614277 | eco_20261120_091653_2376724-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-fin-1677571 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (221/221 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 8.1 | repair_TNS best 82702.6 last 82702.6 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | postcts_gate_FF | 14.3 | last meaningful line 0.0 h ago (1005/1005 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 23.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 58.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 34.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 34.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 8.2 | last meaningful line 0.4 h ago (1373/1373 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 23.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 23.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 23.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_2_route | 10.9 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 4_1_cts | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 18.3 | drt_violations best 11525 last 11525 rows 3 | before-window best 122546, window best 11525 | PROGRESS: drt_violations improved 90.6 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 19.8 | drt_violations best 10389 last 10389 rows 16 | before-window best 14325, window best 10389 | PROGRESS: drt_violations improved 27.5 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 19.5 | drt_violations best 7619 last 38244 rows 18 | before-window best 8942, window best 7619 | PROGRESS: drt_violations improved 14.8 % in window |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 11.6 | last meaningful line 0.0 h ago (6468/6468 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 11.5 | last meaningful line 0.0 h ago (6454/6454 lines) | PROGRESS: log still growing |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 7.3 | last meaningful line 4.9 h ago (249/322 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 21.2 | last meaningful line 0.0 h ago (1262/1262 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 16.2 | last meaningful line 0.0 h ago (984/984 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (987/987 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 14.5 | last meaningful line 0.0 h ago (906/906 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 8.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1036/1036 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (852/852 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 14.9 | last meaningful line 0.0 h ago (964/964 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (852/852 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (852/852 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 15.4 | last meaningful line 0.0 h ago (976/976 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 14.5 | last meaningful line 0.0 h ago (866/866 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (852/852 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (852/852 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (851/851 lines) | PROGRESS: log still growing |  |
