# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 16:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 4, 'NO-PROGRESS': 1, 'GRT-LABEL': 40, 'YOUNG': 220, 'NO-DATA': 8, 'KEEP': 9, 'EXCLUDED': 3, 'PROGRESS': 55}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | tt_setup_repair_grt | 4.7 | repair_Viol best 3409 last 3409 rows 29 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -486.28 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2603/2603 lines) | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -446.29 ps (< -300, gate TT >= -42); job age 4. | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (2935/2935 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -687.56 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2504/2504 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -1491.99 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 20.9 | drt_violations best 144324 last 144324 rows 1 | before-window best 144324, window best 144324 | NO-PROGRESS: drt_violations best 144324 vs 144324 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 23.4 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 19.8 | grt rounds 2 overflow 5:87024 -> 10:50446 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 8.9 | grt rounds 5 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:46508 -> 10:46073 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 18.5 | grt rounds 4 overflow 5:24414 -> 10:16733 -> 15:13155 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 18.9 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:43983 -> 10:46937 -> 15:39542 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t30-921459 | ot_s81sl_leaf__t30 | 5_1_grt | 19.3 | grt rounds 5 overflow 5:32680 -> 10:26052 -> 15:21293 -> 20:20131 -> 25:28075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 17.1 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:16053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 19.1 | grt rounds 3 overflow 5:57640 -> 10:67281 -> 15:55315 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 19.1 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40887 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 27.7 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:36858 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:23778 -> 10:15447 | GRT-LABEL: DESIGN-FAIL: overflow 15447 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_1_grt | 3.4 | grt rounds 6 overflow 5:1144 -> 10:980 -> 15:961 -> 20:863 -> 25:428 -> 30:141 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 2.9 | grt rounds 3 overflow 5:30377 -> 10:16662 -> 15:14043 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 2.7 | grt rounds 3 overflow 5:41957 -> 10:39840 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: overflow 39840 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:597 -> 10:874 -> 15:319 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 29.3 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6284 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 16.7 | grt rounds 3 overflow 5:29640 -> 10:6637 -> 15:5987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 16.7 | grt rounds 3 overflow 5:59583 -> 10:59412 -> 15:50422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:41295 -> 10:41297 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 18.1 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20564 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 16.7 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 29.3 | grt rounds 4 overflow 5:78865 -> 10:60387 -> 15:48404 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_1_grt | 7.6 | grt rounds 3 overflow 5:45755 -> 10:1 -> 15:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 23.6 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 24.7 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 57.9 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 25.9 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:31334 -> 10:16178 | GRT-LABEL: DESIGN-FAIL: overflow 16178 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 25.9 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 7.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 7.8 | grt rounds 3 overflow 5:24921 -> 10:17867 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 18.3 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6221 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 7.8 | grt rounds 3 overflow 5:48001 -> 10:50564 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 27.4 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 19.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 19.3 | grt rounds 3 overflow 5:43779 -> 10:38620 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 18.6 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 14.1 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pv5b623e07-1880851 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.0 | repair_Viol best 5514 last 5514 rows 229 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (4001/4001 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2331179 | col_h10_r2__t1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (3985/3985 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 7.4 | last meaningful line 0.0 h ago (469/469 lines) | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-2685046 | col_h9_r2__t1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (460/460 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_iq_C__t1-2048142 | dsdv_slice_iq_C__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 8.6 | last meaningful line 0.5 h ago (198/200 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 7.4 | last meaningful line 0.0 h ago (3761/3761 lines) | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 7.4 | last meaningful line 0.0 h ago (3200/3200 lines) | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 5_2_route | 20.1 | drt_violations best 12534 last 12534 rows 2 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1t-735514 | eco_20261120_185639_3224747-i1t | 5_2_route | 5.8 | drt_violations best 6137 last 6137 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 3.5 | drt_violations best 48990 last 48990 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1t-1628432 | eco_20261121_003008_2139459-i1t | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (226/1330 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv06a1adf6-grt-1372242 | col-h9-r2--t1--clce45cab5--pv06a1adf6-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q00_s2-1641925 | cbf_q00_s2 | 3_3_place_gp | 1.2 | overflow best 0.1651 last 0.1651 rows 37 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-cbf_q01-1639008 | cbf_q01 | 3_3_place_gp | 1.2 | overflow best 0.4266 last 0.4266 rows 23 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2238/2238 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-1624147 | cbn_q00 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 5_1_grt | 4.6 | last meaningful line 2.0 h ago (200/224 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 4.9 | last meaningful line 2.5 h ago (199/226 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 4.9 | last meaningful line 2.5 h ago (199/226 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 7.2 | drt_violations best 66844 last 66844 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2471/2471 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-3028930 | col_h9_r0_p5__t1 | 3_4_place_resized | 0.8 | repair_Remaining best 93048 last 93048 rows 22 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | 6_report | 11.1 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-coll_core-3054314 | coll_core | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (127/127 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-1636745 | gunit__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 5.6 | last meaningful line 0.0 h ago (464/464 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-3072949 | ot_s81sl_kv_leaf__t3 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.997 last 0.997 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-3048247 | ot_s81sl_leaf__t12 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (206/206 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-622062 | ot_s81sl_leaf__t14 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (324/324 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3045380 | ot_s81sl_leaf__t25 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (447/447 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-1630365 | ot_s81sl_leaf__t4 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t59-3020126 | ot_s81sl_leaf__t59 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1404/1404 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-611382 | sle_ctl | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (321/321 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (269/269 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (283/283 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (5216/5216 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (4956/4956 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (370/370 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4159/4159 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | tt_setup_measure | 2.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5272/5272 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-2148023 | slw_hc2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (223/223 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (290/290 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4841/4841 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (302/302 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (5641/5641 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 2.0 | last meaningful line 0.0 h ago (587/587 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 5.8 | last meaningful line 0.3 h ago (879/879 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 5.0 | last meaningful line 0.1 h ago (656/656 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.1 | last meaningful line 0.2 h ago (435/435 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (362/362 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | eco-abs-1101019 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (388/388 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-3048695-18646 | 3048695 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 6.6 | drt_violations best 25 last 25 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 5.2 | drt_violations best 34 last 34 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_2_route | 2.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (236/1362 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-pv-v4-grt-3094167 | kv3-pv-v4-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-pv-v7-grt-3020048 | kv3-pv-v7-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-2611825 | bk_sel__t2 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (117/117 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01_s2-1971223 | cbf_q01_s2 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200-2363762 | cbx_q10 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 4_1_cts | 0.7 | last meaningful line 0.2 h ago (10748/10748 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (426/426 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 3_1_place_gp_skip_io | 0.7 | overflow best 0.1806 last 0.1806 rows 47 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-2363517 | kv3_pv_v2 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (89/89 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 4.4 | last meaningful line 0.7 h ago (15687/15687 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 4.4 | last meaningful line 0.7 h ago (15592/15592 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 3_5_place_dp | 2.1 | last meaningful line 0.3 h ago (45/45 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 7.1 | last meaningful line 0.4 h ago (15759/15759 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-native59-2890501 | native59 | 2_1_floorplan | 0.2 | repair_Viol best 18803 last 18803 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2740/2740 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 3_5_place_dp | 0.8 | last meaningful line 0.1 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t60-1971113 | ot_s81sl_leaf__t60 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (369/369 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 7.1 | repair_TNS best 161252 last 161252 rows 7 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 6_report | 7.7 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_2_route | 7.7 | drt_violations best 84515 last 84515 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_2_route | 2.1 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-791387 | slw_stm_v1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (305/305 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 7.1 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026 | dsdv_bksel_c_rfda3pt | 5_1_grt | 0.9 | repair_TNS best 195.66 last 195.66 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026-lec | dsdv_bksel_c_rfda3pt | 5_1_grt | 0.8 | repair_TNS best 195.66 last 195.66 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | opus-r3-tkr-mut-2665531 | opus-r3-tkr-mut | p_mut | 0.4 | last meaningful line 0.1 h ago (9247/9247 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_2338284_ff_36459 | so_2338284_ff_36459 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc7 | so_2338284_tt_36459 | so_2338284_tt_36459 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 5.7 | repair_Remaining best 264127 last 264127 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (1009/1009 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (1055/1055 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (894/894 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | 5_2_route | 5.7 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (652/652 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (801/801 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (877/877 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (846/846 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (662/662 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (858/858 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (868/868 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 5.7 | last meaningful line 0.5 h ago (267/268 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 35.7 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbx_q10__cl94a12200-20237 | cbx_q10 | 2_2_floorplan_macro | 0.2 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 7.3 | drt_violations best 91026 last 91026 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 11 last 27 rows 5 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 14646 last 14646 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-20704 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4134 last 0.4134 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1541838 | col_h9_r0_p1__t1 | postcts_gate_FF | 7.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-34019 | col_h9_r0_p3__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line -0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | sdc_lint | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-3235380 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 2.3 | last meaningful line 0.0 h ago (407/407 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-glue-1948074 | glue | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-gunit__t1-3341748 | gunit__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (516/516 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 3_3_place_gp | 1.2 | overflow best 0.2985 last 0.4558 rows 277 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-hd_host_e-18162 | hd_host_e | pregrt_ff_hold | 0.2 | repair_TNS best 13741 last 13741 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-hd_host_n-4082127 | hd_host_n | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-1734167 | hd_mesh | 5_1_grt | 7.3 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 3_2_place_iop | 0.3 | last meaningful line -0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t70-23212 | ot_s81sl_leaf__t70 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8646 last 0.8889 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-3958052 | serdes__t15 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (326/326 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v2-1792546 | sle_sc_v2 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (3606/3606 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9984 last 0.9984 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-4078399 | slice_station__t6 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8724 last 0.8724 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 1.1 | repair_Remaining best 305616 last 305616 rows 29 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (4064/4064 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t6-1947287 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 1.2 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 2.0 | last meaningful line 0.3 h ago (456/456 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 100.9 |  | NO-DATA: empty log |  |
| epyc9 | otc-4021631-12869 | 4021631 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 5.8 | drt_violations best 72611 last 72611 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | postcts_gate_TT | 21.8 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 7.8 | drt_violations best 73630 last 73630 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 7.9 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 8.4 | drt_violations best 62725 last 62725 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-1492344 | coll_ftc | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (632/632 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 3_3_place_gp | 3.5 | overflow best 0.658 last 0.658 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 1.8 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 19.5 | drt_violations best 76548 last 76548 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 7.8 | drt_violations best 19623 last 19623 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 19.8 | drt_violations best 81847 last 81847 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 20.5 | drt_violations best 100416 last 100416 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 20.5 | drt_violations best 11535 last 11535 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | postcts_gate_TT | 4.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 1.8 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 5.1 | last meaningful line 0.3 h ago (653/653 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 3.1 | last meaningful line 0.1 h ago (501/501 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 1.7 | last meaningful line 0.1 h ago (414/414 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-cbn_q01__cld9ff4c40-2195882 | cbn_q01 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7099 last 0.7834 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-361000 | col_h9_r0_p1__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-168013 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7495 last 0.7495 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-359064 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9657 last 0.9657 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-286613 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8998 last 0.9076 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-291993 | col_h9_r0_p3__t1 | 2_3_floorplan_tapcell | 0.3 | last meaningful line -0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-232337 | col_h9_r0_p5__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-182001 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.4 | overflow best 0.3162 last 0.3415 rows 4 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 2.6 | last meaningful line 1.0 h ago (125/125 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 13.9 | last meaningful line 0.1 h ago (167/167 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-186299 | ot_s81sl_leaf__t24 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t30-232707 | ot_s81sl_leaf__t30 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | tt_setup_repair | 2.6 | repair_Violations best 169 last 282 rows 62 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | tt_setup_repair | 1.6 | last meaningful line 0.0 h ago (391/391 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (468/468 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-serdes__t12-408235 | serdes__t12 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (279/279 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-162109 | serdes__t1 | 1_2_yosys | 0.4 | last meaningful line 0.3 h ago (322/322 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5544/5545 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5385/5386 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4854/4854 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | 3_2_place_iop | 0.4 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t18-351808 | slice_station__t18 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9893 last 0.9893 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t25-270940 | slice_station__t25 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.5962 last 0.5962 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-slice_station__t29__clc7772371-261662 | slice_station__t29 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3778/3778 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3756/3756 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 4_1_cts | 0.4 | last meaningful line 0.2 h ago (4642/4642 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5452/5453 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4062/4063 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (5086/5086 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | generate_abstract | 20.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (93/93 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (452/452 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 2.6 | last meaningful line 0.1 h ago (612/612 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (232/344 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_23570_ff_47706 | so_23570_ff_47706 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1196/1196 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_23570_tt_47706 | so_23570_tt_47706 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1196/1196 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_542676_ff_7656 | so_542676_ff_7656 | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (1309/1309 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_542676_tt_7656 | so_542676_tt_7656 | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (1309/1309 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_617331_ff_41679 | so_617331_ff_41679 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (357/357 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_617331_tt_41679 | so_617331_tt_41679 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (357/357 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | stage_odb_cap | 7.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 29.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 9.8 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 9.8 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 4_1_cts | 0.2 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 26.9 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 22.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 16.9 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 9.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 63.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 39.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 40.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (594/594 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 18.9 | last meaningful line 0.0 h ago (9310/9310 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-2974046 | kv3_pv_v8 | 4_1_cts | 17.9 | last meaningful line 1.3 h ago (15607/15607 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 20.0 | last meaningful line 0.0 h ago (9857/9857 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 17.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 8.6 | last meaningful line 0.0 h ago (648/648 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 8.6 | last meaningful line 0.0 h ago (4733/4733 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 21.8 | last meaningful line 0.0 h ago (10973/10973 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 22.3 | last meaningful line 0.0 h ago (11016/11016 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 11.2 | drt_violations best 68 last 68 rows 13 | before-window best 26786, window best 68 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 14.0 | last meaningful line 1.1 h ago (1379/1379 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 11.3 | last meaningful line 0.0 h ago (6390/6390 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 11.1 | last meaningful line 0.0 h ago (5953/5953 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 11.3 | last meaningful line 0.0 h ago (6248/6248 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3317/3317 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 25.6 | drt_violations best 10168 last 49296 rows 18 | before-window best 10389, window best 10168 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 16.7 | last meaningful line 0.0 h ago (9308/9308 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1095/1095 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (953/953 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1172/1172 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1084/1084 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (924/924 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1089/1089 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1050/1050 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1092/1092 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1095/1095 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (878/878 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1105/1105 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 18.2 | last meaningful line 0.0 h ago (1243/1243 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-882202 | col_h10_r0_p1__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (1240/1240 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-2115455 | col_h10_r0_p1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1118/1118 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 9.5 | last meaningful line 0.0 h ago (1202/1202 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (1206/1206 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (1954/1954 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (1211/1211 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 9.4 | last meaningful line 0.0 h ago (4691/4691 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (4429/4429 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (4426/4426 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 19.8 | last meaningful line 0.0 h ago (10462/10462 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 20.0 | last meaningful line 0.0 h ago (10505/10505 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | pregrt_ff_hold | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4029/4029 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (4323/4323 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (515/515 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (3929/3929 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4096/4096 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (3884/3884 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (3968/3968 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 26.9 | last meaningful line 0.0 h ago (1605/1605 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 22.0 | last meaningful line 0.0 h ago (1327/1327 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 13.9 | repair_Violations best 3381 last 3381 rows 109 | before-window best 54561, window best 3381 | PROGRESS: repair_Violations improved 93.8 % in window |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 17.5 | last meaningful line 0.0 h ago (1379/1379 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 20.1 | last meaningful line 0.0 h ago (1195/1195 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 20.1 | last meaningful line 0.0 h ago (1195/1195 lines) | PROGRESS: log still growing |  |
