# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 11:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 16, 'NO-PROGRESS': 6, 'GRT-LABEL': 10, 'NO-DATA': 4, 'YOUNG': 133, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 31}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (1963/1963 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -384.44 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 13.2 | last meaningful line 0.3 h ago (193/199 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1734.56 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 13.2 | repair_Viol best 222 last 222 rows 128 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -843.81 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2605/2605 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -509.62 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:43291 -> 10:27555 -> 15:25376 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -634.17 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 11.4 | drt_violations best 133408 last 133408 rows 1 | before-window best 133408, window best 133408 | NO-PROGRESS: drt_violations best 133408 vs 133408 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 18.1 | drt_violations best 100464 last 100464 rows 1 | before-window best 100464, window best 100464 | NO-PROGRESS: drt_violations best 100464 vs 100464 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 13.6 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1106.94 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 5_1_grt | 13.2 | grt rounds 3 overflow 5:14481 -> 10:8943 -> 15:10176 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1357.30 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 13.1 | drt_violations best 84302 last 84302 rows 1 | before-window best 84302, window best 84302 | NO-PROGRESS: drt_violations best 84302 vs 84302 before window: < 2 % in 6 h | CANCELLED |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 13.4 | drt_violations best 81753 last 81753 rows 1 | before-window best 81753, window best 81753 | NO-PROGRESS: drt_violations best 81753 vs 81753 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 136.9 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -651.19 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 136.9 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -568.86 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | hold_gate | 13.0 | last meaningful line 0.0 h ago (17/17 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -511.24 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 13.4 | grt rounds 3 overflow 5:27801 -> 10:25683 -> 15:21143 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -494.61 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | 5_1_grt | 12.8 | repair_Viol best 95 last 95 rows 17 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -404.82 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 7.5 | last meaningful line 6.3 h ago (249/308 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORTED (cancel next pass) |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 7.5 | last meaningful line 6.4 h ago (249/351 lines) | NO-PROGRESS: no new non-iteration log line for 6.4 h | REPORTED (cancel next pass) |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 14.4 | last meaningful line 0.0 h ago (858/858 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -538.38 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.0 | repair_Viol best 607 last 607 rows 525 | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -1301.87 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (1003/1003 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -871.32 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (971/971 lines) | UNSIGNABLE: 4_1_cts.json cts__timing__setup__ws -348.88 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 5.8 | grt rounds 4 overflow 5:6798 -> 10:4941 -> 15:2610 -> 20:2311 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 16.3 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 2.4 | grt rounds 6 overflow 5:1998 -> 10:1858 -> 15:1870 -> 20:1699 -> 25:1717 -> 30:1567 | GRT-LABEL: DESIGN-FAIL: overflow 1858 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:30456 -> 10:21585 | GRT-LABEL: DESIGN-FAIL: overflow 21585 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:27112 -> 10:11412 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:50814 -> 10:53387 | GRT-LABEL: DESIGN-FAIL: overflow 53387 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 21.9 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 13.8 | grt rounds 2 overflow 5:46995 -> 10:41355 | GRT-LABEL: DESIGN-FAIL: overflow 41355 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 13.8 | grt rounds 2 overflow 5:58470 -> 10:41949 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:11862 -> 10:11192 -> 15:10179 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | ap-ageom-kw-col-h10-r2--t1--cl8b686b3e-grt-1785753 | col-h10-r2--t1--cl8b686b3e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t26-grt-2045785 | ot-s81sl-leaf--t26-grt | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (117/117 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-1944187 | cbn_q00 | 3_3_place_gp | 0.9 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551-2785777 | cbx_q10 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2932/2932 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (221/221 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2979/2979 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | 5_1_grt | 5.8 | last meaningful line 2.8 h ago (199/229 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2980/2980 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (3039/3039 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (3197/3197 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_1_grt | 1.7 | repair_Remaining best 29727 last 29727 rows 59 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2898/2898 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2999/2999 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (3110/3110 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_LP__t2-2817595 | dsdv_slice_lepe_mu_LP__t2 | 3_3_place_gp | 0.7 | overflow best 0.7038 last 0.7038 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v1__cl141fc26e-1783065 | kv3_hgi_v1 | 2_1_floorplan | 0.1 | repair_Viol best 1094 last 1094 rows 1171 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2673/2673 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | 2_1_floorplan | 0.5 | last meaningful line 0.3 h ago (108/108 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1758359 | ot_s81sl_leaf__t32 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-3852983 | ot_s81sl_leaf__t60 | 3_4_place_resized | 0.5 | repair_Remaining best 100221 last 100221 rows 43 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t66-2986632 | ot_s81sl_leaf__t66 | 3_3_place_gp | 0.7 | overflow best 0.1911 last 0.1911 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2976011 | ot_s81sl_leaf__t72 | 3_3_place_gp | 0.7 | overflow best 0.5622 last 0.5622 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-serdes__t1__clb45db5be-2837229 | serdes__t1 | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.3 h ago (93/93 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t3-2131131 | serdes__t3 | stage_odb_cap | 0.9 | last meaningful line 0.1 h ago (12/12 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cl503337ff__padE4-1960211 | sle_ctl | 3_3_place_gp | 0.9 | overflow best 0.1964 last 0.1964 rows 52 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-1703862 | sle_ctl | 3_3_place_gp | 0.9 | overflow best 0.2035 last 0.2035 rows 25 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2604299 | sle_fw_v1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (332/332 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-120949 | sle_hc0 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-2069867 | sle_st_b_v2 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (417/417 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-3911511 | slice_station__t29 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-1782333 | slw_fe_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 14.3 | drt_violations best 110699 last 110699 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 14.3 | drt_violations best 102627 last 102627 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-1772497 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (294/294 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3-1780248 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (303/303 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl3449ea95-4077810 | slw_hc1 | 3_3_place_gp | 0.5 | overflow best 0.878 last 0.8782 rows 13 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-1301687 | slw_hc2 | synth_odb_v | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-120113 | slw_sc_v1 | 3_3_place_gp | 0.5 | overflow best 0.3596 last 0.3599 rows 10 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1783707 | slw_st_a_v1 | 2_1_floorplan | 0.1 | repair_Viol best 2328 last 2328 rows 709 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (93/93 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (143/143 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 7.8 | drt_violations best 26911 last 26911 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | prd-fin-3763698 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (974/974 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slw-fe-v1--clfe325744--cldb4efe33-grt-197088 | slw-fe-v1--clfe325744--cldb4efe33-grt | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q11__cl49ae4555-1386485 | cbn_q11 | 3_3_place_gp | 1.5 | overflow best 0.4843 last 0.4843 rows 24 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3036085 | col_h9_r0_p1__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 11.3 | last meaningful line 1.2 h ago (280/281 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v3-1774449 | kv3_hgi_v3 | 3_3_place_gp | 1.3 | overflow best 0.202 last 0.3695 rows 46 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v5-1793341 | kv3_hgi_v5 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v6-1768022 | kv3_hgi_v6 | 3_3_place_gp | 1.3 | overflow best 0.0982 last 0.0982 rows 53 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v7-1783245 | kv3_hgi_v7 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-2263912 | kv3_hgi_v8 | 3_3_place_gp | 1.1 | overflow best 0.3226 last 0.3226 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v1-3573937 | kv3_pv_v1 | 2_1_floorplan | 0.5 | repair_Viol best 1055 last 1055 rows 1158 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12-3098388 | kv3_pv_v12 | 2_1_floorplan | 0.7 | last meaningful line 0.5 h ago (144/144 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-3603774 | kv3_pv_v12 | 2_1_floorplan | 0.5 | last meaningful line 0.3 h ago (145/145 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | 2_1_floorplan | 0.7 | last meaningful line 0.3 h ago (100/100 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | 2_1_floorplan | 0.7 | last meaningful line 0.3 h ago (101/101 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | 2_1_floorplan | 0.7 | last meaningful line 0.5 h ago (105/105 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | 2_1_floorplan | 0.4 | repair_Viol best 1058 last 1058 rows 619 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | 2_1_floorplan | 0.6 | last meaningful line 0.3 h ago (107/107 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | 2_1_floorplan | 0.6 | repair_Viol best 1554 last 1554 rows 1244 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | 2_1_floorplan | 0.6 | repair_Viol best 1553 last 1553 rows 1207 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v6n-2561884 | kv3_pv_v6n | 2_1_floorplan | 0.9 | last meaningful line 0.5 h ago (767/767 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | 2_1_floorplan | 0.8 | last meaningful line 0.2 h ago (1299/1299 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 3_3_place_gp | 1.8 | overflow best 0.0995 last 0.0995 rows 41 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2490765 | ot_s81sl_kv_leaf__t1 | 3_3_place_gp | 1.0 | overflow best 0.9023 last 0.9023 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-3249047 | ot_s81sl_leaf__t22 | 3_3_place_gp | 0.7 | overflow best 0.381 last 0.381 rows 34 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t36-216377 | ot_s81sl_leaf__t36 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t52-3274743 | ot_s81sl_leaf__t52 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3263130 | ot_s81sl_leaf__t55 | 3_3_place_gp | 0.7 | overflow best 0.465 last 0.4695 rows 32 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-3458307 | ot_s81sl_leaf__t56 | 3_3_place_gp | 0.6 | overflow best 0.5011 last 0.5011 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (178/178 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t14-2640585 | serdes__t14 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.3876 last 0.3876 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-serdes__t16-3746725 | serdes__t16 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (542/542 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cl503337ff__padE0-3721260 | sle_ctl | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_1_grt | 2.5 | repair_TNS best 90.517 last 90.517 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (364/364 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2322694 | sle_st_b_v2 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 2.5 | repair_TNS best 596.672 last 596.672 rows 6 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1884728 | slw_fe_v1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2569223 | slw_fw_v1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3178434 | slw_fw_v2 | 3_3_place_gp | 0.7 | overflow best 0.3569 last 0.3578 rows 12 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8f84514c-1131126 | slw_fw_v2 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-1220049 | slw_fw_v3 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cl6bcaba89-2131191 | slw_hc2 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-2320085 | slw_st_b_v1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (168/168 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-1508321 | slw_st_b_v1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1507079 | slw_st_b_v2 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-2198579 | slw_stm_v2 | 3_3_place_gp | 1.1 | overflow best 0.0998 last 0.0998 rows 43 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 3_3_place_gp | 1.1 | overflow best 0.2998 last 0.3194 rows 158 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264-lec | dsdv_bksel_c_rfda3p | 3_3_place_gp | 0.9 | overflow best 0.2998 last 0.3194 rows 158 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | phscan-1854121 | phscan | 5_2_route | 3.0 | drt_violations best 100464 last 100464 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 6.4 | drt_violations best 28098 last 28098 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_161628_1023465-i1t-2964619 | eco_20261120_161628_1023465-i1t | 5_2_route | 2.9 | last meaningful line 0.5 h ago (128/128 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | so_203092_ff_40323 | so_203092_ff_40323 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_203092_tt_40323 | so_203092_tt_40323 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-kv3-hgi-v1--cl42bc8b12-grt-85794 | kv3-hgi-v1--cl42bc8b12-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-3269452 | cbf_q00 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (388/388 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00_s2-1902764 | cbf_q00_s2 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-3325897 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.4758 last 0.4773 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (290/290 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 2.3 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 2.4 | last meaningful line 1.0 h ago (209/216 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 2.4 | last meaningful line 1.0 h ago (209/215 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 2.4 | last meaningful line 0.8 h ago (209/216 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (218/218 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (1035/1035 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | postcts_gate_TT | 2.9 | last meaningful line -0.0 h ago (280/280 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-1885956 | col_h9_r2__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (1183/1183 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (187/187 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-coll_core-1983638 | coll_core | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 2.8 | last meaningful line 0.7 h ago (127/127 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 2.3 | last meaningful line 1.5 h ago (203/212 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-1210047 | kv3_hub_Wo | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (688/688 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (3728/3728 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | 2_1_floorplan | 0.8 | last meaningful line 0.2 h ago (1259/1259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (818/818 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (661/661 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (4290/4290 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-2518275 | sle_ctl | 3_3_place_gp | 1.0 | overflow best 0.1948 last 0.1948 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 13.1 | last meaningful line 0.5 h ago (217/220 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 14.0 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | postcts_gate_FF | 2.3 | last meaningful line -0.0 h ago (2579/2579 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | postcts_gate_FF | 14.3 | last meaningful line 0.1 h ago (1817/1817 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | postcts_gate_FF | 15.0 | last meaningful line 0.2 h ago (857/857 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 15.0 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 15.4 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2118342 | slw_st_b_v2 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | eco-abs-213241 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_091653_2376724-i1-614277 | eco_20261120_091653_2376724-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (255/256 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 8.4 | last meaningful line 0.1 h ago (49/49 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 24.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 58.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 34.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 35.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 8.5 | last meaningful line 0.6 h ago (1373/1373 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 24.1 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 24.1 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 24.1 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_1_grt | 1.1 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 11.4 | last meaningful line 1.2 h ago (289/290 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 18.8 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 20.3 | drt_violations best 10389 last 10389 rows 16 | before-window best 13349, window best 10389 | PROGRESS: drt_violations improved 22.2 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 20.0 | drt_violations best 7619 last 38244 rows 18 | before-window best 8483, window best 7619 | PROGRESS: drt_violations improved 10.2 % in window |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 12.1 | last meaningful line 0.0 h ago (6768/6768 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (6754/6754 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 7.5 | last meaningful line 5.1 h ago (249/322 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 21.4 | last meaningful line 0.0 h ago (1277/1277 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 16.5 | last meaningful line 0.0 h ago (999/999 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 16.0 | last meaningful line 0.0 h ago (1002/1002 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 14.8 | last meaningful line 0.0 h ago (921/921 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 8.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (1051/1051 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (867/867 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 15.2 | last meaningful line 0.0 h ago (979/979 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (867/867 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (867/867 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (867/867 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 15.6 | last meaningful line 0.0 h ago (991/991 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 14.8 | last meaningful line 0.0 h ago (881/881 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (867/867 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (866/866 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 14.5 | last meaningful line 0.0 h ago (866/866 lines) | PROGRESS: log still growing |  |
