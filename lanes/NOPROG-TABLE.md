# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 14:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 1, 'GRT-LABEL': 49, 'YOUNG': 120, 'NO-DATA': 6, 'KEEP': 2, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 23.7 | last meaningful line 21.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 21.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 15.3 | last meaningful line 7.5 h ago (233/1712 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (FAM-S81-LEPE-4 decides; |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | tt_setup_repair | 6.1 | repair_Viol best 8167 last 8167 rows 5 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -852.99 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 13.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 15.7 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:22539 -> 10:21664 -> 15:15614 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 53.2 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:29001 -> 10:26780 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 9.6 | grt rounds 3 overflow 5:59362 -> 10:66624 -> 15:56340 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 67.6 | grt rounds 6 overflow 5:9414 -> 10:5561 -> 15:3613 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-3487466-21488 | 3487466 | 5_1_grt | 0.6 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:40789 -> 10:31945 -> 15:26894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:59446 -> 10:65132 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:59610 -> 10:62798 -> 15:54963 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:7392 -> 10:5019 -> 15:3941 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:5714 -> 10:3404 -> 15:2651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:32368 -> 10:23713 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:40043 -> 10:36246 -> 15:31833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:24072 -> 10:18739 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:32869 -> 10:27052 -> 15:20655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:10045 -> 10:3730 -> 15:2731 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 9.7 | grt rounds 3 overflow 5:56686 -> 10:36825 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 47.0 | grt rounds 3 overflow 5:65447 -> 10:65234 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 51.9 | grt rounds 3 overflow 5:61609 -> 10:63105 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 41.3 | grt rounds 4 overflow 5:58312 -> 10:48607 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 41.3 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 51.1 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42859 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 40.8 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 15.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 9.9 | grt rounds 4 overflow 5:29534 -> 10:27331 -> 15:29724 -> 20:29740 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 9.6 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-994857 | slw_st_a_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:21080 -> 10:15696 | GRT-LABEL: DESIGN-FAIL: overflow 15696 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 7.3 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 10.1 | grt rounds 8 overflow 15:172 -> 20:100 -> 25:77 -> 30:31 -> 35:4 -> 40:9 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 4 -> 9 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:35677 -> 10:16162 -> 15:8042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:33424 -> 10:30944 -> 15:23760 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 9.9 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 11.1 | grt rounds 3 overflow 5:63320 -> 10:33517 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 10.0 | grt rounds 4 overflow 5:33084 -> 10:3323 -> 15:1561 -> 20:909 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 10.0 | grt rounds 4 overflow 5:33301 -> 10:3290 -> 15:1523 -> 20:1038 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 9.9 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 10.0 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 9.9 | grt rounds 5 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:56176 -> 10:51245 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:34972 -> 10:2857 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:83696 -> 10:70 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 4.0 | grt rounds 3 overflow 5:7202 -> 10:946 -> 15:476 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 4.0 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 7.0 | drt_violations best 1385 last 1394 rows 26 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 7.0 | repair_Viol best 1776 last 1776 rows 42 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 6.9 | drt_violations best 363722 last 363722 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-307240 | dsdv_slice_c1x_C__t10 | 1_2_yosys | 1.9 | last meaningful line 0.0 h ago (424/424 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t57-170995 | ot_s81sl_leaf__t57 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_2_route | 11.6 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 6_report | 16.0 | last meaningful line 0.0 h ago (656/656 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-210420-13766 | 210420 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-574718-9437 | 574718 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 4.0 | drt_violations best 66325 last 66325 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i2-3565304 | eco_20261122_144137_2274607-i2 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-fin-2889585 | fin | 6_report | 0.4 | last meaningful line 0.0 h ago (371/371 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | so_3935872_ff_26815 | so_3935872_ff_26815 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc10 | so_3935872_tt_26815 | so_3935872_tt_26815 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | ap-ageom-kw-dsdv-slice-c1x-C--t5-grt-2947712 | dsdv-slice-c1x-C--t5-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-2811067 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.3948 last 0.3989 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-3109130 | dsdv_slice_c1x_C__t1 | 2_4_floorplan_pdn | 1.9 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t9-1971291 | ot_s81sl_leaf__t9 | 3_3_place_gp | 0.6 | overflow best 0.1901 last 0.1901 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 16.3 | drt_violations best 136712 last 136712 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 16.3 | drt_violations best 16382 last 16382 rows 2 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | generate_abstract | 16.3 | last meaningful line 0.0 h ago (683/683 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 16.2 | drt_violations best 109923 last 109923 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 16.2 | drt_violations best 136145 last 136145 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 6_report | 16.2 | last meaningful line -0.0 h ago (742/742 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-2738927-2977 | 2738927 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i2t-2918971 | eco_20261122_051545_3846533-i2t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 1.8 | drt_violations best 84758 last 84758 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_125009_2644377-i1t-3775722 | eco_20261122_125009_2644377-i1t | 5_2_route | 1.6 | drt_violations best 59992 last 59992 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_140001_4005935-i1-2236985 | eco_20261122_140001_4005935-i1 | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (240/261 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h9-r2--t1--clb8d86cd5--pv8d57997d-grt-3914220 | col-h9-r2--t1--clb8d86cd5--pv8d57997d-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3018400 | col_h10_r1__t1 | 3_3_place_gp | 0.5 | overflow best 0.3684 last 0.3858 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-1848639 | col_h9_r2__t1 | 5_1_grt | 1.1 | grt_overflow best 160 last 160 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_1_grt | 1.4 | grt_overflow best 167 last 167 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | 1_2_yosys | 1.5 | last meaningful line 0.2 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.0 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_sys_c-3993762 | kv3_sys_c | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t29-3865255 | ot_s81sl_leaf__t29 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t36-3026276 | ot_s81sl_leaf__t36 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7602 last 0.7602 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3023399 | ot_s81sl_leaf__t39 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5626 last 0.5626 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3967105 | ot_s81sl_leaf__t46 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3844958 | ot_s81sl_leaf__t55 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t61-3925881 | ot_s81sl_leaf__t61 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 2_2_floorplan_macro | 0.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | tt_setup_repair | 1.5 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-3480572 | sle_st_a_v1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t24__cl66b71008-3013022 | slice_station__t24 | 5_1_grt | 0.5 | repair_TNS best 0.268 last 0.268 rows 2 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1004368-22302 | 1004368 | signoff | 1.5 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 6.9 | last meaningful line 3.5 h ago (562/562 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 6.9 | last meaningful line 3.5 h ago (562/562 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 6.8 | last meaningful line 3.5 h ago (562/562 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc7 | otc-3282639-6845 | 3282639 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 1.7 | last meaningful line 1.6 h ago (3/3 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | otc-4033488-31818 | 4033488 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i1t-2527780 | eco_20261122_215654_330309-i1t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1t-2658286 | eco_20261122_220050_168828-i1t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | postcts_gate_TT | 7.1 | last meaningful line 0.0 h ago (463/463 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 15.5 | drt_violations best 26965 last 26965 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 10.5 | drt_violations best 19807 last 19807 rows 5 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_2_route | 6.5 | drt_violations best 63616 last 63616 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-3684875 | dsdv_slice_c1x_C__t6 | 3_5_place_dp | 3.8 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 7.3 | last meaningful line 3.5 h ago (210/218 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_4_place_resized | 9.5 | last meaningful line 0.3 h ago (449/449 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 12.4 | drt_violations best 69171 last 69171 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | tt_setup_repair_grt | 11.8 | repair_Viol best 558 last 558 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 7.4 | drt_violations best 31724 last 31724 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | otc-2302088-15512 | 2302088 | drc | 0.0 | last meaningful line 0.0 h ago (1360/1360 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco-i2r-1852378 | eco-i2r | 5_2_route | 1.6 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p5--t1--pvc1b82625-grt-1970476 | col-h9-r0-p5--t1--pvc1b82625-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t75-grt-2136578 | ot-s81sl-leaf--t75-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-682008 | col_h9_r1__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 38088.9 last 38088.9 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (214/214 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-175162 | dsdv_slice_c1x_C__t4 | 3_4_place_resized | 2.9 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-566156 | dsdv_slice_iq_C__t1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.3828 last 0.3828 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 0.8 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl501e5681-661733 | ot_s81sl_leaf__t54 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (198/203 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-670966 | ot_s81sl_leaf__t58 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4310/4310 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 6_report | 16.4 | last meaningful line 0.1 h ago (1072/1072 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3139/3139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | pregrt_ff_hold | 0.8 | repair_TNS best 6724.33 last 6724.33 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | pregrt_ff_hold | 0.8 | repair_TNS best 6394.45 last 6394.45 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 0.5 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 0.8 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_2_route | 4.3 | drt_violations best 12821 last 12821 rows 2 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 2.5 | drt_violations best 15272 last 15272 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1-1472150 | eco_20261122_174935_2347281-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (263/698 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1-577405 | eco_20261122_180231_342380-i1 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_223653_314236-i1-2039775 | eco_20261122_223653_314236-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_1343129_ff_75611 | so_1343129_ff_75611 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc9 | so_1343129_tt_75611 | so_1343129_tt_75611 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | postcts_gate_FF | 10.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_2_route | 7.5 | drt_violations best 48217 last 48217 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 10.2 | last meaningful line 4.0 h ago (210/242 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | postcts_gate_TT | 10.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 1386 last 1386 rows 8 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 10.0 | last meaningful line 0.3 h ago (208/214 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 15.8 | drt_violations best 88173 last 88173 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 16.7 | drt_violations best 88269 last 88269 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-3134459-5102 | 3134459 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 6.2 | drt_violations best 33922 last 33922 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 54510.5 last 54510.5 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 9.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 10.4 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 7.5 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 7.9 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_2_route | 1.8 | last meaningful line 0.1 h ago (235/236 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 6.1 | last meaningful line 0.5 h ago (208/211 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 4.1 | last meaningful line 0.1 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.9 | last meaningful line 0.2 h ago (148/148 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 6.1 | repair_TNS best 80460.1 last 80460.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 4_1_cts | 4.0 | last meaningful line 0.0 h ago (5409/5409 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.7 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 5_1_grt | 4.0 | last meaningful line 0.8 h ago (207/213 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-617275 | ot_s81sl_leaf__t50 | 5_1_grt | 1.8 | last meaningful line 0.5 h ago (202/208 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 4.0 | last meaningful line 1.3 h ago (208/214 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | pregrt_ff_hold | 4.0 | last meaningful line 0.1 h ago (42/42 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 5_2_route | 4.0 | drt_violations best 8654 last 8654 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 7.5 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__cl774acf45__pvea45273b-3781481 | col_h9_r2__t1 | 4_1_cts | 0.1 |  | KEEP: col_h9_r2__t1__cl774acf45__pvea45273b	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | prd-eco_20261120_150342_478824-i1-1690412 | eco_20261120_150342_478824-i1 | 5_1_grt | 0.3 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 16.1 | drt_violations best 4374 last 7221 rows 21 | before-window best 4374, window best 7221 | PROGRESS: drt_violations: falling inside the active iteration (7221 -> 6988) |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 8.2 | last meaningful line 0.0 h ago (864/864 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 59.7 | last meaningful line 1.4 h ago (1564/1564 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 16.3 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 16.2 | drt_violations best 415 last 415 rows 4 | before-window best 114889, window best 415 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 | col_h9_r0_p6__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | tt_setup_repair_grt | 9.9 | repair_Violations best 0 last 0 rows 5 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | tt_setup_repair | 1.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | 5_1_grt | 1.1 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | tt_setup_repair | 1.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | otc-3745440-8558 | 3745440 | place | 0.1 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 7.1 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 15.7 | drt_violations best 2539 last 2592 rows 22 | before-window best 3629, window best 2539 | PROGRESS: drt_violations improved 30.0 % in window |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 11.8 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 8.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 15.8 | drt_violations best 2973 last 18181 rows 18 | before-window best 7225, window best 2973 | PROGRESS: drt_violations improved 58.9 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | pregrt_ff_hold | 8.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 17.4 | drt_violations best 1719 last 1719 rows 16 | before-window best 5193, window best 1719 | PROGRESS: drt_violations improved 66.9 % in window |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.0 | repair_TNS best 4962.86 last 4962.86 rows 5 | before-window best 6059.79, window best 4962.86 | PROGRESS: repair_TNS improved 18.1 % in window |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
