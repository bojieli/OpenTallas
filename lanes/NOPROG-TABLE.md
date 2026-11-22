# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 08:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-LABEL': 38, 'NO-DATA': 19, 'YOUNG': 223, 'EXCLUDED': 2, 'KEEP': 2, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -493.23 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 17.2 | last meaningful line 15.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 15.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 7.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 9.5 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:22677 -> 10:22390 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 46.9 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:61583 -> 10:70130 | GRT-LABEL: DESIGN-FAIL: overflow 70130 at round 10 > 1000 |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 61.3 | grt rounds 6 overflow 5:9213 -> 10:5212 -> 15:3426 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:21001 -> 10:20178 | GRT-LABEL: DESIGN-FAIL: overflow 20178 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:11292 -> 10:2889 -> 15:1834 | GRT-LABEL: DESIGN-FAIL: overflow 2889 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:66243 -> 10:59241 | GRT-LABEL: DESIGN-FAIL: overflow 59241 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:38250 -> 10:24305 -> 15:17060 | GRT-LABEL: DESIGN-FAIL: overflow 24305 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:35380 -> 10:27892 -> 15:23179 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:50237 -> 10:35490 | GRT-LABEL: DESIGN-FAIL: overflow 35490 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:11908 -> 10:6080 -> 15:4269 | GRT-LABEL: DESIGN-FAIL: overflow 6080 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:7755 -> 10:3584 | GRT-LABEL: DESIGN-FAIL: overflow 3584 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:43402 -> 10:37170 | GRT-LABEL: DESIGN-FAIL: overflow 37170 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:36220 -> 10:27751 | GRT-LABEL: DESIGN-FAIL: overflow 27751 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:14948 -> 10:4450 | GRT-LABEL: DESIGN-FAIL: overflow 4450 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:38276 -> 10:36558 | GRT-LABEL: DESIGN-FAIL: overflow 36558 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:49663 -> 10:35602 | GRT-LABEL: DESIGN-FAIL: overflow 35602 at round 10 > 1000 |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 40.5 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 45.4 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 34.8 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 34.8 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 44.6 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 34.3 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 9.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:83933 -> 10:43 -> 15:18 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_1_grt | 4.0 | grt rounds 4 overflow 5:43074 -> 10:429 -> 15:42 -> 20:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 5_1_grt | 4.1 | grt rounds 2 overflow 5:4716 -> 10:2224 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:38006 -> 10:19657 -> 15:9316 | GRT-LABEL: DESIGN-FAIL: overflow 19657 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:2796 -> 10:1155 | GRT-LABEL: DESIGN-FAIL: overflow 1155 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 59.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 41.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-col-h9-r0-p1--t1--pva2e3974f-grt-1408068 | col-h9-r0-p1--t1--pva2e3974f-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 82592.2 last 82592.2 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | hold_gate | 0.7 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 1233.6 last 1233.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3565/3566 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3715/3715 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-1491393 | kv3_sys_c | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (354/354 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.0 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 3.4 | last meaningful line 0.3 h ago (204/208 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 5.3 | last meaningful line 0.5 h ago (224/1427 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | postcts_gate_FF | 9.6 | last meaningful line 0.1 h ago (1179/1179 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | generate_abstract | 10.0 | last meaningful line 0.2 h ago (326/326 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | postcts_gate_FF | 9.8 | last meaningful line 0.1 h ago (766/766 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 9.7 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1t-2778713 | eco_20261122_144137_2274607-i1t | 5_2_route | 1.5 | drt_violations best 62976 last 62976 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | tt_setup_repair_grt | 3.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 3.5 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 3.5 | last meaningful line 0.0 h ago (251/252 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 3.5 | last meaningful line 0.8 h ago (197/222 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 3.5 | overflow best 0.4169 last 0.4169 rows 32 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 3.5 | overflow best 0.6461 last 0.6481 rows 24 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 3.5 | overflow best 0.7274 last 0.7297 rows 13 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 3.5 | overflow best 0.6508 last 0.6508 rows 25 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | 3_4_place_resized | 3.5 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 3.5 | overflow best 0.757 last 0.757 rows 2 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 3.5 | overflow best 0.7376 last 0.7595 rows 9 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 3.5 | last meaningful line 1.0 h ago (201/210 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | 5_1_grt | 3.4 | last meaningful line 0.5 h ago (204/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 3.4 | last meaningful line 0.3 h ago (203/210 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 3.4 | last meaningful line 0.8 h ago (202/208 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 3.4 | last meaningful line 0.8 h ago (204/215 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 3.4 | last meaningful line 1.5 h ago (201/210 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 3.4 | last meaningful line 0.8 h ago (207/213 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 3.4 | last meaningful line 2.0 h ago (201/210 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (204/205 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | pregrt_ff_hold | 3.4 | repair_TNS best 52932 last 52932 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 5_1_grt | 3.4 | last meaningful line 0.3 h ago (202/206 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (195/208 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 10.0 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | postcts_gate_TT | 10.0 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | postcts_gate_TT | 10.0 | last meaningful line 0.0 h ago (393/393 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | postcts_gate_TT | 10.0 | last meaningful line -0.0 h ago (83768/83768 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 10.0 | drt_violations best 78672 last 78672 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 10.0 | drt_violations best 77889 last 77889 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | postcts_gate_TT | 10.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 10.0 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 10.0 | repair_TNS best 47990.8 last 47990.8 rows 5 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | postcts_gate_TT | 10.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | postcts_gate_TT | 10.0 | last meaningful line 0.2 h ago (847/847 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | postcts_gate_FF | 10.0 | last meaningful line 0.1 h ago (1115/1115 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 10.0 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_2_route | 3.0 | drt_violations best 60160 last 60160 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-ot-s81sl-kv-leaf--t1-grt-2549460 | ot-s81sl-kv-leaf--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-st-a-v2--pv4242de79-grt-2466663 | sle-st-a-v2--pv4242de79-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 50604.1 last 50604.1 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 56787.8 last 56787.8 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 55220.5 last 55220.5 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 15004.3 last 15004.3 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1106130 | col_h9_r0_p4__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 61395.6 last 61395.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-coll_core-1737007 | coll_core | 2_1_floorplan | 0.5 | last meaningful line 0.0 h ago (1424/1424 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 228722 last 228722 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-hd_turn_a-1541900 | hd_turn_a | 5_2_route | 0.6 | drt_violations best 5474 last 5474 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_turn_a-1543246 | hd_turn_a | 5_2_route | 0.6 | drt_violations best 5492 last 5492 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-native59-1738201 | native59 | 2_1_floorplan | 0.5 | repair_Viol best 18803 last 18803 rows 911 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4259/4259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (208/211 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 4_1_cts | 3.4 | last meaningful line 0.2 h ago (6825/6825 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 3_3_place_gp | 3.4 | overflow best 0.5618 last 0.5618 rows 34 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (9083/9083 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl69f5e854-2551268 | sle_fw_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 10.0 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 10.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1631153 | sle_hc1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.6738 last 0.6738 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1615786 | sle_su_l1 | 3_3_place_gp | 0.6 | overflow best 0.0995 last 0.0995 rows 47 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_2_route | 4.2 | last meaningful line 0.1 h ago (254/255 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-1706410 | slw_fw_v3 | 3_3_place_gp | 0.5 | overflow best 0.3859 last 0.3859 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 6_report | 10.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1947924-28083 | 1947924 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.4 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-1986186-11442 | 1986186 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.4 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.4 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.4 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2062410-18700 | 2062410 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.3 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.3 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-2302603-24753 | 2302603 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.2 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2348189-14156 | 2348189 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.2 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2521693-2951 | 2521693 | ot_hdc_v41x_attn_tr_x_xoff0__orig | 0.1 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-fin-3246240 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-ot-s81sl-kv-leaf--t4-grt-124053 | ot-s81sl-kv-leaf--t4-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-ot-s81sl-kv-leaf--t4-grt-94445 | ot-s81sl-kv-leaf--t4-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t53--clb66fa5cb-grt-54594 | ot-s81sl-leaf--t53--clb66fa5cb-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2857/2857 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 151547 last 151547 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 102659 last 102659 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 49434.6 last 49434.6 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2858145 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.7 | overflow best 0.3986 last 0.3989 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 93931.6 last 93931.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 3.9 | last meaningful line 1.3 h ago (209/229 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | tt_setup_repair | 0.6 | repair_Violations best 7424 last 7424 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3856028 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.3 | overflow best 0.3894 last 0.3985 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 9.2 | drt_violations best 4797 last 4797 rows 10 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-3901928 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3105 last 0.3435 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3794666 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 4_1_cts | 0.0 | last meaningful line -0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (3308/3308 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | 3_3_place_gp | 3.3 | overflow best 0.6343 last 0.6343 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_1_floorplan | 3.0 | last meaningful line 2.5 h ago (1424/1424 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 5.9 | last meaningful line 0.5 h ago (1068/1083 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (2962/2962 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t73-3375193 | ot_s81sl_leaf__t73 | 3_3_place_gp | 0.6 | overflow best 0.6289 last 0.6289 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (4045/4045 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | otc-2657484-2996 | 2657484 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco-i1-3698803 | eco-i1 | 5_2_route | 2.5 | drt_violations best 6 last 6 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (237/1336 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv4754d912-grt-1603167 | col-h9-r2--t1--clce45cab5--pv4754d912-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t29-grt-1706308 | ot-s81sl-leaf--t29-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t34-grt-1602178 | ot-s81sl-leaf--t34-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t39-dump-1745243 | ot-s81sl-leaf--t39-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t39-grt-1745243 | ot-s81sl-leaf--t39-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t41-grt-1601787 | ot-s81sl-leaf--t41-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 8.1 | drt_violations best 75008 last 75008 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 5.9 | drt_violations best 60755 last 60755 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 3.6 | last meaningful line 0.1 h ago (211/214 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 9.9 | drt_violations best 53713 last 53713 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-87338 | hd_ctl | 5_2_route | 1.0 | last meaningful line 0.1 h ago (252/253 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 3.4 | last meaningful line 0.5 h ago (201/208 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 9.9 | last meaningful line 0.1 h ago (265/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | postcts_gate_FF | 9.9 | last meaningful line 0.2 h ago (834/834 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | postcts_gate_TT | 10.5 | last meaningful line -0.0 h ago (74180/74180 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 10.3 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | postcts_gate_FF | 9.9 | last meaningful line -0.0 h ago (87663/87663 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | postcts_gate_FF | 9.9 | last meaningful line 0.2 h ago (844/844 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 9.9 | drt_violations best 72 last 72 rows 50 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | otc-4183895-10969 | 4183895 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_1_grt | 1.2 | last meaningful line 0.8 h ago (232/619 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco2-i2-3675346 | eco2-i2 | 5_2_route | 1.4 | drt_violations best 2413 last 2413 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | prd-fin-1034174 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h10-r0-p1--t1--cl574cc59d--pvb095fa2f-grt-2865196 | col-h10-r0-p1--t1--cl574cc59d--pvb095fa2f-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t40--cl86ea32b3--sid5S-grt-2976916 | ot-s81sl-leaf--t40--cl86ea32b3--sid5S-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 67815.3 last 67815.3 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | 5_1_grt | 4.4 | last meaningful line 2.0 h ago (203/212 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 4.4 | last meaningful line 2.0 h ago (203/212 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 69202.3 last 69202.3 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 48166.6 last 48166.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 3.2 | last meaningful line 0.8 h ago (201/221 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 71892 last 71892 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1497604 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.2912 last 0.2912 rows 37 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-1782182 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.6 | overflow best 0.425 last 0.425 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1398169 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.8 | overflow best 0.4663 last 0.4663 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_1_grt | 3.2 | last meaningful line 1.8 h ago (198/226 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (7102/7102 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 3.2 | last meaningful line 1.5 h ago (126/126 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | selrange | 3.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | selrange | 3.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 3.2 | last meaningful line 1.5 h ago (132/132 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 3.2 | last meaningful line 1.5 h ago (128/128 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 3_4_place_resized | 3.2 | repair_Remaining best 222830 last 222830 rows 156 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 1.5 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 3.2 | repair_Remaining best 263755 last 263755 rows 95 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 3.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_5_place_dp | 3.2 | last meaningful line 2.5 h ago (41/41 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 9.0 | drt_violations best 8258 last 8258 rows 8 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 1.7 | last meaningful line 1.5 h ago (7084/7084 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 4_1_cts | 3.2 | last meaningful line 0.0 h ago (3120/3120 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t24__cl2456157b-1317854 | ot_s81sl_leaf__t24 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (185/185 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 3.2 | last meaningful line 0.1 h ago (152/152 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t51-2973305 | ot_s81sl_leaf__t51 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t61-353186 | ot_s81sl_leaf__t61 | 3_5_place_dp | 1.4 | last meaningful line 0.1 h ago (39/39 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t67-376168 | ot_s81sl_leaf__t67 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (3521/3521 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-2719308 | sle_su_c | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2461538 | slw_hc0 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 10.3 | drt_violations best 6185 last 6185 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | postcts_gate_TT | 10.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2656503-353 | 2656503 | dsdv_gunit_l4r__fix | 0.2 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2869943-31749 | 2869943 | dsdv_gunit_l4r__fix | 0.1 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2957568-1953 | 2957568 | dsdv_gunit_l4r__fix | 0.0 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2959473-15421 | 2959473 | s81.c.ot_s81_svc_smr | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-count-p1_bc-1508898 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 6.2 | drt_violations best 1 last 12 rows 26 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | ap-ageom-kw-ot-s81sl-leaf--t1-grt-1841330 | ot-s81sl-leaf--t1-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | ap-ageom-kw-ot-s81sl-leaf--t1-grt-1872531 | ot-s81sl-leaf--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 3.1 | last meaningful line 0.5 h ago (203/211 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-114446 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.9 | overflow best 0.3922 last 0.3922 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | last meaningful line 1.5 h ago (210/225 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 49104 last 49104 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3822263 | col_h9_r0_p3__t1 | 3_3_place_gp | 1.1 | overflow best 0.2722 last 0.2722 rows 36 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1074022 | col_h9_r1__t1 | 3_3_place_gp | 0.4 | overflow best 0.3055 last 0.3055 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1081901 | col_h9_r1__t1 | 3_3_place_gp | 0.4 | overflow best 0.3069 last 0.3069 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 63390.8 last 63390.8 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 59003.5 last 59003.5 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-4048612 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 72339.6 last 72339.6 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-1300988 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3711 last 0.3711 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 111710 last 111710 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-coll_ftm-2637008 | coll_ftm | 5_2_route | 3.2 | drt_violations best 380 last 380 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | sdc_lint | 1.5 | last meaningful line 1.5 h ago (1/1 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_kv512_C__t1-524813 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 2.4 | repair_Remaining best 306178 last 306178 rows 65 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.4 | repair_TNS best 102526 last 102526 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.8 | repair_Remaining best 131451 last 131451 rows 192 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 3_5_place_dp | 4.1 | last meaningful line 0.1 h ago (121/121 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-glue-813028 | glue | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-gunit__t1-533357 | gunit__t1 | 3_5_place_dp | 2.4 | last meaningful line 1.8 h ago (40/40 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_cor_v1-32063 | kv3_io_cor_v1 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v3-1286721 | kv3_pc_v3 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7658 last 0.7658 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2947333 | ot_s81sl_kv_leaf__t3 | 3_3_place_gp | 1.5 | overflow best 0.6461 last 0.6461 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 5.5 | last meaningful line 0.1 h ago (198/211 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-77059 | ot_s81sl_kv_leaf__t5 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.9192 last 0.9287 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-2985736 | ot_s81sl_leaf__t10 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-4113223 | ot_s81sl_leaf__t11 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t16-961104 | ot_s81sl_leaf__t16 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t23-1069009 | ot_s81sl_leaf__t23 | 3_2_place_iop | 0.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3-1321533 | ot_s81sl_leaf__t40 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t40__clf8bbdae1-292719 | ot_s81sl_leaf__t40 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (3863/3864 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (3609/3609 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (4409/4409 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4094/4094 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t74-3160290 | ot_s81sl_leaf__t74 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-691417 | sle_hc0 | 3_3_place_gp | 0.6 | overflow best 0.6735 last 0.6735 rows 30 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-1751047 | sle_stm_v2 | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (632/632 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (3912/3912 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__clf110fab2-850187 | slw_fe_v2 | 3_3_place_gp | 0.5 | overflow best 0.5949 last 0.5949 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_st_a_v2__clf4365a62-1475380 | slw_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.5445 last 0.5459 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_stm_v2__cl9beb65e6-770558 | slw_stm_v2 | 3_3_place_gp | 0.5 | overflow best 0.5102 last 0.5102 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | otc-1734334-4594 | 1734334 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i2-2979122 | eco_20261122_041142_2199995-i2 | 5_2_route | 1.4 | drt_violations best 25 last 25 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i1-206630 | eco_20261122_054330_1688646-i1 | 5_2_route | 0.8 | last meaningful line 0.1 h ago (227/228 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | otc-2576989-111 | 2576989 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-1701663-21848 | 1701663 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 49.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv45d0c698-794500 | col_h9_r2__t1 | 3_5_place_dp | 0.5 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 8.0 | drt_violations best 28 last 30 rows 55 | before-window best 553, window best 28 | PROGRESS: drt_violations improved 94.9 % in window |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 9.8 | drt_violations best 4374 last 4374 rows 17 | before-window best 86318, window best 4374 | PROGRESS: drt_violations improved 94.9 % in window |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 8.4 | drt_violations best 16 last 67 rows 18 | before-window best 144464, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 53.5 | last meaningful line 1.1 h ago (1560/1560 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 5_1_grt | 3.8 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | pregrt_ff_hold | 1.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | 4_1_cts | 1.0 | repair_Violations best 0 last 0 rows 5 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 19.9 | drt_violations best 49344 last 49344 rows 15 | before-window best 52295, window best 49344 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 19.4 | drt_violations best 597 last 8018 rows 34 | before-window best 1045, window best 597 | PROGRESS: drt_violations improved 42.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 19.2 | drt_violations best 43966 last 43966 rows 15 | before-window best 47754, window best 43966 | PROGRESS: drt_violations improved 7.9 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 8.8 | drt_violations best 8267 last 8267 rows 11 | before-window best 85188, window best 8267 | PROGRESS: drt_violations improved 90.3 % in window |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_1_grt | 3.2 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-eng__t1-1558999 | eng__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | 5_1_grt | 2.8 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 9.1 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 10.7 | drt_violations best 7622 last 7622 rows 11 | before-window best 18627, window best 7622 | PROGRESS: drt_violations improved 59.1 % in window |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
