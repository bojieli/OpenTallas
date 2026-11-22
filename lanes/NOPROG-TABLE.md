# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 07:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 23, 'NO-DATA': 25, 'YOUNG': 244, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 16.2 | last meaningful line 14.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 14.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1921258 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 4_1_cts | 1.0 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 8.5 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:26250 -> 10:22390 | GRT-LABEL: DESIGN-FAIL: overflow 22390 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 45.9 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 60.3 | grt rounds 6 overflow 5:9167 -> 10:5212 -> 15:3582 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | 5_1_grt | 2.5 | grt rounds 3 overflow 5:8312 -> 10:170 -> 15:20 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:11292 -> 10:2889 | GRT-LABEL: DESIGN-FAIL: overflow 2889 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:38250 -> 10:24305 | GRT-LABEL: DESIGN-FAIL: overflow 24305 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:35380 -> 10:27892 | GRT-LABEL: DESIGN-FAIL: overflow 27892 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:11908 -> 10:6080 | GRT-LABEL: DESIGN-FAIL: overflow 6080 at round 10 > 1000 |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 4.2 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 39.5 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 44.4 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 33.8 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 33.8 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 43.6 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 33.3 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_1_grt | 3.0 | grt rounds 4 overflow 5:43074 -> 10:429 -> 15:42 -> 20:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 5_1_grt | 3.1 | grt rounds 2 overflow 5:4716 -> 10:2224 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:38006 -> 10:19657 | GRT-LABEL: DESIGN-FAIL: overflow 19657 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 58.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 41.0 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-bk-sel--t2-grt-3642989 | bk-sel--t2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pvc11684b5-grt-3645310 | col-h9-r0-p3--t1--cl8ce97bcb--pvc11684b5-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 3.4 | last meaningful line 0.3 h ago (195/204 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3185962 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3055 last 0.3055 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3604/3604 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3471661 | col_h9_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 1110 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2137948 | col_h9_r0_p5__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3179547 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3029 last 0.3029 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 49340.3 last 49340.3 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 6.7 | last meaningful line 1.0 h ago (199/208 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | tt_setup_repair | 0.8 | repair_Viol best 787 last 787 rows 19 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 7.0 | drt_violations best 28 last 30 rows 55 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 8.8 | drt_violations best 4691 last 4691 rows 16 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-3035693 | ot_s81sl_leaf__t21 | 3_3_place_gp | 0.4 | overflow best 0.5835 last 0.5835 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-3038614 | ot_s81sl_leaf__t29 | 3_3_place_gp | 0.4 | overflow best 0.7011 last 0.7023 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | pregrt_ff_hold | 2.4 | repair_Violations best 3802 last 3802 rows 28 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t59-3028174 | ot_s81sl_leaf__t59 | 3_3_place_gp | 0.4 | overflow best 0.6094 last 0.6094 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | postcts_gate_TT | 8.6 | last meaningful line 0.1 h ago (1196/1196 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 9.0 | drt_violations best 4315 last 4315 rows 3 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | postcts_gate_TT | 8.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 8.7 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 8.7 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 4.2 | last meaningful line 1.0 h ago (199/208 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | otc-3166564-12863 | 3166564 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-3280936-12441 | 3280936 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (122269/122269 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 4.8 | last meaningful line 1.0 h ago (199/208 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | phscan-3442237 | phscan | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (3604/3604 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1t-2778713 | eco_20261122_144137_2274607-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | tt_setup_repair_grt | 2.5 | repair_Viol best 2396 last 2396 rows 75 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | 3_1_place_gp_skip_io | 2.5 | overflow best 0.8925 last 0.8925 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | 3_1_place_gp_skip_io | 2.5 | overflow best 0.9953 last 0.9953 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | 2_1_floorplan | 2.5 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | 3_1_place_gp_skip_io | 2.5 | overflow best 0.9855 last 0.9855 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | 3_1_place_gp_skip_io | 2.5 | overflow best 0.9952 last 0.9952 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | 1_2_yosys | 2.5 | last meaningful line 0.0 h ago (414/414 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | 1_synth | 2.5 | last meaningful line -0.0 h ago (1458/1458 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2767328 | dsdv_slice_lepw_mus_C__t1 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 2.4 | repair_TNS best 449415 last 449415 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (5062/5062 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (187/200 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 2.4 | last meaningful line 0.2 h ago (204/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | pregrt_ff_hold | 2.4 | repair_Violations best 4262 last 4276 rows 93 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 2.4 | last meaningful line 0.8 h ago (200/209 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (181/181 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | tt_setup_repair | 2.4 | repair_Violations best 3438 last 3670 rows 91 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (203/212 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 2.4 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 2.4 | last meaningful line 0.1 h ago (151/151 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (201/206 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (202/207 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 2.4 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (200/207 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (200/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 2.4 | last meaningful line 1.0 h ago (201/208 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (203/211 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 2.4 | repair_TNS best 753290 last 753290 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (5310/5310 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | pregrt_ff_hold | 2.4 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | tt_setup_repair | 2.4 | repair_Viol best 194 last 194 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 2.4 | last meaningful line 0.8 h ago (201/209 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | postcts_gate_FF | 9.0 | last meaningful line 0.2 h ago (1874/1874 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 9.0 | last meaningful line 0.0 h ago (1244/1250 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_1_grt | 9.0 | last meaningful line 0.0 h ago (1091/1091 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | postcts_gate_FF | 9.0 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 9.0 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | tt_setup_repair_grt | 9.0 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 9.0 | repair_TNS best 57541.4 last 57541.4 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 9.0 | last meaningful line 0.0 h ago (1329/1329 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | tt_setup_repair_grt | 9.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | postcts_gate_TT | 9.0 | last meaningful line -0.0 h ago (502/502 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (261/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_2_route | 2.0 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-bk-sel--t2-grt-587874 | bk-sel--t2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-col-h10-r0-p1--t1--cl574cc59d--pv67036687-grt-660013 | col-h10-r0-p1--t1--cl574cc59d--pv67036687-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-dsdv-slice-kv512-C--t1-grt-660547 | dsdv-slice-kv512-C--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3946946 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8955 last 0.8955 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pv5b623e07-4101554 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.5 | overflow best 0.4662 last 0.4662 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3052/3052 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3032/3032 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | pregrt_ff_hold | 0.3 | repair_TNS best 39248.2 last 39248.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4214/4214 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2484/2484 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2813014 | ot_s81sl_kv_leaf__t1 | 3_1_place_gp_skip_io | 1.2 | overflow best 0.4383 last 0.4383 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-3941151 | ot_s81sl_leaf__t22 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (234/234 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-460174 | ot_s81sl_leaf__t40 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.6464 last 0.6464 rows 22 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3944811 | ot_s81sl_leaf__t47 | 3_2_place_iop | 0.6 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 2_4_floorplan_pdn | 2.4 | last meaningful line 1.8 h ago (130/130 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (9063/9063 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | postcts_gate_FF | 9.0 | last meaningful line -0.0 h ago (36643/36643 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | postcts_gate_FF | 9.0 | last meaningful line 0.2 h ago (375/375 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | postcts_gate_FF | 3.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 9.0 | drt_violations best 16085 last 16085 rows 2 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (3389/3389 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-457717-18262 | 457717 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_2_route | 3.9 | drt_violations best 213 last 213 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | so_327321_ff_61500 | so_327321_ff_61500 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (297/297 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_327321_tt_61500 | so_327321_tt_61500 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (297/297 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-col-h10-r1--t1--cl95b37463--pvce76611c-grt-2031488 | col-h10-r1--t1--cl95b37463--pvce76611c-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt-2250696 | col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p4--t1--cl8ef405e8--pv70731479-grt-2226140 | col-h9-r0-p4--t1--cl8ef405e8--pv70731479-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-hub-Ei-grt-2292010 | kv3-hub-Ei-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t44--clf6cf8492-dump-2411989 | ot-s81sl-leaf--t44--clf6cf8492-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t44--clf6cf8492-grt-2411989 | ot-s81sl-leaf--t44--clf6cf8492-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t58-dump-2409893 | ot-s81sl-leaf--t58-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t58-grt-2409893 | ot-s81sl-leaf--t58-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 3.4 | repair_Remaining best 172946 last 172946 rows 67 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 2.9 | last meaningful line 0.3 h ago (209/215 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 8.2 | drt_violations best 15442 last 15442 rows 3 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-2214400 | col_h9_r1__t1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1543/1543 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-2076675 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | 1_2_yosys | 2.3 | last meaningful line 0.0 h ago (424/424 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_1_floorplan | 2.0 | last meaningful line 1.5 h ago (1424/1424 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 4.9 | last meaningful line 2.1 h ago (232/987 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 4.3 | repair_TNS best 230637 last 230637 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t4-3684447 | ot_s81sl_kv_leaf__t4 | 3_1_place_gp_skip_io | 1.5 | overflow best 0.6144 last 0.6144 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3703022 | ot_s81sl_leaf__t14 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t27-2093219 | ot_s81sl_leaf__t27 | 3_2_place_iop | 0.1 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-558414 | ot_s81sl_leaf__t65 | 3_3_place_gp | 1.0 | last meaningful line 0.0 h ago (295/295 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t70-823669 | ot_s81sl_leaf__t70 | 3_3_place_gp | 0.8 | last meaningful line 0.1 h ago (354/354 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-3908746 | ot_s81sl_leaf__t75 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (321/321 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | nowave-lec-sml_h259 | nowave-lec-sml_h259 | gold.ys | 0.3 | last meaningful line 0.3 h ago (29124/29124 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | nowave-lec-trx_xoff0_h259 | nowave-lec-trx_xoff0_h259 | gold.ys | 0.3 | last meaningful line 0.0 h ago (150356/150356 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-2327416-15680 | 2327416 | qwen_compute.t.slw_hc3__clccfc3e6b__pvcca9ff41 | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2421913-30025 | 2421913 | qwen_compute.t.slw_hc3__clccfc3e6b__pvcca9ff41 | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco-i1-3698803 | eco-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | so_1761191_ff_32273 | so_1761191_ff_32273 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (660/660 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_1761191_tt_32273 | so_1761191_tt_32273 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (660/660 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-kv-leaf--t1-dump-85763 | ot-s81sl-kv-leaf--t1-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-kv-leaf--t1-grt-85763 | ot-s81sl-kv-leaf--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t30-grt-89990 | ot-s81sl-leaf--t30-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t54--cl501e5681-grt-91983 | ot-s81sl-leaf--t54--cl501e5681-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 7.1 | drt_violations best 75008 last 75008 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 8.9 | drt_violations best 53713 last 53713 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-87338 | hd_ctl | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-kv3_pc_v3-3967683 | kv3_pc_v3 | 3_5_place_dp | 2.4 | last meaningful line 0.1 h ago (113/113 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3969057 | kv3_pc_v3 | 3_5_place_dp | 2.4 | last meaningful line 0.1 h ago (113/113 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-3404799 | ot_s81sl_leaf__t17 | 3_3_place_gp | 0.5 | overflow best 0.5614 last 0.5614 rows 5 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3365653 | ot_s81sl_leaf__t25 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t37-3328014 | ot_s81sl_leaf__t37 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t4-3132073 | ot_s81sl_leaf__t4 | 3_3_place_gp | 0.6 | overflow best 0.5056 last 0.51 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t41-3152229 | ot_s81sl_leaf__t41 | 3_3_place_gp | 0.6 | last meaningful line 0.2 h ago (181/181 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t5-3148460 | ot_s81sl_leaf__t5 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3324313 | ot_s81sl_leaf__t53 | 3_3_place_gp | 0.5 | overflow best 0.4222 last 0.4222 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3149759 | ot_s81sl_leaf__t54 | 3_5_place_dp | 0.6 | last meaningful line 0.1 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | pregrt_ff_hold | 2.4 | repair_TNS best 4910.74 last 4910.74 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 2.4 | last meaningful line 0.1 h ago (189/202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | postcts_gate_FF | 8.9 | last meaningful line 0.0 h ago (1837/1837 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | postcts_gate_TT | 8.9 | last meaningful line -0.0 h ago (16012/16012 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | postcts_gate_TT | 9.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | postcts_gate_FF | 9.3 | last meaningful line 0.1 h ago (1079/1079 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t18-3326899 | slice_station__t18 | 3_3_place_gp | 0.5 | overflow best 0.1978 last 0.1978 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-3325426 | slice_station__t29 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | postcts_gate_FF | 8.9 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | postcts_gate_TT | 8.9 | last meaningful line -0.0 h ago (77140/77140 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 8.9 | drt_violations best 72 last 72 rows 35 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | otc-4183895-10969 | 4183895 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-89031-30063 | 89031 | s81.t.ot_v41_rom_elem_q_qxpq_w10_gb_he_vB | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-89817-6853 | 89817 | s81.t.ot_v41_rom_elem_q_qxpq_w10_gb_he_vB | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 4.8 | drt_violations best 12959 last 12959 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco2-i2-3675346 | eco2-i2 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (226/557 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv7c30fd4e-grt-1513103 | col-h9-r2--t1--clce45cab5--pv7c30fd4e-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t60-grt-1321223 | ot-s81sl-leaf--t60-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t71-grt-1220474 | ot-s81sl-leaf--t71-grt | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 4_1_cts | 2.5 | last meaningful line 0.0 h ago (3535/3535 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3818192 | col_h10_r0_p1__t1 | 3_3_place_gp | 1.0 | overflow best 0.4099 last 0.4118 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | 5_1_grt | 3.6 | last meaningful line 1.2 h ago (203/210 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 3.6 | last meaningful line 1.2 h ago (203/210 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | postplace_setup | 0.0 | last meaningful line -0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (201/207 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 31666.7 last 31666.7 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 71892 last 71892 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-3916912 | col_h9_r0_p2__t1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1497604 | col_h9_r0_p3__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (259/259 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-3945629 | col_h9_r0_p4__t1 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 57376.2 last 57376.2 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 55205.4 last 55205.4 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1398169 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 64 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 7.6 | drt_violations best 86218 last 86218 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_1_grt | 2.5 | last meaningful line 1.0 h ago (198/217 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (198/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (7020/7020 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 0.7 h ago (126/126 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | selrange | 2.4 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | selrange | 2.4 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 0.7 h ago (132/132 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 0.8 h ago (128/128 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 2.5 | overflow best 0.6421 last 0.6421 rows 24 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 2_1_floorplan | 0.8 | repair_Viol best 8986 last 8986 rows 1252 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 2.5 | overflow best 0.6525 last 0.6525 rows 24 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 2.4 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 2.5 | repair_TNS best 33967.6 last 33967.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_5_place_dp | 2.4 | last meaningful line 1.8 h ago (41/41 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 8.3 | drt_violations best 10933 last 10933 rows 5 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 1.0 | last meaningful line 0.7 h ago (7084/7084 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 4_1_cts | 2.5 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 2.4 | repair_TNS best 293138 last 293138 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | pregrt_ff_hold | 2.4 | repair_Violations best 5334 last 5334 rows 46 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t24__cl2456157b-1317854 | ot_s81sl_leaf__t24 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (463/463 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 2.4 | repair_Violations best 2223 last 2223 rows 44 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t46-3487755 | ot_s81sl_leaf__t46 | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (274/274 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t61-353186 | ot_s81sl_leaf__t61 | 3_3_place_gp | 0.7 | last meaningful line 0.2 h ago (203/203 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t67-376168 | ot_s81sl_leaf__t67 | 3_3_place_gp | 0.7 | overflow best 0.6201 last 0.6201 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | 5_1_grt | 3.2 | last meaningful line 0.5 h ago (1192/1201 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 8.3 | last meaningful line 1.7 h ago (223/1121 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 9.6 | drt_violations best 70451 last 70451 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | tt_setup_repair_grt | 9.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1042191-13858 | 1042191 | qwen_compute.t.sle_hc1__cl22c1ff36 | 0.3 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1323146-15818 | 1323146 | qwen_compute.t.sle_hc1__cl22c1ff36 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1371283-29671 | 1371283 | ot_s81_cfg7_seq_bfp__orig | 0.1 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1523304-3628 | 1523304 | j6ctl_rom_elem_q_hw__fix | 0.0 | last meaningful line 0.0 h ago (198/198 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-3428097-1823 | 3428097 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 5.4 | drt_violations best 29 last 29 rows 13 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | ap-ageom-kw-ot-s81sl-leaf--t7-grt-3919799 | ot-s81sl-leaf--t7-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | cool_shannon | cool_shannon | verilator_lint | 0.0 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-2931618 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.5 | overflow best 0.3103 last 0.3108 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3350921 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.73 last 0.7466 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | pregrt_ff_hold | 2.1 | repair_Violations best 865 last 865 rows 12 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2938075 | col_h10_r2__t1 | 3_5_place_dp | 0.5 | repair_Violations best 78 last 78 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-2844003 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.5 | last meaningful line -0.0 h ago (297/297 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (210/214 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-3400705 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3822263 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 98 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3369629 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3307 last 0.3307 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 3_4_place_resized | 0.4 | repair_Remaining best 30923 last 30923 rows 37 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-coll_ftm-2637008 | coll_ftm | 5_2_route | 2.2 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_kv512_C__t1-524813 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.4 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3785/3785 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.8 | last meaningful line 0.5 h ago (200/209 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 3_3_place_gp | 3.1 | overflow best 0.6343 last 0.6343 rows 25 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-gunit__t1-533357 | gunit__t1 | 3_5_place_dp | 1.4 | last meaningful line 0.8 h ago (40/40 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N_w-880189 | hd_lep0N_w | 4_2_tapbal_grt | 1.2 | last meaningful line 0.8 h ago (46/105 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-304550 | kv3_io_ft | 5_2_route | 1.5 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2947333 | ot_s81sl_kv_leaf__t3 | port_bind | 0.5 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 4.5 | repair_Remaining best 163583 last 163583 rows 192 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-2405593 | ot_s81sl_leaf__t1 | 3_3_place_gp | 0.7 | last meaningful line 0.3 h ago (347/347 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-2985736 | ot_s81sl_leaf__t10 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (121/121 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t24__cl81374cd8-3403823 | ot_s81sl_leaf__t24 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2083 last 0.2083 rows 39 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t26-3127362 | ot_s81sl_leaf__t26 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1642535 | ot_s81sl_leaf__t28 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t3-2358697 | ot_s81sl_leaf__t3 | 3_3_place_gp | 0.7 | overflow best 0.5753 last 0.5793 rows 9 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t34-3146079 | ot_s81sl_leaf__t34 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t39-3134440 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (108/108 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-3969220 | ot_s81sl_leaf__t50 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (288/288 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t57-2441533 | ot_s81sl_leaf__t57 | 3_3_place_gp | 0.7 | overflow best 0.3043 last 0.3043 rows 24 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-3146562 | ot_s81sl_leaf__t68 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t69-3134611 | ot_s81sl_leaf__t69 | 3_3_place_gp | 0.4 | overflow best 0.6593 last 0.6593 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t74-3160290 | ot_s81sl_leaf__t74 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t8-508307 | ot_s81sl_leaf__t8 | 3_4_place_resized | 1.4 | repair_Remaining best 37909 last 37909 rows 260 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-1723438 | ot_s81sl_leaf__t9 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-seqhost__t1-430619 | seqhost__t1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i2-2979122 | eco_20261122_041142_2199995-i2 | 5_2_route | 0.4 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i1t-261967 | eco_20261122_054330_1688646-i1t | 5_3_fillcell | 1.5 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3722826-20819 | 3722826 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | otc-800046-3034 | 800046 | ot_bind_native_296b4d99839c438c52796785 | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-2307324-23722 | 2307324 | - | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 48.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 7.4 | drt_violations best 16 last 67 rows 18 | before-window best 144464, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 52.5 | last meaningful line 0.1 h ago (1560/1560 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 9.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 5_1_grt | 2.8 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 9.0 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | tt_setup_repair | 0.4 | repair_Violations best 0 last 0 rows 6 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 18.9 | drt_violations best 49344 last 49344 rows 15 | before-window best 52295, window best 49344 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_1_grt | 0.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 18.4 | drt_violations best 597 last 1269 rows 33 | before-window best 1045, window best 597 | PROGRESS: drt_violations improved 42.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 18.2 | drt_violations best 45146 last 45146 rows 14 | before-window best 47754, window best 45146 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 7.8 | drt_violations best 8841 last 8841 rows 10 | before-window best 85188, window best 8841 | PROGRESS: drt_violations improved 89.6 % in window |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 9.9 | drt_violations best 7622 last 7622 rows 11 | before-window best 29565, window best 7622 | PROGRESS: drt_violations improved 74.2 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 13.3 | drt_violations best 20 last 20 rows 60 | before-window best 170434, window best 20 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
