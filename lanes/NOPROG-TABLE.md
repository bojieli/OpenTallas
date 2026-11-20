# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 09:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 15, 'YOUNG': 113, 'NO-DATA': 5, 'KEEP': 2, 'EXCLUDED': 7, 'PROGRESS': 37}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | 5_2_route | 11.8 | drt_violations best 59723 last 59723 rows 1 | before-window best 59723, window best 59723 | NO-PROGRESS: drt_violations best 59723 vs 59723 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 11.0 | grt rounds 4 overflow 5:62 -> 10:91 -> 15:25 -> 20:8 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 21.8 | grt rounds 5 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33130 -> 25:38341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 21.8 | grt rounds 4 overflow 5:35892 -> 10:23163 -> 15:21368 -> 20:20290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 10.6 | grt rounds 3 overflow 5:43291 -> 10:27534 -> 15:25376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 19.9 | grt rounds 5 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3247 -> 25:3339 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 18.1 | grt rounds 4 overflow 5:47612 -> 10:31129 -> 15:29680 -> 20:30528 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 11.6 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | GRT-LABEL: DESIGN-FAIL: overflow 8426 at round 10 > 1000 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 14.3 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 134.9 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 134.9 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 11.4 | grt rounds 3 overflow 5:29114 -> 10:25683 -> 15:21703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 10.8 | grt rounds 3 overflow 5:27810 -> 10:12039 -> 15:6927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 19.9 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 11.8 | grt rounds 2 overflow 5:46995 -> 10:41355 | GRT-LABEL: DESIGN-FAIL: overflow 41355 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 6.3 | grt rounds 3 overflow 5:11862 -> 10:11222 -> 15:10201 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 6.2 | last meaningful line 1.6 h ago (1369/1369 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1602/1602 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2831053 | col_h10_r0_p4__t1 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1678/1678 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3989312 | col_h10_r1__t1 | 5_1_grt | 3.3 | last meaningful line 1.0 h ago (199/214 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1639/1639 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-4014190 | col_h10_r1__t1 | 5_1_grt | 3.3 | last meaningful line 1.0 h ago (199/216 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1747/1747 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3560691 | col_h10_r1__t1 | 5_1_grt | 3.4 | last meaningful line 1.0 h ago (199/217 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1640/1640 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | tt_setup_repair_grt | 3.5 | repair_Viol best 781 last 781 rows 629 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | 5_2_route | 8.5 | drt_violations best 7249 last 7249 rows 3 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1558/1558 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1025/1025 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1770/1770 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | 5_2_route | 8.7 | drt_violations best 13404 last 13404 rows 2 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 11.0 | repair_Viol best 222 last 222 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1333/1333 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1628/1628 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1277/1277 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | 5_2_route | 3.4 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 12.0 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 12.0 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 2_1_floorplan | 10.9 | repair_Viol best 45452 last 45452 rows 864 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 2_1_floorplan | 11.0 | repair_Viol best 54713 last 54713 rows 914 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | 2_1_floorplan | 11.2 | repair_Viol best 45668 last 45668 rows 1087 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-3763736 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (357/357 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_2_route | 8.4 | drt_violations best 29470 last 29470 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 5.5 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-fin-3762223 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (346/346 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 9.1 | last meaningful line 0.8 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 9.2 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 9.2 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_2_route | 9.2 | drt_violations best 97439 last 97439 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_2_route | 9.2 | last meaningful line 0.8 h ago (288/289 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_2_route | 9.5 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_2_route | 9.2 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_2_route | 9.2 | drt_violations best 82734 last 82734 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_2_route | 9.2 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_2_route | 9.2 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_2_route | 9.2 | drt_violations best 83025 last 83025 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t16-3746725 | serdes__t16 | stage_odb_cap | 0.2 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cl503337ff__padE0-3741211 | sle_ctl | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1425/1425 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | pregrt_ff_hold | 0.2 | repair_TNS best 113744 last 113744 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 15.8 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | kvcore-pcfh_-2846360 | kvcore-pcfh_ | 5_1_grt | 0.8 | repair_TNS best 334.337 last 334.337 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | otc-2848231-29567 | 2848231 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc7 | phscan-1854121 | phscan | 5_2_route | 0.7 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_2_route | 8.3 | drt_violations best 22529 last 22529 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 4.2 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_161628_1023465-i1t-2964619 | eco_20261120_161628_1023465-i1t | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (135/135 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1167548 | residual-i2r | 5_2_route | 5.9 | drt_violations best 18566 last 18566 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | so_3956260_ff_16509 | so_3956260_ff_16509 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (192/192 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_3956260_tt_16509 | so_3956260_tt_16509 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (192/192 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-3269452 | cbf_q00 | 2_1_floorplan | 0.3 | repair_Viol best 1128 last 1128 rows 504 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-cbf_q00_s2-1902764 | cbf_q00_s2 | 2_1_floorplan | 0.5 | repair_Viol best 1128 last 1128 rows 725 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 5_1_grt | 11.2 | last meaningful line 0.0 h ago (201/204 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | postcts_gate_FF | 12.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 0.5 | last meaningful line 0.1 h ago (8/8 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | tt_setup_repair | 0.4 | repair_Viol best 1325 last 1325 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_2_route | 11.6 | drt_violations best 74773 last 74773 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | 3_3_place_gp | 0.4 | overflow best 0.352 last 0.3685 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 11.1 | drt_violations best 84302 last 84302 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 11.4 | drt_violations best 81753 last 81753 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (196/206 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-1885956 | col_h9_r2__t1 | 3_3_place_gp | 0.4 | overflow best 0.1992 last 0.1992 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_2_route | 11.8 | drt_violations best 60304 last 60304 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-control_r2-1882631 | control_r2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4359/4359 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-grouped_r2-3317228 | grouped_r2 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (4398/4398 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 4_1_cts | 11.0 | last meaningful line 0.1 h ago (6434/6434 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-1210047 | kv3_hub_Wo | 3_3_place_gp | 2.2 | overflow best 0.6513 last 0.6513 rows 11 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (22/22 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_5_place_dp | 10.6 | last meaningful line 1.3 h ago (119/119 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.5175 last 0.5175 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | tt_setup_repair | 0.3 | repair_Violations best 1221 last 1304 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3285005 | ot_s81sl_leaf__t40 | 3_3_place_gp | 0.3 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8849 last 0.8989 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | tt_setup_repair | 0.3 | repair_Violations best 1075 last 2772 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 11.8 | last meaningful line 2.3 h ago (216/225 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | pregrt_ff_hold | 11.1 | repair_Violations best 483 last 541 rows 24 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v2__cl6740750e-3309324 | sle_fw_v2 | 2_3_floorplan_tapcell | 0.3 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | postcts_gate_TT | 12.0 | last meaningful line 0.0 h ago (1522/1522 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | postcts_gate_FF | 12.3 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-1908466 | slw_fe_v2 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8537f156-3287968 | slw_fw_v2 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | postcts_gate_TT | 13.0 | last meaningful line 0.1 h ago (416/416 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | postcts_gate_TT | 13.0 | last meaningful line 0.2 h ago (725/725 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | postcts_gate_FF | 13.4 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | 5_1_grt | 10.8 | repair_Viol best 54 last 54 rows 65 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | 2_1_floorplan | 9.7 | repair_Viol best 54816 last 54816 rows 1233 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 2_1_floorplan | 10.2 | repair_Viol best 55518 last 55518 rows 1207 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 28.6 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_2_route | 8.4 | drt_violations best 650 last 650 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 5.5 | last meaningful line 4.3 h ago (249/308 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 5.5 | last meaningful line 4.4 h ago (249/351 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 5.5 | last meaningful line 3.1 h ago (249/322 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | so_1681667_ff_13763 | so_1681667_ff_13763 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | so_1681667_tt_13763 | so_1681667_tt_13763 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | cw9a-cw9b | cw9a-cw9b | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | tt_setup_repair | 6.1 | repair_Violations best 4725 last 4864 rows 79 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | tt_setup_repair | 6.1 | repair_Viol best 1192 last 1192 rows 224 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 5_1_grt | 6.3 | repair_TNS best 1.00996e+06 last 1.00996e+06 rows 7 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | 2_1_floorplan | 12.3 | repair_Viol best 54729 last 54729 rows 884 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | so_2849929_ff_8824 | so_2849929_ff_8824 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1090/1090 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_2849929_tt_8824 | so_2849929_tt_8824 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1090/1090 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_2857847_ff_27032 | so_2857847_ff_27032 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1094/1094 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_2857847_tt_27032 | so_2857847_tt_27032 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1094/1094 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_3188870_ff_40256 | so_3188870_ff_40256 | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (1097/1097 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_3188870_tt_40256 | so_3188870_tt_40256 | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (1097/1097 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 21.8 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 21.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 40.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 56.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 69.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 39.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 56.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 32.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 32.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 21.8 | drt_violations best 20 last 20 rows 51 | before-window best 72, window best 20 | PROGRESS: drt_violations improved 72.2 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 21.8 | drt_violations best 20 last 20 rows 51 | before-window best 72, window best 20 | PROGRESS: drt_violations improved 72.2 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 21.8 | drt_violations best 20 last 20 rows 51 | before-window best 72, window best 20 | PROGRESS: drt_violations improved 72.2 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (4850/4850 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (795/795 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | pregrt_ff_hold | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | pregrt_ff_hold | 0.2 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 16.6 | drt_violations best 17194 last 17194 rows 2 | before-window best 122546, window best 17194 | PROGRESS: drt_violations improved 86.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 18.1 | drt_violations best 10756 last 10756 rows 15 | before-window best 16560, window best 10756 | PROGRESS: drt_violations improved 35.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 17.8 | drt_violations best 7619 last 7619 rows 17 | before-window best 10304, window best 7619 | PROGRESS: drt_violations improved 26.1 % in window |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5428/5428 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5424/5424 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 19.2 | last meaningful line 0.0 h ago (1143/1143 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 14.2 | last meaningful line 0.0 h ago (865/865 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 12.2 | last meaningful line 0.0 h ago (724/724 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (868/868 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 12.5 | last meaningful line 0.0 h ago (787/787 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (733/733 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (881/881 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (869/869 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (917/917 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (837/837 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (805/805 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (733/733 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 12.9 | last meaningful line 0.0 h ago (845/845 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | stage_odb_cap | 16.3 | last meaningful line 0.0 h ago (974/974 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (733/733 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (733/733 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (733/733 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 13.4 | last meaningful line 0.0 h ago (857/857 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 12.5 | last meaningful line 0.0 h ago (747/747 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (732/732 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (732/732 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (732/732 lines) | PROGRESS: log still growing |  |
