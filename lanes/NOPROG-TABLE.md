# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 18:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 41, 'NO-DATA': 17, 'YOUNG': 190, 'KEEP': 1, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 10.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 10.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 27.2 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 11.8 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 56.9 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50054 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_a_v1__cl67389ecd-3090743 | sle_st_a_v1 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:1170 -> 10:490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_a_v2__pv4242de79-43496 | sle_st_a_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:18195 -> 10:8116 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 71.3 | grt rounds 6 overflow 5:9414 -> 10:5163 -> 15:3337 -> 20:2951 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2032513 | ot_s81sl_leaf__t30 | 5_1_grt | 2.3 | grt rounds 4 overflow 5:32003 -> 10:28443 -> 15:23403 -> 20:21475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 3.6 | grt rounds 4 overflow 5:33787 -> 10:32188 -> 15:29669 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 13.4 | grt rounds 4 overflow 5:7049 -> 10:4208 -> 15:3277 -> 20:3335 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 13.4 | grt rounds 4 overflow 5:5427 -> 10:2816 -> 15:2050 -> 20:2469 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 13.4 | grt rounds 3 overflow 5:24554 -> 10:16574 -> 15:14263 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 3.0 | grt rounds 3 overflow 5:35625 -> 10:39353 -> 15:30181 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 3.6 | grt rounds 2 overflow 5:47225 -> 10:35808 | GRT-LABEL: DESIGN-FAIL: overflow 35808 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t73-3636691 | ot_s81sl_leaf__t73 | 5_1_grt | 3.6 | grt rounds 2 overflow 5:42658 -> 10:22679 | GRT-LABEL: DESIGN-FAIL: overflow 22679 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-691946 | slw_st_a_v1 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:42283 -> 10:4891 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 | col_h9_r0_p6__t1 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:41798 -> 10:421 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 11.5 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 50.5 | grt rounds 3 overflow 5:76937 -> 10:66805 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 55.4 | grt rounds 3 overflow 5:61116 -> 10:62172 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 44.8 | grt rounds 4 overflow 5:58312 -> 10:48779 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 44.8 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 54.6 | grt rounds 4 overflow 5:77624 -> 10:49527 -> 15:42727 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 44.3 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 19.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3967105 | ot_s81sl_leaf__t46 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:53293 -> 10:26724 | GRT-LABEL: DESIGN-FAIL: overflow 26724 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3844958 | ot_s81sl_leaf__t55 | 5_1_grt | 3.6 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t61-3925881 | ot_s81sl_leaf__t61 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:46065 -> 10:42321 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_1_grt | 1.5 | grt rounds 2 overflow 5:3919 -> 10:1726 | GRT-LABEL: DESIGN-FAIL: overflow 1726 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 10.8 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 13.4 | grt rounds 4 overflow 5:42588 -> 10:29799 -> 15:22754 -> 20:20154 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 13.4 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:35245 -> 10:35993 -> 15:33217 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 13.2 | grt rounds 5 overflow 5:47409 -> 10:2770 -> 15:1232 -> 20:909 -> 25:393 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 13.2 | grt rounds 6 overflow 5:47882 -> 10:3290 -> 15:1523 -> 20:1038 -> 25:413 -> 30:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-1671863 | col_h9_r2__t1 | 5_1_grt | 3.2 | grt rounds 2 overflow 5:4658 -> 10:291 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 11.5 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 13.2 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 13.2 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 13.2 | grt rounds 3 overflow 5:22842 -> 10:2722 -> 15:2123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:60853 -> 10:337 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 10.9 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t67-grt-2318545 | ot-s81sl-leaf--t67-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-2991761 | bk_sel__t2 | pregrt_ff_hold | 2.4 | repair_TNS best 2.47658e+06 last 2.47658e+06 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-3065125 | col_h10_r1__t1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (209/212 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-44672 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 144171 last 144171 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-1098453 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t3-886705 | dsdv_slice_c1x_C__t3 | 1_synth | 0.9 | last meaningful line 0.2 h ago (49/49 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-880876 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 0.9 | last meaningful line 0.2 h ago (127/127 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-1472079 | dsdv_slice_lepe_mu_LP__t2 | tt_setup_measure | 0.6 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3047381 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 2.3 | overflow best 0.6771 last 0.6771 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-2617721 | dsdv_slice_lepw_mus_LP__t2 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-kv3_sys_c-1472961 | kv3_sys_c | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (3700/3700 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-native59-2568165 | native59 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t15-1140501 | ot_s81sl_leaf__t15 | tt_setup_repair | 0.7 | repair_Violations best 99 last 153 rows 71 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | tt_setup_repair | 0.8 | repair_Violations best 50 last 177 rows 64 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1512680 | ot_s81sl_leaf__t27 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (199/201 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-1070507 | ot_s81sl_leaf__t28 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t33-29735 | ot_s81sl_leaf__t33 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t4-1513632 | ot_s81sl_leaf__t4 | tt_setup_repair | 0.6 | repair_Violations best 39 last 40 rows 57 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-1482469 | ot_s81sl_leaf__t67 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (302/302 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | generate_abstract | 15.3 | last meaningful line 0.1 h ago (621/621 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2401859 | sle_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (411/411 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-2457491 | sle_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-2697458 | sle_stm_v1 | 1_1_yosys_canonicalize | 0.0 | last meaningful line -0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t25-3118247 | slice_station__t25 | postcts_gate_TT | 2.3 | last meaningful line -0.0 h ago (21394/21394 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-2670978 | slw_fe_v2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (392/392 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-2598673-6856 | 2598673 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-2600316-20386 | 2600316 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2022266 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 38299.4 last 38299.4 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-2024740 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 96642.4 last 96642.4 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-679902 | col_h10_r1__t1 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (204/208 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1812055 | col_h9_r0_p3__t1 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-2046903 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 122014 last 122014 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-1830421 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 605 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-1903434 | col_h9_r2__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-1865895 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 2.3 | overflow best 0.1989 last 0.1989 rows 42 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 2.3 | overflow best 0.1991 last 0.1991 rows 42 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-3659100 | dsdv_slice_c1x_C__t10 | 4_1_cts | 3.6 | last meaningful line 0.0 h ago (3357/3357 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-1830876 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-1932490 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1830466 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1835310 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-683007 | dsdv_slice_lepw_mus_C__t1 | postplace_setup | 3.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_ctl-1812699 | hd_ctl | port_bind | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-1834292 | kv3_io_cor_v1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t17-1828917 | ot_s81sl_leaf__t17 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-1897215 | ot_s81sl_leaf__t34 | 4_1_cts | 0.0 | last meaningful line -0.0 h ago (10/10 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-1816190 | ot_s81sl_leaf__t41 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t43-1817721 | ot_s81sl_leaf__t43 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t47-1932405 | ot_s81sl_leaf__t47 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-1861843 | ot_s81sl_leaf__t5 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t62-1866677 | ot_s81sl_leaf__t62 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t66-1812083 | ot_s81sl_leaf__t66 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-686262 | ot_s81sl_leaf__t7 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-1849823 | ot_s81sl_leaf__t72 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t2-2124120 | serdes__t2 | 5_1_grt | 2.3 | last meaningful line 0.2 h ago (229/790 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t4-1837565 | serdes__t4 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | pregrt_ff_hold | 2.3 | repair_TNS best 14429.5 last 14429.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 4_1_cts | 2.3 | last meaningful line 0.2 h ago (5380/5380 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t17-1827654 | slice_station__t17 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (219/219 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-1777311 | slw_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (318/318 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | postcts_gate_FF | 2.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-1094939-10134 | 1094939 | signoff | 2.8 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | otc-1481339-18431 | 1481339 | signoff | 2.6 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | otc-2017932-16297 | 2017932 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 5.6 | drt_violations best 45 last 128 rows 18 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_161953_3893587-i1-2758523 | eco_20261122_161953_3893587-i1 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1t-3385034 | eco_20261122_164248_3895049-i1t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1t-3466592 | eco_20261122_164521_3948325-i1t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_180145_3931237-i1-1443078 | eco_20261122_180145_3931237-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1t-1909174 | eco_20261122_181101_3945375-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-fin-2236985 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (681/681 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1770336_ff_50066 | so_1770336_ff_50066 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_1770336_tt_50066 | so_1770336_tt_50066 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1394491 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.0 | repair_Viol best 6050 last 6050 rows 248 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-1188398 | col_h10_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_2_route | 4.9 | drt_violations best 52747 last 52747 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | 5_1_grt | 3.6 | repair_TNS best 24.981 last 24.981 rows 8 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2769627 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 1.8 | last meaningful line 0.1 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-8352 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 0.8 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1402581 | dsdv_slice_lepe_nh_mus_LP__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (63/63 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (206/208 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4886/4886 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t30-10758 | ot_s81sl_leaf__t30 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t50-1499047 | ot_s81sl_leaf__t50 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 13.4 | drt_violations best 107202 last 107202 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_1_grt | 5.0 | last meaningful line 0.1 h ago (2031/2046 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-1184106 | slice_station__t6 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2306/2307 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_1_grt | 4.9 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-1183239-11759 | 1183239 | 3_3_place_gp | 0.1 | overflow best 0.3887 last 0.3945 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | otc-1503843-30452 | 1503843 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1522713-6391 | 1522713 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1-251441 | eco_20261122_215654_330309-i1 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1-3987348 | eco_20261122_220050_168828-i1 | 5_2_route | 1.0 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-dsdv-slice-c1x-C--t4-dump-2275336 | dsdv-slice-c1x-C--t4-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-dsdv-slice-c1x-C--t4-grt-2275336 | dsdv-slice-c1x-C--t4-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 10.1 | drt_violations best 110424 last 110424 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3060/3060 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_2_route | 10.6 | drt_violations best 18 last 18 rows 48 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 10.6 | last meaningful line 0.1 h ago (290/291 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 730 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_5_place_dp | 13.0 | last meaningful line 1.0 h ago (131/131 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-2778952 | kv3_io_cor_v1 | 5_1_grt | 1.5 | last meaningful line 0.1 h ago (753/784 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3e-2217024 | kv3_pv_v3e | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t10-2809979 | ot_s81sl_leaf__t10 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (201/206 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t36-2215632 | ot_s81sl_leaf__t36 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-1998394 | ot_s81sl_leaf__t44 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9962 last 0.9962 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-1995091 | ot_s81sl_leaf__t45 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8309 last 0.853 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t52-2261818 | ot_s81sl_leaf__t52 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t56-1994594 | ot_s81sl_leaf__t56 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t58-589434 | ot_s81sl_leaf__t58 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-2863435 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 1.5 | repair_TNS best 260205 last 260205 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slice_station__t29__cl2e5c855a-3939444 | slice_station__t29 | 5_2_route | 2.9 | drt_violations best 16979 last 16979 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3952570 | slice_station__t40 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-2298305 | kvcore-qkd_ectlk_q0__216x172.8_ | 1_synth | 0.0 | last meaningful line -0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | kvcore-qkd_ectlk_q1__243.648x172.8_-2297614 | kvcore-qkd_ectlk_q1__243.648x172.8_ | 2_1_floorplan | 0.0 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | kvcore-qkd_ectlk_q2__243.648x172.8_-2297415 | kvcore-qkd_ectlk_q2__243.648x172.8_ | 1_synth | 0.0 | last meaningful line -0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | kvcore-qkd_ectlk_q3__216x172.8_-2299899 | kvcore-qkd_ectlk_q3__216x172.8_ | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1232960-5145 | 1232960 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-1322613-22465 | 1322613 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-2132787-11127 | 2132787 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-hd-lep0N-w-grt-179093 | hd-lep0N-w-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-237532 | col_h10_r1__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line -0.0 h ago (101/101 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 13.6 | drt_violations best 178849 last 178849 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-238701 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 909 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-275844 | col_h9_r2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2097/2097 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t6-401942 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-405849 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-288662 | dsdv_slice_kv512_C__t1 | 1_2_yosys | 0.1 | last meaningful line 0.1 h ago (254/254 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-426957 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-eng__t1-443909 | eng__t1 | 4_1_cts | 0.0 | last meaningful line -0.0 h ago (8/8 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-236913 | hd_host_n | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N-3228776 | hd_lep0N | 3_3_place_gp | 0.7 | last meaningful line 0.1 h ago (192/192 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N_w-402981 | hd_lep0N_w | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | 5_2_route | 4.3 | drt_violations best 5637 last 5637 rows 3 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t3-457907 | ot_s81sl_kv_leaf__t3 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-457556 | ot_s81sl_leaf__t22 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-272872 | ot_s81sl_leaf__t25 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-426492 | ot_s81sl_leaf__t39 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t42-283577 | ot_s81sl_leaf__t42 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-306943 | ot_s81sl_leaf__t44 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__cl958451dd-450815 | ot_s81sl_leaf__t53 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-236943 | ot_s81sl_leaf__t59 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8222 last 0.8468 rows 14 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t69-442023 | ot_s81sl_leaf__t69 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t3-403584 | serdes__t3 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t22-239981 | slice_station__t22 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9989 last 0.9989 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 5_2_route | 4.3 | drt_violations best 19950 last 19950 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | postcts_gate_FF | 4.3 | last meaningful line 0.1 h ago (1373/1373 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_2_route | 4.3 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | 6_report | 4.3 | last meaningful line 0.0 h ago (332/332 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clb036e152-429176 | slw_st_a_v1 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 4.0 | last meaningful line 4.0 h ago (3/3 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | otc-237228-21491 | 237228 | qwen_compute.t.slw_fe_v1__clfe325744__cldb4efe33 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3560213-28657 | 3560213 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-396301-31902 | 396301 | qwen_compute.t.slw_fe_v1__clfe325744__cldb4efe33 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-397733-78 | 397733 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_bc-231218 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (460/460 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-3504713 | eco-i1t | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (244/1240 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco-i3-2776988 | eco-i3 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 6.0 | drt_violations best 71 last 71 rows 14 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i2t-4164617 | eco_20261122_174935_2347281-i2t | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (261/660 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i2t-3854167 | eco_20261122_180231_342380-i2t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (239/536 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_2693915_ff_76102 | so_2693915_ff_76102 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (776/776 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | so_2693915_tt_76102 | so_2693915_tt_76102 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (776/776 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 13.2 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 13.2 | last meaningful line 0.3 h ago (287/288 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1675980 | col_h9_r0_p4__t1 | 5_1_grt | 3.2 | last meaningful line 0.1 h ago (194/207 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | 3_1_place_gp_skip_io | 3.2 | overflow best 0.3861 last 0.3861 rows 34 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-gunit__t1-3050526 | gunit__t1 | 3_5_place_dp | 2.5 | last meaningful line 1.8 h ago (40/40 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_1_grt | 11.7 | last meaningful line 0.0 h ago (1059/1060 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 13.2 | last meaningful line 3.5 h ago (208/238 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t68-641169 | ot_s81sl_leaf__t68 | pregrt_ff_hold | 1.4 | repair_Violations best 354 last 387 rows 26 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t70-643388 | ot_s81sl_leaf__t70 | pregrt_ff_hold | 1.4 | repair_TNS best 12217.8 last 12217.8 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | 3_3_place_gp | 1.4 | overflow best 0.6717 last 0.6717 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (5103/5103 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-2998450-18208 | 2998450 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_2_route | 3.4 | drt_violations best 88315 last 88315 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1t-1135156 | eco_20261122_165619_1517073-i1t | 5_2_route | 1.0 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | so_2396315_ff_83052 | so_2396315_ff_83052 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_2396315_tt_83052 | so_2396315_tt_83052 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel2 | ap-ageom-kw-dsdv-slice-lepe-mu-C--t1--strip-N-grt-1605549 | dsdv-slice-lepe-mu-C--t1--strip-N-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 13.9 | drt_violations best 156124 last 156124 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 11.0 | drt_violations best 1397 last 1397 rows 5 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 11.4 | drt_violations best 1390 last 1390 rows 6 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 9.6 | last meaningful line 4.0 h ago (208/217 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 7.6 | last meaningful line 3.5 h ago (36/36 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 9.6 | repair_Violations best 589 last 589 rows 33 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_LP__t2-393920 | dsdv_slice_lepw_mu_LP__t2 | 3_3_place_gp | 0.7 | overflow best 0.1982 last 0.1982 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_lep0N-404470 | hd_lep0N | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (178/178 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1171540 | hd_turn_a | 5_2_route | 0.4 | drt_violations best 3137 last 3137 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-1204232 | hd_turn_a | 5_2_route | 0.3 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 5.5 | repair_TNS best 237075 last 237075 rows 3 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_1_grt | 7.5 | last meaningful line 0.7 h ago (1284/2068 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 11.0 | drt_violations best 4181 last 4181 rows 3 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 7.6 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvea45273b-235092 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 |  | KEEP: col_h9_r2__t1__cl774acf45__pvea45273b	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3113889 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 10.7 | drt_violations best 21337 last 21337 rows 5 | before-window best 363722, window best 21337 | PROGRESS: drt_violations improved 94.1 % in window |  |
| epyc10 | dpkit-iqf__t1-13421 | iqf__t1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_sys_c-1070279 | kv3_sys_c | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 12.0 | last meaningful line 0.5 h ago (1166/1166 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1501489 | sle_st_a_v1 | pregrt_ff_hold | 0.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 7.8 | drt_violations best 41 last 41 rows 13 | before-window best 66325, window best 41 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1t-873116 | eco_20261122_223531_3628570-i1t | 5_2_route | 3.6 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 63.5 | last meaningful line 0.2 h ago (1606/1606 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pva2370bfd-2123745 | col_h9_r1__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-2035057 | tt_ctlm | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 14.0 | drt_violations best 16565 last 16565 rows 11 | before-window best 128949, window best 16565 | PROGRESS: drt_violations improved 87.2 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-2830715 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-glue-555250 | glue | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | pregrt_ff_hold | 2.6 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 13.5 | repair_TNS best 8995.89 last 8995.89 rows 3 | before-window best 10232.3, window best 8995.89 | PROGRESS: repair_TNS improved 12.1 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-645502 | col_h9_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 19.0 | drt_violations best 2973 last 5816 rows 20 | before-window best 3281, window best 2973 | PROGRESS: drt_violations improved 9.4 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 20.7 | drt_violations best 1452 last 1452 rows 19 | before-window best 2439, window best 1452 | PROGRESS: drt_violations improved 40.5 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 9.5 | drt_violations best 18 last 18 rows 31 | before-window best 33922, window best 18 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel2 | dpkit-coll_ftm-1154585 | coll_ftm | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 13.2 | repair_TNS best 3422.48 last 3422.48 rows 11 | before-window best 6154.64, window best 3422.48 | PROGRESS: repair_TNS improved 44.4 % in window |  |
