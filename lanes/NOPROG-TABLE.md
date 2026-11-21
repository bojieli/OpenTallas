# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 20:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-LABEL': 40, 'YOUNG': 186, 'NO-DATA': 12, 'KEEP': 7, 'EXCLUDED': 3, 'PROGRESS': 66}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | 5_1_grt | 2.5 | grt rounds 6 overflow 5:359 -> 10:243 -> 15:219 -> 20:198 -> 25:181 -> 30:182 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 30: 181 -> 182 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 26.7 | grt rounds 3 overflow 5:110819 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 23.0 | grt rounds 3 overflow 5:87024 -> 10:50446 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 12.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 11.9 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 21.8 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 22.1 | grt rounds 6 overflow 5:14060 -> 10:3179 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: overflow 3179 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 12.1 | grt rounds 4 overflow 5:43983 -> 10:46937 -> 15:40008 -> 20:41318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 20.4 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:15441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 22.4 | grt rounds 4 overflow 5:79148 -> 10:67538 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 22.4 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 30.9 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 25.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1184 -> 20:954 -> 25:457 -> 30:171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | 5_1_grt | 8.5 | grt rounds 6 overflow 5:3688 -> 10:2561 -> 15:2268 -> 20:1901 -> 25:1852 -> 30:1871 | GRT-LABEL: DESIGN-FAIL: overflow 2561 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_1_grt | 4.4 | grt rounds 6 overflow 5:7819 -> 10:3205 -> 15:1186 -> 20:653 -> 25:674 -> 30:655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 4.0 | grt rounds 6 overflow 5:727 -> 10:550 -> 15:542 -> 20:538 -> 25:186 -> 30:77 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | 5_1_grt | 9.2 | grt rounds 4 overflow 5:5770 -> 10:2142 -> 15:1335 -> 20:1297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 32.8 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6089 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 20.2 | grt rounds 3 overflow 5:29589 -> 10:6636 -> 15:6011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 20.2 | grt rounds 3 overflow 5:59133 -> 10:59535 -> 15:50667 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 13.3 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 21.6 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 20.2 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 32.8 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48548 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 27.1 | grt rounds 3 overflow 5:78093 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 28.2 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 61.4 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 29.4 | grt rounds 4 overflow 5:49170 -> 10:53420 -> 15:44462 -> 20:46531 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 12.5 | grt rounds 3 overflow 5:27060 -> 10:13905 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 29.4 | grt rounds 4 overflow 5:32226 -> 10:18865 -> 15:17126 -> 20:16680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2018480 | cbn_q00 | 5_1_grt | 1.0 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | GRT-LABEL: DESIGN-FAIL: overflow 8426 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 11.3 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 11.3 | grt rounds 3 overflow 5:24921 -> 10:18037 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 21.8 | grt rounds 4 overflow 5:27548 -> 10:10273 -> 15:6221 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 11.3 | grt rounds 3 overflow 5:46455 -> 10:50111 -> 15:47470 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 30.9 | grt rounds 3 overflow 5:48908 -> 10:43151 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 22.8 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 22.8 | grt rounds 3 overflow 5:44318 -> 10:39317 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 22.1 | grt rounds 3 overflow 5:55450 -> 10:54127 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 17.6 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_1_grt | 2.5 | repair_TNS best 127.337 last 127.337 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3319/3319 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 3_3_place_gp | 0.7 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 11.9 | last meaningful line 3.8 h ago (198/204 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 2_1_floorplan | 0.7 | last meaningful line 0.5 h ago (87/87 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-4062983 | kv3_hub_Eo | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (880/880 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (205/211 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | tt_setup_repair | 0.7 | repair_Violations best 234 last 259 rows 51 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (925/925 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (636/636 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | pregrt_ff_hold | 0.6 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1-3809500 | eco_20261120_185639_3224747-i1 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 6.7 | drt_violations best 1026 last 1026 rows 15 | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 4.4 | drt_violations best 16 last 16 rows 13 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1-831859 | eco_20261121_003008_2139459-i1 | 5_2_route | 1.5 | drt_violations best 4001 last 4001 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1t-3571482 | eco_20261121_014354_2681516-i1t | 5_2_route | 2.2 | drt_violations best 59735 last 59735 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_021137_2680521-i1t-410323 | eco_20261121_021137_2680521-i1t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t8-grt-78629 | ot-s81sl-leaf--t8-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (1122/1122 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (621/621 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-1320857 | col_h10_r2__t1 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (662/662 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (747/747 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (1437/1437 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (518/518 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-528316 | dsdv_slice_c1x_C__t4 | 1_2_yosys | 2.1 | last meaningful line 0.0 h ago (165/165 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (436/436 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla3d02796-450387 | serdes__t15 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (304/304 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (415/415 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (537/537 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | postcts_gate_FF | 5.6 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 5_1_grt | 3.1 | last meaningful line 0.5 h ago (217/777 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (339/339 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (462/462 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (490/490 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-1646967 | slice_station__t24 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (183/183 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1239/1239 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 5_1_grt | 5.2 | repair_Remaining best 112905 last 112905 rows 252 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (578/578 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (374/374 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (427/427 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (513/513 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (779/779 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (413/413 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (497/497 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (427/427 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | tt_setup_repair_grt | 6.9 | repair_Violations best 10 last 48 rows 56 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | stage_odb_cap | 5.5 | last meaningful line 0.2 h ago (28/28 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 2.0 | last meaningful line 0.3 h ago (459/459 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 2.1 | last meaningful line 0.3 h ago (477/477 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-897008 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 1.9 | last meaningful line 0.1 h ago (463/463 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 2.1 | last meaningful line 0.3 h ago (463/463 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1-1701387 | eco_20261120_134605_3273412-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 3.2 | drt_violations best 128283 last 128283 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 4.7 | drt_violations best 968 last 968 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbf-q00--cl870de686-grt-3952152 | cbf-q00--cl870de686-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-cbf-q11-grt-3948780 | cbf-q11-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-cbn-q01--cldd6ea846-grt-3952527 | cbn-q01--cldd6ea846-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-serdes--t16-grt-3947375 | serdes--t16-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 4.5 | last meaningful line 2.8 h ago (198/204 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (420/420 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-3946520 | kv3_hgi_v8 | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc7 | dpkit-kv3_hgi_v8-3997172 | kv3_hgi_v8 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 8.1 | last meaningful line 1.2 h ago (15747/15747 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 8.1 | last meaningful line 1.0 h ago (15653/15653 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 5.9 | last meaningful line 0.1 h ago (15717/15717 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | tt_setup_repair | 10.8 | repair_Violations best 31251 last 31251 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3954291 | ot_s81sl_leaf__t39 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | tt_setup_repair | 0.1 | repair_Violations best 160 last 430 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | tt_setup_repair | 0.0 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | tt_setup_repair | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 6_report | 5.9 | last meaningful line 0.0 h ago (291/291 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (300/300 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (480/480 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (582/582 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3263016 | slw_st_b_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-3970864 | slw_st_b_v2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 10.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-fin-942798 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (1076/1076 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 9.2 | drt_violations best 45501 last 45501 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 39.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 5_1_grt | 3.8 | last meaningful line 1.5 h ago (199/222 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | 5_1_grt | 4.7 | last meaningful line 2.5 h ago (199/229 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | 5_1_grt | 3.8 | last meaningful line 1.8 h ago (199/223 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | pregrt_ff_hold | 1.1 | repair_Violations best 137 last 137 rows 12 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3419982 | col_h9_r0_p5__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (243/243 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 4.7 | overflow best 0.3249 last 0.3249 rows 35 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | 3_1_place_gp_skip_io | 3.7 | overflow best 0.751 last 0.751 rows 27 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | 3_3_place_gp | 4.0 | overflow best 0.6526 last 0.6526 rows 24 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 3.1 | last meaningful line 1.5 h ago (144/144 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (1941/1941 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (329/329 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-3758439 | ot_s81sl_leaf__t39 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 3.8 | last meaningful line 1.3 h ago (202/219 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t56-3359255 | ot_s81sl_leaf__t56 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t12-3735264 | serdes__t12 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t1__clfe1f0815-3499205 | serdes__t1 | 3_1_place_gp_skip_io | 1.0 | overflow best 0.6793 last 0.6793 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1705/1705 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | 5_1_grt | 3.7 | last meaningful line 0.2 h ago (207/617 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 3.7 | repair_TNS best 987.57 last 987.57 rows 5 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 4.6 | last meaningful line 3.7 h ago (215/831 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (362/362 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 5.5 | last meaningful line 0.0 h ago (682/682 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 104.4 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-ot-s81sl-kv-leaf--t4-grt-3772635 | ot-s81sl-kv-leaf--t4-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-render-d8321490cd7b-3900048 | ap-render-d8321490cd7b | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.3 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6921 last 0.7539 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4185 last 0.4185 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4198 last 0.4198 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 4_1_cts | 1.0 | last meaningful line -0.0 h ago (3024/3024 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 1267 last 1267 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9706 last 0.9706 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9704 last 0.9704 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-2007425 | col_h9_r0_p2__t1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 378 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | last meaningful line -0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 208 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 193 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 11.4 | drt_violations best 178775 last 178775 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | 4_1_cts | 0.5 | last meaningful line -0.0 h ago (3385/3385 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | sdc_lint | 1.6 | last meaningful line 1.6 h ago (1/1 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | 3_1_place_gp_skip_io | 4.0 | overflow best 0.8246 last 0.8583 rows 15 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 4.2 | last meaningful line 0.1 h ago (84/84 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | stage_odb_cap | 4.0 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (725/725 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (470/470 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | tt_setup_measure | 0.3 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (1100/1100 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 5.3 | last meaningful line 1.1 h ago (336/336 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-serdes__t4-3454937 | serdes__t4 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (316/316 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 1_synth | 0.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 8.1 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 2.1 | last meaningful line 0.0 h ago (512/512 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (418/418 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 1.9 | last meaningful line 0.0 h ago (448/448 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 2.2 | last meaningful line 0.3 h ago (457/457 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 2_1_floorplan | 5.3 | last meaningful line 0.3 h ago (91/91 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (241/241 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-1993165 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (237/237 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 5.2 | last meaningful line 0.2 h ago (716/716 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | otc-1006993-6312 | 1006993 | gen_lint_yosys | 1.6 | last meaningful line 1.6 h ago (1/1 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-eco_20261120_185032_3498280-i1-1846100 | eco_20261120_185032_3498280-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (246/246 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_3794061_ff_47620 | so_3794061_ff_47620 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_3794061_tt_47620 | so_3794061_tt_47620 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1841/1841 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | 3_4_place_resized | 5.1 | repair_Remaining best 112132 last 112132 rows 226 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1850/1850 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 17.4 | last meaningful line 2.8 h ago (225/231 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 17.4 | last meaningful line 2.3 h ago (226/231 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | 5_1_grt | 6.1 | last meaningful line 0.1 h ago (208/215 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (570/570 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (458/458 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (2558/2558 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (530/530 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (383/383 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1612/1612 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1687/1687 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (437/437 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1662/1662 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (388/388 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 5_1_grt | 3.8 | last meaningful line 0.0 h ago (196/202 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 3.8 | last meaningful line 0.8 h ago (612/612 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 3.7 | last meaningful line 0.0 h ago (594/594 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 4.3 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 3.9 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_2_route | 3.9 | drt_violations best 675 last 675 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (261/261 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 1.7 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 33.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 13.3 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 5_1_grt | 3.7 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 30.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 25.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 20.4 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 13.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 67.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 43.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 44.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 22.1 | last meaningful line 0.0 h ago (11260/11260 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 23.3 | last meaningful line 0.0 h ago (11797/11797 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 21.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 10.7 | last meaningful line 0.0 h ago (5701/5701 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (842/842 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (6673/6673 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 10.6 | last meaningful line 0.0 h ago (5138/5138 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 25.1 | last meaningful line 0.0 h ago (12923/12923 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 17.5 | last meaningful line 1.0 h ago (1426/1426 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (4338/4338 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (4571/4571 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (8043/8043 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 14.8 | last meaningful line 0.0 h ago (8338/8338 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 9.1 | last meaningful line 0.0 h ago (870/870 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (656/656 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (494/494 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 7.2 | last meaningful line 0.0 h ago (562/562 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_1_grt | 5.8 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_1_grt | 5.6 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 9.4 | last meaningful line 0.0 h ago (650/650 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 8.6 | last meaningful line 0.0 h ago (4980/4980 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 10.7 | last meaningful line 0.0 h ago (5557/5557 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1161/1161 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1080/1080 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 20.2 | last meaningful line 0.0 h ago (11398/11398 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1219/1219 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1304/1304 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1104/1104 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1154/1154 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1162/1162 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1382/1382 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (862/862 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1011/1011 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1294/1294 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1087/1087 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | 5_2_route | 13.3 | drt_violations best 9189 last 9189 rows 3 | before-window best 84020, window best 9189 | PROGRESS: drt_violations improved 89.1 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1298/1298 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1259/1259 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1056/1056 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (872/872 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (1068/1068 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1078/1078 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1087/1087 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | 5_2_route | 13.3 | drt_violations best 8703 last 8703 rows 3 | before-window best 81345, window best 8703 | PROGRESS: drt_violations improved 89.3 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | tt_setup_repair_grt | 11.1 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 10.8 | drt_violations best 51 last 51 rows 22 | before-window best 91026, window best 51 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 13.0 | last meaningful line 0.0 h ago (1412/1412 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (1415/1415 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 12.5 | last meaningful line 0.0 h ago (2164/2164 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 12.5 | last meaningful line 0.0 h ago (1420/1420 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 12.9 | last meaningful line 0.0 h ago (6791/6791 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 23.3 | last meaningful line 0.0 h ago (12552/12552 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 23.5 | last meaningful line 0.0 h ago (12595/12595 lines) | PROGRESS: log still growing |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 9.3 | drt_violations best 8412 last 8412 rows 3 | before-window best 72611, window best 8412 | PROGRESS: drt_violations improved 88.4 % in window |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 11.5 | last meaningful line 0.0 h ago (6129/6129 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 11.4 | last meaningful line 0.0 h ago (6423/6423 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 11.3 | last meaningful line 0.0 h ago (6196/6196 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 11.3 | last meaningful line 0.0 h ago (5984/5984 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 11.4 | last meaningful line 0.0 h ago (6058/6058 lines) | PROGRESS: log still growing |  |
| intel1 | prd-eco_20261120_194249_3446526-i1t-3450960 | eco_20261120_194249_3446526-i1t | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 30.4 | last meaningful line 0.0 h ago (1814/1814 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 25.5 | last meaningful line 0.0 h ago (1536/1536 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 21.0 | last meaningful line 0.0 h ago (1588/1588 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_1_grt | 3.9 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | pregrt_ff_hold | 3.9 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
