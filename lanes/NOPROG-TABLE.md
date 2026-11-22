# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 11:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 1, 'GRT-LABEL': 55, 'YOUNG': 138, 'NO-DATA': 9, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 23.4 | drt_violations best 48926 last 48926 rows 16 | before-window best 49344, window best 48926 | NO-PROGRESS: drt_violations best 48926 vs 49344 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 20.7 | last meaningful line 19.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 19.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | tt_setup_repair | 7.0 | repair_Violations best 1675 last 1894 rows 49 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -1501.86 ps (< -300, gate TT >= -42); job a | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 7.9 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 11.2 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 13.0 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:22539 -> 10:21940 -> 15:15764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 50.4 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:38895 -> 10:27872 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:60876 -> 10:66966 -> 15:56502 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 64.8 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3613 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 8.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 9.3 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 7.0 | grt rounds 3 overflow 5:40789 -> 10:31798 -> 15:27448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:19437 -> 10:19849 -> 15:17415 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 6.9 | grt rounds 4 overflow 5:9096 -> 10:2439 -> 15:1748 -> 20:1556 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 6.9 | grt rounds 4 overflow 5:2659 -> 10:1890 -> 15:1296 -> 20:1316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:69154 -> 10:65194 -> 15:61747 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 6.9 | grt rounds 2 overflow 5:65491 -> 10:65132 | GRT-LABEL: DESIGN-FAIL: overflow 65132 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:66235 -> 10:63465 -> 15:54882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 6.9 | grt rounds 4 overflow 5:32004 -> 10:27400 -> 15:23081 -> 20:21475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:33831 -> 10:32112 -> 15:29676 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:7687 -> 10:5183 -> 15:3941 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:5714 -> 10:3404 -> 15:2649 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:31459 -> 10:24947 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:39998 -> 10:36201 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:28701 -> 10:18853 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: overflow 18853 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:32869 -> 10:26686 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:10375 -> 10:3860 -> 15:2868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:61754 -> 10:36825 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:59287 -> 10:3527 -> 15:1004 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:37003 -> 10:36397 -> 15:29898 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:35763 -> 10:34931 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 44.0 | grt rounds 3 overflow 5:64017 -> 10:65234 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 48.9 | grt rounds 3 overflow 5:60065 -> 10:63105 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 38.3 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 38.3 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 48.1 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42813 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 37.8 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 12.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:34248 -> 10:27118 -> 15:30143 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:3567 -> 10:316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 7.1 | grt rounds 8 overflow 15:172 -> 20:100 -> 25:77 -> 30:31 -> 35:4 -> 40:9 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 4 -> 9 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:36431 -> 10:17425 -> 15:8830 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:33647 -> 10:30839 -> 15:23958 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 6.9 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: overflow 1268 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 8.1 | grt rounds 3 overflow 5:62744 -> 10:36554 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:8404 -> 10:286 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 7.0 | grt rounds 3 overflow 5:46985 -> 10:3500 -> 15:1699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 7.0 | grt rounds 3 overflow 5:47106 -> 10:3457 -> 15:1742 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 6.9 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 45.5 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 6.9 | grt rounds 2 overflow 5:56176 -> 10:51245 | GRT-LABEL: DESIGN-FAIL: overflow 51245 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 6.9 | grt rounds 2 overflow 5:43340 -> 10:3595 | GRT-LABEL: DESIGN-FAIL: overflow 3595 at round 10 > 1000 |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 7.4 | grt rounds 4 overflow 5:8485 -> 10:200 -> 15:22 -> 20:7 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 4.5 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 4.3 | drt_violations best 53797 last 53797 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 4.2 | last meaningful line 0.8 h ago (272/1292 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 4.2 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 4.1 | repair_TNS best 207473 last 207473 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 4.2 | repair_TNS best 207751 last 207751 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 5.5 | last meaningful line 0.0 h ago (473/473 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | tt_setup_measure_grt | 8.8 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 13.1 | drt_violations best 92764 last 92764 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 13.3 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 13.2 | drt_violations best 19277 last 19277 rows 2 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 6_report | 13.2 | last meaningful line 0.1 h ago (494/494 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | otc-264663-3675 | 264663 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-890585-26544 | 890585 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_2_route | 2.8 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-fin-3804162 | fin | 6_report | 0.1 | last meaningful line 0.1 h ago (337/337 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 7.0 | drt_violations best 94 last 94 rows 6 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 7.0 | drt_violations best 13126 last 13126 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_2_route | 7.0 | last meaningful line 0.2 h ago (252/253 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3584924 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-3239393 | ot_s81sl_leaf__t16 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-4139161 | ot_s81sl_leaf__t65 | 3_3_place_gp | 0.5 | overflow best 0.6127 last 0.6127 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-serdes__t16-3331703 | serdes__t16 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.9972 last 0.9972 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 13.5 | drt_violations best 132730 last 132730 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 13.5 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 13.5 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 13.5 | drt_violations best 108992 last 108992 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 13.5 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 13.5 | drt_violations best 114889 last 114889 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 13.5 | last meaningful line 0.5 h ago (288/289 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 13.5 | last meaningful line 0.2 h ago (287/288 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 13.5 | drt_violations best 95974 last 95974 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 13.5 | drt_violations best 70104 last 70104 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 6_report | 8.7 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-192453-23804 | 192453 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-3760575-13201 | 3760575 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1-4075679 | eco_20261122_051545_3846533-i1 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | so_835565_ff_83728 | so_835565_ff_83728 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_835565_tt_83728 | so_835565_tt_83728 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_934066_ff_88325 | so_934066_ff_88325 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_934066_tt_88325 | so_934066_tt_88325 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-col-h9-r0-p4--t1--clcb2fbfe8--pvec137455-grt-1019975 | col-h9-r0-p4--t1--clcb2fbfe8--pvec137455-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-serdes--t1--clfe1f0815-grt-1110728 | serdes--t1--clfe1f0815-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3998212 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.7 | overflow best 0.4481 last 0.4504 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 4.5 | repair_Viol best 2530 last 2530 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_2_route | 4.8 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-1020026 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.3676 last 0.3812 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 5_2_route | 4.7 | drt_violations best 27295 last 27295 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_1_grt | 6.9 | last meaningful line 0.2 h ago (229/391 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t1__clb45db5be-2593606 | serdes__t1 | 3_3_place_gp | 1.4 | overflow best 0.5024 last 0.5024 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 6_report | 13.5 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 13.5 | drt_violations best 8100 last 8100 rows 3 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 3.9 | last meaningful line 0.5 h ago (562/562 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 3.9 | last meaningful line 0.5 h ago (562/562 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 3.8 | last meaningful line 0.5 h ago (562/562 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_183009_2671271-i1t-3023419 | eco_20261122_183009_2671271-i1t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t40--clf8bbdae1-grt-1435566 | ot-s81sl-leaf--t40--clf8bbdae1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (211/212 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | 5_1_grt | 4.4 | last meaningful line 0.5 h ago (203/210 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | tt_setup_repair_grt | 4.5 | repair_Viol best 2299 last 2299 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 4.1 | last meaningful line 1.3 h ago (210/229 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 4.1 | last meaningful line 0.5 h ago (211/219 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 12.5 | last meaningful line 0.2 h ago (291/292 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-1556168 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 353 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 7.5 | drt_violations best 128949 last 128949 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-3684875 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 4.3 | last meaningful line 0.5 h ago (210/213 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_3_place_gp | 6.5 | overflow best 0.0998 last 0.0998 rows 44 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 9.4 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 8.8 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (193/206 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t57-629868 | ot_s81sl_leaf__t57 | 5_1_grt | 3.4 | last meaningful line 1.0 h ago (204/212 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | 5_1_grt | 3.7 | last meaningful line 0.5 h ago (208/214 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t9-595588 | ot_s81sl_leaf__t9 | 5_1_grt | 3.4 | last meaningful line 1.3 h ago (207/216 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t3-22213 | serdes__t3 | 3_5_place_dp | 2.0 | repair_Violations best 46913 last 46913 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slice_station__t29__cl2e5c855a-1433829 | slice_station__t29 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9979 last 0.9979 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | postcts_gate_TT | 4.4 | last meaningful line -0.0 h ago (1261/1261 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1429268-21126 | 1429268 | qwen_compute.t.sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1526707-23014 | 1526707 | front_route_r3 | 0.1 | last meaningful line 0.0 h ago (985/985 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1731149-27445 | 1731149 | drc | 0.0 | last meaningful line -0.0 h ago (1846/1846 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-2877912 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-eng--t1-grt-3804615 | eng--t1-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-3663582 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.2753 last 0.2868 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-serdes__t13-425517 | serdes__t13 | 2_4_floorplan_pdn | 1.9 | last meaningful line 1.3 h ago (130/130 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 13.4 | drt_violations best 140478 last 140478 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 13.4 | drt_violations best 107296 last 107296 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_2_route | 14.0 | drt_violations best 93581 last 93581 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 13.8 | drt_violations best 12894 last 12894 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 13.4 | drt_violations best 11537 last 11537 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 13.4 | drt_violations best 99319 last 99319 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | otc-4096999-2937 | 4096999 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 4.7 | drt_violations best 97752 last 97752 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_2_route | 1.8 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1t-805483 | eco_20261122_180231_342380-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_1_grt | 7.0 | last meaningful line 0.3 h ago (162/162 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-2528442 | col_h10_r1__t1 | 3_3_place_gp | 0.4 | overflow best 0.3387 last 0.344 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-1997851 | col_h10_r1__t1 | 3_5_place_dp | 0.6 | repair_Violations best 855987 last 855987 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | 5_1_grt | 5.0 | last meaningful line 0.8 h ago (203/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | postcts_gate_FF | 4.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_2_route | 7.0 | last meaningful line 0.4 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 7.2 | last meaningful line 1.0 h ago (210/219 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 7.0 | last meaningful line 0.3 h ago (212/215 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2852789 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.3139 last 0.3139 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 7.0 | last meaningful line 0.4 h ago (267/268 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 7.0 | drt_violations best 63708 last 63708 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 4_1_cts | 7.0 | last meaningful line 0.0 h ago (2609/2609 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | 2_4_floorplan_pdn | 3.6 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 7.0 | repair_TNS best 7898.96 last 7898.96 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 5.5 | last meaningful line 0.5 h ago (7671/7671 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 6.9 | last meaningful line 0.3 h ago (207/213 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2678008 | ot_s81sl_leaf__t53 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (235/235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t54__cl501e5681-2051161 | ot_s81sl_leaf__t54 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-1738735 | serdes__t14 | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 12.8 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2282799 | slw_st_a_v1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 13.7 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-2017350-30882 | 2017350 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 1.9 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 3.2 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 6.6 | last meaningful line 1.0 h ago (205/223 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 4.5 | last meaningful line 0.8 h ago (1280/1321 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_1_grt | 4.9 | repair_TNS best 953.683 last 953.683 rows 9 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3606558 | coll_ftm | 5_2_route | 2.9 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 4_1_cts | 3.1 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 5.0 | last meaningful line 0.3 h ago (37/37 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 12.3 | last meaningful line 4.5 h ago (233/1712 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 4_1_cts | 3.1 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 3.1 | last meaningful line 0.3 h ago (25/25 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 3_3_place_gp | 1.0 | overflow best 0.2979 last 0.4954 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2931852 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 1.1 | repair_TNS best 449417 last 449417 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.0 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.7 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 1.0 | repair_Violations best 10939 last 10939 rows 60 | YOUNG: stage 1.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 5_1_grt | 4.5 | last meaningful line 1.7 h ago (205/214 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5291/5291 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (206/210 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4237/4237 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3651324 | slice_station__t12 | 5_2_route | 1.1 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-slice_station__t30__cl1653104c-3832946 | slice_station__t30 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (229/230 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | postcts_gate_TT | 4.5 | last meaningful line 0.0 h ago (1382/1382 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1753749-5942 | 1753749 | - | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 52.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 13.3 | drt_violations best 4374 last 10441 rows 19 | before-window best 4948, window best 4374 | PROGRESS: drt_violations improved 11.6 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 57.0 | last meaningful line 1.4 h ago (1562/1562 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 13.5 | repair_TNS best 22801.4 last 22801.4 rows 7 | before-window best 27175.4, window best 22801.4 | PROGRESS: repair_TNS improved 16.1 % in window |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 5_1_grt | 4.9 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-611680 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 5.0 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 7.4 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 12.7 | drt_violations best 2539 last 2539 rows 17 | before-window best 100260, window best 2539 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 8.8 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 4.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 22.7 | drt_violations best 43966 last 43966 rows 15 | before-window best 45146, window best 43966 | PROGRESS: drt_violations improved 2.6 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 12.3 | drt_violations best 7 last 7 rows 53 | before-window best 10021, window best 7 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 12.8 | drt_violations best 3681 last 3681 rows 15 | before-window best 87099, window best 3681 | PROGRESS: drt_violations improved 95.8 % in window |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t2-2411650 | serdes__t2 | 3_5_place_dp | 2.1 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 14.4 | drt_violations best 2439 last 2439 rows 14 | before-window best 11187, window best 2439 | PROGRESS: drt_violations improved 78.2 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 9.9 | drt_violations best 1 last 30 rows 42 | before-window best 58, window best 1 | PROGRESS: drt_violations improved 98.3 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t4-3639183 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 5_1_grt | 1.0 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
