# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 16:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 1, 'GRT-LABEL': 36, 'YOUNG': 195, 'NO-DATA': 7, 'KEEP': 10, 'EXCLUDED': 3, 'PROGRESS': 61}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v1n-2435290 | kv3_pv_v1n | tt_setup_repair | 6.8 | repair_Viol best 3964 last 3964 rows 9 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -1267.93 ps (< -300, gate TT >= -42); job a | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (2635/2635 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -687.56 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2214/2214 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -1491.99 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 24.8 | drt_violations best 7619 last 17503 rows 19 | before-window best 7619, window best 17503 | NO-PROGRESS: drt_violations best 17503 vs 7619 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 22.9 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 8.4 | grt rounds 4 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 8.1 | grt rounds 3 overflow 5:46800 -> 10:46073 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 18.0 | grt rounds 3 overflow 5:24414 -> 10:16733 -> 15:13155 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 18.4 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:43983 -> 10:47629 -> 15:39542 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t30-921459 | ot_s81sl_leaf__t30 | 5_1_grt | 18.8 | grt rounds 5 overflow 5:32680 -> 10:26052 -> 15:21293 -> 20:20131 -> 25:28075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 16.6 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:16053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 18.6 | grt rounds 3 overflow 5:57640 -> 10:67281 -> 15:55315 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 18.6 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40887 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 27.2 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:36858 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | 5_1_grt | 4.3 | grt rounds 6 overflow 5:12227 -> 10:8336 -> 15:4776 -> 20:1436 -> 25:480 -> 30:459 | GRT-LABEL: DESIGN-FAIL: overflow 8336 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 2.4 | grt rounds 3 overflow 5:30377 -> 10:16662 -> 15:14013 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:41957 -> 10:39840 | GRT-LABEL: DESIGN-FAIL: overflow 39840 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 28.8 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6284 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 16.2 | grt rounds 3 overflow 5:29640 -> 10:6637 -> 15:6119 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 16.2 | grt rounds 3 overflow 5:59583 -> 10:59412 -> 15:49973 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 9.3 | grt rounds 3 overflow 5:41295 -> 10:41297 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 17.6 | grt rounds 4 overflow 5:38322 -> 10:26094 -> 15:20564 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 16.2 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 28.8 | grt rounds 4 overflow 5:78865 -> 10:60387 -> 15:48404 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 23.1 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 24.2 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 57.4 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 25.4 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:31334 -> 10:16178 | GRT-LABEL: DESIGN-FAIL: overflow 16178 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 25.4 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 7.5 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 7.5 | grt rounds 3 overflow 5:24525 -> 10:17867 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 18.0 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6221 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 7.5 | grt rounds 3 overflow 5:46348 -> 10:50564 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 27.1 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 19.0 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 19.0 | grt rounds 3 overflow 5:43779 -> 10:38620 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 18.4 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 13.6 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9952 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3701/3701 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2331179 | col_h10_r2__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3685/3685 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (439/439 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-2685046 | col_h9_r2__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (430/430 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_iq_C__t1-2048142 | dsdv_slice_iq_C__t1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_w-2152740 | hd_host_w | 6_1_fill | 8.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 8.1 | last meaningful line 0.1 h ago (198/199 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 19.3 | last meaningful line 2.0 h ago (200/209 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (3461/3461 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t3-213207 | serdes__t3 | 3_5_place_dp | 2.1 | repair_Violations best 94 last 94 rows 51 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-1596289 | serdes__t4 | 3_4_place_resized | 1.6 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (2900/2900 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 5_2_route | 19.6 | drt_violations best 83501 last 83501 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1t-735514 | eco_20261120_185639_3224747-i1t | 5_2_route | 5.3 | drt_violations best 6137 last 6137 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 3.0 | drt_violations best 48990 last 48990 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00_s2-1641925 | cbf_q00_s2 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01-1639008 | cbf_q01 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.6845 last 0.6845 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (1948/1948 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-2956 | cbn_q00 | 3_3_place_gp | 1.2 | overflow best 0.2567 last 0.2567 rows 34 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-1624147 | cbn_q00 | 3_3_place_gp | 0.7 | overflow best 0.4542 last 0.4542 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-613687 | cbn_q00 | 3_3_place_gp | 1.0 | overflow best 0.212 last 0.212 rows 35 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.5 h ago (200/220 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 4.4 | last meaningful line 2.0 h ago (199/223 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 4.4 | last meaningful line 2.0 h ago (199/223 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 6.7 | drt_violations best 66844 last 66844 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (2181/2181 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2631 last 0.2631 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-3028930 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8188 last 0.8188 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-coll_core-3054314 | coll_core | 2_1_floorplan | 0.3 | repair_Viol best 1922 last 1922 rows 1072 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-645513 | dsdv_slice_lepw_mus_LP__t2 | 3_3_place_gp | 1.0 | overflow best 0.4356 last 0.4356 rows 32 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-glue-613021 | glue | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-1636745 | gunit__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 5.1 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-3072949 | ot_s81sl_kv_leaf__t3 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (732/732 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-3048247 | ot_s81sl_leaf__t12 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4179 last 0.4179 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-622062 | ot_s81sl_leaf__t14 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3045380 | ot_s81sl_leaf__t25 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (417/417 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-1623527 | ot_s81sl_leaf__t34 | 3_3_place_gp | 0.7 | overflow best 0.2184 last 0.2184 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-1623915 | ot_s81sl_leaf__t35 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-1630365 | ot_s81sl_leaf__t4 | 3_3_place_gp | 0.7 | overflow best 0.5366 last 0.5366 rows 21 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (323/323 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t59-3020126 | ot_s81sl_leaf__t59 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (1104/1104 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-611382 | sle_ctl | 3_3_place_gp | 1.0 | overflow best 0.1716 last 0.176 rows 29 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_fe_v1__cl8210183c-4184425 | sle_fe_v1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-614524 | sle_fw_v2 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (291/291 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-615542 | sle_sc_v3 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5187/5187 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (239/239 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (4856/4856 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (4746/4746 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (5410/5410 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (5098/5098 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (5266/5266 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-2148023 | slw_hc2 | tt_setup_repair | 1.8 | repair_Viol best 236 last 236 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5619/5619 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-1463093 | slw_st_b_v1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4625/4626 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | pregrt_ff_hold | 1.6 | repair_TNS best 30800.1 last 30800.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_su_c__cl92142dac-3055801 | slw_su_c | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8983 last 0.8986 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3065938 | slw_su_l1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 5.3 | last meaningful line 0.0 h ago (699/699 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 4.5 | last meaningful line 0.8 h ago (653/653 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (358/358 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | otc-1636879-8246 | 1636879 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-3048695-18646 | 3048695 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 6.1 | drt_violations best 25 last 25 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 4.7 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_2_route | 2.4 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-fin-2879183 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01_s2-1971223 | cbf_q01_s2 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200-2363762 | cbx_q10 | 2_1_floorplan | 0.1 | repair_Viol best 847 last 847 rows 912 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2363454 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.822 last 0.822 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (10409/10409 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (283/283 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (166/166 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (166/166 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-2363517 | kv3_pv_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (844/844 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (844/844 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 3.9 | last meaningful line 0.3 h ago (15686/15686 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 3.9 | last meaningful line 0.3 h ago (15592/15592 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 3_4_place_resized | 1.6 | repair_Remaining best 220541 last 220541 rows 302 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 6.6 | last meaningful line 0.3 h ago (15730/15730 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2440/2440 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t60-1971113 | ot_s81sl_leaf__t60 | 3_3_place_gp | 0.4 | overflow best 0.5301 last 0.5368 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | pregrt_ff_hold | 1.6 | repair_Violations best 16052 last 16052 rows 82 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 6.6 | repair_TNS best 166938 last 166938 rows 79 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2231764 | sle_fw_v2 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_2_route | 7.2 | drt_violations best 10755 last 10755 rows 3 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_2_route | 7.2 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | postcts_gate_TT | 1.6 | last meaningful line 0.0 h ago (1480/1480 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-791387 | slw_stm_v1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 6.6 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026 | dsdv_bksel_c_rfda3pt | 3_3_place_gp | 0.4 | overflow best 0.2149 last 0.2149 rows 246 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026-lec | dsdv_bksel_c_rfda3pt | 3_3_place_gp | 0.3 | overflow best 0.2149 last 0.2149 rows 246 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | otc-2480894-27832 | 2480894 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | so_2338284_ff_36459 | so_2338284_ff_36459 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_2338284_tt_36459 | so_2338284_tt_36459 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (841/841 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (979/979 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (1025/1025 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (865/865 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | tt_setup_repair_grt | 5.2 | repair_Viol best 884 last 884 rows 431 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (622/622 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (771/771 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (847/847 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (816/816 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (633/633 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (829/829 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (838/838 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 5.2 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 35.2 |  | NO-DATA: no log found |  |
| epyc8 | so_190390_ff_65331 | so_190390_ff_65331 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_190390_tt_65331 | so_190390_tt_65331 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t16-grt-3343357 | ot-s81sl-leaf--t16-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbx_q10__cl89936551-1944374 | cbx_q10 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-882202 | col_h10_r0_p1__t1 | stage_odb_cap | 7.1 | last meaningful line 0.0 h ago (1210/1210 lines) | YOUNG: evidence 7.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 7.1 | last meaningful line 0.0 h ago (2285/2285 lines) | YOUNG: evidence 7.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 6.8 | drt_violations best 91026 last 91026 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 14646 last 14646 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-1663478 | col_h10_r2__t1 | generate_abstract | 6.8 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1541838 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 6.8 | repair_Viol best 1042 last 1042 rows 642 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-3235380 | dsdv_slice_kv512_C__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (300/300 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1952017 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-glue-1948074 | glue | 3_3_place_gp | 0.7 | overflow best 0.6369 last 0.6369 rows 19 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-gunit__t1-3341748 | gunit__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 3_3_place_gp | 0.7 | overflow best 0.2985 last 0.5772 rows 132 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-hd_mesh-1734167 | hd_mesh | pregrt_ff_hold | 6.8 | repair_TNS best 225508 last 225508 rows 1 | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t31-1529768 | ot_s81sl_leaf__t31 | tt_setup_repair_grt | 6.8 | repair_Viol best 1741 last 1741 rows 1081 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v2-1792546 | sle_sc_v2 | postcts_gate_TT | 6.8 | last meaningful line 0.0 h ago (1797/1797 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 4_1_cts | 0.6 | last meaningful line 0.2 h ago (4010/4010 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t6-1947287 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 0.7 | last meaningful line 0.0 h ago (217/217 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 100.4 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 5.3 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | tt_setup_repair_grt | 21.6 | repair_Violations best 717 last 717 rows 8 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 7.5 | drt_violations best 73630 last 73630 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 7.7 | last meaningful line 0.8 h ago (274/275 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 8.1 | drt_violations best 62725 last 62725 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (245/245 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (572/572 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 3_3_place_gp | 3.2 | last meaningful line 0.0 h ago (522/522 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 19.3 | drt_violations best 76548 last 76548 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 7.5 | drt_violations best 19623 last 19623 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 19.6 | drt_violations best 81847 last 81847 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 20.3 | drt_violations best 100416 last 100416 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 20.3 | drt_violations best 11535 last 11535 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 20.7 | drt_violations best 144324 last 144324 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | postcts_gate_TT | 4.4 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 1.5 | last meaningful line 0.1 h ago (415/415 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 4.8 | last meaningful line 0.2 h ago (653/653 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 2.9 | last meaningful line 0.8 h ago (498/498 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (371/371 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-cbn_q01__cld9ff4c40-2195882 | cbn_q01 | 3_3_place_gp | 1.1 | overflow best 0.556 last 0.556 rows 11 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.5 h ago (125/125 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 13.4 | repair_Violations best 6449 last 6449 rows 35 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (715/715 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5448/5448 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (179/179 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cl503337ff__padE0-2190588 | sle_ctl | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-2676376 | slice_station__t41 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | 5_3_fillcell | 19.6 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 1.1 | last meaningful line 0.0 h ago (374/374 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 2.1 | last meaningful line 0.3 h ago (459/459 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-fin-1367643 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (399/399 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_2526074_ff_33526 | so_2526074_ff_33526 | stage_odb_cap | 0.8 | last meaningful line 0.8 h ago (1253/1253 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | so_2526074_tt_33526 | so_2526074_tt_33526 | stage_odb_cap | 0.8 | last meaningful line 0.8 h ago (1253/1253 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | so_2718457_ff_3436 | so_2718457_ff_3436 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1137/1137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2718457_tt_3436 | so_2718457_tt_3436 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1137/1137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2723811_ff_99167 | so_2723811_ff_99167 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1137/1137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2723811_tt_99167 | so_2723811_tt_99167 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1137/1137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2724540_ff_10565 | so_2724540_ff_10565 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1137/1137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2724540_tt_10565 | so_2724540_tt_10565 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1137/1137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | stage_odb_cap | 6.9 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | so_1034832_ff_19480 | so_1034832_ff_19480 | stage_odb_cap | 0.0 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | so_1034832_tt_19480 | so_1034832_tt_19480 | stage_odb_cap | 0.0 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 29.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 9.3 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 9.3 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 26.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 21.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 16.4 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 9.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 63.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 39.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 40.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (564/564 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 18.4 | last meaningful line 0.0 h ago (9020/9020 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-2974046 | kv3_pv_v8 | 4_1_cts | 17.4 | last meaningful line 0.8 h ago (15607/15607 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 19.5 | last meaningful line 0.0 h ago (9557/9557 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 17.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (618/618 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (4433/4433 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 21.3 | last meaningful line 0.0 h ago (10683/10683 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 21.8 | last meaningful line 0.0 h ago (10716/10716 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 10.7 | drt_violations best 68 last 68 rows 13 | before-window best 26786, window best 68 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 13.5 | last meaningful line 0.6 h ago (1379/1379 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 10.6 | last meaningful line 0.0 h ago (5979/5979 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (6090/6090 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 4.2 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 10.6 | last meaningful line 0.0 h ago (5653/5653 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (5948/5948 lines) | PROGRESS: log still growing |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_1_grt | 0.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (3017/3017 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 25.1 | drt_violations best 10168 last 49296 rows 18 | before-window best 10756, window best 10168 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | 5_1_grt | 5.2 | repair_TNS best 0 last 0 rows 35 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 16.2 | last meaningful line 0.0 h ago (9008/9008 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv291547b4-2471228 | col_h9_r0_p2__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1205/1205 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1065/1065 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (923/923 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1143/1143 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1054/1054 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (894/894 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1059/1059 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1020/1020 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1062/1062 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1065/1065 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (848/848 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1075/1075 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 17.7 | last meaningful line 0.0 h ago (1213/1213 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1254197 | col_h10_r0_p1__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (2075/2075 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-2115455 | col_h10_r0_p1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1088/1088 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (1172/1172 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1176/1176 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (1924/1924 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (1181/1181 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 8.9 | last meaningful line 0.0 h ago (4401/4401 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (4129/4129 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (4126/4126 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 19.3 | last meaningful line 0.0 h ago (10162/10162 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 19.5 | last meaningful line 0.0 h ago (10205/10205 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (3879/3879 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (4173/4173 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (500/500 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (3779/3779 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (3946/3946 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (3734/3734 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (3818/3818 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 26.4 | last meaningful line 0.0 h ago (1576/1576 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 21.5 | last meaningful line 0.0 h ago (1297/1297 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 13.4 | repair_Violations best 3294 last 3294 rows 128 | before-window best 49389, window best 3294 | PROGRESS: repair_Violations improved 93.3 % in window |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 17.0 | last meaningful line 0.0 h ago (1349/1349 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 20.2 | last meaningful line 0.0 h ago (1277/1277 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 19.6 | last meaningful line 0.0 h ago (1165/1165 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 19.6 | last meaningful line 0.0 h ago (1165/1165 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 19.8 | last meaningful line 0.0 h ago (1179/1179 lines) | PROGRESS: log still growing |  |
