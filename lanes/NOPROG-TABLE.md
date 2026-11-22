# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 13:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 2, 'GRT-LABEL': 49, 'YOUNG': 125, 'NO-DATA': 7, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 22.2 | last meaningful line 20.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | tt_setup_repair | 8.2 | repair_Violations best 4693 last 4693 rows 25 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -642.37 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 46.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -3266.53 ps (< -300, gate TT >= -42); job age 4 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 12.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 14.5 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 6.8 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:22539 -> 10:21664 -> 15:15614 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 51.9 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:29001 -> 10:29678 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:59362 -> 10:66624 -> 15:56502 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 66.3 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3613 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 10.2 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 10.8 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:40789 -> 10:31945 -> 15:27448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:19437 -> 10:19849 -> 15:17373 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 8.2 | grt rounds 5 overflow 5:2659 -> 10:1890 -> 15:1296 -> 20:1316 -> 25:676 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:65491 -> 10:65132 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:59610 -> 10:62798 -> 15:54882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:7441 -> 10:4871 -> 15:3941 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:5714 -> 10:3404 -> 15:2651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:32368 -> 10:23432 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:40043 -> 10:36201 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:24286 -> 10:18853 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:32869 -> 10:27052 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:10045 -> 10:3730 -> 15:2868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:61754 -> 10:36825 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:37003 -> 10:36397 -> 15:29681 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:35763 -> 10:34510 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 45.5 | grt rounds 3 overflow 5:65447 -> 10:65234 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 50.4 | grt rounds 3 overflow 5:61609 -> 10:63105 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 39.8 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 39.8 | grt rounds 3 overflow 5:60910 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 49.6 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42859 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 39.3 | grt rounds 4 overflow 5:114153 -> 10:70617 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 14.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:29534 -> 10:27331 -> 15:29724 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 5.6 | grt rounds 3 overflow 5:91555 -> 10:41 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 8.6 | grt rounds 8 overflow 15:172 -> 20:100 -> 25:77 -> 30:31 -> 35:4 -> 40:9 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 4 -> 9 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:35677 -> 10:16162 -> 15:8830 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:33424 -> 10:30944 -> 15:23958 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 8.4 | grt rounds 6 overflow 5:2796 -> 10:1155 -> 15:762 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: overflow 1155 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:61421 -> 10:36554 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:33084 -> 10:3323 -> 15:1699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:33301 -> 10:3290 -> 15:1742 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 8.2 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:2533 -> 10:1498 -> 15:842 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:56176 -> 10:51245 | GRT-LABEL: DESIGN-FAIL: overflow 51245 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 8.2 | grt rounds 3 overflow 5:43340 -> 10:3595 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 6.0 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 5.8 | drt_violations best 1394 last 1394 rows 8 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 5.7 | last meaningful line 1.4 h ago (1319/2573 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1092189 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 5.7 | last meaningful line 0.4 h ago (281/282 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_2_route | 6.4 | drt_violations best 56324 last 56324 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-307240 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | postcts_gate_FF | 10.3 | last meaningful line 0.1 h ago (915/915 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 6_report | 14.6 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 14.8 | drt_violations best 111085 last 111085 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | generate_abstract | 14.7 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1991144-20067 | 1991144 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-574718-9437 | 574718 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i2t-3252184 | eco_20261122_144137_2274607-i2t | 5_2_route | 1.2 | drt_violations best 11920 last 11920 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_2_route | 4.3 | drt_violations best 5337 last 5337 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_2_route | 8.2 | drt_violations best 59763 last 59763 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-3109130 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3584924 | dsdv_slice_c1x_C__t5 | 1_2_yosys | 2.0 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 14.8 | drt_violations best 132730 last 132730 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 14.8 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 14.8 | drt_violations best 113702 last 113702 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 14.8 | drt_violations best 108992 last 108992 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 14.7 | last meaningful line 0.4 h ago (278/279 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 14.7 | drt_violations best 114889 last 114889 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 14.7 | drt_violations best 136145 last 136145 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 14.7 | drt_violations best 100356 last 100356 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_3_fillcell | 14.7 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 6_report | 14.7 | last meaningful line 0.1 h ago (773/773 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-2412624-22295 | 2412624 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-2669299-29018 | 2669299 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1-4075679 | eco_20261122_051545_3846533-i1 | 5_2_route | 3.4 | drt_violations best 21611 last 21611 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (241/1414 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_125009_2644377-i1t-3775722 | eco_20261122_125009_2644377-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t40--cl86ea32b3--sid5S-grt-526627 | ot-s81sl-leaf--t40--cl86ea32b3--sid5S-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 6.2 | last meaningful line 0.2 h ago (1598/1629 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-223971 | col_h10_r1__t1 | 3_4_place_resized | 0.3 | repair_Remaining best 95105 last 95105 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_2_route | 6.3 | drt_violations best 55788 last 55788 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-1845665 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.3 | overflow best 0.1985 last 0.1985 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.5 | repair_TNS best 21132 last 21132 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 6_report | 6.2 | last meaningful line 0.1 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t37-811259 | ot_s81sl_leaf__t37 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-phy__t1-880036 | phy__t1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 8.1 | last meaningful line 0.1 h ago (225/229 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 1_1_yosys_canonicalize | 0.0 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | 5_1_grt | 6.1 | last meaningful line 0.1 h ago (1294/2525 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | eco-abs-2874138 | eco-abs | generate_abstract | 0.9 | last meaningful line 0.4 h ago (608/608 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 5.4 | last meaningful line 2.0 h ago (562/562 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 5.4 | last meaningful line 2.0 h ago (562/562 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 5.3 | last meaningful line 2.0 h ago (562/562 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-777563-14379 | 777563 | qwen_compute.t.slw_st_b_v1__cl6357f1cc__pv6ace3e48 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_3364677_ff_15271 | so_3364677_ff_15271 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_2_route | 6.0 | drt_violations best 55845 last 55845 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | tt_setup_repair_grt | 8.9 | repair_Violations best 609 last 609 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 5.6 | last meaningful line 2.0 h ago (211/242 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 14.0 | drt_violations best 161798 last 161798 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 9.0 | drt_violations best 128949 last 128949 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | tt_setup_repair_grt | 5.0 | repair_Viol best 2292 last 2292 rows 87 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-3684875 | dsdv_slice_c1x_C__t6 | selrange | 2.3 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 5.8 | last meaningful line 2.0 h ago (210/216 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_3_place_gp | 8.0 | overflow best 0.0998 last 0.0998 rows 44 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 10.9 | drt_violations best 69171 last 69171 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 10.3 | repair_TNS best 839.191 last 839.191 rows 3 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 5.8 | last meaningful line 0.3 h ago (207/216 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | 5_1_grt | 4.9 | last meaningful line 1.5 h ago (207/216 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t40__clf8bbdae1-1333111 | ot_s81sl_leaf__t40 | 3_3_place_gp | 0.3 | overflow best 0.6159 last 0.6159 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | otc-2073965-24436 | 2073965 | drc | 0.1 | last meaningful line -0.0 h ago (2479/2479 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco-i2r-1852378 | eco-i2r | 5_1_grt | 0.1 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-2672119 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.3105 last 0.3431 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-175162 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.3 h ago (126/126 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2714333 | ot_s81sl_leaf__t44 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t13-425517 | serdes__t13 | 3_3_place_gp | 3.4 | overflow best 0.6326 last 0.6326 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 14.9 | drt_violations best 27985 last 27985 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 6_report | 14.9 | last meaningful line 0.1 h ago (814/814 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_2_route | 15.5 | drt_violations best 10559 last 10559 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | generate_abstract | 14.9 | last meaningful line 0.1 h ago (239/239 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 6.2 | drt_violations best 97752 last 97752 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (267/268 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_2_route | 3.3 | drt_violations best 56590 last 56590 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1t-805483 | eco_20261122_180231_342380-i1t | 5_2_route | 3.2 | drt_violations best 8542 last 8542 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | so_2825191_ff_90575 | so_2825191_ff_90575 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_2825191_tt_90575 | so_2825191_tt_90575 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_2949217_ff_47972 | so_2949217_ff_47972 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_2949217_tt_47972 | so_2949217_tt_47972 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_1_grt | 8.2 | last meaningful line 1.0 h ago (212/221 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_2_route | 5.8 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_2_route | 8.2 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | postcts_gate_FF | 6.8 | last meaningful line -0.0 h ago (22220/22220 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 8.5 | last meaningful line 2.3 h ago (210/229 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 8.2 | last meaningful line 0.1 h ago (225/225 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-458411 | col_h9_r0_p4__t1 | 3_4_place_resized | 0.7 | repair_Remaining best 30222 last 30222 rows 83 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 8.2 | drt_violations best 67967 last 67967 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-1239799 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 8.2 | drt_violations best 63708 last 63708 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | 3_4_place_resized | 4.9 | repair_Remaining best 111223 last 111223 rows 237 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 8.2 | last meaningful line 0.3 h ago (195/201 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | hold_gate | 6.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t60-1586390 | ot_s81sl_leaf__t60 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8433 last 0.8462 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 14.1 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 15.0 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | otc-2013262-11973 | 2013262 | dump | 0.0 | last meaningful line 0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 3.2 | last meaningful line 3.1 h ago (3/3 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 4.5 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.5 | overflow best 0.386 last 0.386 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 8.1 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 8.9 | last meaningful line 0.1 h ago (151/151 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 6.0 | repair_Remaining best 154953 last 154953 rows 79 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 6.0 | repair_TNS best 8.545 last 8.545 rows 14 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 1_2_yosys | 2.6 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.4 | repair_TNS best 16322.9 last 16322.9 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 4_1_cts | 4.6 | last meaningful line 0.1 h ago (6351/6351 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 4.6 | last meaningful line 0.1 h ago (2535/2535 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-230881 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 3137 last 3137 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2278295 | kv3_io_ft | 5_2_route | 1.3 | last meaningful line 0.1 h ago (228/229 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 3_5_place_dp | 2.5 | last meaningful line 0.3 h ago (111/111 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 10.5 | repair_TNS best 9103.81 last 9103.81 rows 11 | YOUNG: evidence 5.5 h < 6 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 8.2 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 0.5 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 3_3_place_gp | 0.3 | last meaningful line 0.1 h ago (89/89 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 2.5 | last meaningful line 0.6 h ago (204/213 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | pregrt_ff_hold | 2.5 | last meaningful line 0.1 h ago (62/62 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-617275 | ot_s81sl_leaf__t50 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3097/3097 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (157/157 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 4_1_cts | 2.5 | last meaningful line 0.2 h ago (4938/4938 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (241/242 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 6.0 | last meaningful line 0.3 h ago (258/259 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (4588/4588 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | otc-385798-22291 | 385798 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 54.2 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 14.8 | drt_violations best 4374 last 7940 rows 20 | before-window best 4691, window best 4374 | PROGRESS: drt_violations improved 6.8 % in window |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 7.0 | last meaningful line 0.0 h ago (709/709 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 58.2 | last meaningful line 2.6 h ago (1562/1562 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_1_grt | 8.4 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 14.2 | drt_violations best 2539 last 3663 rows 19 | before-window best 15442, window best 2539 | PROGRESS: drt_violations improved 83.6 % in window |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 10.3 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 24.2 | drt_violations best 43315 last 43315 rows 16 | before-window best 45146, window best 43315 | PROGRESS: drt_violations improved 4.1 % in window |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 14.0 | drt_violations best 2973 last 2973 rows 17 | before-window best 14336, window best 2973 | PROGRESS: drt_violations improved 79.3 % in window |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 8.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1738735 | serdes__t14 | 3_5_place_dp | 1.9 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 15.7 | drt_violations best 1939 last 1939 rows 15 | before-window best 11187, window best 1939 | PROGRESS: drt_violations improved 82.7 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 11.2 | drt_violations best 1 last 30 rows 42 | before-window best 58, window best 1 | PROGRESS: drt_violations improved 98.3 % in window |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 13.8 | last meaningful line 6.0 h ago (233/1712 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2931852 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
