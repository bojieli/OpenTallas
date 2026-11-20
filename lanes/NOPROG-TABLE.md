# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 09:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 13, 'YOUNG': 123, 'NO-DATA': 6, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_2_route | 8.8 | drt_violations best 22529 last 22529 rows 1 | before-window best 22529, window best 22529 | NO-PROGRESS: drt_violations best 22529 vs 22529 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_2_route | 12.1 | drt_violations best 74773 last 74773 rows 1 | before-window best 74773, window best 74773 | NO-PROGRESS: drt_violations best 74773 vs 74773 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 60304 last 60304 rows 1 | before-window best 60304, window best 60304 | NO-PROGRESS: drt_violations best 60304 vs 60304 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 59723 last 59723 rows 1 | before-window best 59723, window best 59723 | NO-PROGRESS: drt_violations best 59723 vs 59723 before window: < 2 % in 6 h | CANCELLED |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 11.7 | grt rounds 4 overflow 5:62 -> 10:91 -> 15:25 -> 20:8 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 11.3 | grt rounds 3 overflow 5:43291 -> 10:27534 -> 15:25376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 12.1 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | GRT-LABEL: DESIGN-FAIL: overflow 8426 at round 10 > 1000 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 14.8 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 135.4 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 135.4 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 0.8 | grt rounds 2 overflow 5:34209 -> 10:21585 | GRT-LABEL: DESIGN-FAIL: overflow 21585 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 11.9 | grt rounds 3 overflow 5:29114 -> 10:25683 -> 15:21703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 11.3 | grt rounds 3 overflow 5:27810 -> 10:12039 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 20.4 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 12.3 | grt rounds 2 overflow 5:46995 -> 10:41355 | GRT-LABEL: DESIGN-FAIL: overflow 41355 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 12.3 | grt rounds 2 overflow 5:58470 -> 10:41949 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 7.1 | grt rounds 3 overflow 5:11862 -> 10:11192 -> 15:10201 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (2042/2042 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3100/3100 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3989312 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.8 h ago (199/221 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (2089/2089 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-4014190 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.8 h ago (199/223 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2187/2187 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3560691 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.8 h ago (199/223 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (2090/2090 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (2149/2149 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2307/2307 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (2008/2008 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (1340/1340 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (2109/2109 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | 6_report | 9.2 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | tt_setup_repair_grt | 4.3 | last meaningful line 0.0 h ago (1106/1106 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 11.7 | repair_Viol best 222 last 222 rows 53 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (1783/1783 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2078/2078 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (1717/1717 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2594730 | sle_fw_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (93/93 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2604299 | sle_fw_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-2587375 | sle_fw_v2 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-2590654 | sle_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.5532 last 0.5532 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv4242de79-2423376 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.3463 last 0.3463 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__clfde1249e-2926341 | sle_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-2032336 | slice_station__t29 | 3_3_place_gp | 0.3 | overflow best 0.3283 last 0.3308 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 12.8 | last meaningful line 0.2 h ago (287/288 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 12.8 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2811301 | slw_sc_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2924479 | slw_sc_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clb036e152-2033332 | slw_st_a_v1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 2_1_floorplan | 11.7 | repair_Viol best 45452 last 45452 rows 1131 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 2_1_floorplan | 11.7 | repair_Viol best 54713 last 54713 rows 1187 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_2_route | 9.2 | drt_violations best 141 last 141 rows 5 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 6.3 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | so_1879836_ff_39339 | so_1879836_ff_39339 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (336/336 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_1879836_tt_39339 | so_1879836_tt_39339 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (336/336 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_2464050_ff_42109 | so_2464050_ff_42109 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (392/392 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_2464050_tt_42109 | so_2464050_tt_42109 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (392/392 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_2992856_ff_1259 | so_2992856_ff_1259 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_2992856_tt_1259 | so_2992856_tt_1259 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 9.6 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 9.7 | last meaningful line 1.0 h ago (285/286 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 9.7 | last meaningful line 1.0 h ago (285/286 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_2_route | 9.7 | drt_violations best 97439 last 97439 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_2_route | 9.7 | last meaningful line 1.3 h ago (288/289 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_2_route | 10.0 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_2_route | 9.7 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_2_route | 9.7 | drt_violations best 82734 last 82734 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_2_route | 9.7 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_2_route | 9.7 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_2_route | 9.7 | drt_violations best 13341 last 13341 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | port_bind | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 3_4_place_resized | 0.1 | repair_Remaining best 81831 last 81831 rows 270 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-serdes__t16-3746725 | serdes__t16 | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.0 h ago (98/98 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cl503337ff__padE0-3741211 | sle_ctl | 3_3_place_gp | 0.7 | overflow best 0.1943 last 0.2026 rows 32 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl69f5e854-893019 | sle_fw_v2 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (150/150 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | lec | 0.7 | LEC last write 0.1 h ago | YOUNG: evidence 0.7 h < 6 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | lec | 0.7 | LEC last write 0.1 h ago | YOUNG: evidence 0.7 h < 6 h |  |
| epyc7 | dpkit-slw_fw_v1__cl51d45468-869460 | slw_fw_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 16.3 | drt_violations best 100464 last 100464 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-sust_e3_s1_reseat_shadow-768674 | sust_e3_s1_reseat_shadow | 3_3_place_gp | 0.1 | overflow best 0.3547 last 0.3547 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | kvcore-pcfh_-2846360 | kvcore-pcfh_ | 5_2_route | 1.3 | last meaningful line 0.0 h ago (239/240 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2848231-29567 | 2848231 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | phscan-1854121 | phscan | 5_2_route | 1.2 | drt_violations best 100464 last 100464 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 4.6 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_161628_1023465-i1t-2964619 | eco_20261120_161628_1023465-i1t | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (136/136 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | so_3956260_ff_16509 | so_3956260_ff_16509 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (192/192 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_3956260_tt_16509 | so_3956260_tt_16509 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (192/192 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | ap-ageom-kw-dsdv-slice-iq-C--t1-grt-1080384 | dsdv-slice-iq-C--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-sle-sc-v2-grt-1099914 | sle-sc-v2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbf_q00__cl870de686-3269452 | cbf_q00 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.9085 last 0.9279 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-cbf_q00_s2-1902764 | cbf_q00_s2 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 5_1_grt | 11.7 | last meaningful line 0.5 h ago (201/208 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 0.9 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (195/204 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 0.9 | last meaningful line 0.1 h ago (158/158 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 0.9 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 0.9 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 11.6 | drt_violations best 84302 last 84302 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 11.9 | drt_violations best 81753 last 81753 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_1_grt | 1.4 | last meaningful line 0.8 h ago (196/214 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-1885956 | col_h9_r2__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (285/285 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (99/99 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-control_r2-1882631 | control_r2 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4415/4415 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | sdc_lint | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-grouped_r2-3317228 | grouped_r2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4553/4553 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (203/205 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 4_1_cts | 11.5 | last meaningful line 0.1 h ago (6438/6438 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-1210047 | kv3_hub_Wo | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3285005 | ot_s81sl_leaf__t40 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | 3_3_place_gp | 0.8 | overflow best 0.6173 last 0.6173 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | pregrt_ff_hold | 0.8 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 11.6 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v2__cl6740750e-3309324 | sle_fw_v2 | 3_3_place_gp | 0.8 | overflow best 0.3137 last 0.3137 rows 28 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | postcts_gate_TT | 12.5 | last meaningful line 0.2 h ago (1689/1689 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_1_grt | 0.8 | repair_Remaining best 117514 last 117514 rows 71 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | postcts_gate_TT | 12.8 | last meaningful line 0.2 h ago (875/875 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-1908466 | slw_fe_v2 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8537f156-3287968 | slw_fw_v2 | 3_3_place_gp | 0.8 | overflow best 0.3851 last 0.3851 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | postcts_gate_TT | 13.5 | last meaningful line 0.2 h ago (849/849 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | postcts_gate_FF | 13.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | postcts_gate_FF | 13.9 | last meaningful line 0.3 h ago (969/969 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | 5_1_grt | 11.3 | repair_Viol best 54 last 54 rows 121 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 2_1_floorplan | 10.7 | last meaningful line 0.3 h ago (1372/1372 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_2_route | 8.9 | drt_violations best 650 last 650 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | prd-eco_20261120_091653_2376724-i1-614277 | eco_20261120_091653_2376724-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 6.0 | last meaningful line 4.9 h ago (249/351 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 6.0 | last meaningful line 3.6 h ago (249/322 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 6.9 | repair_TNS best 72075 last 72075 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | tt_setup_repair | 6.9 | repair_Violations best 4141 last 4239 rows 103 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 5_1_grt | 7.1 | repair_TNS best 1.00578e+06 last 1.00578e+06 rows 10 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | 5_1_grt | 10.5 | last meaningful line 0.1 h ago (207/213 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | postcts_gate_TT | 13.1 | last meaningful line 0.0 h ago (1029/1029 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | 5_2_route | 13.1 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | so_3188870_ff_40256 | so_3188870_ff_40256 | stage_odb_cap | 0.9 | last meaningful line 0.8 h ago (1097/1097 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | so_3188870_tt_40256 | so_3188870_tt_40256 | stage_odb_cap | 0.9 | last meaningful line 0.8 h ago (1097/1097 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | so_3859242_ff_32268 | so_3859242_ff_32268 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1005/1005 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_3859242_tt_32268 | so_3859242_tt_32268 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1005/1005 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 22.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 56.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 32.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 33.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 7.0 | last meaningful line 0.6 h ago (1371/1371 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2831053 | col_h10_r0_p4__t1 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 22.6 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 22.6 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 22.6 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 17.1 | drt_violations best 17194 last 17194 rows 2 | before-window best 122546, window best 17194 | PROGRESS: drt_violations improved 86.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 18.6 | drt_violations best 10756 last 10756 rows 15 | before-window best 16045, window best 10756 | PROGRESS: drt_violations improved 33.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 18.3 | drt_violations best 7619 last 7619 rows 17 | before-window best 10304, window best 7619 | PROGRESS: drt_violations improved 26.1 % in window |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (5728/5728 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (5714/5714 lines) | PROGRESS: log still growing |  |
| epyc7 | prd-residual-i2r-1167548 | residual-i2r | 5_2_route | 6.4 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 6.0 | last meaningful line 4.8 h ago (249/308 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | 5_2_route | 19.9 | drt_violations best 43 last 43 rows 45 | before-window best 247, window best 43 | PROGRESS: drt_violations improved 82.6 % in window |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 15.0 | last meaningful line 0.0 h ago (910/910 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 12.9 | last meaningful line 0.0 h ago (768/768 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 14.5 | last meaningful line 0.0 h ago (912/912 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (832/832 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (778/778 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 10.5 | last meaningful line 0.0 h ago (926/926 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 10.5 | last meaningful line 0.0 h ago (914/914 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 10.5 | last meaningful line 0.0 h ago (882/882 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (778/778 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 13.7 | last meaningful line 0.0 h ago (889/889 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (777/777 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (777/777 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 14.1 | last meaningful line 0.0 h ago (902/902 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (777/777 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 13.0 | last meaningful line 0.0 h ago (777/777 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (778/778 lines) | PROGRESS: log still growing |  |
