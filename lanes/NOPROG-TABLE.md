# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 15:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'GRT-LABEL': 37, 'YOUNG': 155, 'NO-DATA': 7, 'KEEP': 10, 'EXCLUDED': 3, 'PROGRESS': 52}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (1500/1500 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -971.84 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 22.2 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 7.6 | grt rounds 4 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 7.4 | grt rounds 3 overflow 5:46800 -> 10:46349 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 17.3 | grt rounds 3 overflow 5:24414 -> 10:16733 -> 15:13155 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 17.6 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 7.6 | grt rounds 3 overflow 5:44251 -> 10:47629 -> 15:39542 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t30-921459 | ot_s81sl_leaf__t30 | 5_1_grt | 18.1 | grt rounds 5 overflow 5:32680 -> 10:26052 -> 15:21293 -> 20:20131 -> 25:28075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 15.9 | grt rounds 3 overflow 5:26008 -> 10:17213 -> 15:16053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 17.9 | grt rounds 3 overflow 5:57640 -> 10:67281 -> 15:55315 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 17.9 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40887 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 26.4 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:36858 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:18240 -> 10:58 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 28.3 | grt rounds 4 overflow 5:19451 -> 10:7268 -> 15:6284 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 15.7 | grt rounds 3 overflow 5:29640 -> 10:6637 -> 15:6119 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 15.7 | grt rounds 3 overflow 5:59583 -> 10:59412 -> 15:49973 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 8.8 | grt rounds 3 overflow 5:41193 -> 10:41297 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 17.1 | grt rounds 4 overflow 5:32994 -> 10:26094 -> 15:20564 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 15.7 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 28.3 | grt rounds 4 overflow 5:78865 -> 10:60387 -> 15:48404 -> 20:50724 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-3742048 | col_h10_r0_p1__t1 | 5_1_grt | 8.3 | grt rounds 6 overflow 5:70914 -> 10:983 -> 15:533 -> 20:471 -> 25:434 -> 30:119 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-2115455 | col_h10_r0_p1__t1 | 5_1_grt | 7.6 | grt rounds 5 overflow 5:3253 -> 10:1518 -> 15:1307 -> 20:900 -> 25:956 | GRT-LABEL: DESIGN-FAIL: overflow 1518 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 22.3 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 23.4 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 56.6 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 24.7 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 7.8 | grt rounds 2 overflow 5:31334 -> 10:16178 | GRT-LABEL: DESIGN-FAIL: overflow 16178 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 24.7 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | 5_1_grt | 7.0 | grt rounds 6 overflow 5:1959 -> 10:1638 -> 15:1659 -> 20:1470 -> 25:1486 -> 30:1355 | GRT-LABEL: DESIGN-FAIL: overflow 1638 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 6.8 | grt rounds 3 overflow 5:37849 -> 10:45315 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 6.8 | grt rounds 3 overflow 5:24525 -> 10:19532 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 17.3 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6221 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 6.8 | grt rounds 3 overflow 5:46348 -> 10:50564 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 26.4 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 18.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 18.3 | grt rounds 3 overflow 5:43779 -> 10:41949 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 17.6 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 12.8 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3261/3261 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2331179 | col_h10_r2__t1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3235/3235 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (394/394 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | 5_2_route | 7.3 | drt_violations best 95025 last 95025 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-2685046 | col_h9_r2__t1 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_iq_C__t1-2048142 | dsdv_slice_iq_C__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8818 last 0.8861 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-hd_host_w-2152740 | hd_host_w | 5_2_route | 7.4 | drt_violations best 34674 last 34674 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | pregrt_ff_hold | 7.4 | repair_TNS best 25933.2 last 25933.2 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 18.5 | last meaningful line 1.3 h ago (200/207 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1n-2435290 | kv3_pv_v1n | 4_1_cts | 6.1 | last meaningful line 0.3 h ago (8193/8193 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (3011/3011 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 7.4 | last meaningful line 0.0 h ago (573/573 lines) | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (3983/3983 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t3-213207 | serdes__t3 | 3_3_place_gp | 1.3 | overflow best 0.5111 last 0.5111 rows 54 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-1596289 | serdes__t4 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.9287 last 0.9303 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (2450/2450 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-2673781 | sle_stm_v1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (3641/3641 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 5_2_route | 18.8 | drt_violations best 83501 last 83501 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | otc-1046587-15419 | 1046587 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-79236-20479 | 79236 | gen_lint_yosys | 1.4 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1t-735514 | eco_20261120_185639_3224747-i1t | 5_2_route | 4.5 | drt_violations best 6137 last 6137 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 2.2 | last meaningful line 0.3 h ago (257/258 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | so_3614084_ff_22487 | so_3614084_ff_22487 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (634/634 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | so_3614084_tt_22487 | so_3614084_tt_22487 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (634/634 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | so_3649585_ff_85108 | so_3649585_ff_85108 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | so_3649585_tt_85108 | so_3649585_tt_85108 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-2956 | cbn_q00 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8957 last 0.9137 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-613687 | cbn_q00 | 2_1_floorplan | 0.3 | repair_Viol best 1128 last 1128 rows 809 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-924790 | cbn_q01 | 3_5_place_dp | 2.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 5_1_grt | 3.4 | last meaningful line 0.8 h ago (200/213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 3.7 | last meaningful line 1.3 h ago (199/218 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 3.7 | last meaningful line 1.3 h ago (199/218 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (1731/1731 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 3.5 | repair_Viol best 282 last 282 rows 168 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-645513 | dsdv_slice_lepw_mus_LP__t2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7754 last 0.7754 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-glue-613021 | glue | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (816/816 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 4.3 | last meaningful line 1.5 h ago (336/336 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-622062 | ot_s81sl_leaf__t14 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.5126 last 0.5126 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-4183077 | ot_s81sl_leaf__t54 | 3_3_place_gp | 0.5 | overflow best 0.603 last 0.612 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (278/278 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (665/665 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-3045415 | ot_s81sl_leaf__t74 | 3_3_place_gp | 0.8 | overflow best 0.6615 last 0.6615 rows 11 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-serdes__t15__cla2127225-2739353 | serdes__t15 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-611382 | sle_ctl | 2_1_floorplan | 0.3 | repair_Viol best 2866 last 2866 rows 1152 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fe_v1__cl8210183c-4184425 | sle_fe_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.9603 last 0.9603 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-657729 | sle_fw_v2 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (3663/3663 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-614524 | sle_fw_v2 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4106/4106 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-615542 | sle_sc_v3 | 3_3_place_gp | 0.3 | overflow best 0.4523 last 0.4523 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5074/5075 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5824/5824 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (4585/4585 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4718/4719 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4711/4711 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5379/5379 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (5063/5063 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5210/5210 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-2148023 | slw_hc2 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (5232/5232 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5554/5554 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-1463093 | slw_st_b_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5287/5287 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4621/4621 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (309/309 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 4.6 | last meaningful line 0.8 h ago (672/672 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (653/653 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (205/205 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 5.4 | drt_violations best 25 last 25 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 5.0 | drt_violations best 49 last 49 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 4.0 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (891/891 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (811/811 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (949/949 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (995/995 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (835/835 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (741/741 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (817/817 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (787/787 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (603/603 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (808/808 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 4.7 | last meaningful line 0.5 h ago (263/264 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 34.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261120_080032_3761085-i1-1022173 | eco_20261120_080032_3761085-i1 | 5_2_route | 5.9 | drt_violations best 4 last 4 rows 35 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-882202 | col_h10_r0_p1__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (1165/1165 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (2240/2240 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 6.1 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-1661189 | col_h10_r1__t1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3218/3218 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-1597344 | col_h10_r1__t1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3239/3239 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-1663478 | col_h10_r2__t1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3298/3298 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-1643657 | col_h10_r2__t1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3307/3307 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1541838 | col_h9_r0_p1__t1 | 5_1_grt | 6.1 | last meaningful line 0.5 h ago (244/361 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-3235380 | dsdv_slice_kv512_C__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-gunit__t1-3341748 | gunit__t1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (216/216 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-1734167 | hd_mesh | pregrt_ff_hold | 6.0 | repair_TNS best 225508 last 225508 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2768122 | ot_s81sl_kv_leaf__t5 | 3_3_place_gp | 1.2 | overflow best 0.2479 last 0.2479 rows 38 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t31-1529768 | ot_s81sl_leaf__t31 | tt_setup_repair_grt | 6.1 | repair_Viol best 1741 last 1741 rows 359 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-seqhost__t1-2837346 | seqhost__t1 | 3_3_place_gp | 1.2 | overflow best 0.7083 last 0.7083 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (3679/3679 lines) | YOUNG: evidence 7.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (3676/3676 lines) | YOUNG: evidence 7.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v2-1792546 | sle_sc_v2 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (2866/2866 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-2389841 | svc_hi_dsdv_svc_pvso_entry__t2 | 2_2_floorplan_macro | 4.7 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (198/198 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 99.7 |  | NO-DATA: empty log |  |
| epyc9 | otc-2411353-23881 | 2411353 | gen_lint_yosys | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | otc-2491977-4017 | 2491977 | gen_lint_yosys | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | otc-2969764-31157 | 2969764 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 4.5 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | ap-ageom-kw-slice-station--t37-grt-3379992 | slice-station--t37-grt | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-slice-station--t41-grt-3398259 | slice-station--t41-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-slice-station--t52-dump-3468345 | slice-station--t52-dump | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-slice-station--t52-grt-3468345 | slice-station--t52-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | tt_setup_repair_grt | 20.8 | repair_Remaining best 162493 last 162493 rows 160 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 6.8 | drt_violations best 73630 last 73630 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 6.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (3723/3723 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 7.4 | drt_violations best 62725 last 62725 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (392/392 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3329/3329 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 3_1_place_gp_skip_io | 2.5 | overflow best 0.8706 last 0.8723 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | 3_5_place_dp | 5.3 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_1_yosys_canonicalize | 0.8 | last meaningful line 0.0 h ago (353/353 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3294/3294 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 18.5 | drt_violations best 76548 last 76548 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 6.8 | drt_violations best 19623 last 19623 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 18.8 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 19.5 | drt_violations best 100416 last 100416 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 19.5 | drt_violations best 89452 last 89452 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 19.9 | drt_violations best 144324 last 144324 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (866/866 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 4.1 | last meaningful line 0.0 h ago (611/611 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 2.1 | last meaningful line 0.2 h ago (498/498 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 0.7 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-cbf_q01-749277 | cbf_q01 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-cbn_q01__cld9ff4c40-2195882 | cbn_q01 | 2_1_floorplan | 0.3 | repair_Viol best 1128 last 1128 rows 1241 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | sdc_lint | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t16-2172002 | ot_s81sl_leaf__t16 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (310/310 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-872108 | ot_s81sl_leaf__t67 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cl503337ff__padE0-2190588 | sle_ctl | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | 6_report | 18.8 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-944789 | slw_fw_v3 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 1.3 | last meaningful line 0.1 h ago (417/417 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 4.8 | drt_violations best 357 last 357 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | so_2322774_ff_40545 | so_2322774_ff_40545 | stage_odb_cap | 0.3 | last meaningful line 0.3 h ago (1118/1118 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | so_2322774_tt_40545 | so_2322774_tt_40545 | stage_odb_cap | 0.3 | last meaningful line 0.3 h ago (1118/1118 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | so_2526074_ff_33526 | so_2526074_ff_33526 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (1253/1253 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_2526074_tt_33526 | so_2526074_tt_33526 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (1253/1253 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-2648902 | col_h10_r2__t1 | 5_2_route | 7.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | stage_odb_cap | 6.1 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 28.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 8.8 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 8.8 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-1657776 | col_h10_r1__t1 | stage_odb_cap | 6.1 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 25.7 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 20.8 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 15.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 8.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 62.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 38.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 39.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 17.6 | last meaningful line 0.0 h ago (8570/8570 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-2974046 | kv3_pv_v8 | 4_1_cts | 16.7 | last meaningful line 0.1 h ago (15607/15607 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 18.8 | last meaningful line 0.0 h ago (9107/9107 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 16.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 20.6 | last meaningful line 0.0 h ago (10233/10233 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 21.1 | last meaningful line 0.0 h ago (10266/10266 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 9.9 | drt_violations best 77 last 77 rows 11 | before-window best 26786, window best 77 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 12.7 | last meaningful line 1.6 h ago (1377/1377 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5462/5462 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | 5_2_route | 9.8 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5428/5428 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5529/5529 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 10.0 | last meaningful line 0.0 h ago (5650/5650 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5213/5213 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 10.0 | last meaningful line 0.0 h ago (5498/5498 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 15.7 | last meaningful line 0.0 h ago (8708/8708 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv291547b4-2471228 | col_h9_r0_p2__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1175/1175 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1035/1035 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (893/893 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1113/1113 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1025/1025 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (864/864 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1029/1029 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (990/990 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1033/1033 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1036/1036 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (818/818 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1045/1045 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 16.9 | last meaningful line 0.0 h ago (1168/1168 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1254197 | col_h10_r0_p1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (2030/2030 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1127/1127 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (1131/1131 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (1880/1880 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (1136/1136 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (3951/3951 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 18.5 | last meaningful line 0.0 h ago (9712/9712 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 18.8 | last meaningful line 0.0 h ago (9755/9755 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (456/456 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3496/3496 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (3368/3368 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 25.7 | last meaningful line 0.0 h ago (1531/1531 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 20.7 | last meaningful line 0.0 h ago (1252/1252 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 12.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 12.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 16.3 | last meaningful line 0.0 h ago (1304/1304 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 19.4 | last meaningful line 0.0 h ago (1232/1232 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 18.8 | last meaningful line 0.0 h ago (1120/1120 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 18.8 | last meaningful line 0.0 h ago (1120/1120 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | 5_2_route | 19.0 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 18.8 | last meaningful line 0.0 h ago (1120/1120 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 18.8 | last meaningful line 0.0 h ago (1120/1120 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 18.8 | last meaningful line 0.0 h ago (1120/1120 lines) | PROGRESS: log still growing |  |
