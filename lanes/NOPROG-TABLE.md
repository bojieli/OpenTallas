# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 14:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 1, 'GRT-LABEL': 51, 'YOUNG': 117, 'NO-DATA': 9, 'KEEP': 1, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 15.8 | drt_violations best 4374 last 7221 rows 21 | before-window best 4374, window best 7221 | NO-PROGRESS: drt_violations best 7221 vs 4374 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-HROOT-R1 decides |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 23.2 | last meaningful line 21.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 21.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 24.9 | drt_violations best 43315 last 43315 rows 16 | before-window best 43966, window best 43315 | NO-PROGRESS: drt_violations best 43315 vs 43966 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 12.2 | drt_violations best 1 last 30 rows 42 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 14.8 | last meaningful line 7.0 h ago (233/1712 lines) | NO-PROGRESS: no new non-iteration log line for 7.0 h | REPORT-ONLY: lane-own kit (FAM-S81-LEPE-4 decides; |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2931852 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -429.51 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 13.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 15.5 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 7.8 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:22539 -> 10:21664 -> 15:15614 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 52.9 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:29001 -> 10:26780 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:59362 -> 10:66624 -> 15:56340 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 67.3 | grt rounds 6 overflow 5:9414 -> 10:5561 -> 15:3613 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-3487466-21488 | 3487466 | 5_1_grt | 0.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 9.5 | grt rounds 3 overflow 5:40789 -> 10:31945 -> 15:26894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:19437 -> 10:19849 -> 15:17373 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:59446 -> 10:65132 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:59610 -> 10:62798 -> 15:54963 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:7392 -> 10:5019 -> 15:3941 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:5714 -> 10:3404 -> 15:2651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:32368 -> 10:23713 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:40043 -> 10:36246 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:24286 -> 10:18739 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:32869 -> 10:27052 -> 15:20655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:10045 -> 10:3730 -> 15:2731 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:56686 -> 10:36825 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 46.5 | grt rounds 3 overflow 5:65447 -> 10:65234 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 51.4 | grt rounds 3 overflow 5:61609 -> 10:63105 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 40.8 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 40.8 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 50.6 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42859 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 40.3 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 15.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:29534 -> 10:27331 -> 15:29724 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 9.1 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 6.4 | grt rounds 3 overflow 5:91555 -> 10:41 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 6.5 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 9.6 | grt rounds 8 overflow 15:172 -> 20:100 -> 25:77 -> 30:31 -> 35:4 -> 40:9 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 4 -> 9 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:35677 -> 10:16162 -> 15:8042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:33424 -> 10:30944 -> 15:23760 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 9.4 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:61421 -> 10:33517 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:33084 -> 10:3323 -> 15:1561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:33301 -> 10:3290 -> 15:1523 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 9.2 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 9.2 | grt rounds 4 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:56176 -> 10:51245 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: overflow 51245 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 9.2 | grt rounds 3 overflow 5:34972 -> 10:3595 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 7.0 | grt rounds 2 overflow 5:83696 -> 10:70 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 3.5 | grt rounds 3 overflow 5:8238 -> 10:946 -> 15:476 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 6.9 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 7.0 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 6.8 | drt_violations best 1385 last 1388 rows 21 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 6.7 | repair_Viol best 1776 last 1776 rows 33 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 6.7 | drt_violations best 363722 last 363722 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-307240 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.7 | last meaningful line 0.5 h ago (133/133 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_2_route | 11.3 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 15.8 | drt_violations best 357 last 357 rows 4 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc10 | otc-574718-9437 | 574718 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 3.8 | drt_violations best 66325 last 66325 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i2-3565304 | eco_20261122_144137_2274607-i2 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (230/834 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-fin-2889585 | fin | 6_report | 0.1 | last meaningful line 0.1 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | so_3123525_ff_86469 | so_3123525_ff_86469 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc10 | so_3123525_tt_86469 | so_3123525_tt_86469 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc10 | so_3935872_ff_26815 | so_3935872_ff_26815 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_3935872_tt_26815 | so_3935872_tt_26815 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-3109130 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 1.7 | last meaningful line 0.7 h ago (127/127 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3584924 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 3.2 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t9-1971291 | ot_s81sl_leaf__t9 | 3_3_place_gp | 0.3 | overflow best 0.6219 last 0.6219 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 16.0 | drt_violations best 136712 last 136712 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 16.0 | drt_violations best 16382 last 16382 rows 2 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 6_report | 16.0 | last meaningful line 0.1 h ago (1014/1014 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 16.0 | drt_violations best 109923 last 109923 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 16.0 | drt_violations best 11205 last 11205 rows 3 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 16.0 | drt_violations best 136145 last 136145 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 16.0 | drt_violations best 269 last 269 rows 4 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 1.6 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_125009_2644377-i1t-3775722 | eco_20261122_125009_2644377-i1t | 5_2_route | 1.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_140001_4005935-i1-2236985 | eco_20261122_140001_4005935-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_2127161_ff_25526 | so_2127161_ff_25526 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (522/522 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | so_2127161_tt_25526 | so_2127161_tt_25526 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (522/522 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t37-grt-2808665 | ot-s81sl-leaf--t37-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3018400 | col_h10_r1__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-2713181 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.3066 last 0.3347 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.0 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t36-3026276 | ot_s81sl_leaf__t36 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3023399 | ot_s81sl_leaf__t39 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (235/235 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | tt_setup_repair_grt | 9.4 | repair_Viol best 1596 last 1596 rows 6 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5812/5812 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5843/5843 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t24__cl66b71008-3013022 | slice_station__t24 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (2170/2170 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | pregrt_ff_hold | 0.6 | repair_TNS best 300.615 last 300.615 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (4325/4325 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-994857 | slw_st_a_v2 | 5_1_grt | 1.0 | last meaningful line 0.4 h ago (256/1265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-1004368-22302 | 1004368 | signoff | 1.0 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | otc-1940430-23511 | 1940430 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 6.4 | last meaningful line 3.0 h ago (562/562 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 6.4 | last meaningful line 3.0 h ago (562/562 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 6.3 | last meaningful line 3.0 h ago (562/562 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1t-2527780 | eco_20261122_215654_330309-i1t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (229/617 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1t-2658286 | eco_20261122_220050_168828-i1t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (249/747 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
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
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc1b82625-566573 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4017 last 0.4017 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-682008 | col_h9_r1__t1 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 1.1 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-175162 | dsdv_slice_c1x_C__t4 | 3_1_place_gp_skip_io | 2.4 | overflow best 0.4177 last 0.4177 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-566156 | dsdv_slice_iq_C__t1 | 2_1_floorplan | 0.3 | repair_Viol best 8999 last 8999 rows 386 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3668/3668 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2647/2648 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl431c660f-648073 | ot_s81sl_leaf__t25 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl501e5681-661733 | ot_s81sl_leaf__t54 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2535/2535 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-670966 | ot_s81sl_leaf__t58 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 3_3_place_gp | 0.3 | last meaningful line 0.1 h ago (75/75 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t75-250684 | ot_s81sl_leaf__t75 | 3_3_place_gp | 0.5 | overflow best 0.6168 last 0.6168 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | generate_abstract | 16.5 | last meaningful line 0.1 h ago (358/358 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 3_3_place_gp | 0.3 | overflow best 0.2329 last 0.2329 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3415 last 0.3415 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3636/3636 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | 3_3_place_gp | 0.3 | overflow best 0.3432 last 0.3693 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 7.2 | drt_violations best 232 last 232 rows 4 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_2_route | 3.8 | drt_violations best 83470 last 83470 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1-577405 | eco_20261122_180231_342380-i1 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (241/538 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (194/197 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-fin-460298 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_4128351_ff_76511 | so_4128351_ff_76511 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc9 | so_4128351_tt_76511 | so_4128351_tt_76511 | signoff | 0.6 |  | NO-DATA: empty log |  |
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
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 54510.5 last 54510.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 9.1 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 9.9 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 7.0 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 7.4 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_2_route | 1.3 | last meaningful line 0.0 h ago (219/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (208/209 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_3_place_gp | 3.6 | overflow best 0.6465 last 0.6465 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | tt_setup_repair | 5.6 | repair_Violations best 321 last 373 rows 56 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 5.6 | last meaningful line 0.0 h ago (2902/2902 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 4_1_cts | 3.5 | last meaningful line 0.0 h ago (5292/5292 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.2 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 1.5 | repair_Violations best 1729 last 1729 rows 63 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (2952/2952 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 5_1_grt | 3.5 | last meaningful line 0.3 h ago (207/210 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-617275 | ot_s81sl_leaf__t50 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (202/204 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 3.5 | last meaningful line 0.8 h ago (208/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | hold_gate | 3.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 5_2_route | 3.5 | drt_violations best 8654 last 8654 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 7.0 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_3_fillcell | 55.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 8.0 | last meaningful line 0.0 h ago (836/836 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 59.5 | last meaningful line 1.1 h ago (1564/1564 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 16.0 | drt_violations best 16643 last 16643 rows 3 | before-window best 132730, window best 16643 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc7 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-1848639 | col_h9_r2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | otc-3018577-22558 | 3018577 | place | 0.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 14.9 | drt_violations best 2539 last 2962 rows 20 | before-window best 4926, window best 2539 | PROGRESS: drt_violations improved 48.5 % in window |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t30-grt-1159478 | ot-s81sl-leaf--t30-grt | 3_5_place_dp | 0.0 | repair_Violations best 0 last 0 rows 16 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 15.9 | drt_violations best 34 last 34 rows 16 | before-window best 140478, window best 34 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | ap-ageom-kw-col-h9-r2--t1--cl774acf45--pve3ab90e7-grt-3784138 | col-h9-r2--t1--cl774acf45--pve3ab90e7-grt | 3_5_place_dp | 0.2 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 15.0 | drt_violations best 2973 last 18181 rows 18 | before-window best 8258, window best 2973 | PROGRESS: drt_violations improved 64.0 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 16.7 | drt_violations best 1939 last 1939 rows 15 | before-window best 7622, window best 1939 | PROGRESS: drt_violations improved 74.6 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 7.4 | repair_Violations best 1027 last 1043 rows 143 | before-window best 50052, window best 1027 | PROGRESS: repair_Violations improved 97.9 % in window |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 11.5 | repair_TNS best 6088.46 last 6088.46 rows 11 | before-window best 9041.62, window best 6088.46 | PROGRESS: repair_TNS improved 32.7 % in window |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
