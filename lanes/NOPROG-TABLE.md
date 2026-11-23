# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 18:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 1, 'GRT-LABEL': 35, 'YOUNG': 210, 'NO-DATA': 16, 'EXCLUDED': 1, 'PROGRESS': 43}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 11.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 11.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-3659100 | dsdv_slice_c1x_C__t10 | tt_setup_repair | 4.1 | repair_Viol best 7997 last 7997 rows 25 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -812.68 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 27.7 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 12.3 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 57.4 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50054 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_a_v1__cl67389ecd-3090743 | sle_st_a_v1 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:1170 -> 10:490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_a_v2__pv4242de79-43496 | sle_st_a_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:18195 -> 10:8116 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 71.8 | grt rounds 6 overflow 5:9414 -> 10:5163 -> 15:3337 -> 20:2951 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2032513 | ot_s81sl_leaf__t30 | 5_1_grt | 2.8 | grt rounds 4 overflow 5:32003 -> 10:27757 -> 15:23403 -> 20:21475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 4.1 | grt rounds 4 overflow 5:33787 -> 10:32188 -> 15:29669 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 13.9 | grt rounds 4 overflow 5:7049 -> 10:4695 -> 15:3277 -> 20:3335 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 13.9 | grt rounds 3 overflow 5:24554 -> 10:16574 -> 15:14263 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 3.5 | grt rounds 3 overflow 5:35625 -> 10:36184 -> 15:30181 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 4.1 | grt rounds 2 overflow 5:47225 -> 10:35808 | GRT-LABEL: DESIGN-FAIL: overflow 35808 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-691946 | slw_st_a_v1 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:42283 -> 10:4891 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 12.0 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 51.0 | grt rounds 3 overflow 5:76937 -> 10:70297 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 55.9 | grt rounds 3 overflow 5:61116 -> 10:63134 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 45.3 | grt rounds 4 overflow 5:58312 -> 10:48779 -> 15:39348 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 45.3 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 4.0 | grt rounds 2 overflow 5:1776 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 55.1 | grt rounds 4 overflow 5:77624 -> 10:49527 -> 15:42727 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 44.8 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 19.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 11.3 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 13.9 | grt rounds 4 overflow 5:42588 -> 10:29799 -> 15:22754 -> 20:20154 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 13.9 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 5_1_grt | 4.8 | grt rounds 3 overflow 5:35245 -> 10:35993 -> 15:33217 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 13.7 | grt rounds 5 overflow 5:47409 -> 10:2770 -> 15:1232 -> 20:909 -> 25:393 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 13.7 | grt rounds 6 overflow 5:47882 -> 10:2931 -> 15:1523 -> 20:1038 -> 25:413 -> 30:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-1671863 | col_h9_r2__t1 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:4658 -> 10:291 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 12.0 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 13.7 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 13.7 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 13.7 | grt rounds 3 overflow 5:22842 -> 10:2722 -> 15:2123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_1_grt | 6.0 | grt rounds 2 overflow 5:60853 -> 10:337 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 11.4 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-2991761 | bk_sel__t2 | pregrt_ff_hold | 2.9 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-3065125 | col_h10_r1__t1 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (209/219 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3113889 | col_h9_r0_p5__t1 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (195/208 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-1098453 | dsdv_slice_c1x_C__t10 | selrange | 1.3 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t3-886705 | dsdv_slice_c1x_C__t3 | 1_synth | 1.4 | last meaningful line 0.5 h ago (49/49 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-880876 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.5 h ago (127/127 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-1472079 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.1 | repair_TNS best 102526 last 102526 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3047381 | dsdv_slice_lepw_mu_C__t1 | 3_4_place_resized | 2.8 | last meaningful line 0.1 h ago (397/397 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-2617721 | dsdv_slice_lepw_mus_LP__t2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5334/5334 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-iqf__t1-13421 | iqf__t1 | tt_setup_repair_grt | 2.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-native59-2568165 | native59 | 2_1_floorplan | 0.6 | last meaningful line 0.1 h ago (1359/1359 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t15-1140501 | ot_s81sl_leaf__t15 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | pregrt_ff_hold | 1.3 | repair_Violations best 5999 last 6034 rows 112 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1512680 | ot_s81sl_leaf__t27 | 5_1_grt | 1.1 | last meaningful line 0.5 h ago (199/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-1070507 | ot_s81sl_leaf__t28 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t33-29735 | ot_s81sl_leaf__t33 | 5_1_grt | 2.0 | last meaningful line 0.3 h ago (205/208 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t35-2862501 | ot_s81sl_leaf__t35 | hold_gate | 0.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t38-2879349 | ot_s81sl_leaf__t38 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3247/3247 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t4-1513632 | ot_s81sl_leaf__t4 | 5_1_grt | 1.1 | last meaningful line -0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-1482469 | ot_s81sl_leaf__t67 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-3226431 | ot_s81sl_leaf__t67 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | generate_abstract | 15.8 | last meaningful line 0.2 h ago (623/623 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-2766932 | sle_fw_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5983 last 0.5983 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3138515 | sle_hc1 | 3_3_place_gp | 0.3 | last meaningful line -0.0 h ago (332/332 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2401859 | sle_hc1 | 3_3_place_gp | 0.6 | overflow best 0.6529 last 0.6529 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-2457491 | sle_hc2 | 3_3_place_gp | 0.6 | overflow best 0.099 last 0.099 rows 50 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1501489 | sle_st_a_v1 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (274/1283 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-2697458 | sle_stm_v1 | 3_3_place_gp | 0.5 | overflow best 0.2763 last 0.2763 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slice_station__t25-3118247 | slice_station__t25 | 5_2_route | 2.8 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-2670978 | slw_fe_v2 | 3_3_place_gp | 0.5 | overflow best 0.4719 last 0.4719 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-3180450 | slw_su_l1 | 3_3_place_gp | 0.3 | overflow best 0.3015 last 0.3015 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | otc-2598673-6856 | 2598673 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-2600316-20386 | 2600316 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-3288262-271 | 3288262 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | prd-fin-873116 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7873 last 0.7873 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2022266 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 38299.4 last 38299.4 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.2066 last 0.2066 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-679902 | col_h10_r1__t1 | 5_1_grt | 3.5 | last meaningful line 0.8 h ago (204/213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1812055 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3228 last 0.3228 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-2046903 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 122014 last 122014 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pva2370bfd-2123745 | col_h9_r1__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-1903434 | col_h9_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 67926.7 last 67926.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-1865895 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 3_5_place_dp | 2.8 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 4_1_cts | 2.8 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-1830876 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-1932490 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1830466 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1835310 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-glue-2092798 | glue | 3_3_place_gp | 0.5 | overflow best 0.6069 last 0.6069 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-hd_ctl-1812699 | hd_ctl | 3_3_place_gp | 0.5 | overflow best 0.2986 last 0.319 rows 185 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-1834292 | kv3_io_cor_v1 | 3_3_place_gp | 0.5 | overflow best 0.1702 last 0.1702 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v3-2034326 | kv3_pv_v3 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.936 last 0.9366 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t17-1828917 | ot_s81sl_leaf__t17 | 3_3_place_gp | 0.5 | overflow best 0.4543 last 0.4643 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3416/3416 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-1897215 | ot_s81sl_leaf__t34 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3447/3447 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-1816190 | ot_s81sl_leaf__t41 | 3_3_place_gp | 0.5 | last meaningful line 0.2 h ago (181/181 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t43-1817721 | ot_s81sl_leaf__t43 | 3_3_place_gp | 0.5 | overflow best 0.4551 last 0.4591 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t47-1932405 | ot_s81sl_leaf__t47 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4164/4164 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-1861843 | ot_s81sl_leaf__t5 | pregrt_ff_hold | 0.5 | last meaningful line -0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t62-1866677 | ot_s81sl_leaf__t62 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4342/4342 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t66-1812083 | ot_s81sl_leaf__t66 | 3_3_place_gp | 0.5 | overflow best 0.5509 last 0.5509 rows 10 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-686262 | ot_s81sl_leaf__t7 | 5_1_grt | 3.5 | last meaningful line 0.8 h ago (203/212 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-1849823 | ot_s81sl_leaf__t72 | 3_3_place_gp | 0.5 | last meaningful line 0.1 h ago (497/497 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t4-1837565 | serdes__t4 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | pregrt_ff_hold | 2.8 | repair_TNS best 19626.5 last 19626.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slice_station__t17-1827654 | slice_station__t17 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-2336581 | slice_station__t29 | pregrt_ff_hold | 0.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-2458281 | slw_fe_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 7827.05 last 7827.05 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 3_3_place_gp | 0.6 | overflow best 0.6701 last 0.6701 rows 30 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 3_3_place_gp | 0.4 | overflow best 0.9261 last 0.9268 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-1777311 | slw_hc1 | 3_3_place_gp | 0.6 | overflow best 0.6505 last 0.6505 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (257/257 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | eco-abs-2513704 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.0 h ago (731/731 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-1094939-10134 | 1094939 | signoff | 3.3 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | otc-1481339-18431 | 1481339 | signoff | 3.1 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | otc-2017932-16297 | 2017932 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 6.1 | drt_violations best 1 last 28 rows 31 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_161953_3893587-i1-2758523 | eco_20261122_161953_3893587-i1 | 5_3_fillcell | 2.4 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1t-3385034 | eco_20261122_164248_3895049-i1t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1t-3466592 | eco_20261122_164521_3948325-i1t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_180145_3931237-i1-1443078 | eco_20261122_180145_3931237-i1 | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (235/248 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1t-1909174 | eco_20261122_181101_3945375-i1t | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_1770336_ff_50066 | so_1770336_ff_50066 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc2 | so_1770336_tt_50066 | so_1770336_tt_50066 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-dsdv-slice-kv512-C--t1-grt-2171845 | dsdv-slice-kv512-C--t1-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-gunit--t1-grt-2220293 | gunit--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1394491 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.5 | overflow best 0.3468 last 0.3468 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_2_route | 5.4 | drt_violations best 52747 last 52747 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-8352 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1402581 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_3_place_gp | 0.5 | overflow best 0.6417 last 0.6417 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_ctl-1922947 | hd_ctl | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3126/3126 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t21-1786623 | ot_s81sl_leaf__t21 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2927/2927 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t30-10758 | ot_s81sl_leaf__t30 | 5_1_grt | 1.3 | last meaningful line 0.3 h ago (197/204 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4381/4381 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t50-1499047 | ot_s81sl_leaf__t50 | hold_gate | 0.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 13.9 | drt_violations best 107202 last 107202 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-1949749 | sle_fw_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl69f5e854-1618794 | sle_fw_v2 | 3_3_place_gp | 0.5 | overflow best 0.3903 last 0.3903 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | postcts_gate_FF | 0.5 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-1764151 | sle_hc1 | 3_3_place_gp | 0.4 | overflow best 0.882 last 0.882 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1983201 | sle_st_a_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6068/6068 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | postcts_gate_TT | 5.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1619357 | sle_su_l1 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t18-1919126 | slice_station__t18 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-1928775 | slice_station__t40 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2819/2819 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t45-1870760 | slice_station__t45 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl0755c26e-1918139 | slice_station__t6 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (167/168 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1946912 | slw_fe_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_1_grt | 5.4 | last meaningful line 0.3 h ago (250/1257 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1955539 | slw_fw_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-1986095 | tt_ctlm | 3_3_place_gp | 0.3 | last meaningful line -0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1183239-11759 | 1183239 | 3_4_place_resized | 0.6 | last meaningful line 0.1 h ago (364/364 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1-251441 | eco_20261122_215654_330309-i1 | 5_2_route | 1.2 | last meaningful line 0.2 h ago (250/251 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1-3987348 | eco_20261122_220050_168828-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 10.6 | drt_violations best 110424 last 110424 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 93931.6 last 93931.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_2_route | 11.1 | drt_violations best 15 last 15 rows 63 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 11.1 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 2.0 | last meaningful line 0.0 h ago (243/244 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_5_place_dp | 13.5 | last meaningful line 1.5 h ago (131/131 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (259/272 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-2778952 | kv3_io_cor_v1 | postcts_gate_TT | 2.0 | last meaningful line -0.0 h ago (29048/29048 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t10-2809979 | ot_s81sl_leaf__t10 | 5_1_grt | 2.0 | last meaningful line 0.8 h ago (201/210 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t36-2215632 | ot_s81sl_leaf__t36 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3818/3818 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-1998394 | ot_s81sl_leaf__t44 | 3_3_place_gp | 0.6 | overflow best 0.506 last 0.506 rows 21 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-1995091 | ot_s81sl_leaf__t45 | 3_3_place_gp | 0.6 | overflow best 0.3903 last 0.3903 rows 33 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t52-2261818 | ot_s81sl_leaf__t52 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3709/3709 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t56-1994594 | ot_s81sl_leaf__t56 | 3_3_place_gp | 0.6 | overflow best 0.5558 last 0.5565 rows 5 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t29__cl2e5c855a-3939444 | slice_station__t29 | 5_2_route | 3.4 | drt_violations best 16979 last 16979 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3952570 | slice_station__t40 | 5_2_route | 3.4 | drt_violations best 17220 last 17220 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-3106818 | kvcore-qkd_ectlk_q0__216x172.8_ | 3_3_place_gp | 0.1 | overflow best 0.2992 last 0.5676 rows 91 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-3106818-lec | kvcore-qkd_ectlk_q0__216x172.8_ | lec | 0.0 | LEC last write -0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc8 | otc-1322613-22465 | 1322613 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-2132787-11127 | 2132787 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2358604-8404 | 2358604 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-237532 | col_h10_r1__t1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 14.1 | drt_violations best 178849 last 178849 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-238701 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.6 | overflow best 0.4519 last 0.4519 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-275844 | col_h9_r2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 104767 last 104767 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 77152 last 77152 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t6-401942 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-405849 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3387/3388 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-288662 | dsdv_slice_kv512_C__t1 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-426957 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-236913 | hd_host_n | 5_2_route | 0.6 | last meaningful line 0.0 h ago (217/218 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N-3228776 | hd_lep0N | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N_w-402981 | hd_lep0N_w | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 6_report | 4.8 | last meaningful line 0.2 h ago (1035/1035 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-852757 | ot_s81sl_kv_leaf__t5 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (845/845 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-457556 | ot_s81sl_leaf__t22 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4111/4112 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-426492 | ot_s81sl_leaf__t39 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3457/3457 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t42-283577 | ot_s81sl_leaf__t42 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-306943 | ot_s81sl_leaf__t44 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3264/3264 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-236943 | ot_s81sl_leaf__t59 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t3-403584 | serdes__t3 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t22-239981 | slice_station__t22 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 5_2_route | 4.8 | last meaningful line 0.1 h ago (255/255 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_2_route | 4.8 | drt_violations best 31237 last 31237 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-627789 | slw_fw_v3 | 3_3_place_gp | 0.4 | overflow best 0.3534 last 0.3537 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_st_a_v1__clb036e152-429176 | slw_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (9080/9080 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_stm_v2__cl9beb65e6-644083 | slw_stm_v2 | 3_3_place_gp | 0.4 | overflow best 0.4922 last 0.4922 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-1172605-8135 | 1172605 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3560213-28657 | 3560213 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-682537-13250 | 682537 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1t-3504713 | eco-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco-i3-2776988 | eco-i3 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 6.5 | drt_violations best 53 last 53 rows 15 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i2t-3854167 | eco_20261122_180231_342380-i2t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 13.7 | last meaningful line 0.5 h ago (292/293 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3359910 | col_h10_r0_p4__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3155/3155 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-3355984 | col_h10_r2__t1 | 3_3_place_gp | 0.4 | overflow best 0.2717 last 0.305 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3367083 | col_h10_r2__t1 | pregrt_ff_hold | 0.4 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3522831 | col_h10_r2__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2429/2429 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 13.7 | last meaningful line 0.5 h ago (289/290 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1675980 | col_h9_r0_p4__t1 | 5_1_grt | 3.7 | last meaningful line 0.5 h ago (208/214 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3518851 | col_h9_r0_p4__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3289/3289 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3535177 | col_h9_r0_p5__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3067/3067 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3531236 | col_h9_r0_p5__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3106/3106 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3517762 | col_h9_r0_p5__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (433/433 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-3367117 | col_h9_r1__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2586/2586 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3522410 | col_h9_r1__t1 | 4_1_cts | 0.3 | last meaningful line -0.0 h ago (2410/2410 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2404/2404 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-645502 | col_h9_r2__t1 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (151/151 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_1_grt | 3.7 | repair_Remaining best 98675 last 98675 rows 20 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-3365034 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | 3_3_place_gp | 3.7 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-3050526 | gunit__t1 | 3_5_place_dp | 3.0 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_1_grt | 12.2 | last meaningful line 0.3 h ago (1121/1127 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 13.7 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-3536309 | ot_s81sl_leaf__t2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3521776 | ot_s81sl_leaf__t25 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t32-3518438 | ot_s81sl_leaf__t32 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8647 last 0.8647 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3-3373654 | ot_s81sl_leaf__t40 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2449/2449 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (54/54 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t68-641169 | ot_s81sl_leaf__t68 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (189/202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t70-643388 | ot_s81sl_leaf__t70 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-3360119 | sle_st_a_v1 | 3_3_place_gp | 0.4 | overflow best 0.3207 last 0.3207 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | pregrt_ff_hold | 1.9 | repair_TNS best 42532.8 last 42532.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slice_station__t28-3353995 | slice_station__t28 | 3_3_place_gp | 0.4 | overflow best 0.3664 last 0.3666 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9984 last 0.9984 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3514989 | slw_hc3 | 3_3_place_gp | 0.3 | overflow best 0.9694 last 0.9694 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2372/2372 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-2998450-18208 | 2998450 | signoff | 0.5 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-3506113-5412 | 3506113 | qwen_compute.t.sle_st_b_v2__cl14c98df5__pvcd986c42 | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3507570-5942 | 3507570 | qwen_compute.t.sle_st_b_v2__cl14c98df5__pvcd986c42 | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_2_route | 3.9 | drt_violations best 88315 last 88315 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1t-1135156 | eco_20261122_165619_1517073-i1t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | so_2396315_ff_83052 | so_2396315_ff_83052 | signoff | 0.9 |  | NO-DATA: empty log |  |
| intel1 | so_2396315_tt_83052 | so_2396315_tt_83052 | signoff | 0.9 |  | NO-DATA: empty log |  |
| intel2 | ap-ageom-kw-dsdv-slice-lepe-mu-C--t1-grt-2748223 | dsdv-slice-lepe-mu-C--t1-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 14.4 | drt_violations best 156124 last 156124 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1154585 | coll_ftm | 5_1_grt | 0.9 | repair_TNS best 17.396 last 17.396 rows 8 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 10.1 | last meaningful line 4.5 h ago (208/217 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1__strip_N-2063007 | dsdv_slice_lepe_mu_C__t1__strip_N | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 10.1 | last meaningful line 0.1 h ago (159/159 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N-404470 | hd_lep0N | 3_3_place_gp | 1.2 | overflow best 0.5172 last 0.5172 rows 19 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 6.0 | last meaningful line 0.2 h ago (534/547 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_2_route | 8.1 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 6_report | 11.5 | last meaningful line 0.0 h ago (347/347 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 8.1 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | otc-1804292-14396 | 1804292 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2844492 | col_h10_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-2806984 | col_h10_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-44672 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 11.2 | drt_violations best 17830 last 17830 rows 6 | before-window best 363722, window best 17830 | PROGRESS: drt_violations improved 95.1 % in window |  |
| epyc10 | dpkit-kv3_sys_c-1070279 | kv3_sys_c | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_sys_c-1472961 | kv3_sys_c | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 12.5 | last meaningful line 1.0 h ago (1166/1166 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 8.3 | drt_violations best 41 last 41 rows 13 | before-window best 66325, window best 41 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 64.0 | last meaningful line 0.5 h ago (1606/1606 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-2024740 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2510614 | col_h9_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-serdes__t2-2124120 | serdes__t2 | 5_1_grt | 2.8 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-2035057 | tt_ctlm | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | 5_1_grt | 4.1 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | tt_setup_repair | 1.3 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-1772119 | slice_station__t6 | pregrt_ff_hold | 0.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | pregrt_ff_hold | 0.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 14.5 | drt_violations best 15336 last 15336 rows 12 | before-window best 128949, window best 15336 | PROGRESS: drt_violations improved 88.1 % in window |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-2830715 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-glue-555250 | glue | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-2863435 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-eng__t1-443909 | eng__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t69-442023 | ot_s81sl_leaf__t69 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 5_2_route | 4.8 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3365642 | col_h10_r1__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 14.0 | repair_TNS best 6607.94 last 6607.94 rows 7 | before-window best 10232.3, window best 6607.94 | PROGRESS: repair_TNS improved 35.4 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-3533701 | col_h9_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 19.5 | drt_violations best 2973 last 5326 rows 21 | before-window best 3281, window best 2973 | PROGRESS: drt_violations improved 9.4 % in window |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | 3_5_place_dp | 1.9 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 21.2 | drt_violations best 1202 last 1202 rows 20 | before-window best 2439, window best 1202 | PROGRESS: drt_violations improved 50.7 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 10.0 | drt_violations best 18 last 18 rows 48 | before-window best 33922, window best 18 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 8.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 13.7 | repair_TNS best 2390.66 last 2390.66 rows 5 | before-window best 3370.61, window best 2390.66 | PROGRESS: repair_TNS improved 29.1 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_1_grt | 8.0 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
