# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 10:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 3, 'GRT-LABEL': 55, 'NO-DATA': 15, 'YOUNG': 172, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 19.5 | last meaningful line 17.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 17.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 21.4 | drt_violations best 597 last 1991 rows 36 | before-window best 597, window best 1269 | NO-PROGRESS: drt_violations best 1269 vs 597 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | tt_setup_repair | 5.7 | repair_Viol best 8339 last 8339 rows 25 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -648.07 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | pregrt_ff_hold | 5.7 | last meaningful line 0.0 h ago (1451/1451 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -684.14 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | tt_setup_repair | 5.7 | repair_Violations best 13694 last 13694 rows 14 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -1143.47 ps (< -300, gate TT >= -42); job a | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 6.7 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_1_grt | 3.6 | grt rounds 2 overflow 5:3231 -> 10:234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 9.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 11.7 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:23152 -> 10:21940 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 49.2 | grt rounds 4 overflow 5:108780 -> 10:62060 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:33908 -> 10:27872 | GRT-LABEL: DESIGN-FAIL: overflow 27872 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 5.6 | grt rounds 3 overflow 5:60876 -> 10:66966 -> 15:72547 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 63.6 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3426 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 5.7 | grt rounds 6 overflow 5:5968 -> 10:452 -> 15:57 -> 20:13 -> 25:5 -> 30:1 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:40844 -> 10:37996 -> 15:27448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:19413 -> 10:19610 -> 15:17415 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:9096 -> 10:2439 -> 15:1748 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:2659 -> 10:1890 -> 15:1296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:69154 -> 10:65194 -> 15:60682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:65491 -> 10:65132 | GRT-LABEL: DESIGN-FAIL: overflow 65132 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:66235 -> 10:63465 | GRT-LABEL: DESIGN-FAIL: overflow 63465 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:29527 -> 10:22456 -> 15:17060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:32004 -> 10:27400 -> 15:23081 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:33831 -> 10:32112 -> 15:29676 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:7687 -> 10:5183 -> 15:4269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:5723 -> 10:3390 -> 15:2649 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:36793 -> 10:24947 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:39998 -> 10:37170 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:28701 -> 10:18853 | GRT-LABEL: DESIGN-FAIL: overflow 18853 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:32655 -> 10:27751 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:10375 -> 10:3860 -> 15:3468 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:61754 -> 10:36825 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:23007 -> 10:3527 | GRT-LABEL: DESIGN-FAIL: overflow 3527 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:37003 -> 10:36144 -> 15:29898 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:35319 -> 10:34931 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 42.7 | grt rounds 3 overflow 5:64017 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 47.7 | grt rounds 3 overflow 5:60065 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 37.1 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 37.1 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 46.8 | grt rounds 4 overflow 5:78032 -> 10:50077 -> 15:42813 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 36.6 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 11.4 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:34248 -> 10:29364 -> 15:30446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:9870 -> 10:488 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 6.4 | grt rounds 3 overflow 5:83933 -> 10:43 -> 15:18 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:36431 -> 10:17597 -> 15:9316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:33647 -> 10:32273 -> 15:23958 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 5.6 | grt rounds 4 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 6.9 | grt rounds 2 overflow 5:62744 -> 10:36554 | GRT-LABEL: DESIGN-FAIL: overflow 36554 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:7404 -> 10:123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:8404 -> 10:286 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:44293 -> 10:4215 -> 15:1699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:43521 -> 10:4266 -> 15:1742 | GRT-LABEL: DESIGN-FAIL: overflow 4266 at round 10 > 1000 |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 5.7 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 44.3 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:43340 -> 10:3595 | GRT-LABEL: DESIGN-FAIL: overflow 3595 at round 10 > 1000 |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 6.1 | grt rounds 4 overflow 5:8485 -> 10:200 -> 15:22 -> 20:7 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-col-h9-r0-p5--t1--pv5c8f2166-grt-3504994 | col-h9-r0-p5--t1--pv5c8f2166-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | 5_1_grt | 3.6 | last meaningful line 0.8 h ago (204/213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 3.0 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_1_grt | 2.9 | repair_Viol best 951 last 951 rows 15 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | 3_3_place_gp | 3.4 | overflow best 0.6457 last 0.6457 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | 3_3_place_gp | 3.4 | overflow best 0.723 last 0.723 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 4.0 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | 3_3_place_gp | 3.4 | overflow best 0.6363 last 0.6363 rows 24 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 2.9 | repair_TNS best 207473 last 207473 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 2.9 | repair_TNS best 207751 last 207751 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 4.2 | last meaningful line 1.3 h ago (336/336 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t55-1257352 | ot_s81sl_leaf__t55 | 3_3_place_gp | 0.8 | overflow best 0.1976 last 0.1976 rows 43 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t62-1457612 | ot_s81sl_leaf__t62 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (265/265 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1466438 | sle_hc1 | 3_3_place_gp | 0.8 | overflow best 0.305 last 0.3621 rows 98 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 11.9 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t25-1088717 | slice_station__t25 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 12.0 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 12.0 | drt_violations best 119597 last 119597 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 11.9 | drt_violations best 10462 last 10462 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | otc-2891866-5466 | 2891866 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-3374081-15985 | 3374081 | gen_lint_check | 0.1 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1-3804162 | eco_20261122_144137_2274607-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (255/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_2_route | 1.6 | last meaningful line 0.3 h ago (257/258 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-dsdv-slice-lepe-nh-mus-LP--t1-grt-2254447 | dsdv-slice-lepe-nh-mus-LP--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 5.7 | drt_violations best 60898 last 60898 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 5.7 | drt_violations best 63830 last 63830 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t33-351893 | ot_s81sl_leaf__t33 | 3_5_place_dp | 0.7 | last meaningful line -0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 5_1_grt | 5.7 | last meaningful line 1.0 h ago (207/214 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 12.3 | last meaningful line 0.5 h ago (289/290 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 12.3 | last meaningful line 0.3 h ago (136/136 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 12.3 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 12.3 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 12.3 | drt_violations best 7335 last 7335 rows 3 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 12.2 | drt_violations best 7392 last 7392 rows 3 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 12.2 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 12.2 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 12.2 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 12.2 | last meaningful line 0.0 h ago (273/274 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 12.2 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 12.2 | drt_violations best 70104 last 70104 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_2_route | 7.5 | drt_violations best 34720 last 34720 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | otc-755443-31238 | 755443 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1-4075679 | eco_20261122_051545_3846533-i1 | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (238/1831 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-fw-v1--cl9d029624-grt-2808923 | sle-fw-v1--cl9d029624-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 5_1_grt | 3.7 | last meaningful line 0.9 h ago (246/1341 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | 5_1_grt | 3.4 | repair_Remaining best 70353 last 70353 rows 132 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 3.4 | repair_Remaining best 34175 last 34175 rows 167 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1106130 | col_h9_r0_p4__t1 | 5_1_grt | 3.1 | last meaningful line 0.3 h ago (207/214 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 5_2_route | 3.5 | last meaningful line 0.1 h ago (250/251 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t10-1490841 | ot_s81sl_leaf__t10 | 3_3_place_gp | 0.6 | last meaningful line 0.3 h ago (121/121 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | 5_1_grt | 3.0 | last meaningful line 0.8 h ago (206/213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t59-2530517 | ot_s81sl_leaf__t59 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8222 last 0.848 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-serdes__t1__clb45db5be-2593606 | serdes__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (322/322 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t1__clfe1f0815-1376853 | serdes__t1 | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.1 h ago (94/94 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 12.3 | drt_violations best 12789 last 12789 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 12.3 | drt_violations best 99129 last 99129 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | generate_abstract | 6.4 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1986186-11442 | 1986186 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.6 | last meaningful line 1.5 h ago (468/468 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.6 | last meaningful line 1.5 h ago (468/468 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.6 | last meaningful line 1.5 h ago (468/468 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-2062410-18700 | 2062410 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.6 | last meaningful line 1.5 h ago (468/468 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.6 | last meaningful line 1.5 h ago (468/468 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-2817836-9660 | 2817836 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-2868506-15214 | 2868506 | ot_bind_native_319a0d1b9721503ed2462315 | 0.0 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 3.8 | drt_violations best 47 last 47 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-dsdv-slice-kv512-C--t1-grt-1124208 | dsdv-slice-kv512-C--t1-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-dsdv-slice-kv512-C--t1-grt-1172830 | dsdv-slice-kv512-C--t1-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pv07945c1e-479695 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8343 last 0.8368 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (203/206 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-1071817 | col_h10_r2__t1 | 3_4_place_resized | 0.2 | repair_Remaining best 40702 last 40702 rows 30 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 5.9 | last meaningful line 1.2 h ago (263/1462 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 11.0 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 6.0 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.1 h ago (201/204 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-3253598 | dsdv_slice_lepw_mu_LP__t2 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.6952 last 0.7648 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_1_place_gp_skip_io | 5.0 | overflow best 0.592 last 0.592 rows 20 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 7.9 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 7.3 | last meaningful line 0.1 h ago (160/160 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3463794 | ot_s81sl_leaf__t14 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t21-3790741 | ot_s81sl_leaf__t21 | 3_3_place_gp | 0.7 | overflow best 0.6336 last 0.6336 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | pregrt_ff_hold | 1.9 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t57-629868 | ot_s81sl_leaf__t57 | 5_1_grt | 1.9 | last meaningful line -0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t60-538445 | ot_s81sl_leaf__t60 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (204/206 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-320857 | ot_s81sl_leaf__t7 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7766 last 0.7766 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t71-349182 | ot_s81sl_leaf__t71 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.5932 last 0.5932 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t72-157835 | ot_s81sl_leaf__t72 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.9117 last 0.9519 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t9-595588 | ot_s81sl_leaf__t9 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-phy__t1-700606 | phy__t1 | 3_3_place_gp | 0.3 | overflow best 0.3412 last 0.3412 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-seqhost__t1-4071746 | seqhost__t1 | 2_1_floorplan | 0.6 | repair_Viol best 2319 last 2319 rows 1189 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-serdes__t3-22213 | serdes__t3 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-816007 | sle_stm_v1 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (604/604 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t17-1258586 | slice_station__t17 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9842 last 0.9842 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t28-3845035 | slice_station__t28 | 3_3_place_gp | 0.7 | overflow best 0.3446 last 0.3484 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3411742 | slice_station__t40 | 3_3_place_gp | 0.8 | overflow best 0.23 last 0.23 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t42__cl4bd1432c-3803277 | slice_station__t42 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.3526 last 0.3526 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t51-3956484 | slice_station__t51 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8499 last 0.8499 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t52-4028024 | slice_station__t52 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.3887 last 0.3887 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t8-3843883 | slice_station__t8 | 3_3_place_gp | 0.7 | overflow best 0.3713 last 0.3713 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-3692227-30432 | 3692227 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_2_route | 2.7 | drt_violations best 215 last 215 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t39-grt-1452583 | ot-s81sl-leaf--t39-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t52-grt-1365243 | ot-s81sl-leaf--t52-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t58-grt-1327854 | ot-s81sl-leaf--t58-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t73-grt-1293119 | ot-s81sl-leaf--t73-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 8.1 | drt_violations best 1386 last 1389 rows 21 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 5.9 | last meaningful line 2.3 h ago (211/242 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | 3_3_place_gp | 3.3 | overflow best 0.7009 last 0.7009 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-850957 | ot_s81sl_leaf__t17 | 3_3_place_gp | 0.4 | overflow best 0.5558 last 0.5604 rows 13 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-4096373 | ot_s81sl_leaf__t22 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t41-484715 | ot_s81sl_leaf__t41 | 3_3_place_gp | 0.6 | overflow best 0.5954 last 0.5957 rows 16 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-3851629 | ot_s81sl_leaf__t46 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t13-425517 | serdes__t13 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 12.1 | drt_violations best 140478 last 140478 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 12.2 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_2_route | 12.7 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 12.6 | drt_violations best 98877 last 98877 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 12.2 | drt_violations best 96831 last 96831 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 12.2 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | otc-758725-2436 | 758725 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-763364-1025 | 763364 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 3.4 | last meaningful line 0.5 h ago (290/291 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_1_grt | 0.6 | last meaningful line 0.5 h ago (260/1234 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1t-805483 | eco_20261122_180231_342380-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (239/549 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_568034_tt_42834 | so_568034_tt_42834 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-col-h10-r2--t1--cl1f5d6c2a--pvec003743-grt-166757 | col-h10-r2--t1--cl1f5d6c2a--pvec003743-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t23-grt-8162 | ot-s81sl-leaf--t23-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl911743eb-3523541 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.4 | overflow best 0.3103 last 0.3115 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2574197 | col_h10_r0_p4__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | postcts_gate_TT | 5.7 | last meaningful line -0.0 h ago (286/286 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 6.0 | last meaningful line 0.2 h ago (160/160 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 5.7 | last meaningful line 1.3 h ago (211/220 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-41241 | col_h9_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3589 last 3589 rows 1040 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 3_5_place_dp | 5.7 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 3_3_place_gp | 5.7 | overflow best 0.1979 last 0.1979 rows 42 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 3_5_place_dp | 5.7 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 4_1_cts | 5.7 | last meaningful line 0.0 h ago (3602/3602 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-221469 | dsdv_slice_iq_C__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.4 | last meaningful line 0.7 h ago (143/143 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 5_1_grt | 5.7 | last meaningful line 1.3 h ago (197/213 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 4.2 | last meaningful line 0.4 h ago (7500/7500 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 5.7 | repair_TNS best 373590 last 373590 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 5.7 | repair_TNS best 6682.67 last 6682.67 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-2884271 | ot_s81sl_leaf__t11 | 3_3_place_gp | 0.7 | overflow best 0.5303 last 0.5309 rows 19 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 5.7 | last meaningful line 2.0 h ago (207/216 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-2473787 | ot_s81sl_leaf__t2 | 3_3_place_gp | 0.8 | overflow best 0.4451 last 0.4451 rows 23 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3411008 | ot_s81sl_leaf__t53 | 3_3_place_gp | 0.5 | overflow best 0.5522 last 0.5728 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (1047/1047 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-serdes__t2-2411650 | serdes__t2 | 2_4_floorplan_pdn | 0.8 | last meaningful line 0.3 h ago (92/92 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | postcts_gate_FF | 11.6 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | postcts_gate_FF | 12.5 | last meaningful line -0.0 h ago (63361/63361 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-148484-8382 | 148484 | ot_s81sl_xrt1__fix | 1.8 | last meaningful line 0.0 h ago (1476/1476 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 2.0 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (210/212 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 3.2 | last meaningful line 0.2 h ago (236/326 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (202/208 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3606558 | coll_ftm | 5_2_route | 1.7 | last meaningful line 0.1 h ago (231/232 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | selrange | 1.9 |  | NO-DATA: empty log |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | 3_1_place_gp_skip_io | 3.7 | overflow best 0.7838 last 0.7838 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 11.0 | last meaningful line 3.2 h ago (233/1712 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 1.9 |  | NO-DATA: empty log |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | selrange | 1.9 |  | NO-DATA: empty log |  |
| intel2 | dpkit-hd_turn_a-1222041 | hd_turn_a | 5_2_route | 0.7 | drt_violations best 5474 last 5474 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-1229182 | hd_turn_a | 5_2_route | 0.7 | drt_violations best 5492 last 5492 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-1230053 | hd_turn_a | 5_2_route | 0.7 | drt_violations best 5474 last 5474 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t4-3639183 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 1.7 | repair_TNS best 266780 last 266780 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.8 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 5.5 | repair_Remaining best 187583 last 187583 rows 168 | YOUNG: stage 1.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 5_1_grt | 3.2 | last meaningful line 0.5 h ago (205/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 3.2 | last meaningful line 1.2 h ago (204/213 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 3.2 | last meaningful line 0.5 h ago (209/215 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | 5_1_grt | 3.2 | last meaningful line 0.8 h ago (206/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | otc-2146642-21452 | 2146642 | - | 0.3 |  | NO-DATA: no log found |  |
| intel2 | otc-2680274-15840 | 2680274 | ot_bind_native_65880f83d3582120795cb765 | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i2-4136869 | eco_20261122_054330_1688646-i2 | 5_3_fillcell | 1.4 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-2746791-17160 | 2746791 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-801626-7983 | 801626 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 51.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 12.1 | drt_violations best 4374 last 20511 rows 18 | before-window best 7642, window best 4374 | PROGRESS: drt_violations improved 42.8 % in window |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 7.6 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 55.7 | last meaningful line 0.1 h ago (1562/1562 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 12.2 | repair_TNS best 31885.5 last 31885.5 rows 2 | before-window best 32656.8, window best 31885.5 | PROGRESS: repair_TNS improved 2.4 % in window |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | 5_1_grt | 3.2 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_1_grt | 3.6 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 22.1 | drt_violations best 48926 last 48926 rows 16 | before-window best 51519, window best 48926 | PROGRESS: drt_violations improved 5.0 % in window |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 11.2 | drt_violations best 3207 last 3207 rows 15 | before-window best 100260, window best 3207 | PROGRESS: drt_violations improved 96.8 % in window |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_1_grt | 2.9 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 21.2 | drt_violations best 43966 last 43966 rows 15 | before-window best 46518, window best 43966 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 11.0 | drt_violations best 2520 last 2520 rows 14 | before-window best 10655, window best 2520 | PROGRESS: drt_violations improved 76.3 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 11.5 | drt_violations best 4012 last 4012 rows 14 | before-window best 87099, window best 4012 | PROGRESS: drt_violations improved 95.4 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 13.2 | drt_violations best 3242 last 3242 rows 13 | before-window best 13015, window best 3242 | PROGRESS: drt_violations improved 75.1 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 8.7 | drt_violations best 1 last 30 rows 42 | before-window best 2262, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_io_ft-2585034 | kv3_io_ft | 5_2_route | 1.9 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_1_grt | 3.2 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
