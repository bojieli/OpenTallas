# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 17:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'GRT-LABEL': 40, 'NO-DATA': 10, 'YOUNG': 128, 'KEEP': 1, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 18.8 | drt_violations best 4374 last 5773 rows 23 | before-window best 4374, window best 5773 | NO-PROGRESS: drt_violations best 5773 vs 4374 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-HROOT-R1 decides |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 26.2 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 9.4 | last meaningful line 6.0 h ago (562/562 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (fam-s81-col-h10-r4 deci |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 9.4 | last meaningful line 6.0 h ago (562/562 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (fam-s81-col-h10-r4 deci |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 9.3 | last meaningful line 6.0 h ago (562/562 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (fam-s81-col-h10-r4 deci |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 16.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 10.8 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 55.9 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50054 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 70.3 | grt rounds 6 overflow 5:9414 -> 10:5163 -> 15:3337 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 12.4 | grt rounds 3 overflow 5:59557 -> 10:65368 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2032513 | ot_s81sl_leaf__t30 | 5_1_grt | 1.3 | grt rounds 4 overflow 5:35195 -> 10:28443 -> 15:23081 -> 20:21475 | GRT-LABEL: DESIGN-FAIL: overflow 28443 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 2.6 | grt rounds 4 overflow 5:33787 -> 10:35370 -> 15:30500 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 12.4 | grt rounds 4 overflow 5:8269 -> 10:4208 -> 15:3621 -> 20:3335 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 12.4 | grt rounds 4 overflow 5:5427 -> 10:2816 -> 15:2050 -> 20:2469 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 12.4 | grt rounds 3 overflow 5:24072 -> 10:16574 -> 15:14263 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 12.4 | grt rounds 3 overflow 5:32852 -> 10:26729 -> 15:20376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 2.0 | grt rounds 3 overflow 5:51432 -> 10:39353 -> 15:29681 | GRT-LABEL: DESIGN-FAIL: overflow 39353 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-691946 | slw_st_a_v1 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:42283 -> 10:4891 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 | col_h9_r0_p6__t1 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:41798 -> 10:421 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 10.5 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 49.5 | grt rounds 3 overflow 5:76937 -> 10:66805 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 54.4 | grt rounds 3 overflow 5:61116 -> 10:62172 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 43.8 | grt rounds 4 overflow 5:58312 -> 10:48779 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 43.8 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 53.6 | grt rounds 4 overflow 5:77624 -> 10:49527 -> 15:42727 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 43.3 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 18.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3844958 | ot_s81sl_leaf__t55 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 12.1 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 9.8 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t21-3954640 | ot_s81sl_leaf__t21 | 5_1_grt | 1.9 | grt rounds 2 overflow 5:59171 -> 10:48750 | GRT-LABEL: DESIGN-FAIL: overflow 48750 at round 10 > 1000 |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3845641 | sle_st_a_v2 | 5_1_grt | 1.9 | grt rounds 2 overflow 5:8684 -> 10:4245 | GRT-LABEL: DESIGN-FAIL: overflow 4245 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 12.4 | grt rounds 4 overflow 5:42588 -> 10:29799 -> 15:22754 -> 20:20154 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 12.4 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:46736 -> 10:35993 | GRT-LABEL: DESIGN-FAIL: overflow 35993 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 13.4 | grt rounds 3 overflow 5:63320 -> 10:33957 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 12.2 | grt rounds 5 overflow 5:47409 -> 10:2770 -> 15:1561 -> 20:909 -> 25:393 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 12.2 | grt rounds 5 overflow 5:33301 -> 10:3290 -> 15:1523 -> 20:1038 -> 25:413 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 12.2 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 12.2 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 12.2 | grt rounds 3 overflow 5:55088 -> 10:54804 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 12.2 | grt rounds 3 overflow 5:22842 -> 10:2722 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 9.9 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-2966245 | slice_station__t24 | 5_1_grt | 0.9 | grt rounds 2 overflow 5:5555 -> 10:4300 | GRT-LABEL: DESIGN-FAIL: overflow 4300 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-col-h10-r1--t1--cl95b37463--pv6a7ae122-grt-704969 | col-h10-r1--t1--cl95b37463--pv6a7ae122-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t35-grt-502460 | ot-s81sl-leaf--t35-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t38-grt-511030 | ot-s81sl-leaf--t38-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-2991761 | bk_sel__t2 | pregrt_ff_hold | 1.4 | repair_TNS best 2.47658e+06 last 2.47658e+06 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-3065125 | col_h10_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 69202.3 last 69202.3 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3113889 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 131142 last 131142 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-44672 | col_h9_r0_p5__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 144171 last 144171 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3047381 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.3 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-13225 | dsdv_slice_lepw_mus_LP__t2 | 3_3_place_gp | 0.5 | overflow best 0.6494 last 0.6494 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_sys_c-15901 | kv3_sys_c | 3_3_place_gp | 0.5 | overflow best 0.3674 last 0.3674 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t33-29735 | ot_s81sl_leaf__t33 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4207/4207 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_2_route | 14.3 | drt_violations best 14922 last 14922 rows 2 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_a_v1__cl67389ecd-3090743 | sle_st_a_v1 | 5_1_grt | 1.3 | repair_Remaining best 127944 last 127944 rows 29 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-sle_st_a_v2__pv4242de79-43496 | sle_st_a_v2 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (6174/6174 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | otc-210420-13766 | 210420 | signoff | 2.9 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 6.8 | drt_violations best 41 last 41 rows 13 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1t-873116 | eco_20261122_223531_3628570-i1t | 5_2_route | 2.6 | drt_violations best 13619 last 13619 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-fin-693810 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (362/362 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2022266 | col_h10_r0_p1__t1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3529/3529 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-2024740 | col_h10_r0_p1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 96642.4 last 96642.4 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-2046903 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 122014 last 122014 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pva2370bfd-2123745 | col_h9_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 85618.3 last 85618.3 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-2121887 | col_h9_r2__t1 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (200/203 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | selrange | 1.3 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | selrange | 1.3 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-3659100 | dsdv_slice_c1x_C__t10 | 4_1_cts | 2.6 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-683007 | dsdv_slice_lepw_mus_C__t1 | 3_1_place_gp_skip_io | 2.0 | overflow best 0.7047 last 0.7047 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t23-694414 | ot_s81sl_leaf__t23 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (206/208 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t47-3171357 | ot_s81sl_leaf__t47 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-687429 | ot_s81sl_leaf__t54 | 5_1_grt | 2.0 | last meaningful line 0.8 h ago (200/209 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t71-691089 | ot_s81sl_leaf__t71 | 5_1_grt | 2.0 | last meaningful line 0.1 h ago (203/206 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t73-3636691 | ot_s81sl_leaf__t73 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (206/209 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-seqhost__t1-3813097 | seqhost__t1 | 2_1_floorplan | 0.2 | repair_Viol best 2319 last 2319 rows 899 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (4841/4841 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | generate_abstract | 19.0 | last meaningful line 0.0 h ago (955/955 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5243/5243 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 4_1_cts | 1.3 | last meaningful line 0.3 h ago (5345/5345 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | generate_abstract | 19.0 | last meaningful line 0.1 h ago (707/707 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (5247/5247 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | generate_abstract | 19.0 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_1_grt | 1.3 | last meaningful line 0.3 h ago (262/1272 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-1094939-10134 | 1094939 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | otc-1481339-18431 | 1481339 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | otc-2017932-16297 | 2017932 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-3827287-12142 | 3827287 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-3856677-7853 | 3856677 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 4.6 | drt_violations best 1403 last 1403 rows 12 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_140001_4005935-i1-2236985 | eco_20261122_140001_4005935-i1 | 5_2_route | 3.2 | drt_violations best 595 last 595 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_161953_3893587-i1-2758523 | eco_20261122_161953_3893587-i1 | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (234/1303 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1t-3385034 | eco_20261122_164248_3895049-i1t | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (174/174 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1t-3466592 | eco_20261122_164521_3948325-i1t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_retry_1795389734917048336-i1t-961404 | eco_retry_1795389734917048336-i1t | 5_2_route | 1.9 | drt_violations best 59992 last 59992 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-one_hold_pad-pass-2019024 | one_hold_pad-pass | 5_2_route | 1.3 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_2_route | 3.9 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (312/1266 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2769627 | dsdv_slice_kv512_C__t1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.2068 last 0.2068 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3967105 | ot_s81sl_leaf__t46 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (207/212 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t61-3925881 | ot_s81sl_leaf__t61 | 5_1_grt | 2.5 | last meaningful line 0.8 h ago (203/209 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 12.4 | last meaningful line 0.3 h ago (291/292 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | tt_setup_measure | 3.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (187/187 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | 6_report | 3.6 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1t-2527780 | eco_20261122_215654_330309-i1t | 5_3_fillcell | 3.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-sle-st-a-v2--pv30dda31f--pvd2ec7769-grt-3730809 | sle-st-a-v2--pv30dda31f--pvd2ec7769-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 9.1 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2778972 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_2_route | 9.6 | drt_violations best 23424 last 23424 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | postcts_gate_TT | 9.6 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3468686 | col_h9_r2__t1 | 3_4_place_resized | 0.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t4-3857153 | dsdv_slice_c1x_C__t4 | 3_1_place_gp_skip_io | 1.9 | overflow best 0.5697 last 0.5697 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-2830715 | dsdv_slice_lepw_mu_LP__t2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4425/4425 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mus_LP__t2-2776465 | dsdv_slice_lepw_mus_LP__t2 | 3_3_place_gp | 0.5 | overflow best 0.6856 last 0.6938 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mus_LP__t2-2789207 | dsdv_slice_lepw_mus_LP__t2 | 3_3_place_gp | 0.5 | overflow best 0.6856 last 0.697 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_5_place_dp | 12.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | pregrt_ff_hold | 1.6 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-2778952 | kv3_io_cor_v1 | pregrt_ff_hold | 0.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t10-2809979 | ot_s81sl_leaf__t10 | tt_setup_repair | 0.5 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-2863435 | ot_s81sl_leaf__t65 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4528/4529 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t21-3827757 | slice_station__t21 | 6_report | 1.9 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t29__cl2e5c855a-3939444 | slice_station__t29 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (251/252 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3952570 | slice_station__t40 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | eco-abs-3598837 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (656/656 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_2246053_ff_51586 | so_2246053_ff_51586 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_2246053_tt_51586 | so_2246053_tt_51586 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 12.6 | last meaningful line 0.2 h ago (291/292 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 5_2_route | 3.3 | drt_violations best 60656 last 60656 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (210/213 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t50-1830145 | ot_s81sl_leaf__t50 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t67-2555054 | ot_s81sl_leaf__t67 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 5_2_route | 3.3 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_2_route | 3.3 | last meaningful line 0.1 h ago (252/253 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | 5_2_route | 3.3 | drt_violations best 18073 last 18073 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | eco-abs-2153662 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (772/772 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | eco-abs-2470134 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (1026/1026 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 3.0 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | otc-2867161-32206 | 2867161 | signoff | 2.2 | last meaningful line 2.1 h ago (3/3 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 3.3 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 5.0 | drt_violations best 71 last 71 rows 14 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1-1472150 | eco_20261122_174935_2347281-i1 | 5_2_route | 2.9 | drt_violations best 15395 last 15395 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_2_route | 3.5 | drt_violations best 100267 last 100267 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | so_1752686_ff_26401 | so_1752686_ff_26401 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (532/532 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_1752686_tt_26401 | so_1752686_tt_26401 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (532/532 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 12.2 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_2_route | 10.7 | drt_violations best 55826 last 55826 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 12.2 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1675980 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 94532.8 last 94532.8 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-645502 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 49340.3 last 49340.3 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-1671863 | col_h9_r2__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (201/204 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 10.5 | last meaningful line 0.8 h ago (200/207 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.8 h ago (131/131 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-3050526 | gunit__t1 | 3_5_place_dp | 1.5 | last meaningful line 0.8 h ago (40/40 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_1_grt | 10.7 | last meaningful line 0.7 h ago (226/1033 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 12.2 | last meaningful line 2.5 h ago (208/232 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t68-641169 | ot_s81sl_leaf__t68 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3379/3379 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t70-643388 | ot_s81sl_leaf__t70 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3625/3625 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | synth_odb_v | 0.4 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4806/4807 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_2_route | 2.4 | drt_violations best 88315 last 88315 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1t-1135156 | eco_20261122_165619_1517073-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | so_1121096_ff_82150 | so_1121096_ff_82150 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | so_1121096_tt_82150 | so_1121096_tt_82150 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 12.1 | drt_violations best 101024 last 101024 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 12.9 | drt_violations best 156124 last 156124 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 52737 last 52737 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 10.4 | drt_violations best 55511 last 55511 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 8.6 | last meaningful line 3.0 h ago (208/215 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 6.6 | last meaningful line 2.5 h ago (36/36 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2253150 | kv3_io_ft | 5_2_route | 1.0 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 6.5 | repair_TNS best 10405.5 last 10405.5 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 4.5 | last meaningful line 0.1 h ago (209/212 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_1_grt | 6.5 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | postcts_gate_FF | 6.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2204878 | slice_station__t12 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (227/228 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 10.0 | drt_violations best 48586 last 48586 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_1_grt | 6.6 | last meaningful line 0.3 h ago (2926/2953 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1-1690412 | eco_20261120_150342_478824-i1 | 5_2_route | 2.8 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 9.7 | drt_violations best 73151 last 73151 rows 3 | before-window best 363722, window best 73151 | PROGRESS: drt_violations improved 79.9 % in window |  |
| epyc10 | dpkit-iqf__t1-13421 | iqf__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 9.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 9.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 11.0 | last meaningful line 0.1 h ago (1136/1136 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slice_station__t25-3118247 | slice_station__t25 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 62.5 | last meaningful line 1.6 h ago (1566/1566 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-679902 | col_h10_r1__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-686262 | ot_s81sl_leaf__t7 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-serdes__t2-2124120 | serdes__t2 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-2035057 | tt_ctlm | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 13.0 | drt_violations best 16565 last 16565 rows 11 | before-window best 128949, window best 16565 | PROGRESS: drt_violations improved 87.2 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-497679 | col_h9_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-glue-555250 | glue | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 12.5 | repair_TNS best 16519.3 last 16519.3 rows 3 | before-window best 18374.4, window best 16519.3 | PROGRESS: repair_TNS improved 10.1 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 12.2 | drt_violations best 1385 last 1391 rows 39 | before-window best 67967, window best 1385 | PROGRESS: drt_violations improved 98.0 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 18.0 | drt_violations best 2973 last 8310 rows 19 | before-window best 4012, window best 2973 | PROGRESS: drt_violations improved 25.9 % in window |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 18.1 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 19.7 | drt_violations best 1565 last 2343 rows 18 | before-window best 3242, window best 1565 | PROGRESS: drt_violations improved 51.7 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 8.5 | drt_violations best 80 last 80 rows 11 | before-window best 33922, window best 80 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 8.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 14.5 | last meaningful line 0.1 h ago (595/601 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.2 | repair_TNS best 6475.5 last 6475.5 rows 10 | before-window best 9175.39, window best 6475.5 | PROGRESS: repair_TNS improved 29.4 % in window |  |
