# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 07:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 17, 'NO-DATA': 29, 'YOUNG': 238, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 16.0 | last meaningful line 14.3 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 14.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1921258 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.7 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1921258-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.3 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 8.2 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:26250 -> 10:22390 | GRT-LABEL: DESIGN-FAIL: overflow 22390 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 45.7 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 60.1 | grt rounds 6 overflow 5:9167 -> 10:5212 -> 15:3582 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | 5_1_grt | 2.2 | grt rounds 3 overflow 5:8312 -> 10:170 -> 15:20 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 4.0 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 39.2 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 44.2 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 33.6 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 33.6 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 43.3 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 33.1 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 7.9 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 7.8 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 5_1_grt | 2.9 | grt rounds 2 overflow 5:4716 -> 10:2224 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 58.0 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 40.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-col-h10-r2--t1--cl99efd374--pv1619ecc6-grt-3242508 | col-h10-r2--t1--cl99efd374--pv1619ecc6-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-col-h9-r0-p2--t1--cl9f71e63d--pv11b73b67-grt-3158575 | col-h9-r0-p2--t1--cl9f71e63d--pv11b73b67-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv2f96c04f-grt-3080557 | col-h9-r1--t1--cl49d7a23e--pv2f96c04f-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t66-grt-2986704 | ot-s81sl-leaf--t66-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-1676750 | bk_sel__t2 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (195/198 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3185962 | col_h10_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3559 last 3559 rows 749 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3134/3135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2137948 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.5 | overflow best 0.4007 last 0.4007 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3179547 | col_h9_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3589 last 3589 rows 880 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2195/2195 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 6.4 | last meaningful line 0.8 h ago (199/207 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4405/4405 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 6.8 | drt_violations best 28 last 30 rows 55 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 8.6 | drt_violations best 4754 last 4754 rows 15 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 0.7 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-3035693 | ot_s81sl_leaf__t21 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8174 last 0.8268 rows 16 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-3038614 | ot_s81sl_leaf__t29 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9481 last 0.9481 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t59-3028174 | ot_s81sl_leaf__t59 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8222 last 0.8504 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (203/207 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | postcts_gate_TT | 8.4 | last meaningful line 0.0 h ago (1189/1189 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 8.7 | drt_violations best 6269 last 6269 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | postcts_gate_TT | 8.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 8.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 3.9 | last meaningful line 0.8 h ago (199/207 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | otc-3166564-12863 | 3166564 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-3280936-12441 | 3280936 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 4.5 | last meaningful line 0.8 h ago (199/207 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1t-2778713 | eco_20261122_144137_2274607-i1t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (230/623 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | tt_setup_repair_grt | 2.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_1_grt | 2.2 | last meaningful line 1.0 h ago (198/221 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 2.2 | last meaningful line 1.0 h ago (196/225 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | 1_2_yosys | 2.2 | last meaningful line -0.0 h ago (291/291 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | 1_2_yosys | 2.2 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 1.0 h ago (134/134 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | 1_2_yosys | 2.2 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | 1_2_yosys | 2.2 | last meaningful line 0.0 h ago (213/213 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 1.0 h ago (144/144 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 1.0 h ago (144/144 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2767328 | dsdv_slice_lepw_mus_C__t1 | port_bind | 2.2 | last meaningful line 2.2 h ago (1/1 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 2.2 | repair_TNS best 449415 last 449415 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (5001/5001 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | pregrt_ff_hold | 2.2 | repair_Violations best 1399 last 1425 rows 147 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (190/203 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (200/209 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | pregrt_ff_hold | 2.2 | repair_TNS best 6652.02 last 6652.02 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (200/207 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | tt_setup_repair | 2.2 | repair_Violations best 7598 last 9737 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 2.2 | last meaningful line 0.8 h ago (202/211 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (197/206 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (198/206 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (201/204 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (202/205 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (200/205 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (200/203 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 2.2 | last meaningful line 0.8 h ago (201/207 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | pregrt_ff_hold | 2.2 | repair_TNS best 240719 last 240719 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 2.2 | repair_TNS best 753290 last 753290 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (5229/5229 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | pregrt_ff_hold | 2.2 | repair_TNS best 60589.2 last 60589.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (6119/6119 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (201/207 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | postcts_gate_FF | 8.8 | last meaningful line 0.0 h ago (1868/1868 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_1_grt | 8.8 | last meaningful line 1.0 h ago (213/1025 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | tt_setup_measure_grt | 8.8 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 8.8 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 8.7 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 8.7 | last meaningful line 0.1 h ago (1670/1685 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 8.7 | last meaningful line 2.5 h ago (220/983 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_1_grt | 8.7 | last meaningful line 0.1 h ago (1066/1072 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | postcts_gate_TT | 8.7 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 8.7 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h10-r0-p4--t1--pvcc166a6d-grt-12929 | col-h10-r0-p4--t1--pvcc166a6d-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-col-h9-r0-p4--t1--clcb2fbfe8--pvec137455-grt-18317 | col-h9-r0-p4--t1--clcb2fbfe8--pvec137455-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t33-grt-57838 | ot-s81sl-leaf--t33-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t55-grt-162626 | ot-s81sl-leaf--t55-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t62-grt-249972 | ot-s81sl-leaf--t62-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-1937834 | bk_sel__t2 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3946946 | col_h10_r0_p1__t1 | 2_1_floorplan | 0.3 | repair_Viol best 5514 last 5514 rows 1280 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2435818 | col_h10_r0_p1__t1 | 3_5_place_dp | 1.1 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pv5b623e07-4101554 | col_h10_r0_p4__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3029/3029 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2247/2247 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2702252 | col_h9_r0_p3__t1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (273/273 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3867/3867 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2813014 | ot_s81sl_kv_leaf__t1 | 2_3_floorplan_tapcell | 1.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-3941151 | ot_s81sl_leaf__t22 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t42-3847498 | ot_s81sl_leaf__t42 | 3_3_place_gp | 0.4 | overflow best 0.7788 last 0.7788 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3944811 | ot_s81sl_leaf__t47 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (555/555 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 2_4_floorplan_pdn | 2.1 | last meaningful line 1.5 h ago (130/130 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (9061/9061 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | postcts_gate_FF | 8.8 | last meaningful line 0.0 h ago (791/791 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | postcts_gate_FF | 8.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | tt_setup_repair_grt | 2.9 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 8.7 | drt_violations best 91576 last 91576 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_2_route | 3.6 | drt_violations best 213 last 213 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_327321_ff_61500 | so_327321_ff_61500 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (297/297 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_327321_tt_61500 | so_327321_tt_61500 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (297/297 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-col-h10-r2--t1--cl8b686b3e-grt-1696950 | col-h10-r2--t1--cl8b686b3e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt-1696493 | col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pv1489a898-dump-1856284 | col-h9-r0-p3--t1--cl8ce97bcb--pv1489a898-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pv1489a898-grt-1856284 | col-h9-r0-p3--t1--cl8ce97bcb--pv1489a898-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h9-r1--t1--clf32cde8d--pv387d6579-grt-1820875 | col-h9-r1--t1--clf32cde8d--pv387d6579-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-hub-Ei-dump-1855561 | kv3-hub-Ei-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-hub-Ei-grt-1855561 | kv3-hub-Ei-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 3.1 | last meaningful line 0.8 h ago (210/228 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 2.7 | last meaningful line 0.1 h ago (209/212 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_1_grt | 2.8 | last meaningful line 0.7 h ago (247/1335 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 7.9 | drt_violations best 21351 last 21351 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | 1_2_yosys | 2.1 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_1_floorplan | 1.7 | last meaningful line 1.3 h ago (1424/1424 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 4.7 | last meaningful line 1.9 h ago (232/987 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 4.1 | repair_TNS best 230637 last 230637 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t4-3684447 | ot_s81sl_kv_leaf__t4 | 2_3_floorplan_tapcell | 1.2 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3703022 | ot_s81sl_leaf__t14 | 3_3_place_gp | 1.2 | overflow best 0.5698 last 0.5698 rows 10 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-3703972 | ot_s81sl_leaf__t44 | 3_4_place_resized | 1.2 | last meaningful line 0.1 h ago (208/208 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t58-3789284 | ot_s81sl_leaf__t58 | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-558414 | ot_s81sl_leaf__t65 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.1993 last 0.1993 rows 39 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t70-823669 | ot_s81sl_leaf__t70 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8746 last 0.8746 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-3908746 | ot_s81sl_leaf__t75 | 3_3_place_gp | 1.1 | overflow best 0.5663 last 0.5671 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | nowave-lec-sml_h259 | nowave-lec-sml_h259 | gold.ys | 0.1 | last meaningful line 0.0 h ago (29124/29124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | nowave-lec-trx_xoff0_h259 | nowave-lec-trx_xoff0_h259 | gate.ys | 0.1 | last meaningful line 0.1 h ago (15150/15150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | nowave-lec-trx_xoff16_h259 | nowave-lec-trx_xoff16_h259 | gold.ys | 0.1 | last meaningful line -0.0 h ago (20673/20673 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | nowave-lec-trx_xoff24_h259 | nowave-lec-trx_xoff24_h259 | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc8 | nowave-lec-trx_xoff8_h259 | nowave-lec-trx_xoff8_h259 | gold.ys | 0.1 | last meaningful line 0.0 h ago (20690/20690 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1855721-3887 | 1855721 | qwen_compute.t.slw_hc2__cl6bcaba89 | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | phscan-182279 | phscan | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco-i1-3698803 | eco-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (247/248 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_1761191_ff_32273 | so_1761191_ff_32273 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (660/660 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_1761191_tt_32273 | so_1761191_tt_32273 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (660/660 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 6.8 | drt_violations best 75008 last 75008 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 4.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 8.6 | drt_violations best 53713 last 53713 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3967683 | kv3_pc_v3 | 3_4_place_resized | 2.2 | last meaningful line 0.1 h ago (379/379 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3969057 | kv3_pc_v3 | 3_4_place_resized | 2.2 | last meaningful line 0.1 h ago (381/381 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-3404799 | ot_s81sl_leaf__t17 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.5539 last 0.5539 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3142036 | ot_s81sl_leaf__t25 | 3_3_place_gp | 0.3 | overflow best 0.6176 last 0.6189 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3365653 | ot_s81sl_leaf__t25 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (94/94 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t37-3328014 | ot_s81sl_leaf__t37 | 3_3_place_gp | 0.3 | last meaningful line 0.1 h ago (70/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t4-3132073 | ot_s81sl_leaf__t4 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (160/160 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (199/208 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t41-3152229 | ot_s81sl_leaf__t41 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (181/181 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t5-3148460 | ot_s81sl_leaf__t5 | 3_3_place_gp | 0.3 | overflow best 0.6618 last 0.6632 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3324313 | ot_s81sl_leaf__t53 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl501e5681-3130636 | ot_s81sl_leaf__t54 | 3_3_place_gp | 0.4 | overflow best 0.244 last 0.244 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3149759 | ot_s81sl_leaf__t54 | 3_3_place_gp | 0.3 | overflow best 0.5991 last 0.5991 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | tt_setup_repair | 2.2 | repair_Violations best 492 last 492 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | postcts_gate_FF | 8.6 | last meaningful line 0.1 h ago (833/833 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | postcts_gate_TT | 8.7 | last meaningful line 0.0 h ago (823/823 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | postcts_gate_FF | 9.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | postcts_gate_FF | 9.1 | last meaningful line 0.2 h ago (484/484 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t18-3326899 | slice_station__t18 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3209 last 0.3209 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-3325426 | slice_station__t29 | 3_3_place_gp | 0.3 | last meaningful line -0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | postcts_gate_TT | 8.7 | last meaningful line -0.0 h ago (65109/65109 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | postcts_gate_TT | 8.7 | last meaningful line 0.2 h ago (861/861 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 8.6 | drt_violations best 72 last 72 rows 32 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 4.6 | drt_violations best 83927 last 83927 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | prd-eco2-i2-3675346 | eco2-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_3383117_ff_38177 | so_3383117_ff_38177 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | so_3383117_tt_38177 | so_3383117_tt_38177 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-col-h10-r1--t1--cl95b37463--pv69c7e9a6-grt-1040240 | col-h10-r1--t1--cl95b37463--pv69c7e9a6-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-eng--t1-grt-958077 | eng--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (3365/3365 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3818192 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.2559 last 0.2559 rows 37 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | 5_1_grt | 3.4 | last meaningful line 1.0 h ago (203/209 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 3.4 | last meaningful line 1.0 h ago (203/209 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 31666.7 last 31666.7 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 71892 last 71892 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-3916912 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.7 | overflow best 0.3689 last 0.3689 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-3945629 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.7 | overflow best 0.3717 last 0.3721 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 57376.2 last 57376.2 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 55205.4 last 55205.4 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 7.4 | drt_violations best 86218 last 86218 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_1_grt | 2.2 | last meaningful line 0.8 h ago (198/213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-581356 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3797 last 0.3833 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (198/201 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6912/6913 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.5 h ago (126/126 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | selrange | 2.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | selrange | 2.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.5 h ago (128/128 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 2.2 | overflow best 0.7255 last 0.7401 rows 8 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 2_1_floorplan | 0.5 | repair_Viol best 8986 last 8986 rows 346 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 2.2 | overflow best 0.7294 last 0.7323 rows 17 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 2.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | tt_setup_repair | 2.2 | repair_Viol best 1100 last 1100 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_5_place_dp | 2.2 | last meaningful line 1.5 h ago (41/41 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 8.0 | drt_violations best 14336 last 14336 rows 4 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 0.7 | last meaningful line 0.5 h ago (7084/7084 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 3_5_place_dp | 2.2 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 2.2 | repair_TNS best 293138 last 293138 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | pregrt_ff_hold | 2.2 | repair_TNS best 11143.3 last 11143.3 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t46-3487755 | ot_s81sl_leaf__t46 | 3_3_place_gp | 0.9 | overflow best 0.3132 last 0.3601 rows 30 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t61-353186 | ot_s81sl_leaf__t61 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3389 last 0.3389 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t67-376168 | ot_s81sl_leaf__t67 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6388 last 0.6388 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t71-3526655 | ot_s81sl_leaf__t71 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (1192/1198 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 3_4_place_resized | 2.2 | last meaningful line 0.1 h ago (292/292 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 9.3 | drt_violations best 70451 last 70451 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_1_grt | 9.0 | last meaningful line 0.3 h ago (1228/1245 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | otc-1042191-13858 | 1042191 | s81.c.ot_s81_svc_mergex | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1044819-24860 | 1044819 | s81.c.ot_s81_svc_mergex | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2047425-5864 | 2047425 | gen_lint_yosys | 1.7 | last meaningful line 1.7 h ago (1/1 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-3428097-1823 | 3428097 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 5.2 | drt_violations best 58 last 58 rows 12 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | ap-ageom-kw-ot-s81sl-leaf--t43-grt-3280553 | ot-s81sl-leaf--t43-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | ap-ageom-kw-ot-s81sl-leaf--t52-grt-3357117 | ot-s81sl-leaf--t52-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | ap-ageom-kw-slice-station--t51-grt-3345837 | slice-station--t51-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-2931618 | col_h10_r0_p1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3350921 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.0 | repair_Viol best 6050 last 6050 rows 37 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2938075 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.371 last 0.371 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-2844003 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (210/213 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-3400705 | col_h9_r0_p2__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (283/283 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-685457 | col_h9_r0_p3__t1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-2511805 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.4 | overflow best 0.3308 last 0.3679 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3369629 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 83 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2637008 | coll_ftm | 5_2_route | 2.0 | last meaningful line 0.2 h ago (240/241 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_kv512_C__t1-524813 | dsdv_slice_kv512_C__t1 | 3_1_place_gp_skip_io | 1.1 | overflow best 0.8372 last 0.8372 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.5 | last meaningful line 0.3 h ago (200/205 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 3_3_place_gp | 2.8 | overflow best 0.7244 last 0.7247 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-gunit__t1-533357 | gunit__t1 | 3_5_place_dp | 1.1 | last meaningful line 0.5 h ago (40/40 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N_w-880189 | hd_lep0N_w | 4_2_tapbal_grt | 1.0 | last meaningful line 0.5 h ago (46/95 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2374283 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 3137 last 3137 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-921223 | hd_turn_a | 6_report | 1.0 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-304550 | kv3_io_ft | 5_2_route | 1.2 | last meaningful line 0.1 h ago (223/224 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2947333 | ot_s81sl_kv_leaf__t3 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (509/509 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 4.3 | last meaningful line 0.3 h ago (210/216 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-2405593 | ot_s81sl_leaf__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (347/347 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-2985736 | ot_s81sl_leaf__t10 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8442 last 0.8442 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t24__cl81374cd8-3403823 | ot_s81sl_leaf__t24 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (210/210 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t26-3127362 | ot_s81sl_leaf__t26 | 3_1_place_gp_skip_io | 0.1 | last meaningful line -0.0 h ago (10/10 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1642535 | ot_s81sl_leaf__t28 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t3-2358697 | ot_s81sl_leaf__t3 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (325/325 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t34-3146079 | ot_s81sl_leaf__t34 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (430/430 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t39-3134440 | ot_s81sl_leaf__t39 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t57-2441533 | ot_s81sl_leaf__t57 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (310/310 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t60-1673352 | ot_s81sl_leaf__t60 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-3146562 | ot_s81sl_leaf__t68 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (579/579 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t69-3134611 | ot_s81sl_leaf__t69 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9231 last 0.9231 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t7-637595 | ot_s81sl_leaf__t7 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t74-3160290 | ot_s81sl_leaf__t74 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (579/579 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t8-508307 | ot_s81sl_leaf__t8 | 3_3_place_gp | 1.1 | overflow best 0.3513 last 0.3516 rows 36 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-1723438 | ot_s81sl_leaf__t9 | 3_3_place_gp | 0.8 | overflow best 0.2218 last 0.2218 rows 41 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-seqhost__t1-430619 | seqhost__t1 | 3_3_place_gp | 1.2 | overflow best 0.6302 last 0.6302 rows 30 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i2-2979122 | eco_20261122_041142_2199995-i2 | 5_2_route | 0.2 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i1t-261967 | eco_20261122_054330_1688646-i1t | 5_2_route | 1.3 | drt_violations best 4216 last 4216 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | so_3205844_ff_9132 | so_3205844_ff_9132 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | so_3205844_tt_9132 | so_3205844_tt_9132 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | otc-1410918-25294 | 1410918 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 47.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 7.2 | drt_violations best 26 last 26 rows 15 | before-window best 144464, window best 26 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 52.2 | last meaningful line 2.6 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | 5_1_grt | 2.2 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 8.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 8.8 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 5_1_grt | 2.6 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 8.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 8.7 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | tt_setup_repair | 2.2 | repair_Violations best 0 last 0 rows 5 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 18.6 | drt_violations best 49344 last 49344 rows 15 | before-window best 52295, window best 49344 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 18.1 | drt_violations best 597 last 1279 rows 32 | before-window best 1045, window best 597 | PROGRESS: drt_violations improved 42.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 17.9 | drt_violations best 45146 last 45146 rows 14 | before-window best 47754, window best 45146 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t30-3137826 | ot_s81sl_leaf__t30 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 16 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 7.5 | drt_violations best 8841 last 8841 rows 10 | before-window best 85188, window best 8841 | PROGRESS: drt_violations improved 89.6 % in window |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 29 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 8.1 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 9.7 | drt_violations best 11187 last 11187 rows 10 | before-window best 152197, window best 11187 | PROGRESS: drt_violations improved 92.6 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 13.1 | drt_violations best 20 last 20 rows 56 | before-window best 170434, window best 20 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
