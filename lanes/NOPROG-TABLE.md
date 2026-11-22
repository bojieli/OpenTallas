# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 07:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 33, 'YOUNG': 239, 'NO-DATA': 12, 'KEEP': 2, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 9.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 16.7 | last meaningful line 15.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 15.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 7.2 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 9.0 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 2.9 | grt rounds 3 overflow 5:26250 -> 10:22390 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: overflow 22390 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 46.4 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 60.8 | grt rounds 6 overflow 5:9167 -> 10:5212 -> 15:3426 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | 5_1_grt | 3.0 | grt rounds 3 overflow 5:8312 -> 10:170 -> 15:20 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:11292 -> 10:2889 | GRT-LABEL: DESIGN-FAIL: overflow 2889 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:66243 -> 10:59241 | GRT-LABEL: DESIGN-FAIL: overflow 59241 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:38250 -> 10:24305 | GRT-LABEL: DESIGN-FAIL: overflow 24305 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:35380 -> 10:27892 | GRT-LABEL: DESIGN-FAIL: overflow 27892 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:50237 -> 10:35490 | GRT-LABEL: DESIGN-FAIL: overflow 35490 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:11908 -> 10:6080 | GRT-LABEL: DESIGN-FAIL: overflow 6080 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:14948 -> 10:4450 | GRT-LABEL: DESIGN-FAIL: overflow 4450 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:38276 -> 10:36558 | GRT-LABEL: DESIGN-FAIL: overflow 36558 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:49663 -> 10:35602 | GRT-LABEL: DESIGN-FAIL: overflow 35602 at round 10 > 1000 |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 4.7 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 40.0 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 44.9 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 34.3 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 34.3 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 44.1 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 33.8 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 8.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:83933 -> 10:43 -> 15:18 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_1_grt | 3.5 | grt rounds 4 overflow 5:43074 -> 10:429 -> 15:42 -> 20:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 5_1_grt | 3.6 | grt rounds 2 overflow 5:4716 -> 10:2224 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:38006 -> 10:19657 | GRT-LABEL: DESIGN-FAIL: overflow 19657 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 58.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 41.5 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 82592.2 last 82592.2 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | tt_setup_repair | 0.3 | repair_Viol best 34 last 34 rows 26 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3846806 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3471661 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.6 | overflow best 0.198 last 0.198 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3092/3092 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 49340.3 last 49340.3 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 1.3 | last meaningful line 0.1 h ago (44/44 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 2.9 | last meaningful line 0.8 h ago (203/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (195/201 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | postcts_gate_FF | 9.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 6_report | 9.5 | last meaningful line 0.1 h ago (367/367 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | postcts_gate_TT | 9.3 | last meaningful line 0.1 h ago (1636/1636 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 9.2 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 9.2 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-3166564-12863 | 3166564 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1t-2778713 | eco_20261122_144137_2274607-i1t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 3.0 | last meaningful line 0.0 h ago (253/254 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | tt_setup_repair_grt | 3.0 | repair_Violations best 19 last 60 rows 12 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (197/212 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 3.0 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 3.0 | last meaningful line 0.1 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | 3_1_place_gp_skip_io | 3.0 | overflow best 0.2223 last 0.2287 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 3.0 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | 3_3_place_gp | 3.0 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | 3_1_place_gp_skip_io | 3.0 | overflow best 0.4155 last 0.4155 rows 34 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | 3_1_place_gp_skip_io | 3.0 | overflow best 0.3063 last 0.3063 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2767328 | dsdv_slice_lepw_mus_C__t1 | 4_1_cts | 2.9 | last meaningful line 0.0 h ago (3368/3369 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 2.9 | repair_TNS best 50656.2 last 50656.2 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | hold_gate | 2.9 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 3.0 | last meaningful line 0.5 h ago (201/207 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (204/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 2.9 | last meaningful line 0.7 h ago (204/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 2.9 | last meaningful line 0.3 h ago (202/206 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | pregrt_ff_hold | 2.9 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 2.9 | last meaningful line 0.3 h ago (204/210 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 2.9 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 2.9 | last meaningful line 1.0 h ago (201/208 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 2.9 | last meaningful line 0.8 h ago (202/210 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 2.9 | last meaningful line 0.3 h ago (207/211 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 2.9 | last meaningful line 1.0 h ago (200/209 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 2.9 | last meaningful line 1.5 h ago (201/209 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 4_1_cts | 2.9 | last meaningful line 0.0 h ago (5512/5512 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 9.5 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | tt_setup_repair_grt | 9.5 | repair_Violations best 43 last 86 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | tt_setup_measure_grt | 9.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | postcts_gate_TT | 9.5 | last meaningful line 0.0 h ago (739/739 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 9.5 | drt_violations best 78672 last 78672 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 9.5 | drt_violations best 77889 last 77889 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | tt_setup_repair_grt | 9.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | postcts_gate_TT | 9.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 9.5 | last meaningful line 3.3 h ago (220/1007 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | tt_setup_repair_grt | 9.5 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | postcts_gate_TT | 9.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | postcts_gate_FF | 9.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 9.5 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_2_route | 2.5 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3946946 | col_h10_r0_p1__t1 | 3_3_place_gp | 1.1 | overflow best 0.2215 last 0.2215 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 50604.1 last 50604.1 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 56787.8 last 56787.8 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 55220.5 last 55220.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | tt_setup_measure | 0.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-897645 | col_h10_r1__t1 | 3_4_place_resized | 0.4 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-911267 | col_h10_r2__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 39248.2 last 39248.2 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1106130 | col_h9_r0_p4__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3542/3542 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | 3_4_place_resized | 0.5 | last meaningful line -0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-coll_core-1737007 | coll_core | selrange | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.0 | repair_TNS best 228722 last 228722 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_turn_a-1541900 | hd_turn_a | 3_3_place_gp | 0.1 | overflow best 0.4147 last 0.4493 rows 28 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-hd_turn_a-1543246 | hd_turn_a | 3_3_place_gp | 0.1 | overflow best 0.4096 last 0.4611 rows 27 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 8930.77 last 8930.77 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-native59-1738201 | native59 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2813014 | ot_s81sl_kv_leaf__t1 | 3_3_place_gp | 1.7 | overflow best 0.1998 last 0.1998 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-3941151 | ot_s81sl_leaf__t22 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3944811 | ot_s81sl_leaf__t47 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 4_1_cts | 2.9 | last meaningful line 0.0 h ago (6770/6770 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.1967 last 0.1967 rows 45 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 2.6 | last meaningful line 0.5 h ago (9064/9064 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 9.5 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | postcts_gate_FF | 9.5 | last meaningful line -0.0 h ago (17740/17740 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1631153 | sle_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1615786 | sle_su_l1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_2_route | 3.7 | last meaningful line 0.1 h ago (245/245 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-1706410 | slw_fw_v3 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (246/246 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 9.5 | drt_violations best 229 last 229 rows 4 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | tt_setup_repair | 0.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-457717-18262 | 457717 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-3246240 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_1_grt | 1.0 | last meaningful line 0.5 h ago (235/1313 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-kv3-hub-Ei-grt-3420400 | kv3-hub-Ei-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 49434.6 last 49434.6 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2858145 | col_h9_r0_p1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3105/3106 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 3.4 | last meaningful line 0.8 h ago (209/222 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2974/2975 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 8.7 | drt_violations best 5325 last 5325 rows 7 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2898181 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.3063 last 0.3321 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2985/2985 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.7598 last 0.7598 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_1_floorplan | 2.5 | last meaningful line 2.0 h ago (1424/1424 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3320552 | kv3_io_cor_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2523/2523 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t4-3684447 | ot_s81sl_kv_leaf__t4 | 3_4_place_resized | 2.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2510495 | ot_s81sl_leaf__t53 | 3_3_place_gp | 0.5 | overflow best 0.5741 last 0.5779 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-558414 | ot_s81sl_leaf__t65 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t70-823669 | ot_s81sl_leaf__t70 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t73-3375193 | ot_s81sl_leaf__t73 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-phy__t1-2971093 | phy__t1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (3956/3956 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t45-2936664 | slice_station__t45 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.3907 last 0.3907 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-2657484-2996 | 2657484 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-3271975-5314 | 3271975 | qwen_compute.t.qfd_qc_coll_n_part | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco-i1-3698803 | eco-i1 | 5_2_route | 2.0 | drt_violations best 6 last 6 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv4754d912-grt-733928 | col-h9-r2--t1--clce45cab5--pv4754d912-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 7.6 | drt_violations best 75008 last 75008 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 5.4 | drt_violations best 60755 last 60755 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 9.4 | drt_violations best 53713 last 53713 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-87338 | hd_ctl | postcts_gate_FF | 0.5 | last meaningful line 0.0 h ago (900/900 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (201/203 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (203/210 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 9.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | postcts_gate_FF | 9.4 | last meaningful line 0.1 h ago (383/383 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | postcts_gate_TT | 10.0 | last meaningful line 0.1 h ago (1189/1189 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | postcts_gate_FF | 9.8 | last meaningful line -0.0 h ago (78433/78433 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | postcts_gate_FF | 9.4 | last meaningful line 0.1 h ago (840/840 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | postcts_gate_FF | 9.4 | last meaningful line 0.2 h ago (405/405 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 9.4 | drt_violations best 72 last 72 rows 43 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | fable-lep0n-paireco-232399 | fable-lep0n-paireco | eco | 0.4 | last meaningful line 0.0 h ago (374/374 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-4183895-10969 | 4183895 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 5.3 | drt_violations best 7925 last 7925 rows 3 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_1_grt | 0.7 | repair_Remaining best 414481 last 414481 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | prd-eco2-i2-3675346 | eco2-i2 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (238/238 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | ap-ageom-kw-eng--t1-grt-2179142 | eng--t1-grt | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t28-grt-2208342 | ot-s81sl-leaf--t28-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t60-grt-2267288 | ot-s81sl-leaf--t60-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t9-grt-2343743 | ot-s81sl-leaf--t9-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.0 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3818192 | col_h10_r0_p1__t1 | 3_5_place_dp | 1.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.7 h ago (203/211 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.7 h ago (203/211 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 69202.3 last 69202.3 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 48166.6 last 48166.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 3.0 | last meaningful line 0.5 h ago (201/216 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 31666.7 last 31666.7 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 71892 last 71892 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1497604 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.9186 last 0.9186 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-1782182 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8151 last 0.8653 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1398169 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.7029 last 0.7029 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_1_grt | 3.0 | last meaningful line 1.5 h ago (198/224 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_1_grt | 3.0 | repair_TNS best 26.86 last 26.86 rows 3 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (7076/7076 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 3.0 | last meaningful line 1.2 h ago (126/126 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | selrange | 2.9 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | selrange | 2.9 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 3.0 | last meaningful line 1.2 h ago (132/132 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 3.0 | last meaningful line 1.3 h ago (128/128 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 3_4_place_resized | 3.0 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 3_1_place_gp_skip_io | 1.3 | overflow best 0.6933 last 0.6933 rows 29 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 3.0 | repair_Remaining best 310755 last 310755 rows 48 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 2.9 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 3.0 | repair_TNS best 33967.6 last 33967.6 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-eng__t1-1558999 | eng__t1 | tt_setup_repair | 0.5 | repair_Viol best 653 last 653 rows 51 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_5_place_dp | 2.9 | last meaningful line 2.3 h ago (41/41 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 8.8 | drt_violations best 8743 last 8743 rows 7 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 1.5 | last meaningful line 1.2 h ago (7084/7084 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (2879/2879 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t24__cl2456157b-1317854 | ot_s81sl_leaf__t24 | 3_3_place_gp | 0.6 | overflow best 0.6175 last 0.6175 rows 16 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t61-353186 | ot_s81sl_leaf__t61 | 3_3_place_gp | 1.2 | overflow best 0.2482 last 0.2482 rows 39 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t67-376168 | ot_s81sl_leaf__t67 | 3_3_place_gp | 1.2 | overflow best 0.1941 last 0.1941 rows 41 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 4_1_cts | 2.9 | last meaningful line 0.0 h ago (3445/3445 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (150/150 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 8.8 | last meaningful line 2.2 h ago (223/1170 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2461538 | slw_hc0 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (181/181 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 10.1 | drt_violations best 70451 last 70451 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | postcts_gate_TT | 9.7 | last meaningful line 0.2 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1974797-25147 | 1974797 | qwen_compute.t.slw_stm_v1__cl05fc43f7__cl389df4e9 | 0.3 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-2208612-11566 | 2208612 | ot_s81sl_xrt1__orig | 0.1 | last meaningful line 0.0 h ago (1227/1227 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-3428097-1823 | 3428097 | gen_lint_yosys | 1.7 | last meaningful line 1.7 h ago (1/1 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-1508898 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 5.9 | drt_violations best 1 last 1 rows 16 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | ap-ageom-kw-ot-s81sl-leaf--t57-grt-675898 | ot-s81sl-leaf--t57-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | ap-ageom-kw-ot-s81sl-leaf--t57-grt-682038 | ot-s81sl-leaf--t57-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3350921 | col_h10_r0_p4__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (203/205 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-114446 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.996 last 0.996 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-2844003 | col_h9_r0_p2__t1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 3.4 | last meaningful line 1.0 h ago (210/218 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3301/3301 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-3400705 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.8 | overflow best 0.1989 last 0.1989 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3822263 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.6954 last 0.6954 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | tt_setup_repair | 0.5 | repair_Viol best 533 last 533 rows 55 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 59003.5 last 59003.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-21801 | col_h9_r2__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-4048612 | col_h9_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 72339.6 last 72339.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-750143 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 230 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-684543 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 2770 last 2770 rows 963 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 111710 last 111710 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-coll_ftm-2637008 | coll_ftm | 5_2_route | 2.7 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_kv512_C__t1-524813 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.9 | overflow best 0.647 last 0.647 rows 24 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (4220/4220 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.3 | repair_Remaining best 235451 last 235451 rows 88 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 3_4_place_resized | 3.6 | repair_Remaining best 72502 last 72502 rows 282 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-glue-813028 | glue | 1_1_yosys_canonicalize | 0.0 | last meaningful line 0.0 h ago (243/243 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-gunit__t1-533357 | gunit__t1 | 3_5_place_dp | 1.9 | last meaningful line 1.3 h ago (40/40 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N_w-880189 | hd_lep0N_w | 4_2_tapbal_grt | 1.7 | last meaningful line 1.3 h ago (46/129 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_cor_v1-32063 | kv3_io_cor_v1 | 3_3_place_gp | 0.4 | overflow best 0.1827 last 0.1827 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2947333 | ot_s81sl_kv_leaf__t3 | 3_1_place_gp_skip_io | 1.0 | overflow best 0.9466 last 0.9541 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 5.0 | repair_Remaining best 163583 last 163583 rows 192 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-77059 | ot_s81sl_kv_leaf__t5 | 1_2_yosys | 0.4 | last meaningful line 0.0 h ago (845/845 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-2405593 | ot_s81sl_leaf__t1 | 3_3_place_gp | 1.2 | overflow best 0.3107 last 0.3107 rows 37 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-2985736 | ot_s81sl_leaf__t10 | 3_3_place_gp | 0.9 | last meaningful line 0.5 h ago (121/121 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-4113223 | ot_s81sl_leaf__t11 | 3_3_place_gp | 0.5 | last meaningful line 0.2 h ago (90/90 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t15-269879 | ot_s81sl_leaf__t15 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t3-2358697 | ot_s81sl_leaf__t3 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t34-3146079 | ot_s81sl_leaf__t34 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t39-3134440 | ot_s81sl_leaf__t39 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t40__clf8bbdae1-292719 | ot_s81sl_leaf__t40 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-3969220 | ot_s81sl_leaf__t50 | 3_3_place_gp | 0.5 | overflow best 0.4109 last 0.4109 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (71/71 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3722/3722 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-3146562 | ot_s81sl_leaf__t68 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t74-3160290 | ot_s81sl_leaf__t74 | 3_3_place_gp | 0.9 | last meaningful line 0.5 h ago (86/86 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-691417 | sle_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (291/291 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3852/3853 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slw_stm_v2__cl9beb65e6-770558 | slw_stm_v2 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i2-2979122 | eco_20261122_041142_2199995-i2 | 5_2_route | 0.9 | drt_violations best 25 last 25 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i1-206630 | eco_20261122_054330_1688646-i1 | 5_2_route | 0.3 | last meaningful line 0.1 h ago (212/212 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 48.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv45d0c698-794500 | col_h9_r2__t1 | 1_synth | 0.0 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 7.5 | drt_violations best 28 last 30 rows 55 | before-window best 33979, window best 28 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 9.3 | drt_violations best 4691 last 4691 rows 16 | before-window best 86318, window best 4691 | PROGRESS: drt_violations improved 94.6 % in window |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 7.9 | drt_violations best 16 last 67 rows 18 | before-window best 144464, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 53.0 | last meaningful line 0.6 h ago (1560/1560 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 19.4 | drt_violations best 49344 last 49344 rows 15 | before-window best 52295, window best 49344 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 7 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 18.9 | drt_violations best 597 last 8018 rows 34 | before-window best 1045, window best 597 | PROGRESS: drt_violations improved 42.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 18.7 | drt_violations best 43966 last 43966 rows 15 | before-window best 47754, window best 43966 | PROGRESS: drt_violations improved 7.9 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 8.3 | drt_violations best 8267 last 8267 rows 11 | before-window best 85188, window best 8267 | PROGRESS: drt_violations improved 90.3 % in window |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.0 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 10.4 | drt_violations best 7622 last 7622 rows 11 | before-window best 23058, window best 7622 | PROGRESS: drt_violations improved 66.9 % in window |  |
| intel2 | dpkit-kv3_io_ft-304550 | kv3_io_ft | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
