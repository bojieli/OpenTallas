# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 09:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 1, 'GRT-LABEL': 54, 'YOUNG': 179, 'NO-DATA': 13, 'KEEP': 1, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 9.3 | drt_violations best 28 last 30 rows 55 | before-window best 28, window best 30 | NO-PROGRESS: drt_violations best 30 vs 28 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | pregrt_ff_hold | 4.9 | repair_TNS best 250264 last 250264 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -934.15 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 18.7 | last meaningful line 17.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 17.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:3231 -> 10:234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 8.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 10.7 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 4.7 | grt rounds 3 overflow 5:23152 -> 10:21988 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 48.2 | grt rounds 4 overflow 5:108780 -> 10:62060 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:33908 -> 10:27872 | GRT-LABEL: DESIGN-FAIL: overflow 27872 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 4.6 | grt rounds 3 overflow 5:60876 -> 10:70130 -> 15:72547 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 62.6 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3426 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 6.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 7.0 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 5.0 | grt rounds 6 overflow 5:5968 -> 10:452 -> 15:57 -> 20:13 -> 25:5 -> 30:1 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 5.0 | grt rounds 3 overflow 5:51765 -> 10:37996 -> 15:27448 | GRT-LABEL: DESIGN-FAIL: overflow 37996 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:19413 -> 10:20178 -> 15:17415 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:9096 -> 10:2439 -> 15:1834 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:2659 -> 10:2062 -> 15:1321 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:69154 -> 10:65194 -> 15:60682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:65491 -> 10:65132 | GRT-LABEL: DESIGN-FAIL: overflow 65132 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:66235 -> 10:63465 | GRT-LABEL: DESIGN-FAIL: overflow 63465 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:29978 -> 10:22443 -> 15:17060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:32004 -> 10:27400 -> 15:23081 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:33831 -> 10:32112 -> 15:30362 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:7687 -> 10:5205 -> 15:4269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:7299 -> 10:701 -> 15:522 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:7755 -> 10:3584 -> 15:2649 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:36793 -> 10:24947 | GRT-LABEL: DESIGN-FAIL: overflow 24947 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:43402 -> 10:37170 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: overflow 37170 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:28701 -> 10:18853 | GRT-LABEL: DESIGN-FAIL: overflow 18853 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:36220 -> 10:27751 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:11135 -> 10:3890 -> 15:3468 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:61754 -> 10:36825 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:23007 -> 10:3527 | GRT-LABEL: DESIGN-FAIL: overflow 3527 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:36053 -> 10:36144 -> 15:29898 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:21322 -> 10:4099 | GRT-LABEL: DESIGN-FAIL: overflow 4099 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:35319 -> 10:35602 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 42.0 | grt rounds 3 overflow 5:64017 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 46.9 | grt rounds 3 overflow 5:60065 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 36.3 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 36.3 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 46.1 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 35.8 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 10.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:33627 -> 10:29364 -> 15:30446 | GRT-LABEL: DESIGN-FAIL: overflow 29364 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:9870 -> 10:488 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 5.9 | grt rounds 3 overflow 5:83933 -> 10:43 -> 15:18 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:36049 -> 10:17597 -> 15:9316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:35993 -> 10:32273 -> 15:23958 | GRT-LABEL: DESIGN-FAIL: overflow 32273 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:1893 -> 10:1268 -> 15:872 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 6.1 | grt rounds 2 overflow 5:62744 -> 10:36554 | GRT-LABEL: DESIGN-FAIL: overflow 36554 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 5.0 | grt rounds 5 overflow 5:11097 -> 10:255 -> 15:41 -> 20:7 -> 25:6 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:44293 -> 10:4215 | GRT-LABEL: DESIGN-FAIL: overflow 4215 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:43521 -> 10:4266 | GRT-LABEL: DESIGN-FAIL: overflow 4266 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 43.5 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 5.4 | grt rounds 4 overflow 5:8485 -> 10:200 -> 15:22 -> 20:7 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (1400/1415 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 60498 last 60498 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (1292/1292 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | 1_1_yosys_canonicalize | 2.4 | last meaningful line 0.0 h ago (215/215 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 2.4 | last meaningful line 1.0 h ago (132/132 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | 1_2_yosys | 2.4 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | tt_setup_repair | 1.9 | repair_Viol best 1051 last 1051 rows 14 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 1.9 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 3.2 | last meaningful line 0.3 h ago (336/336 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-1760524 | sle_fw_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve289215f-1673529 | sle_hc1 | 3_3_place_gp | 1.2 | overflow best 0.1951 last 0.1951 rows 246 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 10.9 | last meaningful line 0.0 h ago (265/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1757602 | slw_fe_v1 | 3_5_place_dp | 1.2 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 11.0 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2005514 | slw_fw_v1 | 3_3_place_gp | 1.0 | overflow best 0.0987 last 0.0987 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 11.0 | drt_violations best 119597 last 119597 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 10.9 | drt_violations best 88765 last 88765 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1-3804162 | eco_20261122_144137_2274607-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (230/286 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 5.0 | drt_violations best 60898 last 60898 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 5.0 | drt_violations best 63830 last 63830 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-117968 | dsdv_slice_lepe_nh_mus_LP__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (211/211 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 4.9 | last meaningful line 0.5 h ago (205/217 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 5_1_grt | 4.9 | last meaningful line 0.3 h ago (207/211 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 11.5 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | postcts_gate_FF | 11.5 | last meaningful line -0.0 h ago (35151/35151 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | postcts_gate_FF | 11.5 | last meaningful line 0.2 h ago (825/825 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 11.5 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 11.5 | drt_violations best 11216 last 11216 rows 2 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 11.5 | drt_violations best 11338 last 11338 rows 2 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | postcts_gate_FF | 11.5 | last meaningful line 0.1 h ago (1839/1839 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 11.5 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 11.5 | repair_TNS best 36816.3 last 36816.3 rows 3 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 11.5 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 11.5 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 11.5 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 11.5 | drt_violations best 70104 last 70104 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_2_route | 6.7 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1-4075679 | eco_20261122_051545_3846533-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-fw-v2--cl69f5e854-grt-1000742 | sle-fw-v2--cl69f5e854-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 5_1_grt | 2.9 | last meaningful line 0.2 h ago (246/325 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (209/215 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (207/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | 5_1_grt | 2.5 | repair_Remaining best 116933 last 116933 rows 88 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.4 h ago (313/1244 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1106130 | col_h9_r0_p4__t1 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 84209.8 last 84209.8 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | tt_setup_repair_grt | 2.7 | repair_Viol best 22 last 22 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-native59-1738201 | native59 | 3_4_place_resized | 2.0 | last meaningful line 0.1 h ago (333/333 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (206/207 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | pregrt_ff_hold | 4.6 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 11.5 | drt_violations best 99129 last 99129 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 11.5 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_2_route | 5.7 | drt_violations best 16746 last 16746 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | generate_abstract | 11.5 | last meaningful line 0.1 h ago (1032/1032 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | otc-1986186-11442 | 1986186 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.9 | last meaningful line 0.8 h ago (468/468 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.9 | last meaningful line 0.8 h ago (468/468 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.9 | last meaningful line 0.8 h ago (468/468 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-2062410-18700 | 2062410 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.8 | last meaningful line 0.8 h ago (468/468 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.8 | last meaningful line 0.8 h ago (468/468 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 3.0 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 55553.4 last 55553.4 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 1071.3 last 1071.3 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 5.4 | repair_Remaining best 91552 last 91552 rows 165 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 10.5 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 5.5 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 10.7 | drt_violations best 3379 last 3379 rows 14 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_Violations best 1423 last 1423 rows 12 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | tt_setup_measure | 2.3 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-3253598 | dsdv_slice_lepw_mu_LP__t2 | 1_synth | 0.3 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_4_floorplan_pdn | 4.5 | last meaningful line 0.2 h ago (181/181 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 7.4 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3463794 | ot_s81sl_leaf__t14 | 2_2_floorplan_macro | 0.3 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t21-3790741 | ot_s81sl_leaf__t21 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (101/101 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (6166/6166 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t57-629868 | ot_s81sl_leaf__t57 | pregrt_ff_hold | 1.4 | repair_TNS best 290507 last 290507 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | tt_setup_measure | 1.7 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-seqhost__t1-4071746 | seqhost__t1 | 1_1_yosys_canonicalize | 0.1 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t3-22213 | serdes__t3 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t24__cl66b71008-3836775 | slice_station__t24 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t28-3845035 | slice_station__t28 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (215/571 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3411742 | slice_station__t40 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__cl4bd1432c-3803277 | slice_station__t42 | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t51-3956484 | slice_station__t51 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t52-4028024 | slice_station__t52 | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc8 | dpkit-slice_station__t8-3843883 | slice_station__t8 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2076558 | slw_st_a_v1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-3692227-30432 | 3692227 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p1--t1--pvf9acce4c-grt-4068396 | col-h9-r0-p1--t1--pvf9acce4c-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-slw-st-a-v1--clfc5867a6--pvf82a6c28-grt-80748 | slw-st-a-v1--clfc5867a6--pvf82a6c28-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 7.4 | drt_violations best 1391 last 1391 rows 8 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 5.1 | last meaningful line 1.5 h ago (211/234 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | 2_1_floorplan | 2.5 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-4096373 | ot_s81sl_leaf__t22 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-3851629 | ot_s81sl_leaf__t46 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8845 last 0.8845 rows 11 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t52-3751129 | ot_s81sl_leaf__t52 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4529 last 0.4529 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-3752631 | ot_s81sl_leaf__t58 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.5584 last 0.5584 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 11.4 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 11.4 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_2_route | 12.0 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 11.8 | last meaningful line 0.1 h ago (289/290 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t21-3691170 | slice_station__t21 | 3_3_place_gp | 0.3 | overflow best 0.3121 last 0.3128 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t26-3693012 | slice_station__t26 | 3_3_place_gp | 0.3 | overflow best 0.2646 last 0.2646 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 11.4 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 11.4 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | generate_abstract | 11.4 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-149091-18548 | 149091 | ot_bind_native_a4bf56c9eff96f2365d151d3 | 0.0 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-149898-24841 | 149898 | ot_bind_native_a4bf56c9eff96f2365d151d3 | 0.0 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-4183895-10969 | 4183895 | signoff | 2.6 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | otc-63591-3152 | 63591 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 2.7 | last meaningful line 0.4 h ago (284/285 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco2-i3t-3248873 | eco2-i3t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_109044_ff_88704 | so_109044_ff_88704 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_109044_tt_88704 | so_109044_tt_88704 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_145660_ff_12342 | so_145660_ff_12342 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (515/515 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_145660_tt_12342 | so_145660_tt_12342 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (515/515 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_3392483_ff_80597 | so_3392483_ff_80597 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc9 | so_3392483_tt_80597 | so_3392483_tt_80597 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc9 | so_4189971_ff_45772 | so_4189971_ff_45772 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_4189971_tt_45772 | so_4189971_tt_45772 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-kv3-pc-v3-grt-2325991 | kv3-pc-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 67815.3 last 67815.3 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2574197 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.0 | repair_Viol best 6050 last 6050 rows 80 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-2554395 | col_h10_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2204 last 2204 rows 411 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_1_grt | 3.5 | last meaningful line 0.3 h ago (203/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 5.0 | last meaningful line 0.5 h ago (211/216 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-1857793 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3225 last 0.3554 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 3.3 | repair_TNS best 81868.6 last 81868.6 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 5.0 | overflow best 0.7432 last 0.7479 rows 11 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | 4_1_cts | 4.9 | last meaningful line 0.0 h ago (3311/3311 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | 4_1_cts | 4.9 | last meaningful line 0.0 h ago (2800/2800 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 3_3_place_gp | 5.0 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 3_3_place_gp | 5.0 | overflow best 0.6502 last 0.6502 rows 24 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 4_1_cts | 5.0 | last meaningful line 0.0 h ago (3309/3309 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 3_5_place_dp | 3.3 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 4_1_cts | 5.0 | last meaningful line 0.1 h ago (3360/3360 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 4.9 | repair_Remaining best 410 last 410 rows 226 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-eng__t1-1558999 | eng__t1 | 5_1_grt | 2.5 | last meaningful line 1.3 h ago (191/200 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 5_1_grt | 4.9 | last meaningful line 0.6 h ago (197/206 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 3.5 | last meaningful line 0.2 h ago (7498/7498 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 5.0 | repair_TNS best 373590 last 373590 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 4.9 | last meaningful line 1.3 h ago (207/214 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-2473787 | ot_s81sl_leaf__t2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 4.9 | last meaningful line 1.3 h ago (205/214 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | 5_1_grt | 4.5 | last meaningful line 1.5 h ago (1293/2078 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-serdes__t2-2411650 | serdes__t2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-3149151 | sle_ctl | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | postcts_gate_TT | 10.8 | last meaningful line 0.1 h ago (975/975 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-2719308 | sle_su_c | 3_5_place_dp | 1.9 | last meaningful line 0.1 h ago (116/116 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__cl1653104c-2641625 | slice_station__t30 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | postcts_gate_FF | 11.7 | last meaningful line 0.3 h ago (551/551 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-148484-8382 | 148484 | ot_s81sl_xrt1__fix | 1.1 | last meaningful line 0.0 h ago (1288/1288 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | otc-2656503-353 | 2656503 | ot_s81sl_xrt1__fix | 1.9 | last meaningful line 0.0 h ago (1528/1528 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (253/701 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | so_1549740_ff_68877 | so_1549740_ff_68877 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_1549740_tt_68877 | so_1549740_tt_68877 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 4.6 | repair_Remaining best 78684 last 78684 rows 102 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3626195 | col_h9_r0_p5__t1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 663.173 last 663.173 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 2.5 | grt_overflow best 199 last 199 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (200/204 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3606558 | coll_ftm | 5_1_grt | 0.9 | last meaningful line 0.4 h ago (243/359 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 3.0 | last meaningful line 1.3 h ago (132/132 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 10.3 | last meaningful line 2.5 h ago (233/1712 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2585034 | kv3_io_ft | 5_2_route | 1.1 | last meaningful line 0.1 h ago (223/224 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t4-3639183 | ot_s81sl_kv_leaf__t4 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (3026/3026 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.0 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (151/151 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-3630514 | ot_s81sl_leaf__t44 | 3_5_place_dp | 0.9 | last meaningful line 0.1 h ago (39/39 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (204/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (158/158 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (206/207 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t73-348929 | ot_s81sl_leaf__t73 | 3_3_place_gp | 0.5 | overflow best 0.6289 last 0.6289 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-2733013 | sle_fw_v1 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2632859 | slice_station__t12 | 5_2_route | 1.1 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (184/185 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t52-3617204 | slice_station__t52 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-2734287 | slw_hc0 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | fable-lep0n-sta-3578726 | fable-lep0n-sta | - | 0.9 |  | NO-DATA: no log found |  |
| intel2 | prd-eco_20261122_054330_1688646-i2-4136869 | eco_20261122_054330_1688646-i2 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (225/226 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 50.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 11.1 | drt_violations best 4374 last 20511 rows 18 | before-window best 36979, window best 4374 | PROGRESS: drt_violations improved 88.2 % in window |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 6.6 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 9.7 | drt_violations best 11 last 11 rows 47 | before-window best 19915, window best 11 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 55.0 | last meaningful line 2.6 h ago (1560/1560 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | tt_setup_repair | 4.9 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 21.4 | drt_violations best 49344 last 49344 rows 15 | before-window best 51519, window best 49344 | PROGRESS: drt_violations improved 4.2 % in window |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 6.8 | repair_Violations best 0 last 0 rows 5 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t60-538445 | ot_s81sl_leaf__t60 | pregrt_ff_hold | 1.4 | repair_Violations best 0 last 0 rows 28 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t9-595588 | ot_s81sl_leaf__t9 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 20.9 | drt_violations best 597 last 2670 rows 35 | before-window best 597, window best 1269 | PROGRESS: drt_violations: falling inside the active iteration (2670 -> 2001) |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 20.7 | drt_violations best 43966 last 43966 rows 15 | before-window best 46518, window best 43966 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 10.3 | drt_violations best 5445 last 5445 rows 13 | before-window best 12136, window best 5445 | PROGRESS: drt_violations improved 55.1 % in window |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 10.8 | drt_violations best 5167 last 5167 rows 12 | before-window best 87099, window best 5167 | PROGRESS: drt_violations improved 94.1 % in window |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 24 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 12.4 | drt_violations best 5193 last 5193 rows 12 | before-window best 13795, window best 5193 | PROGRESS: drt_violations improved 62.4 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 7.9 | drt_violations best 1 last 30 rows 42 | before-window best 20664, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
