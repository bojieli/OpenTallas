# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 19:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'GRT-LABEL': 39, 'YOUNG': 188, 'NO-DATA': 5, 'EXCLUDED': 4, 'KEEP': 7, 'PROGRESS': 61}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-182001 | col_h9_r0_p6__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1685/1685 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -338.84 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | 5_1_grt | 2.3 | grt rounds 6 overflow 5:359 -> 10:243 -> 15:219 -> 20:198 -> 25:181 -> 30:182 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 30: 181 -> 182 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 26.4 | grt rounds 3 overflow 5:110819 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 22.8 | grt rounds 3 overflow 5:87024 -> 10:50446 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 11.9 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 11.6 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 21.5 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 21.9 | grt rounds 6 overflow 5:14060 -> 10:3179 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: overflow 3179 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 11.9 | grt rounds 3 overflow 5:43983 -> 10:46937 -> 15:40008 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 20.1 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:15441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 22.1 | grt rounds 4 overflow 5:79148 -> 10:67538 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 22.1 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 30.7 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 25.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1184 -> 20:954 -> 25:457 -> 30:171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 5_1_grt | 6.7 | grt rounds 3 overflow 5:19163 -> 10:15333 -> 15:12400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_1_grt | 3.9 | grt rounds 6 overflow 5:7819 -> 10:3205 -> 15:1186 -> 20:653 -> 25:674 -> 30:655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 3.5 | grt rounds 6 overflow 5:727 -> 10:550 -> 15:542 -> 20:538 -> 25:186 -> 30:77 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 32.3 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6089 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 19.7 | grt rounds 3 overflow 5:29589 -> 10:6636 -> 15:6011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 19.7 | grt rounds 3 overflow 5:59133 -> 10:59535 -> 15:50422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 21.1 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 19.7 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 32.3 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48548 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 26.6 | grt rounds 3 overflow 5:78093 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 27.7 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 60.9 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 28.9 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 12.0 | grt rounds 3 overflow 5:27060 -> 10:13905 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 28.9 | grt rounds 4 overflow 5:32226 -> 10:19209 -> 15:17126 -> 20:16680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2018480 | cbn_q00 | 5_1_grt | 0.5 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | GRT-LABEL: DESIGN-FAIL: overflow 8426 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 10.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 10.8 | grt rounds 3 overflow 5:24921 -> 10:18037 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 21.3 | grt rounds 4 overflow 5:27548 -> 10:10273 -> 15:6221 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 10.8 | grt rounds 3 overflow 5:48001 -> 10:50111 -> 15:47470 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 30.4 | grt rounds 3 overflow 5:48908 -> 10:43151 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 22.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 22.3 | grt rounds 3 overflow 5:44318 -> 10:39317 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 21.6 | grt rounds 3 overflow 5:59628 -> 10:54127 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 17.1 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3110/3111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (197/206 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2966/2966 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (874/874 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | 3_3_place_gp | 3.5 | overflow best 0.7174 last 0.718 rows 11 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 11.6 | last meaningful line 3.5 h ago (198/204 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 2_1_floorplan | 0.4 | last meaningful line 0.3 h ago (87/87 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-4062983 | kv3_hub_Eo | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (820/820 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t3-4025566 | ot_s81sl_kv_leaf__t3 | 3_5_place_dp | 1.8 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t4-3962225 | ot_s81sl_kv_leaf__t4 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (220/220 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (205/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3424/3424 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t60-4062057 | ot_s81sl_leaf__t60 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (1174/1174 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | tt_setup_repair | 2.3 | repair_Violations best 86 last 171 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-serdes__t2-3852722 | serdes__t2 | 3_5_place_dp | 1.8 | repair_Violations best 45 last 45 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (501/501 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1-3809500 | eco_20261120_185639_3224747-i1 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 6.5 | drt_violations best 1026 last 1026 rows 15 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 4.1 | drt_violations best 58 last 58 rows 11 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1-831859 | eco_20261121_003008_2139459-i1 | 5_2_route | 1.3 | drt_violations best 4001 last 4001 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1t-3571482 | eco_20261121_014354_2681516-i1t | 5_2_route | 2.0 | drt_violations best 59735 last 59735 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_021137_2680521-i1t-410323 | eco_20261121_021137_2680521-i1t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-fin-3773198 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (753/753 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (824/824 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | pregrt_ff_hold | 1.0 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-1320857 | col_h10_r2__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (497/497 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (370/370 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (447/447 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1227/1227 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-528316 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.5 h ago (126/126 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | 3_4_place_resized | 4.5 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (464/464 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3194/3194 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t8-1240171 | ot_s81sl_leaf__t8 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla2127225-539609 | serdes__t15 | 3_3_place_gp | 1.6 | overflow best 0.4073 last 0.4073 rows 50 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-serdes__t15__cla3d02796-450387 | serdes__t15 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (184/184 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t16-3293794 | serdes__t16 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (507/507 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (291/291 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_1_grt | 5.1 | last meaningful line 1.8 h ago (233/943 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (186/189 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (309/309 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (446/446 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | 5_1_grt | 5.5 | last meaningful line 1.6 h ago (217/889 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-1646967 | slice_station__t24 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (523/552 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (355/355 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (466/466 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (548/548 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (483/483 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (509/509 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (383/383 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (375/375 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (467/467 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_1_grt | 5.1 | repair_Remaining best 381120 last 381120 rows 38 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (326/326 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (460/460 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 2_4_floorplan_pdn | 5.0 | last meaningful line 0.3 h ago (23/23 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (424/424 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (441/441 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-897008 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 1.4 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (429/429 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1-1701387 | eco_20261120_134605_3273412-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 2.7 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 4.2 | drt_violations best 968 last 968 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | so_3214559_ff_96410 | so_3214559_ff_96410 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (933/933 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_3214559_tt_96410 | so_3214559_tt_96410 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (933/933 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 4.0 | last meaningful line 2.3 h ago (198/203 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (390/390 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 7.6 | last meaningful line 0.7 h ago (15747/15747 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 7.6 | last meaningful line 0.6 h ago (15652/15652 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 5.4 | last meaningful line 0.1 h ago (15688/15688 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_2_route | 5.4 | drt_violations best 3487 last 3487 rows 2 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (270/270 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (450/450 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-3208717 | slw_hc0 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (552/552 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3263016 | slw_st_b_v1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (222/222 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 10.3 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_3_fillcell | 4.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_3446429_ff_30981 | so_3446429_ff_30981 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_3446429_tt_30981 | so_3446429_tt_30981 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | 5_2_route | 8.7 | last meaningful line 0.4 h ago (280/281 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 8.7 | last meaningful line 0.7 h ago (279/280 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 38.7 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | tt_setup_repair_grt | 10.6 | repair_Viol best 950 last 950 rows 779 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 10.3 | drt_violations best 100 last 100 rows 12 | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 5_1_grt | 3.3 | last meaningful line 1.0 h ago (199/218 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | 5_1_grt | 4.2 | last meaningful line 2.0 h ago (199/226 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | 5_1_grt | 3.3 | last meaningful line 1.3 h ago (199/219 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3419982 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.6 | overflow best 0.4674 last 0.4674 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (213/213 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (168/168 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | 2_1_floorplan | 3.2 | last meaningful line -0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.6 | last meaningful line 1.0 h ago (143/143 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (1641/1641 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | 3_3_place_gp | 0.6 | overflow best 0.3201 last 0.3201 rows 34 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (299/299 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-3758439 | ot_s81sl_leaf__t39 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 3.3 | last meaningful line 0.8 h ago (202/214 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t56-3359255 | ot_s81sl_leaf__t56 | 3_3_place_gp | 0.6 | overflow best 0.5582 last 0.564 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-serdes__t12-3735264 | serdes__t12 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t1__clfe1f0815-3499205 | serdes__t1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 5_1_grt | 3.3 | last meaningful line 0.3 h ago (213/598 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 3.2 | repair_TNS best 2142.78 last 2142.78 rows 8 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 4.1 | repair_TNS best 3590.49 last 3590.49 rows 4 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (332/332 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 5.0 | last meaningful line 1.3 h ago (648/648 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 103.9 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 8.8 | drt_violations best 12631 last 12631 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pvd2159f4a-grt-2824395 | col-h9-r0-p3--t1--cl8ce97bcb--pvd2159f4a-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (280/280 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | 5_2_route | 11.0 | last meaningful line 0.0 h ago (259/260 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 3_3_place_gp | 0.5 | overflow best 0.2121 last 0.2121 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | generate_abstract | 10.8 | last meaningful line -0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-2007425 | col_h9_r0_p2__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 10.9 | last meaningful line 0.7 h ago (288/289 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | 1_2_yosys | 3.5 | last meaningful line 0.0 h ago (197/197 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | 2_1_floorplan | 3.7 | last meaningful line 0.1 h ago (91/91 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | 1_2_yosys | 3.5 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (4756/4757 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (440/440 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9944 last 0.9944 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (980/980 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 4.8 | last meaningful line 0.6 h ago (336/336 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-479703 | ot_s81sl_leaf__t2 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3086 last 0.3086 rows 40 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 6_report | 23.5 | last meaningful line 0.2 h ago (273/273 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (392/392 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 1.1 | last meaningful line 0.0 h ago (327/327 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 1.4 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 1.7 | last meaningful line 0.0 h ago (425/425 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 2_1_floorplan | 4.8 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-1993165 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 6.1 | last meaningful line 1.3 h ago (690/690 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 4.7 | last meaningful line 0.0 h ago (684/684 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | otc-1006993-6312 | 1006993 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | otc-473923-2002 | 473923 | gen_lint_yosys | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261120_175848_3183588-i1t-312780 | eco_20261120_175848_3183588-i1t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_185032_3498280-i1-1846100 | eco_20261120_185032_3498280-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (226/670 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1541/1541 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 4.6 | overflow best 0.417 last 0.417 rows 33 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1550/1550 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 16.9 | last meaningful line 2.3 h ago (225/231 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 16.9 | last meaningful line 1.8 h ago (226/231 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (2788/2788 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (540/540 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | pregrt_ff_hold | 3.3 | repair_Violations best 11129 last 11150 rows 87 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (2258/2258 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (500/500 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (369/369 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (353/353 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1312/1312 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1387/1387 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1520/1520 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1372/1372 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (359/359 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (370/370 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (376/376 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (456/456 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 3.3 | last meaningful line 0.3 h ago (612/612 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 3.2 | last meaningful line 0.0 h ago (526/526 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 3.8 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 3.4 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_2_route | 3.4 | drt_violations best 675 last 675 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 1.9 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (232/1275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | otc-2579942-9151 | 2579942 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 32.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | 5_2_route | 12.8 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 5_1_grt | 3.2 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 29.9 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 25.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 19.9 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 12.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 66.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 42.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 43.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 21.9 | last meaningful line 0.0 h ago (11110/11110 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 23.0 | last meaningful line 0.0 h ago (11647/11647 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 20.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (5551/5551 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 11.6 | last meaningful line 0.0 h ago (827/827 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 11.6 | last meaningful line 0.0 h ago (6523/6523 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (4988/4988 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 24.8 | last meaningful line 0.0 h ago (12773/12773 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 17.0 | last meaningful line 0.5 h ago (1426/1426 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (4038/4038 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4271/4271 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 14.1 | last meaningful line 0.0 h ago (7743/7743 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (8038/8038 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 8.6 | last meaningful line 0.0 h ago (829/829 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (627/627 lines) | PROGRESS: log still growing |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4883/4883 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 8.9 | last meaningful line 0.0 h ago (620/620 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 10.3 | last meaningful line 0.2 h ago (15793/15793 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (4680/4680 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 10.2 | last meaningful line 0.0 h ago (5257/5257 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (1131/1131 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (1050/1050 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 19.7 | last meaningful line 0.0 h ago (11108/11108 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (1189/1189 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (1234/1234 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1274/1274 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (1074/1074 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (1124/1124 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1132/1132 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1352/1352 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (832/832 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (981/981 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1264/1264 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1057/1057 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1103/1103 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1268/1268 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1229/1229 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (1026/1026 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (842/842 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1048/1048 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1057/1057 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1284/1284 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 12.5 | last meaningful line 0.0 h ago (1382/1382 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1385/1385 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (2134/2134 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (1390/1390 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 12.4 | last meaningful line 0.0 h ago (6491/6491 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 22.8 | last meaningful line 0.0 h ago (12252/12252 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 23.0 | last meaningful line 0.0 h ago (12295/12295 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2006927 | col_h10_r2__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 34 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (6123/6123 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (5729/5729 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (5896/5896 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (5684/5684 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (5768/5768 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 29.9 | last meaningful line 0.0 h ago (1784/1784 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 25.0 | last meaningful line 0.0 h ago (1506/1506 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 20.5 | last meaningful line 0.0 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
