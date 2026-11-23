# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 17:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 4, 'GRT-LABEL': 41, 'YOUNG': 130, 'NO-DATA': 20, 'KEEP': 1, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-coll_core-2083685 | coll_core | tt_setup_repair_grt | 16.9 | repair_Violations best 155 last 155 rows 13 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -534.10 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 26.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 9.6 | last meaningful line 6.3 h ago (562/562 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (fam-s81-col-h10-r4 deci |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 9.6 | last meaningful line 6.3 h ago (562/562 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (fam-s81-col-h10-r4 deci |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 9.6 | last meaningful line 6.3 h ago (562/562 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (fam-s81-col-h10-r4 deci |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 11.0 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 56.2 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50054 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_a_v1__cl67389ecd-3090743 | sle_st_a_v1 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:1170 -> 10:490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 70.6 | grt rounds 6 overflow 5:9414 -> 10:5163 -> 15:3337 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 12.7 | grt rounds 3 overflow 5:59557 -> 10:65368 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2032513 | ot_s81sl_leaf__t30 | 5_1_grt | 1.6 | grt rounds 4 overflow 5:35195 -> 10:28443 -> 15:23081 -> 20:21475 | GRT-LABEL: DESIGN-FAIL: overflow 28443 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 2.8 | grt rounds 4 overflow 5:33787 -> 10:35370 -> 15:30500 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 12.7 | grt rounds 4 overflow 5:8269 -> 10:4208 -> 15:3621 -> 20:3335 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 12.7 | grt rounds 4 overflow 5:5427 -> 10:2816 -> 15:2050 -> 20:2469 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 12.7 | grt rounds 3 overflow 5:24072 -> 10:16574 -> 15:14263 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 12.7 | grt rounds 3 overflow 5:32852 -> 10:26729 -> 15:20376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-687429 | ot_s81sl_leaf__t54 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:32490 -> 10:17813 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 2.2 | grt rounds 3 overflow 5:51432 -> 10:39353 -> 15:30181 | GRT-LABEL: DESIGN-FAIL: overflow 39353 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-691946 | slw_st_a_v1 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:42283 -> 10:4891 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:3841 -> 10:2693 | GRT-LABEL: DESIGN-FAIL: overflow 2693 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 | col_h9_r0_p6__t1 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:41798 -> 10:421 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 10.8 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 49.7 | grt rounds 3 overflow 5:76937 -> 10:66805 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 54.7 | grt rounds 3 overflow 5:61116 -> 10:62172 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 44.1 | grt rounds 4 overflow 5:58312 -> 10:48779 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 44.1 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 53.8 | grt rounds 4 overflow 5:77624 -> 10:49527 -> 15:42727 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 43.6 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 18.4 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3844958 | ot_s81sl_leaf__t55 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 12.4 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 10.0 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3845641 | sle_st_a_v2 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:8684 -> 10:4245 | GRT-LABEL: DESIGN-FAIL: overflow 4245 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 12.7 | grt rounds 4 overflow 5:42588 -> 10:29799 -> 15:22754 -> 20:20154 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 12.6 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 5_1_grt | 3.6 | grt rounds 2 overflow 5:46736 -> 10:35993 | GRT-LABEL: DESIGN-FAIL: overflow 35993 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 12.7 | grt rounds 5 overflow 5:47409 -> 10:2770 -> 15:1561 -> 20:909 -> 25:393 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 12.7 | grt rounds 6 overflow 5:33301 -> 10:3290 -> 15:1523 -> 20:1038 -> 25:413 -> 30:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 11.0 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: overflow 2584 at round 10 > 1000 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 12.7 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 12.7 | grt rounds 5 overflow 5:805 -> 10:203 -> 15:132 -> 20:64 -> 25:77 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 25: 64 -> 77 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 12.7 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 12.7 | grt rounds 3 overflow 5:55088 -> 10:54804 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 12.7 | grt rounds 3 overflow 5:22842 -> 10:2722 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 4.6 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 10.2 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-2991761 | bk_sel__t2 | pregrt_ff_hold | 1.6 | repair_TNS best 2.47658e+06 last 2.47658e+06 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3113889 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 131142 last 131142 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-44672 | col_h9_r0_p5__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 144171 last 144171 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-1098453 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t3-886705 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-880876 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3047381 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.5 h ago (144/144 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-13225 | dsdv_slice_lepw_mus_LP__t2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-iqf__t1-13421 | iqf__t1 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (204/256 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-1070279 | kv3_sys_c | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-15901 | kv3_sys_c | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-1070507 | ot_s81sl_leaf__t28 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (101/101 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t33-29735 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 0.7 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_2_route | 14.6 | drt_violations best 10069 last 10069 rows 3 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_a_v2__pv4242de79-43496 | sle_st_a_v2 | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (204/210 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | eco-abs-909190 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (324/324 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 7.0 | drt_violations best 41 last 41 rows 13 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1t-873116 | eco_20261122_223531_3628570-i1t | 5_2_route | 2.9 | drt_violations best 13619 last 13619 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t47-grt-282106 | ot-s81sl-leaf--t47-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2022266 | col_h10_r0_p1__t1 | tt_setup_repair | 1.6 | repair_Viol best 587 last 587 rows 111 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-2024740 | col_h10_r0_p1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 96642.4 last 96642.4 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-2046903 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 122014 last 122014 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pva2370bfd-2123745 | col_h9_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 85618.3 last 85618.3 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | selrange | 1.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | selrange | 1.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-3659100 | dsdv_slice_c1x_C__t10 | 4_1_cts | 2.8 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-683007 | dsdv_slice_lepw_mus_C__t1 | 3_3_place_gp | 2.2 | overflow best 0.7473 last 0.7473 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t23-694414 | ot_s81sl_leaf__t23 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (206/212 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (207/212 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-686262 | ot_s81sl_leaf__t7 | pregrt_ff_hold | 2.2 | repair_Violations best 1726 last 1726 rows 44 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t71-691089 | ot_s81sl_leaf__t71 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t73-3636691 | ot_s81sl_leaf__t73 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (206/212 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-seqhost__t1-3813097 | seqhost__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8162 last 0.8162 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (4846/4846 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | generate_abstract | 19.3 | last meaningful line 0.2 h ago (970/970 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (5245/5245 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (5372/5372 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5251/5251 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | otc-1094939-10134 | 1094939 | signoff | 2.0 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | otc-1481339-18431 | 1481339 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | otc-2017932-16297 | 2017932 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc2 | otc-3827287-12142 | 3827287 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-3856677-7853 | 3856677 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 4.8 | drt_violations best 1403 last 1403 rows 12 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_140001_4005935-i1-2236985 | eco_20261122_140001_4005935-i1 | 5_2_route | 3.5 | drt_violations best 595 last 595 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_161953_3893587-i1-2758523 | eco_20261122_161953_3893587-i1 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1t-3385034 | eco_20261122_164248_3895049-i1t | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (237/380 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1t-3466592 | eco_20261122_164521_3948325-i1t | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (235/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_retry_1795389734917048336-i1t-961404 | eco_retry_1795389734917048336-i1t | 5_2_route | 2.1 | drt_violations best 59992 last 59992 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-fin-2019024 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_106384_ff_20300 | so_106384_ff_20300 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_106384_tt_20300 | so_106384_tt_20300 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_278096_ff_11749 | so_278096_ff_11749 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_278096_tt_11749 | so_278096_tt_11749 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t39-grt-116361 | ot-s81sl-leaf--t39-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t50-grt-4099953 | ot-s81sl-leaf--t50-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-35095 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.7197 last 0.7197 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_2_route | 4.2 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | 5_1_grt | 2.9 | repair_TNS best 2094.05 last 2094.05 rows 4 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2769627 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.1 | overflow best 0.647 last 0.647 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-8352 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t30-10758 | ot_s81sl_leaf__t30 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3967105 | ot_s81sl_leaf__t46 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (207/213 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t61-3925881 | ot_s81sl_leaf__t61 | 5_1_grt | 2.8 | last meaningful line 1.0 h ago (203/211 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 12.6 | last meaningful line 0.3 h ago (293/294 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | pregrt_ff_hold | 3.3 | repair_TNS best 7398.51 last 7398.51 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_1_grt | 4.3 | repair_Remaining best 134615 last 134615 rows 275 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1-3987348 | eco_20261122_220050_168828-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (256/667 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-fin-2527780 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (410/410 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_82814_ff_12212 | so_82814_ff_12212 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_82814_tt_12212 | so_82814_tt_12212 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 9.4 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_2_route | 9.9 | drt_violations best 868 last 868 rows 4 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 9.9 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-497679 | col_h9_r1__t1 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t4-3857153 | dsdv_slice_c1x_C__t4 | 3_3_place_gp | 2.2 | overflow best 0.7776 last 0.7776 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-2830715 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 0.8 | repair_TNS best 23200.4 last 23200.4 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mus_LP__t2-2776465 | dsdv_slice_lepw_mus_LP__t2 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mus_LP__t2-2789207 | dsdv_slice_lepw_mus_LP__t2 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (282/282 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_5_place_dp | 12.2 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-2778952 | kv3_io_cor_v1 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t10-2809979 | ot_s81sl_leaf__t10 | pregrt_ff_hold | 0.8 | repair_TNS best 6605.78 last 6605.78 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-2863435 | ot_s81sl_leaf__t65 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4641/4641 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t29__cl2e5c855a-3939444 | slice_station__t29 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3952570 | slice_station__t40 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (249/250 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_198040_ff_38374 | so_198040_ff_38374 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_198040_tt_38374 | so_198040_tt_38374 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_2246053_ff_51586 | so_2246053_ff_51586 | signoff | 1.0 |  | NO-DATA: empty log |  |
| epyc8 | so_2246053_tt_51586 | so_2246053_tt_51586 | signoff | 1.0 |  | NO-DATA: empty log |  |
| epyc8 | so_4190100_ff_29330 | so_4190100_ff_29330 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (660/660 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_4190100_tt_29330 | so_4190100_tt_29330 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (660/660 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-slice-station--t40--cl1ea9de02-grt-3050497 | slice-station--t40--cl1ea9de02-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-slice-station--t45-dump-3088369 | slice-station--t45-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-slice-station--t45-grt-3088369 | slice-station--t45-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 12.9 | last meaningful line 0.3 h ago (293/294 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 5_2_route | 3.6 | drt_violations best 60656 last 60656 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 3.6 | last meaningful line 0.3 h ago (210/218 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t67-2555054 | ot_s81sl_leaf__t67 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 5_2_route | 3.6 | drt_violations best 19950 last 19950 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | tt_setup_repair_grt | 3.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_2_route | 3.6 | last meaningful line 0.2 h ago (256/257 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | 5_2_route | 3.6 | drt_violations best 18073 last 18073 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v2__clf4365a62-2746317 | slw_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.3331 last 0.3331 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 3.3 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | otc-2867161-32206 | 2867161 | signoff | 2.4 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 3.5 | last meaningful line 3.5 h ago (3/3 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-1472150 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i3-2776988 | eco-i3 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 5.3 | drt_violations best 71 last 71 rows 14 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_2_route | 3.7 | drt_violations best 13140 last 13140 rows 2 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | so_2652148_ff_30829 | so_2652148_ff_30829 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_2652148_tt_30829 | so_2652148_tt_30829 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_2693915_ff_76102 | so_2693915_ff_76102 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (776/776 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_2693915_tt_76102 | so_2693915_tt_76102 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (776/776 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 12.7 | last meaningful line 0.5 h ago (286/287 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_2_route | 11.3 | drt_violations best 206 last 206 rows 4 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 12.7 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-645502 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 49340.3 last 49340.3 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (200/204 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-1671863 | col_h9_r2__t1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | 1_2_yosys | 2.7 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-3050526 | gunit__t1 | 3_5_place_dp | 2.0 | last meaningful line 1.3 h ago (40/40 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t68-641169 | ot_s81sl_leaf__t68 | hold_gate | 0.9 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t70-643388 | ot_s81sl_leaf__t70 | pregrt_ff_hold | 0.9 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.8694 last 0.8694 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | generate_abstract | 18.6 | last meaningful line 0.0 h ago (485/485 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (4970/4970 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_2_route | 2.9 | drt_violations best 88315 last 88315 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1t-1135156 | eco_20261122_165619_1517073-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_1121096_ff_82150 | so_1121096_ff_82150 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | so_1121096_tt_82150 | so_1121096_tt_82150 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (209/211 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 12.4 | drt_violations best 101024 last 101024 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 13.1 | drt_violations best 156124 last 156124 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 10.2 | drt_violations best 52737 last 52737 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 10.6 | drt_violations best 55511 last 55511 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 8.9 | last meaningful line 3.3 h ago (208/215 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 6.9 | last meaningful line 2.8 h ago (36/36 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2253150 | kv3_io_ft | 5_2_route | 1.2 | last meaningful line 0.1 h ago (228/229 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 6.7 | repair_TNS best 10405.5 last 10405.5 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | tt_setup_repair_grt | 14.8 | repair_Viol best 1104 last 1104 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 4.7 | last meaningful line 0.3 h ago (209/217 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_1_grt | 6.7 | last meaningful line 0.2 h ago (249/1257 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | postcts_gate_TT | 6.8 | last meaningful line 0.1 h ago (786/786 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2204878 | slice_station__t12 | 5_2_route | 1.2 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 10.2 | drt_violations best 48586 last 48586 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | tt_setup_measure_grt | 6.8 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1-1690412 | eco_20261120_150342_478824-i1 | 5_3_fillcell | 3.0 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-3065125 | col_h10_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 9.9 | drt_violations best 73151 last 73151 rows 3 | before-window best 363722, window best 73151 | PROGRESS: drt_violations improved 79.9 % in window |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 9.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 9.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 11.2 | last meaningful line 0.0 h ago (1150/1150 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | tt_setup_repair | 1.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slice_station__t25-3118247 | slice_station__t25 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 62.7 | last meaningful line 1.9 h ago (1566/1566 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-679902 | col_h10_r1__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-serdes__t2-2124120 | serdes__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-2035057 | tt_ctlm | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 13.3 | drt_violations best 16565 last 16565 rows 11 | before-window best 128949, window best 16565 | PROGRESS: drt_violations improved 87.2 % in window |  |
| epyc8 | dpkit-glue-555250 | glue | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 13.0 | repair_TNS best 11882.9 last 11882.9 rows 8 | before-window best 18374.4, window best 11882.9 | PROGRESS: repair_TNS improved 35.3 % in window |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1675980 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 18.5 | drt_violations best 2973 last 5816 rows 20 | before-window best 3681, window best 2973 | PROGRESS: drt_violations improved 19.2 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_1_grt | 11.2 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 20.2 | drt_violations best 1452 last 1452 rows 19 | before-window best 2439, window best 1452 | PROGRESS: drt_violations improved 40.5 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 9.0 | drt_violations best 24 last 24 rows 15 | before-window best 33922, window best 24 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 8.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.5 | repair_TNS best 5893.93 last 5893.93 rows 2 | before-window best 6154.64, window best 5893.93 | PROGRESS: repair_TNS improved 4.2 % in window |  |
