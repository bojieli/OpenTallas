# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 14:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 1, 'GRT-LABEL': 34, 'YOUNG': 206, 'NO-DATA': 12, 'KEEP': 10, 'EXCLUDED': 4, 'PROGRESS': 49}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 27.3 | drt_violations best 20 last 20 rows 53 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 27.3 | drt_violations best 20 last 20 rows 53 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 27.3 | drt_violations best 20 last 20 rows 53 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | tt_setup_repair | 3.7 | repair_Viol best 110 last 110 rows 183 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -363.94 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| epyc9 | otc-478595-4315 | 478595 | signoff_meas_072023 | 64.3 | last meaningful line 21.2 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 21.2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 21.4 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:11004 -> 10:7238 -> 15:3184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 6.6 | grt rounds 3 overflow 5:46800 -> 10:46349 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 16.5 | grt rounds 3 overflow 5:24414 -> 10:16733 -> 15:13155 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 16.9 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:44251 -> 10:47629 -> 15:39542 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t30-921459 | ot_s81sl_leaf__t30 | 5_1_grt | 17.3 | grt rounds 5 overflow 5:32680 -> 10:26052 -> 15:21293 -> 20:20131 -> 25:28075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 15.1 | grt rounds 3 overflow 5:26008 -> 10:17213 -> 15:16053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 17.1 | grt rounds 3 overflow 5:57640 -> 10:67281 -> 15:54951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 17.1 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40887 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 25.7 | grt rounds 3 overflow 5:46983 -> 10:40250 -> 15:36858 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_serdes-379194 | hd_serdes | 5_1_grt | 3.2 | grt rounds 3 overflow 5:11153 -> 10:9375 -> 15:5708 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 27.5 | grt rounds 4 overflow 5:19451 -> 10:7268 -> 15:6284 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 15.0 | grt rounds 3 overflow 5:29640 -> 10:6673 -> 15:6119 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 15.0 | grt rounds 3 overflow 5:59583 -> 10:59317 -> 15:49973 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 8.0 | grt rounds 3 overflow 5:41193 -> 10:41297 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 16.3 | grt rounds 3 overflow 5:32994 -> 10:26094 -> 15:20564 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 15.0 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 27.5 | grt rounds 4 overflow 5:78865 -> 10:60387 -> 15:48404 -> 20:50724 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 21.3 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 22.4 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 55.6 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42367 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 23.7 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44275 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 23.7 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 19.8 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 5.8 | grt rounds 3 overflow 5:48999 -> 10:45315 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 5.8 | grt rounds 3 overflow 5:24525 -> 10:19532 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 16.3 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6221 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 5.8 | grt rounds 3 overflow 5:46348 -> 10:51002 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 25.4 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 17.3 | grt rounds 3 overflow 5:43280 -> 10:41355 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 17.3 | grt rounds 3 overflow 5:43779 -> 10:41949 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 16.6 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 12.1 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2811/2811 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2331179 | col_h10_r2__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2785/2785 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (349/349 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-2186872 | col_h9_r0_p3__t1 | tt_setup_repair_grt | 6.7 | repair_Viol best 905 last 905 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-817269 | col_h9_r0_p6__t1 | 3_4_place_resized | 0.4 | repair_Remaining best 52115 last 52115 rows 25 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (474/474 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-2691830 | col_h9_r2__t1 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (422/422 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-2685046 | col_h9_r2__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (341/341 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-730381 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-eng__t1-602379 | eng__t1 | 3_3_place_gp | 0.5 | overflow best 0.2526 last 0.2526 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_host_w-2152740 | hd_host_w | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (3523/3523 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | pregrt_ff_hold | 6.6 | repair_TNS best 680111 last 680111 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 17.8 | last meaningful line 0.5 h ago (200/205 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-3470062 | kv3_hub_Eo | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (444/444 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1n-2435290 | kv3_pv_v1n | 4_1_cts | 5.3 | last meaningful line 0.3 h ago (8189/8189 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2561/2561 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (528/528 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3533/3533 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t3-213207 | serdes__t3 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-1596289 | serdes__t4 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2020/2020 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-2673781 | sle_stm_v1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3201/3201 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t27-424919 | slice_station__t27 | 3_3_place_gp | 0.5 | overflow best 0.2951 last 0.2951 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slice_station__t43-473369 | slice_station__t43 | 3_3_place_gp | 0.5 | overflow best 0.2622 last 0.2622 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 5_2_route | 18.1 | drt_violations best 83501 last 83501 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | eco-abs-1527505 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (628/628 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1046587-15419 | 1046587 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-4170529-10555 | 4170529 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-79236-20479 | 79236 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1t-735514 | eco_20261120_185639_3224747-i1t | 5_2_route | 3.8 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (249/250 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-slw-fe-v1--cl95cd1d0c-grt-2183057 | slw-fe-v1--cl95cd1d0c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (910/910 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-924790 | cbn_q01 | 3_3_place_gp | 1.2 | overflow best 0.663 last 0.663 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-861738 | cbn_q11 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (168/168 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3259666 | cbn_q11 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1359563 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2708 last 0.2708 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 5.0 | last meaningful line 2.8 h ago (199/228 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (199/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (199/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | 5_2_route | 8.8 | drt_violations best 9518 last 9518 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | 6_report | 9.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.5 h ago (259/260 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | 5_1_grt | 8.8 | last meaningful line 0.8 h ago (207/235 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (1141/1141 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 2.5 | repair_Viol best 282 last 282 rows 83 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (576/576 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 3.3 | last meaningful line 0.5 h ago (336/336 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | pregrt_ff_hold | 2.4 | repair_Violations best 28136 last 28136 rows 81 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-725289 | ot_s81sl_leaf__t44 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-861295 | ot_s81sl_leaf__t46 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (219/219 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-722706 | ot_s81sl_leaf__t65 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla2127225-2739353 | serdes__t15 | 2_4_floorplan_pdn | 0.8 | last meaningful line 0.1 h ago (94/94 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-4038564 | sle_st_b_v1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__clfde1249e-2763157 | sle_st_b_v2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (4207/4207 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-3671630 | slw_fw_v2 | 3_3_place_gp | 0.7 | overflow best 0.3307 last 0.3307 rows 24 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-2148023 | slw_hc2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-1463093 | slw_st_b_v1 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (4907/4907 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 3.6 | last meaningful line 0.0 h ago (642/642 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 2.8 | last meaningful line 0.0 h ago (506/506 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | otc-3418299-1777 | 3418299 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-3434320-23245 | 3434320 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 4.4 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 4.0 | drt_violations best 49 last 49 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 3.0 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (232/410 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbx-q10--cl94a12200-grt-561897 | cbx-q10--cl94a12200-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-pv-v2-grt-722396 | kv3-pv-v2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-pv-v2n-dump-764114 | kv3-pv-v2n-dump | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (656/656 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-pv-v2n-grt-764114 | kv3-pv-v2n-grt | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (656/656 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-4106372 | bk_sel__t2 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01_s2-3869485 | cbf_q01_s2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | tt_setup_repair | 2.7 | repair_Violations best 90 last 111 rows 18 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (2776/2776 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2881/2881 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | tt_setup_repair | 2.8 | repair_Remaining best 17771 last 17771 rows 353 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (656/656 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (516/516 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (556/556 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (496/496 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (484/484 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 3_5_place_dp | 2.4 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 3_5_place_dp | 2.4 | last meaningful line 0.1 h ago (95/95 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 2_1_floorplan | 0.1 | repair_Viol best 258 last 258 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 5.1 | last meaningful line 0.2 h ago (15697/15698 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 0.9 | last meaningful line 0.1 h ago (202/209 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1540/1540 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (199/202 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 5.1 | repair_TNS best 187647 last 187647 rows 54 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-37263 | sle_fe_v1 | 3_3_place_gp | 0.6 | overflow best 0.5229 last 0.5229 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | 5_2_route | 5.7 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_2_route | 5.7 | drt_violations best 16543 last 16543 rows 2 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2117/2117 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | postcts_gate_FF | 5.7 | last meaningful line 0.3 h ago (17/17 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (4234/4234 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-648681 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4737/4737 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (4027/4027 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 5.1 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | generate_abstract | 4.3 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-fin-3989767 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (1070/1070 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | repair_Remaining best 32039 last 32039 rows 158 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (766/766 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (904/904 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (950/950 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (790/790 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (839/839 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | tt_setup_repair_grt | 3.9 | repair_Viol best 759 last 759 rows 299 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | tt_setup_repair_grt | 3.9 | repair_Viol best 759 last 759 rows 254 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (773/773 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (742/742 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | tt_setup_repair_grt | 3.9 | repair_Viol best 759 last 759 rows 207 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | tt_setup_repair_grt | 3.9 | repair_Viol best 759 last 759 rows 120 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (764/764 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 3.9 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 33.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261120_080032_3761085-i1-1022173 | eco_20261120_080032_3761085-i1 | 5_2_route | 5.2 | drt_violations best 3666 last 3666 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | prd-fin-3048356 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-882202 | col_h10_r0_p1__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (1105/1105 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1254197 | col_h10_r0_p1__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (1970/1970 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2180/2180 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-3742048 | col_h10_r0_p1__t1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (1971/1971 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-2115455 | col_h10_r0_p1__t1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (984/984 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 5.1 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-1661189 | col_h10_r1__t1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (2618/2618 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-1597344 | col_h10_r1__t1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (2649/2649 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-1663478 | col_h10_r2__t1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (2708/2708 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-1643657 | col_h10_r2__t1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (2707/2707 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | 5_2_route | 7.3 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (1071/1071 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 6.8 | repair_Viol best 1048 last 1048 rows 403 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 6.8 | repair_Viol best 1048 last 1048 rows 198 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1541838 | col_h9_r0_p1__t1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (1749/1749 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-3235380 | dsdv_slice_kv512_C__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_LP__t2-2710828 | dsdv_slice_lepw_mu_LP__t2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7003 last 0.8221 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-gunit__t1-3341748 | gunit__t1 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-1734167 | hd_mesh | pregrt_ff_hold | 5.0 | repair_TNS best 225508 last 225508 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2768122 | ot_s81sl_kv_leaf__t5 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (732/732 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 6.8 | last meaningful line 0.3 h ago (208/213 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t31-1529768 | ot_s81sl_leaf__t31 | 5_1_grt | 5.1 | repair_TNS best 3453.04 last 3453.04 rows 8 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-seqhost__t1-2837346 | seqhost__t1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (471/471 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 7.2 | last meaningful line 0.0 h ago (3351/3351 lines) | YOUNG: evidence 7.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (3079/3079 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | 5_1_grt | 6.5 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v2-1792546 | sle_sc_v2 | 5_1_grt | 5.0 | last meaningful line 0.2 h ago (226/285 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t36-2129362 | slice_station__t36 | 3_3_place_gp | 0.4 | overflow best 0.4501 last 0.4501 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2361144 | slice_station__t6 | 3_3_place_gp | 0.4 | overflow best 0.3063 last 0.3063 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-2389841 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 3.7 | last meaningful line 0.1 h ago (763/763 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t3-2814940 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 3.5 | last meaningful line 0.0 h ago (636/636 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t4-2265883 | svc_hi_dsdv_svc_rs__t4 | reg_fanout | 3.7 |  | NO-DATA: empty log |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 98.7 |  | NO-DATA: empty log |  |
| epyc9 | otc-1540477-32324 | 1540477 | - | 5.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1598589-12 | 1598589 | - | 5.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1599853-12191 | 1599853 | - | 5.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2411353-23881 | 2411353 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-2491977-4017 | 2491977 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-2969764-31157 | 2969764 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 3.5 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | ap-ageom-kw-dsdv-slice-c1x-C--t5-dump-667606 | dsdv-slice-c1x-C--t5-dump | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-dsdv-slice-c1x-C--t5-grt-667606 | dsdv-slice-c1x-C--t5-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-3533052 | cbf_q00 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (332/332 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | 3_4_place_resized | 2.7 | repair_Remaining best 162278 last 162278 rows 56 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (2839/2839 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 5.8 | drt_violations best 73630 last 73630 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (408/408 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 5.9 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (3133/3133 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 6.4 | drt_violations best 62725 last 62725 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-iqf__t1-4060768 | iqf__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9972 last 0.9972 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2464/2464 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (2739/2739 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 2_1_floorplan | 1.5 | last meaningful line 1.2 h ago (144/144 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (616/616 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (2906/2906 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (2694/2694 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (2768/2768 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 17.5 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t37-3308231 | slice_station__t37 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5018 last 0.5018 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 5.8 | drt_violations best 19623 last 19623 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t41-3247802 | slice_station__t41 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3566 last 0.3566 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slice_station__t49-3261186 | slice_station__t49 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.2355 last 0.2355 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slice_station__t52-4120788 | slice_station__t52 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9988 last 0.9988 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 17.8 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 18.5 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 18.5 | drt_violations best 89452 last 89452 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 18.9 | last meaningful line 0.7 h ago (280/281 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 2.6 | last meaningful line 1.5 h ago (217/790 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 3.1 | last meaningful line 1.0 h ago (463/463 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 1.1 | last meaningful line 0.0 h ago (287/287 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-2876778 | tt_ctlm | 3_3_place_gp | 0.6 | overflow best 0.3512 last 0.3512 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-cbf_q01-749277 | cbf_q01 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.8771 last 0.8795 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-cbx_q10__cl94a12200_h-868687 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.3429 last 0.3461 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-944745 | dsdv_slice_lepe_nh_mus_LP__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-916896 | eng__t1 | 3_3_place_gp | 0.6 | overflow best 0.2508 last 0.254 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t24__cl81374cd8-914297 | ot_s81sl_leaf__t24 | 3_3_place_gp | 0.6 | overflow best 0.4435 last 0.4435 rows 34 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t42-751333 | ot_s81sl_leaf__t42 | 3_5_place_dp | 0.7 | repair_Violations best 2365 last 2365 rows 49 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t51-867407 | ot_s81sl_leaf__t51 | 3_3_place_gp | 0.6 | overflow best 0.5726 last 0.5726 rows 19 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | 3_3_place_gp | 0.6 | overflow best 0.6011 last 0.6011 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-872108 | ot_s81sl_leaf__t67 | 3_3_place_gp | 0.6 | overflow best 0.6204 last 0.6204 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-760479 | slice_station__t51 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-944789 | slw_fw_v3 | 3_3_place_gp | 0.6 | overflow best 0.3655 last 0.3655 rows 15 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | 6_report | 19.1 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 0.6 | last meaningful line 0.0 h ago (205/205 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 4.1 | drt_violations best 357 last 357 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-2648902 | col_h10_r2__t1 | 5_2_route | 6.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | stage_odb_cap | 5.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 27.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 8.1 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 8.1 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-1657776 | col_h10_r1__t1 | stage_odb_cap | 5.1 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 24.7 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 19.8 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 14.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 7.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 61.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | otc-3484103-7192 | 3484103 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 37.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 38.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 16.9 | last meaningful line 0.0 h ago (8120/8120 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-2974046 | kv3_pv_v8 | 4_1_cts | 15.9 | last meaningful line 0.5 h ago (15603/15603 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 18.0 | last meaningful line 0.0 h ago (8657/8657 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 15.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 19.8 | last meaningful line 0.0 h ago (9783/9783 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 20.3 | last meaningful line 0.0 h ago (9816/9816 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 9.2 | drt_violations best 77 last 77 rows 11 | before-window best 26786, window best 77 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 11.7 | last meaningful line 0.6 h ago (1377/1377 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (4872/4872 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (4939/4939 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (5050/5050 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (4613/4613 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (4908/4908 lines) | PROGRESS: log still growing |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 11.0 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 14.6 | drt_violations best 13 last 13 rows 59 | before-window best 150968, window best 13 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 23.6 | drt_violations best 10168 last 49296 rows 18 | before-window best 11104, window best 10168 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 23.3 | drt_violations best 7619 last 17503 rows 19 | before-window best 8002, window best 7619 | PROGRESS: drt_violations improved 4.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 15.0 | last meaningful line 0.0 h ago (8258/8258 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv291547b4-2471228 | col_h9_r0_p2__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (1130/1130 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (990/990 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (848/848 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (1068/1068 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (980/980 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (819/819 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (984/984 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (945/945 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (988/988 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (991/991 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (773/773 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (1000/1000 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 15.9 | last meaningful line 0.0 h ago (1108/1108 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 17.5 | last meaningful line 0.0 h ago (9112/9112 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 17.8 | last meaningful line 0.0 h ago (9155/9155 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-777724 | col_h10_r1__t1 | 3_5_place_dp | 0.6 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 24.9 | last meaningful line 0.0 h ago (1486/1486 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 20.0 | last meaningful line 0.0 h ago (1208/1208 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 11.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 11.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 15.5 | last meaningful line 0.0 h ago (1260/1260 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 18.1 | last meaningful line 0.0 h ago (1076/1076 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | 5_2_route | 18.7 | drt_violations best 12337 last 12337 rows 3 | before-window best 97324, window best 12337 | PROGRESS: drt_violations improved 87.3 % in window |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 18.1 | last meaningful line 0.0 h ago (1075/1075 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 18.1 | last meaningful line 0.0 h ago (1076/1076 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 18.1 | last meaningful line 0.0 h ago (1076/1076 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (1090/1090 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 18.1 | last meaningful line 0.0 h ago (1075/1075 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 18.1 | last meaningful line 0.0 h ago (1075/1075 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 18.0 | last meaningful line 0.0 h ago (1075/1075 lines) | PROGRESS: log still growing |  |
