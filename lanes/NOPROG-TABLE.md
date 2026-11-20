# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 15:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 33, 'YOUNG': 170, 'NO-DATA': 5, 'KEEP': 10, 'EXCLUDED': 3, 'PROGRESS': 48}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 27.6 | drt_violations best 20 last 20 rows 53 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 27.6 | drt_violations best 20 last 20 rows 53 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 27.6 | drt_violations best 20 last 20 rows 53 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | CANCELLED |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 21.7 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 7.1 | grt rounds 4 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:46800 -> 10:46349 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 16.8 | grt rounds 3 overflow 5:24414 -> 10:16733 -> 15:13155 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 17.1 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 7.1 | grt rounds 3 overflow 5:44251 -> 10:47629 -> 15:39542 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t30-921459 | ot_s81sl_leaf__t30 | 5_1_grt | 17.6 | grt rounds 5 overflow 5:32680 -> 10:26052 -> 15:21293 -> 20:20131 -> 25:28075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 15.4 | grt rounds 3 overflow 5:26008 -> 10:17213 -> 15:16053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 17.4 | grt rounds 3 overflow 5:57640 -> 10:67281 -> 15:54951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 17.4 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40887 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 25.9 | grt rounds 3 overflow 5:46983 -> 10:40250 -> 15:36858 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 27.8 | grt rounds 4 overflow 5:19451 -> 10:7268 -> 15:6284 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 15.2 | grt rounds 3 overflow 5:29640 -> 10:6673 -> 15:6119 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 15.2 | grt rounds 3 overflow 5:59583 -> 10:59412 -> 15:49973 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:41193 -> 10:41297 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 16.6 | grt rounds 4 overflow 5:32994 -> 10:26094 -> 15:20564 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 15.2 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 27.8 | grt rounds 4 overflow 5:78865 -> 10:60387 -> 15:48404 -> 20:50724 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 21.8 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 22.9 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 56.1 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42367 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 24.2 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 24.2 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 20.1 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 6.0 | grt rounds 3 overflow 5:37849 -> 10:45315 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 6.0 | grt rounds 3 overflow 5:24525 -> 10:19532 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 16.5 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6221 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 6.0 | grt rounds 3 overflow 5:46348 -> 10:51002 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 25.7 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 17.5 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 17.5 | grt rounds 3 overflow 5:43779 -> 10:41949 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 16.9 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 12.3 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-eng--t1-grt-2370913 | eng--t1-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-slice-station--t27-grt-2397118 | slice-station--t27-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2961/2961 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2331179 | col_h10_r2__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2935/2935 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (364/364 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-2186872 | col_h9_r0_p3__t1 | postcts_gate_FF | 6.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (489/489 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-2691830 | col_h9_r2__t1 | 5_2_route | 6.8 | drt_violations best 7567 last 7567 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-2685046 | col_h9_r2__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_iq_C__t1-2048142 | dsdv_slice_iq_C__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (402/402 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-730381 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_w-2152740 | hd_host_w | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (3673/3673 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | pregrt_ff_hold | 6.9 | repair_TNS best 680111 last 680111 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 18.0 | last meaningful line 0.8 h ago (200/206 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-3470062 | kv3_hub_Eo | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (504/504 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1n-2435290 | kv3_pv_v1n | 4_1_cts | 5.6 | last meaningful line 0.5 h ago (8189/8189 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (2711/2711 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (543/543 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3683/3683 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t3-213207 | serdes__t3 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.9015 last 0.9048 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-1596289 | serdes__t4 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 4_1_cts | 5.6 | last meaningful line 0.0 h ago (8017/8017 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-2673781 | sle_stm_v1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3351/3351 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t43-473369 | slice_station__t43 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 5_2_route | 18.3 | drt_violations best 83501 last 83501 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | eco-abs-1527505 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (628/628 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-1046587-15419 | 1046587 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-4170529-10555 | 4170529 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-79236-20479 | 79236 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1t-735514 | eco_20261120_185639_3224747-i1t | 5_2_route | 4.0 | drt_violations best 6137 last 6137 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (251/252 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-cbx-q10--cl89936551-grt-2986695 | cbx-q10--cl89936551-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-sle-sc-v1--cl7479a5ec-grt-2988281 | sle-sc-v1--cl7479a5ec-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-slw-fe-v1--clfe325744--cl08d14f0d-grt-3043326 | slw-fe-v1--clfe325744--cl08d14f0d-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1060/1060 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-924790 | cbn_q01 | 3_3_place_gp | 1.4 | overflow best 0.433 last 0.4374 rows 22 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-861738 | cbn_q11 | 3_4_place_resized | 1.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3259666 | cbn_q11 | 3_4_place_resized | 1.0 | repair_Remaining best 135021 last 135021 rows 44 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1359563 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.5 | overflow best 0.2785 last 0.2871 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 5_1_grt | 2.6 | last meaningful line 0.1 h ago (200/201 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 5.2 | last meaningful line 3.0 h ago (199/229 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (199/210 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (199/210 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (1291/1291 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 2.7 | repair_Viol best 282 last 282 rows 104 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (636/636 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 3.6 | last meaningful line 0.8 h ago (336/336 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | pregrt_ff_hold | 2.6 | repair_Violations best 26335 last 26335 rows 151 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 1.4 | repair_Violations best 1656 last 1673 rows 98 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (234/234 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-722706 | ot_s81sl_leaf__t65 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (250/250 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-3045415 | ot_s81sl_leaf__t74 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla2127225-2739353 | serdes__t15 | 3_1_place_gp_skip_io | 1.1 | overflow best 0.9012 last 0.904 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__clfde1249e-2763157 | sle_st_b_v2 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5608/5609 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4518/4518 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-3671630 | slw_fw_v2 | 3_3_place_gp | 0.9 | overflow best 0.0986 last 0.0986 rows 42 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (4701/4701 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-2148023 | slw_hc2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4992/4993 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-1463093 | slw_st_b_v1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5181/5181 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (672/672 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 3.0 | last meaningful line 0.0 h ago (543/543 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3418299-1777 | 3418299 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | otc-3434320-23245 | 3434320 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-2162531 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 4.6 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 4.2 | drt_violations best 49 last 49 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_1_grt | 0.9 | last meaningful line 0.4 h ago (232/1613 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | 5_1_grt | 4.2 | last meaningful line 2.1 h ago (240/1334 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (781/781 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (919/919 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (965/965 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (805/805 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (854/854 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | tt_setup_repair_grt | 4.2 | repair_Viol best 759 last 759 rows 963 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | tt_setup_repair_grt | 4.2 | repair_Viol best 759 last 759 rows 952 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (788/788 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | 5_2_route | 8.3 | last meaningful line 0.0 h ago (283/284 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | postcts_gate_FF | 4.2 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | tt_setup_repair_grt | 4.2 | repair_Viol best 759 last 759 rows 880 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | tt_setup_repair_grt | 4.2 | repair_Viol best 759 last 759 rows 840 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (779/779 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 4.2 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 34.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261120_080032_3761085-i1-1022173 | eco_20261120_080032_3761085-i1 | 5_2_route | 5.4 | drt_violations best 3666 last 3666 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-882202 | col_h10_r0_p1__t1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (1135/1135 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1254197 | col_h10_r0_p1__t1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (2000/2000 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (2210/2210 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-2115455 | col_h10_r0_p1__t1 | stage_odb_cap | 7.1 | last meaningful line 0.0 h ago (1014/1014 lines) | YOUNG: evidence 7.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 5.6 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-1661189 | col_h10_r1__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2918/2918 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-1597344 | col_h10_r1__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2949/2949 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-1663478 | col_h10_r2__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (3008/3008 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-1643657 | col_h10_r2__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (3007/3007 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 7.1 | repair_Viol best 1048 last 1048 rows 657 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 7.3 | repair_Viol best 1048 last 1048 rows 1258 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 7.3 | repair_Viol best 1048 last 1048 rows 1052 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1541838 | col_h9_r0_p1__t1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (1779/1779 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-3235380 | dsdv_slice_kv512_C__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.9616 last 0.9616 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_LP__t2-2710828 | dsdv_slice_lepw_mu_LP__t2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-gunit__t1-3341748 | gunit__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-1734167 | hd_mesh | pregrt_ff_hold | 5.5 | repair_TNS best 225508 last 225508 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2768122 | ot_s81sl_kv_leaf__t5 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.7079 last 0.7079 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 7.3 | last meaningful line 0.8 h ago (208/216 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t31-1529768 | ot_s81sl_leaf__t31 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (931/946 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-seqhost__t1-2837346 | seqhost__t1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.9309 last 0.9415 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | 5_1_grt | 7.7 | repair_TNS best 9040.56 last 9040.56 rows 3 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | 5_1_grt | 7.0 | repair_Remaining best 261881 last 261881 rows 146 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3386/3386 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v2-1792546 | sle_sc_v2 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (2566/2566 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t36-2129362 | slice_station__t36 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-2389841 | svc_hi_dsdv_svc_pvso_entry__t2 | synth_odb_v | 4.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t3-2814940 | svc_hi_dsdv_svc_rs__t3 | synth_odb_v | 4.0 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t4-2265883 | svc_hi_dsdv_svc_rs__t4 | 2_2_floorplan_macro | 4.2 | last meaningful line -0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 99.2 |  | NO-DATA: empty log |  |
| epyc9 | otc-2411353-23881 | 2411353 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | otc-2491977-4017 | 2491977 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | otc-2969764-31157 | 2969764 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 4.0 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h10-r2--t1--clac068e56-grt-1180958 | col-h10-r2--t1--clac068e56-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (64/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-3533052 | cbf_q00 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (564/564 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (2989/2989 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 6.0 | drt_violations best 73630 last 73630 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 3.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 6.2 | last meaningful line 0.1 h ago (147/147 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (3283/3283 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 6.6 | drt_violations best 62725 last 62725 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (411/411 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-iqf__t1-4060768 | iqf__t1 | 3_3_place_gp | 0.5 | overflow best 0.4569 last 0.4569 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (158/158 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (212/212 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (2889/2889 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 2_1_floorplan | 1.7 | last meaningful line 1.5 h ago (144/144 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (680/680 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (3056/3056 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (2844/2844 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (2928/2928 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 17.8 | last meaningful line 0.8 h ago (285/286 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t37-3308231 | slice_station__t37 | 3_3_place_gp | 0.7 | overflow best 0.3472 last 0.3473 rows 8 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 6.0 | drt_violations best 19623 last 19623 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t41-3247802 | slice_station__t41 | 3_3_place_gp | 0.7 | overflow best 0.2647 last 0.2647 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slice_station__t49-3261186 | slice_station__t49 | 3_3_place_gp | 0.7 | overflow best 0.2855 last 0.303 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slice_station__t52-4120788 | slice_station__t52 | 3_3_place_gp | 0.5 | overflow best 0.3938 last 0.3938 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 18.1 | last meaningful line 0.8 h ago (270/271 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 18.8 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 18.8 | drt_violations best 89452 last 89452 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 19.2 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 2.9 | repair_TNS best 6.243 last 6.243 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 3.3 | last meaningful line 0.0 h ago (478/478 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 1.4 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-2876778 | tt_ctlm | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (307/307 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-cbf_q01-749277 | cbf_q01 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1209 last 0.1209 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-cbx_q10__cl94a12200_h-868687 | cbx_q10 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | 3_3_place_gp | 0.8 | overflow best 0.1987 last 0.1987 rows 42 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-872108 | ot_s81sl_leaf__t67 | 3_3_place_gp | 0.8 | overflow best 0.3457 last 0.3457 rows 36 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-760479 | slice_station__t51 | 3_4_place_resized | 0.9 | repair_Remaining best 110597 last 110597 rows 80 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_fw_v3-944789 | slw_fw_v3 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (294/294 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 4.3 | drt_violations best 357 last 357 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-2648902 | col_h10_r2__t1 | stage_odb_cap | 6.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | stage_odb_cap | 5.6 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 27.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 8.3 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 8.3 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-1657776 | col_h10_r1__t1 | stage_odb_cap | 5.6 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 25.2 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 20.3 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 15.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 7.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 62.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 38.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 38.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | ap-ageom-kw-col-h9-r0-p6--t1--pv0012ba28-grt-2066560 | col-h9-r0-p6--t1--pv0012ba28-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 17.1 | last meaningful line 0.0 h ago (8270/8270 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-2974046 | kv3_pv_v8 | 4_1_cts | 16.2 | last meaningful line 0.8 h ago (15603/15603 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (8807/8807 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 16.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 20.1 | last meaningful line 0.0 h ago (9933/9933 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 20.6 | last meaningful line 0.0 h ago (9966/9966 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 9.4 | drt_violations best 77 last 77 rows 11 | before-window best 26786, window best 77 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 12.0 | last meaningful line 0.9 h ago (1377/1377 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (5012/5012 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (5129/5129 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (4978/4978 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (5079/5079 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (5200/5200 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (4763/4763 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (5048/5048 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 15.2 | last meaningful line 0.0 h ago (8408/8408 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv291547b4-2471228 | col_h9_r0_p2__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1145/1145 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1005/1005 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (863/863 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1083/1083 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (995/995 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (999/999 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (960/960 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1003/1003 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1006/1006 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (788/788 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (1015/1015 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 16.4 | last meaningful line 0.0 h ago (1138/1138 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-3742048 | col_h10_r0_p1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (2001/2001 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (1098/1098 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 18.0 | last meaningful line 0.0 h ago (9412/9412 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (9455/9455 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 25.2 | last meaningful line 0.0 h ago (1501/1501 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 20.2 | last meaningful line 0.0 h ago (1223/1223 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 12.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 12.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (1274/1274 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (1091/1091 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 18.9 | last meaningful line 0.0 h ago (1202/1202 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (1090/1090 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | 5_2_route | 18.3 | drt_violations best 13684 last 13684 rows 3 | before-window best 108699, window best 13684 | PROGRESS: drt_violations improved 87.4 % in window |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (1090/1090 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 19.4 | last meaningful line 0.0 h ago (1215/1215 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 18.5 | last meaningful line 0.0 h ago (1105/1105 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (1090/1090 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (1090/1090 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 18.3 | last meaningful line 0.0 h ago (1090/1090 lines) | PROGRESS: log still growing |  |
