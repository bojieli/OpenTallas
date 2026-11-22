# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 10:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 57, 'NO-DATA': 9, 'YOUNG': 183, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 19.0 | last meaningful line 17.3 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 17.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 21.1 | drt_violations best 597 last 1991 rows 36 | before-window best 597, window best 1269 | NO-PROGRESS: drt_violations best 1269 vs 597 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:3231 -> 10:234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 9.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 11.2 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:23152 -> 10:21988 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 48.7 | grt rounds 4 overflow 5:108780 -> 10:62060 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:33908 -> 10:27872 | GRT-LABEL: DESIGN-FAIL: overflow 27872 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:60876 -> 10:70130 -> 15:72547 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 63.1 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3426 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 6.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 5.2 | grt rounds 6 overflow 5:5968 -> 10:452 -> 15:57 -> 20:13 -> 25:5 -> 30:1 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:51765 -> 10:37996 -> 15:27448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:19413 -> 10:20178 -> 15:17415 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:9096 -> 10:2439 -> 15:1748 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:2659 -> 10:1890 -> 15:1321 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:69154 -> 10:65194 -> 15:60682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:65491 -> 10:65132 | GRT-LABEL: DESIGN-FAIL: overflow 65132 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:66235 -> 10:63465 | GRT-LABEL: DESIGN-FAIL: overflow 63465 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:29527 -> 10:22443 -> 15:17060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:32004 -> 10:27400 -> 15:23081 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:33831 -> 10:32112 -> 15:30362 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:7687 -> 10:5205 -> 15:4269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:7816 -> 10:701 -> 15:522 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:5723 -> 10:3584 -> 15:2649 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:36793 -> 10:24947 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: overflow 24947 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:43402 -> 10:37170 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:28701 -> 10:18853 | GRT-LABEL: DESIGN-FAIL: overflow 18853 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:32655 -> 10:27751 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:10375 -> 10:3890 -> 15:3468 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:61754 -> 10:36825 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:23007 -> 10:3527 | GRT-LABEL: DESIGN-FAIL: overflow 3527 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:36053 -> 10:36144 -> 15:29898 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:21322 -> 10:4099 | GRT-LABEL: DESIGN-FAIL: overflow 4099 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:35319 -> 10:35602 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 42.2 | grt rounds 3 overflow 5:64017 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 47.2 | grt rounds 3 overflow 5:60065 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 36.6 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 36.6 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 46.3 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 36.1 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 10.9 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:33627 -> 10:29364 -> 15:30446 | GRT-LABEL: DESIGN-FAIL: overflow 29364 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:9870 -> 10:488 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 6.1 | grt rounds 3 overflow 5:83933 -> 10:43 -> 15:18 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:36431 -> 10:17597 -> 15:9316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:35993 -> 10:32273 -> 15:23958 | GRT-LABEL: DESIGN-FAIL: overflow 32273 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:1893 -> 10:1268 -> 15:872 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 6.4 | grt rounds 2 overflow 5:62744 -> 10:36554 | GRT-LABEL: DESIGN-FAIL: overflow 36554 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 5.2 | grt rounds 5 overflow 5:11097 -> 10:255 -> 15:41 -> 20:7 -> 25:6 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:8404 -> 10:286 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:44293 -> 10:4215 | GRT-LABEL: DESIGN-FAIL: overflow 4215 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:43521 -> 10:4266 | GRT-LABEL: DESIGN-FAIL: overflow 4266 at round 10 > 1000 |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 5.2 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-eng__t1-1558999 | eng__t1 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:57928 -> 10:1104 | GRT-LABEL: DESIGN-FAIL: overflow 1104 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 43.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 5.6 | grt rounds 4 overflow 5:8485 -> 10:200 -> 15:22 -> 20:7 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-slice-station--t21-grt-2241282 | slice-station--t21-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2243264 | col_h10_r1__t1 | 3_1_place_gp_skip_io | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | 5_1_grt | 3.1 | last meaningful line 0.3 h ago (204/207 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 2.5 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.8234 last 0.8536 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.8419 last 0.8557 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.586 last 0.586 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 2.4 | repair_TNS best 207473 last 207473 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 2.4 | repair_TNS best 207751 last 207751 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 3.7 | last meaningful line 0.8 h ago (336/336 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t47-618796 | ot_s81sl_leaf__t47 | 3_3_place_gp | 0.5 | overflow best 0.3559 last 0.4128 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t55-1257352 | ot_s81sl_leaf__t55 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t62-1457612 | ot_s81sl_leaf__t62 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4623 last 0.4623 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1466438 | sle_hc1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 11.4 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t25-1088717 | slice_station__t25 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.648 last 0.648 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 11.5 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2005514 | slw_fw_v1 | 3_5_place_dp | 1.5 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 11.5 | drt_violations best 119597 last 119597 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 11.4 | drt_violations best 88765 last 88765 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | otc-2241706-6822 | 2241706 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-853863 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1-3804162 | eco_20261122_144137_2274607-i1 | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (231/2025 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 5.2 | drt_violations best 60898 last 60898 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 5.2 | drt_violations best 63830 last 63830 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-117968 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_3_place_gp | 0.3 | overflow best 0.6863 last 0.6863 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 5.2 | last meaningful line 0.8 h ago (205/220 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t33-351893 | ot_s81sl_leaf__t33 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.69 last 0.69 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 5_1_grt | 5.2 | last meaningful line 0.5 h ago (207/212 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 11.8 | last meaningful line 0.3 h ago (287/288 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 11.8 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 11.8 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 11.8 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 11.8 | drt_violations best 11216 last 11216 rows 2 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 11.7 | drt_violations best 11338 last 11338 rows 2 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 11.7 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 11.7 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 11.7 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 11.7 | last meaningful line 0.3 h ago (138/138 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 11.7 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 11.7 | drt_violations best 70104 last 70104 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_2_route | 7.0 | drt_violations best 34720 last 34720 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | otc-755443-31238 | 755443 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1-4075679 | eco_20261122_051545_3846533-i1 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 5_1_grt | 3.2 | repair_Remaining best 117604 last 117604 rows 86 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (209/220 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (207/219 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | 5_1_grt | 2.7 | repair_Remaining best 45933 last 45933 rows 159 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1106130 | col_h9_r0_p4__t1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | pregrt_ff_hold | 2.7 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | postcts_gate_TT | 3.0 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-native59-1738201 | native59 | 3_5_place_dp | 2.3 | last meaningful line 0.1 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t10-1490841 | ot_s81sl_leaf__t10 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8133 last 0.8133 rows 17 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (206/210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | pregrt_ff_hold | 5.1 | repair_TNS best 513433 last 513433 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-serdes__t1__clfe1f0815-1376853 | serdes__t1 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (316/316 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 11.8 | drt_violations best 99129 last 99129 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 11.8 | drt_violations best 99129 last 99129 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_2_route | 5.9 | drt_violations best 1763 last 1763 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | otc-1773808-1894 | 1773808 | s81.c.ot_s81_svc_idx_hslice_fp__h8_1119 | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1986186-11442 | 1986186 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.1 | last meaningful line 1.0 h ago (468/468 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.1 | last meaningful line 1.0 h ago (468/468 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.1 | last meaningful line 1.0 h ago (468/468 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-2062410-18700 | 2062410 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.1 | last meaningful line 1.0 h ago (468/468 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 2.1 | last meaningful line 1.0 h ago (468/468 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 3.3 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | so_1396612_ff_60217 | so_1396612_ff_60217 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_1396612_tt_60217 | so_1396612_tt_60217 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pv07945c1e-479695 | col_h10_r0_p4__t1 | 1_synth | 0.1 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (203/204 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 5.7 | repair_Remaining best 38552 last 38552 rows 218 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 10.8 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 5.8 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-3253598 | dsdv_slice_lepw_mu_LP__t2 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_1_place_gp_skip_io | 4.7 | overflow best 0.6859 last 0.6859 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 7.7 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 7.1 | last meaningful line 0.1 h ago (158/158 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3463794 | ot_s81sl_leaf__t14 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (480/480 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t21-3790741 | ot_s81sl_leaf__t21 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9912 last 0.9912 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (6181/6181 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t60-538445 | ot_s81sl_leaf__t60 | 5_1_grt | 1.7 | last meaningful line 0.1 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-320857 | ot_s81sl_leaf__t7 | 1_synth | 0.2 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t71-349182 | ot_s81sl_leaf__t71 | 1_synth | 0.2 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t72-157835 | ot_s81sl_leaf__t72 | 1_synth | 0.2 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | pregrt_ff_hold | 1.9 | repair_TNS best 193852 last 193852 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t9-595588 | ot_s81sl_leaf__t9 | pregrt_ff_hold | 1.6 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-phy__t1-700606 | phy__t1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-seqhost__t1-4071746 | seqhost__t1 | 1_2_yosys | 0.3 | last meaningful line 0.1 h ago (482/482 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t3-22213 | serdes__t3 | 1_2_yosys | 0.3 | last meaningful line 0.1 h ago (328/328 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-816007 | sle_stm_v1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t24__cl66b71008-3836775 | slice_station__t24 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9606 last 0.9606 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t28-3845035 | slice_station__t28 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6809 last 0.6809 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3411742 | slice_station__t40 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5376 last 0.5376 rows 33 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t42__cl4bd1432c-3803277 | slice_station__t42 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t51-3956484 | slice_station__t51 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t52-4028024 | slice_station__t52 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t8-3843883 | slice_station__t8 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-3692227-30432 | 3692227 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_2_route | 2.5 | drt_violations best 215 last 215 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 7.6 | drt_violations best 1386 last 1386 rows 12 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 5.4 | last meaningful line 1.8 h ago (211/237 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.8929 last 0.8949 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-4096373 | ot_s81sl_leaf__t22 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (234/234 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t41-484715 | ot_s81sl_leaf__t41 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8633 last 0.8633 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-3851629 | ot_s81sl_leaf__t46 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t52-3751129 | ot_s81sl_leaf__t52 | 3_3_place_gp | 0.5 | overflow best 0.5797 last 0.5803 rows 14 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-3752631 | ot_s81sl_leaf__t58 | 3_3_place_gp | 0.5 | overflow best 0.5444 last 0.5444 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-serdes__t13-425517 | serdes__t13 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 11.6 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 11.7 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_2_route | 12.2 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 12.1 | drt_violations best 98877 last 98877 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3693012 | slice_station__t26 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 11.7 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 11.7 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-4183895-10969 | 4183895 | signoff | 2.8 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 2.9 | last meaningful line 0.2 h ago (288/289 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco2-i3t-3248873 | eco2-i3t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (250/251 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_145660_ff_12342 | so_145660_ff_12342 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (515/515 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_145660_tt_12342 | so_145660_tt_12342 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (515/515 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_3392483_tt_80597 | so_3392483_tt_80597 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc9 | so_568034_ff_42834 | so_568034_ff_42834 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_568034_tt_42834 | so_568034_tt_42834 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-col-h10-r2--t1--cl1f5d6c2a--pv0c1de895-grt-3054361 | col-h10-r2--t1--cl1f5d6c2a--pv0c1de895-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-col-h9-r1--t1--clf32cde8d--pv387d6579-grt-3347895 | col-h9-r1--t1--clf32cde8d--pv387d6579-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-dsdv-slice-iq-C--t1-dump-3336890 | dsdv-slice-iq-C--t1-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-dsdv-slice-iq-C--t1-grt-3313518 | dsdv-slice-iq-C--t1-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-dsdv-slice-iq-C--t1-grt-3336890 | dsdv-slice-iq-C--t1-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-sle-su-c-grt-3008559 | sle-su-c-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.2 | repair_TNS best 67815.3 last 67815.3 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2574197 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.73 last 0.7936 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (202/208 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3246710 | col_h10_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2204 last 2204 rows 362 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-2554395 | col_h10_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.2713 last 0.2757 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 5.5 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 5.2 | last meaningful line 0.8 h ago (211/217 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 5.2 | overflow best 0.6456 last 0.6456 rows 23 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | 4_1_cts | 5.2 | last meaningful line 0.1 h ago (3332/3332 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | 4_1_cts | 5.2 | last meaningful line 0.0 h ago (2869/2869 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 3_3_place_gp | 5.2 | overflow best 0.726 last 0.7275 rows 13 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 3_3_place_gp | 5.2 | overflow best 0.2779 last 0.2779 rows 36 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 4_1_cts | 5.2 | last meaningful line 0.0 h ago (3515/3516 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 4_1_cts | 5.2 | last meaningful line 0.1 h ago (3382/3382 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.2 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 5_1_grt | 5.2 | last meaningful line 0.8 h ago (197/209 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 3.7 | last meaningful line 0.4 h ago (7498/7498 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 5.2 | repair_TNS best 373590 last 373590 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-2884271 | ot_s81sl_leaf__t11 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.4517 last 0.4517 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 5.2 | last meaningful line 1.5 h ago (207/215 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-2473787 | ot_s81sl_leaf__t2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3692 last 0.3692 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 5.2 | last meaningful line 1.5 h ago (205/214 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | tt_setup_repair_grt | 4.8 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-serdes__t2-2411650 | serdes__t2 | 1_2_yosys | 0.3 | last meaningful line 0.2 h ago (313/313 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-3149151 | sle_ctl | 3_5_place_dp | 1.9 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | postcts_gate_TT | 11.1 | last meaningful line 0.0 h ago (1115/1115 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__cl1653104c-2641625 | slice_station__t30 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2109 last 0.2109 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | postcts_gate_FF | 12.0 | last meaningful line 0.1 h ago (1235/1235 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-148484-8382 | 148484 | ot_s81sl_xrt1__fix | 1.3 | last meaningful line 0.0 h ago (1348/1348 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_1_grt | 1.5 | last meaningful line 0.7 h ago (253/920 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 4.9 | repair_Remaining best 76684 last 76684 rows 104 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_1_grt | 3.1 | last meaningful line 0.3 h ago (200/210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3606558 | coll_ftm | postcts_gate_TT | 1.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | 1_2_yosys | 3.2 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 10.5 | last meaningful line 2.7 h ago (233/1712 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1229182 | hd_turn_a | 5_1_grt | 0.2 | repair_Remaining best 6944 last 6944 rows 17 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2585034 | kv3_io_ft | 5_2_route | 1.4 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t4-3639183 | ot_s81sl_kv_leaf__t4 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (3081/3081 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.3 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (211/212 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 5_1_grt | 2.7 | last meaningful line 0.1 h ago (191/204 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 2.7 | last meaningful line 0.7 h ago (204/210 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 2.7 | last meaningful line 0.1 h ago (195/208 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (206/209 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t73-348929 | ot_s81sl_leaf__t73 | 3_3_place_gp | 0.7 | overflow best 0.2259 last 0.2259 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-2733013 | sle_fw_v1 | 3_5_place_dp | 1.3 | last meaningful line -0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2632859 | slice_station__t12 | 5_2_route | 1.4 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_1_grt | 2.7 | last meaningful line 0.2 h ago (208/603 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | fable-lep0n-sta-3578726 | fable-lep0n-sta | - | 1.2 |  | NO-DATA: no log found |  |
| intel2 | prd-eco_20261122_054330_1688646-i2-4136869 | eco_20261122_054330_1688646-i2 | 5_2_route | 0.9 | drt_violations best 3 last 3 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | otc-1516547-32671 | 1516547 | asbuilt.yosys | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 50.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_1_grt | 2.4 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 11.6 | drt_violations best 4374 last 20511 rows 18 | before-window best 10671, window best 4374 | PROGRESS: drt_violations improved 59.0 % in window |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 7.1 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 55.2 | last meaningful line 2.9 h ago (1560/1560 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 11.7 | repair_TNS best 34074.8 last 34074.8 rows 6 | before-window best 38631.5, window best 34074.8 | PROGRESS: repair_TNS improved 11.8 % in window |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_1_grt | 3.1 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 21.6 | drt_violations best 49344 last 49344 rows 15 | before-window best 51519, window best 49344 | PROGRESS: drt_violations improved 4.2 % in window |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 10.9 | drt_violations best 3207 last 3207 rows 15 | before-window best 100260, window best 3207 | PROGRESS: drt_violations improved 96.8 % in window |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t57-629868 | ot_s81sl_leaf__t57 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_1_grt | 2.7 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 20.9 | drt_violations best 43966 last 43966 rows 15 | before-window best 46518, window best 43966 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 10.5 | drt_violations best 5445 last 5445 rows 13 | before-window best 12136, window best 5445 | PROGRESS: drt_violations improved 55.1 % in window |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 11.0 | drt_violations best 4680 last 4680 rows 13 | before-window best 87099, window best 4680 | PROGRESS: drt_violations improved 94.6 % in window |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 5_1_grt | 4.9 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 12.7 | drt_violations best 5193 last 5193 rows 12 | before-window best 13795, window best 5193 | PROGRESS: drt_violations improved 62.4 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 8.2 | drt_violations best 1 last 30 rows 42 | before-window best 20664, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-hd_turn_a-1222041 | hd_turn_a | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-hd_turn_a-1230053 | hd_turn_a | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
