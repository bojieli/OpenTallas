# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 14:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 1, 'GRT-LABEL': 49, 'YOUNG': 124, 'NO-DATA': 15, 'KEEP': 1, 'PROGRESS': 16}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 23.0 | last meaningful line 21.3 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 21.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 24.9 | drt_violations best 43315 last 43315 rows 16 | before-window best 43966, window best 43315 | NO-PROGRESS: drt_violations best 43315 vs 43966 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 12.2 | drt_violations best 1 last 30 rows 42 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 14.5 | last meaningful line 6.7 h ago (233/1712 lines) | NO-PROGRESS: no new non-iteration log line for 6.7 h | REPORT-ONLY: lane-own kit (FAM-S81-LEPE-4 decides; |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2931852 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -429.51 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 13.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 15.2 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:22539 -> 10:21664 -> 15:15614 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 52.7 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:29001 -> 10:26780 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 9.1 | grt rounds 3 overflow 5:59362 -> 10:66624 -> 15:56340 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 67.1 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3613 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-3487466-21488 | 3487466 | 5_1_grt | 0.1 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:40789 -> 10:31945 -> 15:26894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:19437 -> 10:19849 -> 15:17373 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 9.2 | grt rounds 6 overflow 5:2659 -> 10:1890 -> 15:1296 -> 20:1316 -> 25:676 -> 30:286 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:59446 -> 10:65132 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:59610 -> 10:62798 -> 15:54882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:7392 -> 10:5019 -> 15:3941 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:5714 -> 10:3404 -> 15:2651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:32368 -> 10:23713 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:40043 -> 10:36246 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:24286 -> 10:18739 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:32869 -> 10:27052 -> 15:20655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:10045 -> 10:3730 -> 15:2731 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:56686 -> 10:36825 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 46.2 | grt rounds 3 overflow 5:65447 -> 10:65234 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 51.2 | grt rounds 3 overflow 5:61609 -> 10:63105 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 40.6 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 40.6 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 50.3 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42859 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 40.1 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 14.9 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:29534 -> 10:27331 -> 15:29724 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 8.9 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 6.4 | grt rounds 3 overflow 5:91555 -> 10:41 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 6.5 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 9.4 | grt rounds 8 overflow 15:172 -> 20:100 -> 25:77 -> 30:31 -> 35:4 -> 40:9 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 4 -> 9 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:35677 -> 10:16162 -> 15:8830 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:33424 -> 10:30944 -> 15:23760 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 9.1 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:61421 -> 10:33517 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:33084 -> 10:3323 -> 15:1561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:33301 -> 10:3290 -> 15:1523 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 9.2 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 9.2 | grt rounds 4 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:56176 -> 10:51245 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: overflow 51245 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:34972 -> 10:3595 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 6.7 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 6.7 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 3.2 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 6.5 | drt_violations best 1385 last 1389 rows 19 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 6.5 | repair_Viol best 1776 last 1776 rows 25 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 6.4 | last meaningful line 0.3 h ago (287/288 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_2_route | 7.1 | drt_violations best 6741 last 6741 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-307240 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_2_route | 11.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 15.5 | drt_violations best 16793 last 16793 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | generate_abstract | 15.5 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | kqc-sle_cland_w517_n_s10_2_freg_synth0-3474412 | sle_cland_w517_n_s10_2_freg_synth0 | 6_1_merge | 0.1 | last meaningful line 0.0 h ago (2/2 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3736044-27056 | 3736044 | geom.client | 0.0 | last meaningful line 0.0 h ago (8/8 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-574718-9437 | 574718 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-2889585 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 3.5 | drt_violations best 66325 last 66325 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i2-3565304 | eco_20261122_144137_2274607-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | so_3123525_ff_86469 | so_3123525_ff_86469 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc10 | so_3123525_tt_86469 | so_3123525_tt_86469 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-3109130 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.5 h ago (126/126 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3584924 | dsdv_slice_c1x_C__t5 | 3_4_place_resized | 3.0 | repair_Remaining best 263378 last 263378 rows 63 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t9-1971291 | ot_s81sl_leaf__t9 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 15.8 | drt_violations best 136712 last 136712 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 15.8 | drt_violations best 16382 last 16382 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 15.7 | drt_violations best 109923 last 109923 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 15.7 | drt_violations best 16838 last 16838 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 15.7 | drt_violations best 136145 last 136145 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 15.7 | drt_violations best 13466 last 13466 rows 2 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 1.3 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_125009_2644377-i1t-3775722 | eco_20261122_125009_2644377-i1t | 5_2_route | 1.1 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | so_1255285_ff_47352 | so_1255285_ff_47352 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_1255285_tt_47352 | so_1255285_tt_47352 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_2127161_ff_25526 | so_2127161_ff_25526 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (522/522 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_2127161_tt_25526 | so_2127161_tt_25526 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (522/522 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-dsdv-slice-kv512-C--t1-dump-2521343 | dsdv-slice-kv512-C--t1-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-dsdv-slice-kv512-C--t1-grt-2521343 | dsdv-slice-kv512-C--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-1848639 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 46622.5 last 46622.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 67179.5 last 67179.5 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 0.8 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.3 | last meaningful line 0.1 h ago (200/203 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | tt_setup_repair_grt | 9.1 | last meaningful line 0.0 h ago (642/642 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5783/5783 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5487/5487 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4296/4296 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-994857 | slw_st_a_v2 | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (256/1260 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-1004368-22302 | 1004368 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | otc-1305471-15069 | 1305471 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-1940430-23511 | 1940430 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 6.1 | last meaningful line 2.8 h ago (562/562 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 6.1 | last meaningful line 2.8 h ago (562/562 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 6.1 | last meaningful line 2.8 h ago (562/562 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 1.0 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1t-2527780 | eco_20261122_215654_330309-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_1412167_ff_60050 | so_1412167_ff_60050 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (612/612 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_1412167_tt_60050 | so_1412167_tt_60050 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (612/612 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_2426988_ff_72399 | so_2426988_ff_72399 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_2426988_tt_72399 | so_2426988_tt_72399 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t40--cl86ea32b3-grt-4063129 | ot-s81sl-leaf--t40--cl86ea32b3-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_2_route | 6.7 | drt_violations best 55845 last 55845 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 6.4 | repair_Remaining best 155446 last 155446 rows 159 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 14.8 | drt_violations best 161798 last 161798 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 9.8 | drt_violations best 33015 last 33015 rows 3 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_2_route | 5.8 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-3684875 | dsdv_slice_c1x_C__t6 | 3_3_place_gp | 3.1 | last meaningful line 0.0 h ago (158/158 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 6.5 | last meaningful line 2.8 h ago (210/217 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_3_place_gp | 8.7 | overflow best 0.0998 last 0.0998 rows 44 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 11.7 | drt_violations best 69171 last 69171 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 11.1 | last meaningful line 0.2 h ago (1155/1161 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 11.1 | last meaningful line 0.2 h ago (1111/1124 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 6.7 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco-i2r-1852378 | eco-i2r | 5_2_route | 0.9 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc1b82625-566573 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 277 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-682008 | col_h9_r1__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 0.9 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-175162 | dsdv_slice_c1x_C__t4 | 2_4_floorplan_pdn | 2.1 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-566156 | dsdv_slice_iq_C__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3376/3376 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl431c660f-648073 | ot_s81sl_leaf__t25 | 3_1_place_gp_skip_io | 0.0 | overflow best 0.7119 last 0.7162 rows 19 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t30-640940 | ot_s81sl_leaf__t30 | 3_3_place_gp | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl501e5681-661733 | ot_s81sl_leaf__t54 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-670966 | ot_s81sl_leaf__t58 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (587/587 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t75-250684 | ot_s81sl_leaf__t75 | 3_2_place_iop | 0.2 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 6_report | 16.2 | last meaningful line 0.1 h ago (404/404 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3333/3333 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-3698275-17901 | 3698275 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 6.9 | drt_violations best 17985 last 17985 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_2_route | 3.5 | drt_violations best 83470 last 83470 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_3_fillcell | 4.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1-577405 | eco_20261122_180231_342380-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_3595715_ff_3427 | so_3595715_ff_3427 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc9 | so_3595715_tt_3427 | so_3595715_tt_3427 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc9 | so_4128351_ff_76511 | so_4128351_ff_76511 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | so_4128351_tt_76511 | so_4128351_tt_76511 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_1_grt | 9.2 | last meaningful line 0.2 h ago (488/519 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_2_route | 6.8 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_2_route | 9.2 | drt_violations best 87699 last 87699 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 9.5 | last meaningful line 3.3 h ago (210/236 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 9.2 | last meaningful line 0.0 h ago (478/480 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 9.2 | drt_violations best 15243 last 15243 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 9.2 | drt_violations best 603 last 603 rows 4 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 9.2 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 15.1 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 16.0 | drt_violations best 88269 last 88269 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 4.2 | last meaningful line 4.1 h ago (3/3 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-3034506-22939 | 3034506 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | otc-3134459-5102 | 3134459 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 5.5 | drt_violations best 33922 last 33922 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | hold_gate | 1.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 8.9 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 9.6 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 6.7 | last meaningful line 0.9 h ago (329/1385 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | postcts_gate_TT | 7.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (441/447 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 5.4 | last meaningful line 0.3 h ago (158/158 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_3_place_gp | 3.4 | overflow best 0.8263 last 0.8263 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 7.1 | repair_Violations best 1068 last 1069 rows 88 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | tt_setup_repair | 5.4 | repair_Violations best 15896 last 15896 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 5.4 | last meaningful line 0.1 h ago (2880/2880 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2278295 | kv3_io_ft | generate_abstract | 2.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 4_1_cts | 3.2 | last meaningful line 0.0 h ago (5238/5238 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.0 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 1.2 | repair_Violations best 12359 last 12359 rows 11 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 3.2 | last meaningful line 1.3 h ago (204/218 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (207/208 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-617275 | ot_s81sl_leaf__t50 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 3.3 | last meaningful line 0.5 h ago (208/211 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (5055/5055 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 5_2_route | 3.2 | drt_violations best 8654 last 8654 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 6.7 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | pregrt_ff_hold | 3.3 | repair_TNS best 6450.92 last 6450.92 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 54.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 15.6 | drt_violations best 4374 last 7940 rows 20 | before-window best 4691, window best 4374 | PROGRESS: drt_violations improved 6.8 % in window |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 7.7 | last meaningful line 0.0 h ago (816/816 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 59.2 | last meaningful line 0.9 h ago (1564/1564 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 15.8 | drt_violations best 22829 last 22829 rows 2 | before-window best 132730, window best 22829 | PROGRESS: drt_violations improved 82.8 % in window |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 15.8 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 14.9 | drt_violations best 2539 last 2962 rows 20 | before-window best 4926, window best 2539 | PROGRESS: drt_violations improved 48.5 % in window |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 15.6 | drt_violations best 39 last 39 rows 14 | before-window best 140478, window best 39 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | ap-ageom-kw-col-h9-r2--t1--cl774acf45--pve3ab90e7-grt-3784138 | col-h9-r2--t1--cl774acf45--pve3ab90e7-grt | 3_5_place_dp | 0.2 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 15.0 | drt_violations best 2973 last 18181 rows 18 | before-window best 8258, window best 2973 | PROGRESS: drt_violations improved 64.0 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 16.7 | drt_violations best 1939 last 1939 rows 15 | before-window best 7622, window best 1939 | PROGRESS: drt_violations improved 74.6 % in window |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 11.3 | repair_TNS best 6960.36 last 6960.36 rows 8 | before-window best 9041.62, window best 6960.36 | PROGRESS: repair_TNS improved 23.0 % in window |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
