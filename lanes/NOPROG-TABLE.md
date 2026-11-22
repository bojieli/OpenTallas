# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 09:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 47, 'YOUNG': 177, 'NO-DATA': 8, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 31}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 9.0 | drt_violations best 28 last 30 rows 55 | before-window best 28, window best 30 | NO-PROGRESS: drt_violations best 30 vs 28 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | tt_setup_repair | 4.4 | repair_Violations best 1267 last 1335 rows 93 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -1001.21 ps (< -300, gate TT >= -42); job a | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 18.2 | last meaningful line 16.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 16.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2642185 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.6 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2586170 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_4_place_resized | 0.6 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 5.4 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 8.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 10.5 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:22677 -> 10:21988 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 47.9 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:61583 -> 10:70130 -> 15:72547 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 62.3 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3426 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 6.8 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 4.5 | grt rounds 6 overflow 5:5968 -> 10:452 -> 15:57 -> 20:13 -> 25:5 -> 30:1 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 4.5 | grt rounds 2 overflow 5:51765 -> 10:37996 | GRT-LABEL: DESIGN-FAIL: overflow 37996 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:21001 -> 10:20178 -> 15:17415 | GRT-LABEL: DESIGN-FAIL: overflow 20178 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:9096 -> 10:2439 -> 15:1834 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 4.5 | grt rounds 3 overflow 5:3611 -> 10:2062 -> 15:1321 | GRT-LABEL: DESIGN-FAIL: overflow 2062 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:69154 -> 10:59241 -> 15:60682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:65491 -> 10:65132 | GRT-LABEL: DESIGN-FAIL: overflow 65132 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:29978 -> 10:24305 -> 15:17060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:32004 -> 10:27400 -> 15:23179 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:33831 -> 10:35490 -> 15:30362 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:7927 -> 10:5205 -> 15:4269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:7299 -> 10:942 -> 15:522 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:7755 -> 10:3584 | GRT-LABEL: DESIGN-FAIL: overflow 3584 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:36793 -> 10:24947 | GRT-LABEL: DESIGN-FAIL: overflow 24947 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:43402 -> 10:37170 | GRT-LABEL: DESIGN-FAIL: overflow 37170 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:28701 -> 10:18853 | GRT-LABEL: DESIGN-FAIL: overflow 18853 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:36220 -> 10:27751 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: overflow 27751 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:11135 -> 10:4450 -> 15:3468 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:61754 -> 10:36825 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:36053 -> 10:36558 -> 15:29898 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:21322 -> 10:4099 | GRT-LABEL: DESIGN-FAIL: overflow 4099 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:49663 -> 10:35602 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 41.5 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 46.4 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 35.8 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 35.8 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 45.6 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 35.3 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 10.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:33627 -> 10:29364 | GRT-LABEL: DESIGN-FAIL: overflow 29364 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 5.4 | grt rounds 3 overflow 5:83933 -> 10:43 -> 15:18 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:36049 -> 10:19657 -> 15:9316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:35993 -> 10:32273 | GRT-LABEL: DESIGN-FAIL: overflow 32273 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:1893 -> 10:1268 -> 15:762 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 5.6 | grt rounds 2 overflow 5:62744 -> 10:36554 | GRT-LABEL: DESIGN-FAIL: overflow 36554 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 4.5 | grt rounds 5 overflow 5:11097 -> 10:255 -> 15:41 -> 20:7 -> 25:6 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 43.0 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 60498 last 60498 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_1_grt | 1.7 | last meaningful line 0.7 h ago (265/1282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (202/212 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.8 h ago (131/131 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 1.0 h ago (132/132 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (3794/3794 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | tt_setup_repair | 1.7 | last meaningful line -0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-1491393 | kv3_sys_c | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 3.0 | last meaningful line 0.2 h ago (336/336 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 4.4 | last meaningful line 1.3 h ago (204/213 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 6.3 | last meaningful line 1.5 h ago (224/1475 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-1760524 | sle_fw_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.2 h ago (364/364 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve289215f-1673529 | sle_hc1 | 3_3_place_gp | 0.9 | overflow best 0.2991 last 0.4678 rows 190 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 10.6 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1757602 | slw_fe_v1 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (377/377 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 10.8 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2005514 | slw_fw_v1 | 3_3_place_gp | 0.8 | overflow best 0.4218 last 0.4218 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 10.7 | drt_violations best 119597 last 119597 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 10.7 | drt_violations best 88765 last 88765 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1-3804162 | eco_20261122_144137_2274607-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 4.5 | drt_violations best 60898 last 60898 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 4.5 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (205/208 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (208/212 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 4.5 | last meaningful line 0.6 h ago (201/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 4.4 | last meaningful line 1.0 h ago (204/212 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | 5_1_grt | 4.4 | last meaningful line 0.3 h ago (207/213 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 5_1_grt | 4.4 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 5_1_grt | 4.4 | last meaningful line 1.0 h ago (209/214 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 11.0 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | postcts_gate_FF | 11.0 | last meaningful line 0.2 h ago (847/847 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | postcts_gate_FF | 11.0 | last meaningful line 0.1 h ago (380/380 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 11.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 11.0 | drt_violations best 78672 last 78672 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 11.0 | drt_violations best 77889 last 77889 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | postcts_gate_FF | 11.0 | last meaningful line 0.0 h ago (865/865 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 11.0 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 11.0 | last meaningful line 4.8 h ago (220/1052 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 11.0 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | postcts_gate_FF | 11.0 | last meaningful line 0.1 h ago (849/849 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 11.0 | last meaningful line 0.0 h ago (267/268 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 11.0 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | otc-2526596-10086 | 2526596 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-3825271 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (542/542 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h9-r0-p5--t1--pveda1ecc9-grt-4171608 | col-h9-r0-p5--t1--pveda1ecc9-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-fw-v1--clf58b4dfb-grt-4134000 | sle-fw-v1--clf58b4dfb-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-st-a-v2--pv4242de79-grt-113258 | sle-st-a-v2--pv4242de79-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v2--cl7b3062fa-grt-160326 | sle-stm-v2--cl7b3062fa-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-fw-v3-grt-93130 | slw-fw-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (209/213 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (203/212 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1106130 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 61395.6 last 61395.6 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 84209.8 last 84209.8 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.5 | repair_TNS best 228722 last 228722 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-native59-1738201 | native59 | 3_3_place_gp | 1.5 | overflow best 0.2988 last 0.4972 rows 238 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 1.7 | repair_Violations best 629 last 629 rows 93 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 4.1 | last meaningful line 0.0 h ago (9321/9321 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl69f5e854-2551268 | sle_fw_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 11.0 | drt_violations best 99129 last 99129 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 11.0 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1631153 | sle_hc1 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_2_route | 5.2 | drt_violations best 16746 last 16746 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | generate_abstract | 11.0 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-1986186-11442 | 1986186 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.4 | last meaningful line 0.3 h ago (468/468 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.4 | last meaningful line 0.3 h ago (468/468 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.4 | last meaningful line 0.3 h ago (468/468 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-2062410-18700 | 2062410 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.3 | last meaningful line 0.3 h ago (468/468 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 1.3 | last meaningful line 0.3 h ago (468/468 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-243120-22419 | 243120 | ot_bind_native_6d7365f85255c403e78b3715 | 0.0 | last meaningful line -0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | so_4189647_ff_22877 | so_4189647_ff_22877 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (694/694 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_4189647_tt_22877 | so_4189647_tt_22877 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (694/694 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 55553.4 last 55553.4 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 151547 last 151547 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_1_grt | 2.0 | grt_overflow best 420 last 420 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 93931.6 last 93931.6 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 4.9 | last meaningful line 0.2 h ago (263/377 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 96178 last 96178 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 10.0 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 5.0 | last meaningful line 0.0 h ago (271/272 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 10.2 | drt_violations best 3572 last 3572 rows 13 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 67926.7 last 67926.7 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | tt_setup_repair | 1.8 | repair_Violations best 2864 last 2891 rows 30 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_4_floorplan_pdn | 4.0 | last meaningful line 0.6 h ago (175/175 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | postcts_gate_FF | 6.9 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5897/5897 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t57-629868 | ot_s81sl_leaf__t57 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (3956/3956 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t60-538445 | ot_s81sl_leaf__t60 | tt_setup_repair | 0.9 | repair_Viol best 159 last 159 rows 21 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5567/5567 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t9-595588 | ot_s81sl_leaf__t9 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (4346/4346 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2076558 | slw_st_a_v1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1816348-31983 | 1816348 | qwen_compute.t.slw_hc0__cl1bc59e1c | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t69-grt-3060443 | ot-s81sl-leaf--t69-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 6.9 | drt_violations best 12734 last 12734 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 4.6 | last meaningful line 1.0 h ago (211/227 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | generate_abstract | 10.9 | last meaningful line 0.0 h ago (1026/1026 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-87338 | hd_ctl | 5_2_route | 2.0 | drt_violations best 6914 last 6914 rows 2 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 10.9 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 10.9 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | postcts_gate_FF | 11.5 | last meaningful line -0.0 h ago (42889/42889 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 11.3 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 10.9 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 10.9 | last meaningful line 0.0 h ago (263/264 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | eco-abs-2213072 | eco-abs | generate_abstract | 0.7 | last meaningful line 0.2 h ago (511/511 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-3274446-24655 | 3274446 | j6ctl_rom_elem_q_hw__fix | 0.0 | last meaningful line 0.0 h ago (198/198 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-4183895-10969 | 4183895 | signoff | 2.1 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 2.2 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco2-i3t-3248873 | eco2-i3t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r2--t1--cl774acf45--pv858fb2ba-grt-992820 | col-h9-r2--t1--cl774acf45--pv858fb2ba-grt | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 67815.3 last 67815.3 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 69202.3 last 69202.3 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (201/204 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 4.5 | last meaningful line 0.1 h ago (211/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 4.5 | last meaningful line 0.8 h ago (206/215 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 4.5 | last meaningful line 0.5 h ago (207/214 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | tt_setup_repair_grt | 4.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 4.5 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 2.8 | repair_TNS best 81868.6 last 81868.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 3_1_place_gp_skip_io | 4.5 | overflow best 0.2641 last 0.2641 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | 4_1_cts | 4.4 | last meaningful line 0.0 h ago (3228/3228 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | 4_1_cts | 4.4 | last meaningful line 0.0 h ago (2723/2723 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 3_1_place_gp_skip_io | 4.5 | overflow best 0.5355 last 0.5355 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 3_1_place_gp_skip_io | 4.5 | overflow best 0.487 last 0.487 rows 35 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 4_1_cts | 4.5 | last meaningful line 0.1 h ago (44/44 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 3_5_place_dp | 2.8 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 4_1_cts | 4.5 | last meaningful line 0.0 h ago (3170/3171 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 4.4 | last meaningful line 0.1 h ago (195/198 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-eng__t1-1558999 | eng__t1 | 5_1_grt | 2.0 | last meaningful line 0.8 h ago (191/197 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 5_1_grt | 4.4 | last meaningful line 0.1 h ago (197/201 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 10.3 | drt_violations best 5167 last 5167 rows 12 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 3.0 | last meaningful line 0.0 h ago (7496/7496 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | hold_gate | 4.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 4.4 | last meaningful line 0.8 h ago (207/213 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t24__cl2456157b-1317854 | ot_s81sl_leaf__t24 | 3_5_place_dp | 2.1 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 4.4 | last meaningful line 0.8 h ago (205/211 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-3149151 | sle_ctl | 3_3_place_gp | 1.1 | overflow best 0.1705 last 0.1705 rows 37 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3682021 | sle_hc0 | 3_4_place_resized | 0.9 | repair_Remaining best 41630 last 41630 rows 328 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | postcts_gate_FF | 10.3 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-2719308 | sle_su_c | 3_3_place_gp | 1.4 | overflow best 0.201 last 0.2059 rows 44 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | generate_abstract | 11.6 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | postcts_gate_TT | 11.2 | last meaningful line -0.0 h ago (72953/72953 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-148484-8382 | 148484 | ot_s81sl_xrt1__fix | 0.6 | last meaningful line 0.0 h ago (1210/1210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | otc-2656503-353 | 2656503 | ot_s81sl_xrt1__fix | 1.4 | last meaningful line 0.0 h ago (1354/1354 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.5 h ago (203/224 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 4.9 | last meaningful line 0.7 h ago (254/1423 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 49104 last 49104 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3626195 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8533 last 0.8533 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 63390.8 last 63390.8 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-4048612 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (201/205 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 0.8 h ago (131/131 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.4 | last meaningful line 0.1 h ago (45/45 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 9.8 | last meaningful line 2.0 h ago (233/1712 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2744267 | hd_turn_a | 5_2_route | 0.6 | drt_violations best 5492 last 5492 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2585034 | kv3_io_ft | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (423/448 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v3-1286721 | kv3_pc_v3 | 3_4_place_resized | 1.3 | last meaningful line 0.1 h ago (375/375 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t4-3639183 | ot_s81sl_kv_leaf__t4 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.5 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 4.2 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | pregrt_ff_hold | 2.0 | repair_TNS best 7048.35 last 7048.35 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-3630514 | ot_s81sl_leaf__t44 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (124/124 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (190/203 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-2733013 | sle_fw_v1 | 3_3_place_gp | 0.6 | overflow best 0.3396 last 0.3396 rows 18 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-sle_st_a_v1__cl67389ecd-3606635 | sle_st_a_v1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2632859 | slice_station__t12 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | pregrt_ff_hold | 2.0 | repair_TNS best 16329.6 last 16329.6 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-slice_station__t52-3617204 | slice_station__t52 | 3_3_place_gp | 0.4 | overflow best 0.3961 last 0.3961 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_fe_v2__clf110fab2-850187 | slw_fe_v2 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-2734287 | slw_hc0 | 3_3_place_gp | 0.6 | overflow best 0.2068 last 0.2068 rows 45 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | fable-lep0n-sta-3578726 | fable-lep0n-sta | - | 0.4 |  | NO-DATA: no log found |  |
| intel2 | otc-1734334-4594 | 1734334 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i2-4136869 | eco_20261122_054330_1688646-i2 | 5_2_route | 0.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2275367-2185 | 2275367 | - | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 50.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_1_grt | 1.8 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 10.8 | drt_violations best 4374 last 20511 rows 18 | before-window best 86318, window best 4374 | PROGRESS: drt_violations improved 94.9 % in window |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 9.4 | drt_violations best 11 last 11 rows 39 | before-window best 144464, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 54.5 | last meaningful line 2.1 h ago (1560/1560 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | 5_1_grt | 2.0 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 5_1_grt | 2.2 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 4_1_cts | 4.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 20.9 | drt_violations best 49344 last 49344 rows 15 | before-window best 51519, window best 49344 | PROGRESS: drt_violations improved 4.2 % in window |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 20.4 | drt_violations best 597 last 2670 rows 35 | before-window best 597, window best 1269 | PROGRESS: drt_violations: falling inside the active iteration (2670 -> 2509) |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 20.2 | drt_violations best 43966 last 43966 rows 15 | before-window best 46518, window best 43966 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 9.1 | drt_violations best 0 last 0 rows 10 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 10.9 | drt_violations best 72 last 72 rows 54 | before-window best 39741, window best 72 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 9.8 | drt_violations best 5445 last 5445 rows 13 | before-window best 13686, window best 5445 | PROGRESS: drt_violations improved 60.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | 5_1_grt | 4.0 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 5_1_grt | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 11.9 | drt_violations best 5193 last 5193 rows 12 | before-window best 15183, window best 5193 | PROGRESS: drt_violations improved 65.8 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 7.4 | drt_violations best 1 last 49 rows 34 | before-window best 20664, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_1_grt | 0.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_ftm-3606558 | coll_ftm | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
