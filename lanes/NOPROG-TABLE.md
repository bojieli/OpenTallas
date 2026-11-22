# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 15:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 2, 'GRT-LABEL': 45, 'NO-DATA': 9, 'YOUNG': 113, 'KEEP': 2, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-coll_core-3827287 | coll_core | tt_setup_repair_grt | 16.2 | last meaningful line 0.0 h ago (21/21 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -512.73 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 24.2 | last meaningful line 21.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 21.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 15.8 | last meaningful line 8.0 h ago (233/1712 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (FAM-S81-LEPE-4 decides; |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | tt_setup_repair | 6.6 | repair_Violations best 253 last 253 rows 102 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -852.99 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 14.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 10.2 | grt rounds 4 overflow 5:22539 -> 10:21664 -> 15:15614 -> 20:13398 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 53.7 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 10.2 | grt rounds 3 overflow 5:29001 -> 10:26780 -> 15:24876 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 10.1 | grt rounds 3 overflow 5:59362 -> 10:66624 -> 15:56340 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 68.1 | grt rounds 6 overflow 5:9414 -> 10:5163 -> 15:3613 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-3487466-21488 | 3487466 | 5_1_grt | 1.1 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:59446 -> 10:64367 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 0.6 | grt rounds 4 overflow 5:33831 -> 10:32112 -> 15:29676 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: overflow 32112 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:7392 -> 10:5019 -> 15:3621 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 10.4 | grt rounds 4 overflow 5:5714 -> 10:3404 -> 15:2651 -> 20:2469 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:32368 -> 10:23713 -> 15:20435 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:24072 -> 10:16574 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:32852 -> 10:27052 -> 15:20655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 10.4 | grt rounds 4 overflow 5:10045 -> 10:3730 -> 15:2731 -> 20:2771 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:56686 -> 10:35827 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 47.5 | grt rounds 3 overflow 5:65447 -> 10:66805 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 52.4 | grt rounds 3 overflow 5:61609 -> 10:62172 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 41.8 | grt rounds 4 overflow 5:58312 -> 10:48607 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 41.8 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 51.6 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42859 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 41.3 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 16.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 10.1 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-994857 | slw_st_a_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:21080 -> 10:15696 | GRT-LABEL: DESIGN-FAIL: overflow 15696 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 7.1 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 7.8 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:35677 -> 10:16162 -> 15:8042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl501e5681-661733 | ot_s81sl_leaf__t54 | 5_1_grt | 1.3 | grt rounds 2 overflow 5:17755 -> 10:7921 | GRT-LABEL: DESIGN-FAIL: overflow 7921 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 10.4 | grt rounds 4 overflow 5:33424 -> 10:30944 -> 15:23760 -> 20:20154 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 10.4 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 11.4 | grt rounds 3 overflow 5:63320 -> 10:33517 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 10.2 | grt rounds 4 overflow 5:33084 -> 10:3323 -> 15:1561 -> 20:909 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 10.2 | grt rounds 4 overflow 5:33301 -> 10:3290 -> 15:1523 -> 20:1038 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 10.2 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 10.2 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 10.2 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 10.2 | grt rounds 3 overflow 5:56176 -> 10:51245 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 10.2 | grt rounds 3 overflow 5:34972 -> 10:2857 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:83696 -> 10:70 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 4.5 | grt rounds 3 overflow 5:7202 -> 10:738 -> 15:476 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 7.9 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 4.5 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t57-grt-1468238 | ot-s81sl-leaf--t57-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 7.5 | drt_violations best 1385 last 1389 rows 31 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 7.5 | repair_Viol best 1776 last 1776 rows 59 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 7.4 | drt_violations best 363722 last 363722 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-307240 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 2.4 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_2_route | 12.1 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | generate_abstract | 16.5 | last meaningful line 0.2 h ago (663/663 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-210420-13766 | 210420 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-574718-9437 | 574718 | signoff | 2.3 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 4.5 | drt_violations best 66325 last 66325 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i2-3565304 | eco_20261122_144137_2274607-i2 | 5_2_route | 1.1 | drt_violations best 4303 last 4303 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1-693810 | eco_20261122_165114_3352738-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (233/893 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1t-873116 | eco_20261122_223531_3628570-i1t | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-3109130 | dsdv_slice_c1x_C__t1 | 3_4_place_resized | 2.7 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-3659100 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t13-3636335 | ot_s81sl_leaf__t13 | 3_3_place_gp | 0.6 | last meaningful line 0.3 h ago (155/155 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 0.6 | repair_TNS best 754066 last 754066 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t73-3636691 | ot_s81sl_leaf__t73 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | generate_abstract | 17.0 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 17.0 | drt_violations best 136712 last 136712 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 6_report | 17.0 | last meaningful line 0.2 h ago (1062/1062 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 17.0 | drt_violations best 16588 last 16588 rows 2 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | generate_abstract | 17.0 | last meaningful line 0.1 h ago (555/555 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-2738927-2977 | 2738927 | signoff | 1.0 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 2.6 | drt_violations best 84758 last 84758 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_125009_2644377-i1t-3775722 | eco_20261122_125009_2644377-i1t | 5_2_route | 2.4 | drt_violations best 59992 last 59992 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_140001_4005935-i1-2236985 | eco_20261122_140001_4005935-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_3835265_ff_81331 | so_3835265_ff_81331 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | so_3835265_tt_81331 | so_3835265_tt_81331 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | so_648173_ff_8919 | so_648173_ff_8919 | signoff_20261122_151410_3684072 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_648173_tt_8919 | so_648173_tt_8919 | signoff_20261122_151410_3684072 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_80751_ff_18750 | so_80751_ff_18750 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | so_80751_tt_18750 | so_80751_tt_18750 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 | col_h9_r0_p6__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 29643.1 last 29643.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (235/274 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 111710 last 111710 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | 3_1_place_gp_skip_io | 2.0 | overflow best 0.5728 last 0.5728 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t9-4106886 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_C__t1-4102769 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.5 | last meaningful line 0.3 h ago (201/210 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (2743/2743 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t29-3865255 | ot_s81sl_leaf__t29 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3622/3622 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3967105 | ot_s81sl_leaf__t46 | 4_1_cts | 0.5 | last meaningful line -0.0 h ago (4391/4391 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3844958 | ot_s81sl_leaf__t55 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3609/3609 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t61-3925881 | ot_s81sl_leaf__t61 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3887/3887 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 10.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 3_4_place_resized | 1.0 | repair_Remaining best 23543 last 23543 rows 297 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | pregrt_ff_hold | 2.0 | repair_TNS best 14472.7 last 14472.7 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | postcts_gate_TT | 1.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | pregrt_ff_hold | 1.9 | repair_TNS best 55416 last 55416 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6030/6030 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-470365 | slw_su_l1 | 3_3_place_gp | 0.2 | overflow best 0.2055 last 0.2055 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | otc-1004368-22302 | 1004368 | signoff | 2.0 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 7.4 | last meaningful line 4.0 h ago (562/562 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 7.4 | last meaningful line 4.0 h ago (562/562 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 7.3 | last meaningful line 4.0 h ago (562/562 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 2.2 | last meaningful line 2.1 h ago (3/3 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1t-2527780 | eco_20261122_215654_330309-i1t | 5_2_route | 1.3 | last meaningful line 0.2 h ago (250/251 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1t-2658286 | eco_20261122_220050_168828-i1t | 5_2_route | 1.2 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t15-grt-3345853 | ot-s81sl-leaf--t15-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_2_route | 7.6 | last meaningful line 0.1 h ago (284/285 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_2_route | 7.0 | drt_violations best 63616 last 63616 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 7.8 | last meaningful line 4.0 h ago (210/219 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_4_place_resized | 10.0 | last meaningful line 0.8 h ago (449/449 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | postcts_gate_FF | 12.3 | last meaningful line 0.1 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 12.3 | last meaningful line 0.2 h ago (1234/1240 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 7.9 | drt_violations best 31724 last 31724 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | prd-eco-i2r-1852378 | eco-i2r | 5_2_route | 2.1 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-dsdv-slice-c1x-C--t4-grt-2866461 | dsdv-slice-c1x-C--t4-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | tt_setup_repair_grt | 10.6 | repair_Viol best 2461 last 2461 rows 53 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | 3_1_place_gp_skip_io | 2.1 | overflow best 0.2422 last 0.2422 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-566156 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 1.3 | overflow best 0.6149 last 0.6149 rows 25 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 5_1_grt | 1.3 | last meaningful line 0.2 h ago (1660/1710 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-670966 | ot_s81sl_leaf__t58 | pregrt_ff_hold | 1.3 | repair_TNS best 7613.78 last 7613.78 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | pregrt_ff_hold | 1.3 | repair_TNS best 174460 last 174460 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | generate_abstract | 16.9 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3911/3911 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_1_grt | 1.3 | last meaningful line 0.2 h ago (206/582 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 1.0 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | otc-2867161-32206 | 2867161 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-1586484 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 3.0 | drt_violations best 15272 last 15272 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1-1472150 | eco_20261122_174935_2347281-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (272/273 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1-577405 | eco_20261122_180231_342380-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_2_route | 1.5 | last meaningful line 0.0 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_223653_314236-i1-2039775 | eco_20261122_223653_314236-i1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (234/998 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 10.2 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_2_route | 7.8 | drt_violations best 48217 last 48217 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_2_route | 8.8 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 10.5 | last meaningful line 0.2 h ago (265/349 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 10.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1675980 | col_h9_r0_p4__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3226/3226 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-1659288 | col_h9_r1__t1 | 3_2_place_iop | 0.2 | last meaningful line -0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 10.2 | drt_violations best 1385 last 1385 rows 13 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4696 last 0.4696 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-1671863 | col_h9_r2__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2211/2211 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 10.2 | last meaningful line 0.5 h ago (208/217 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 16.1 | drt_violations best 88173 last 88173 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 17.0 | drt_violations best 88269 last 88269 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 6.5 | drt_violations best 33922 last 33922 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (240/1424 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 54510.5 last 54510.5 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 10.1 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 10.9 | last meaningful line 0.5 h ago (288/289 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 8.0 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 8.4 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_2_route | 2.3 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 6.6 | last meaningful line 1.0 h ago (208/211 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 4.6 | last meaningful line 0.5 h ago (36/36 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.4 | last meaningful line 0.3 h ago (198/204 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 6.6 | repair_TNS best 80460.1 last 80460.1 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 10.2 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (209/210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (202/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 5_1_grt | 4.5 | last meaningful line 1.3 h ago (207/216 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-617275 | ot_s81sl_leaf__t50 | 5_1_grt | 2.3 | last meaningful line 1.0 h ago (202/211 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 4.5 | last meaningful line 1.8 h ago (208/215 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 6_report | 4.5 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 8.0 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__cl774acf45__pvea45273b-3781481 | col_h9_r2__t1 | pregrt_ff_hold | 0.6 |  | KEEP: col_h9_r2__t1__cl774acf45__pvea45273b	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | prd-eco_20261120_150342_478824-i1-1690412 | eco_20261120_150342_478824-i1 | 5_2_route | 0.8 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 16.6 | drt_violations best 4374 last 7221 rows 21 | before-window best 4374, window best 7221 | PROGRESS: drt_violations: falling inside the active iteration (7221 -> 6780) |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 7.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 7.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 8.7 | last meaningful line 0.0 h ago (918/918 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 60.5 | last meaningful line 2.1 h ago (1564/1564 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 17.0 | drt_violations best 17053 last 17053 rows 3 | before-window best 136145, window best 17053 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 7.6 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 16.0 | drt_violations best 26965 last 26965 rows 2 | before-window best 161798, window best 26965 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 11.0 | drt_violations best 19062 last 19062 rows 7 | before-window best 128949, window best 19062 | PROGRESS: drt_violations improved 85.2 % in window |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 12.9 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-682008 | col_h9_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 8.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 16.0 | drt_violations best 2973 last 18181 rows 18 | before-window best 5991, window best 2973 | PROGRESS: drt_violations improved 50.4 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | pregrt_ff_hold | 8.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 17.7 | drt_violations best 1719 last 1719 rows 16 | before-window best 5193, window best 1719 | PROGRESS: drt_violations improved 66.9 % in window |  |
| intel2 | dpkit-native59-3804419 | native59 | tt_setup_repair | 4.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.5 | grt_hold_TNS best 3315.1 last 3315.1 rows 2 | before-window best 6059.8, window best 3315.1 | PROGRESS: grt_hold_TNS improved 45.3 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
