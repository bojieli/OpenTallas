# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 20:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 39, 'YOUNG': 202, 'NO-DATA': 6, 'EXCLUDED': 4, 'KEEP': 7, 'PROGRESS': 63}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 9.7 | drt_violations best 45501 last 45501 rows 1 | before-window best 45501, window best 45501 | NO-PROGRESS: drt_violations best 45501 vs 45501 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 11.9 | drt_violations best 178775 last 178775 rows 1 | before-window best 178775, window best 178775 | NO-PROGRESS: drt_violations best 178775 vs 178775 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | 5_1_grt | 3.3 | grt rounds 6 overflow 5:359 -> 10:243 -> 15:219 -> 20:198 -> 25:181 -> 30:182 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 30: 181 -> 182 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 27.4 | grt rounds 3 overflow 5:110819 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 23.8 | grt rounds 3 overflow 5:87024 -> 10:50446 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 12.9 | grt rounds 6 overflow 5:16689 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: overflow 7238 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 12.6 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 22.5 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 22.9 | grt rounds 6 overflow 5:6728 -> 10:3179 -> 15:2382 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 12.9 | grt rounds 4 overflow 5:43983 -> 10:46937 -> 15:40008 -> 20:41318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 21.1 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:15441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 23.1 | grt rounds 4 overflow 5:79148 -> 10:67538 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 23.1 | grt rounds 5 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 -> 25:40097 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 31.7 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 5_1_grt | 8.9 | grt rounds 6 overflow 5:2761 -> 10:2433 -> 15:2287 -> 20:2095 -> 25:2087 -> 30:2077 | GRT-LABEL: DESIGN-FAIL: overflow 2433 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_1_grt | 4.9 | grt rounds 6 overflow 5:7819 -> 10:3205 -> 15:1186 -> 20:653 -> 25:674 -> 30:655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 0.6 | grt rounds 3 overflow 5:38517 -> 10:38944 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: overflow 38944 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 33.3 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6089 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 20.7 | grt rounds 3 overflow 5:29589 -> 10:6636 -> 15:6011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 20.7 | grt rounds 3 overflow 5:59133 -> 10:59535 -> 15:50667 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 13.8 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 22.1 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 20.7 | grt rounds 4 overflow 5:41921 -> 10:44894 -> 15:44490 -> 20:47845 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 33.3 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48548 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 27.3 | grt rounds 3 overflow 5:78093 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 28.4 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 61.6 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 29.7 | grt rounds 4 overflow 5:49170 -> 10:53420 -> 15:44462 -> 20:46531 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:27060 -> 10:13870 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 29.7 | grt rounds 4 overflow 5:32226 -> 10:18865 -> 15:17126 -> 20:16680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 23.5 | grt rounds 4 overflow 5:18562 -> 10:18456 -> 15:11655 -> 20:10171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 11.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | 5_1_grt | 0.8 | grt rounds 6 overflow 5:18796 -> 10:17709 -> 15:15585 -> 20:16567 -> 25:14112 -> 30:13066 | GRT-LABEL: DESIGN-FAIL: overflow 17709 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:24921 -> 10:18037 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 22.3 | grt rounds 4 overflow 5:27548 -> 10:10273 -> 15:6221 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:46455 -> 10:50111 -> 15:47470 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 31.4 | grt rounds 3 overflow 5:48908 -> 10:43151 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 23.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 23.3 | grt rounds 3 overflow 5:44318 -> 10:39317 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 22.6 | grt rounds 3 overflow 5:55450 -> 10:54127 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 18.1 | grt rounds 5 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbx_q10__cl94a12200-3336899 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.1184 last 0.1184 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | tt_setup_repair | 0.6 | repair_Viol best 626 last 626 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (178/178 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_2_route | 3.3 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (237/237 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.6 | overflow best 0.3874 last 0.3874 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (223/223 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (209/209 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (249/249 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-3316818 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 3_3_place_gp | 1.4 | last meaningful line 0.5 h ago (179/179 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 12.6 | last meaningful line 4.5 h ago (198/205 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-4062983 | kv3_hub_Eo | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1056/1056 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 2.9 | last meaningful line 1.3 h ago (205/214 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1374/1374 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 4_1_cts | 2.8 | last meaningful line 0.0 h ago (4072/4072 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (353/353 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (630/630 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (236/1486 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1-3809500 | eco_20261120_185639_3224747-i1 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1-102804 | eco_20261120_233525_2680444-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (177/177 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1t-3571482 | eco_20261121_014354_2681516-i1t | 5_2_route | 3.0 | drt_violations best 3508 last 3508 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_021137_2680521-i1t-410323 | eco_20261121_021137_2680521-i1t | 5_2_route | 2.5 | drt_violations best 126076 last 126076 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (205/211 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (921/921 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-1320857 | col_h10_r2__t1 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (199/214 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (962/962 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (1047/1047 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (1647/1647 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (795/795 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-528316 | dsdv_slice_c1x_C__t4 | 3_1_place_gp_skip_io | 2.6 | overflow best 0.7163 last 0.7163 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (445/445 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (567/567 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (350/350 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (558/558 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 5_1_grt | 3.6 | last meaningful line 1.0 h ago (217/865 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (369/369 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (492/492 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (520/520 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-1646967 | slice_station__t24 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (213/213 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1539/1539 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (412/412 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (526/526 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (608/608 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (457/457 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (543/543 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1049/1049 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (441/441 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (435/435 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (527/527 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (457/457 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_1_grt | 6.1 | last meaningful line 1.2 h ago (219/905 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 7.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (292/292 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 3_3_place_gp | 6.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 2.5 | last meaningful line 0.0 h ago (486/486 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 2.6 | last meaningful line 0.1 h ago (482/482 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 2.6 | last meaningful line 0.1 h ago (471/471 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1-1701387 | eco_20261120_134605_3273412-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 3.7 | drt_violations best 128283 last 128283 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 5.2 | drt_violations best 968 last 968 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-203995 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7386 last 0.7386 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5464/5464 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3392/3392 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-24246 | cbn_q01 | 4_1_cts | 0.4 | last meaningful line -0.0 h ago (5964/5964 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5649/5650 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (185/185 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 5.0 | last meaningful line 3.3 h ago (198/205 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (450/450 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-3946520 | kv3_hgi_v8 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5116/5117 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-3997172 | kv3_hgi_v8 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5068/5068 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_io_cor_v1-86377 | kv3_io_cor_v1 | 3_3_place_gp | 0.4 | overflow best 0.2009 last 0.2009 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 8.6 | last meaningful line 0.3 h ago (15774/15774 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 8.6 | last meaningful line 0.3 h ago (15680/15680 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 6.4 | last meaningful line 0.5 h ago (15717/15717 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-native59-304297 | native59 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (4980/4980 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 9.1 | repair_Violations best 13150 last 13150 rows 101 | YOUNG: evidence 7.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-114116 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | pregrt_ff_hold | 0.5 | repair_Violations best 145 last 157 rows 19 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-serdes__t13-26511 | serdes__t13 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5326/5326 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-489474 | sle_sc_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2742/2742 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | generate_abstract | 6.4 | last meaningful line 0.2 h ago (244/244 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__cl95cd1d0c-520320 | slw_fe_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-476577 | slw_fe_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (508/508 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | pregrt_ff_hold | 0.3 | repair_TNS best 2516.35 last 2516.35 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (612/612 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-4184213 | slw_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.7628 last 0.7628 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-3970864 | slw_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.4162 last 0.4162 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (185/185 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (314/314 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | tt_setup_repair_grt | 4.5 | repair_Viol best 85 last 85 rows 8 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 11.3 |  | NO-DATA: no log found |  |
| epyc7 | so_423851_ff_37193 | so_423851_ff_37193 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_423851_tt_37193 | so_423851_tt_37193 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | 6_report | 13.8 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 39.7 |  | NO-DATA: no log found |  |
| epyc9 | cpr1930-col_A-663216 | cpr1930-col_A | 3_3_place_gp | 0.2 | overflow best 0.3477 last 0.3494 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | cpr1930-col_B-663046 | cpr1930-col_B | 3_3_place_gp | 0.2 | overflow best 0.285 last 0.2906 rows 6 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | postcts_gate_TT | 11.3 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 5_1_grt | 4.0 | last meaningful line 1.8 h ago (199/224 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | 5_1_grt | 4.0 | last meaningful line 2.0 h ago (199/225 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (199/202 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | 1_2_yosys | 3.4 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2091/2091 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (4746/4746 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 4.0 | last meaningful line 1.5 h ago (202/221 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t12-3735264 | serdes__t12 | 3_3_place_gp | 1.1 | overflow best 0.9046 last 0.9181 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-serdes__t1__clfe1f0815-3499205 | serdes__t1 | 3_3_place_gp | 1.3 | overflow best 0.8546 last 0.8789 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (1855/1855 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (1819/1819 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 3.9 | repair_TNS best 491.117 last 491.117 rows 10 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 4.9 | repair_TNS best 2036.2 last 2036.2 rows 4 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (377/377 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | postcts_gate_TT | 3.9 | last meaningful line 0.0 h ago (484/484 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 5.8 | last meaningful line 0.2 h ago (872/872 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 104.7 |  | NO-DATA: empty log |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2018480 | cbn_q00 | 5_1_grt | 1.5 | last meaningful line 0.5 h ago (206/221 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.8 | overflow best 0.2617 last 0.2667 rows 29 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 4_1_cts | 0.8 | last meaningful line -0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (98/98 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (195/195 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.8 | overflow best 0.4656 last 0.4656 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8538 last 0.8538 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.3955 last 0.3955 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.2097 last 0.2097 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (995/995 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (500/500 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (311/311 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (1220/1220 lines) | YOUNG: evidence 7.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 5.8 | last meaningful line 1.6 h ago (336/336 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (2468/2468 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-serdes__t4-3454937 | serdes__t4 | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 3_3_place_gp | 0.8 | overflow best 0.6582 last 0.6582 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (364/364 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 8.6 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 2.6 | last meaningful line 0.0 h ago (585/585 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 2.1 | last meaningful line 0.2 h ago (455/455 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 2.4 | last meaningful line 0.3 h ago (457/457 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 2.7 | last meaningful line 0.1 h ago (460/460 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 2_4_floorplan_pdn | 5.8 | last meaningful line 0.2 h ago (23/23 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-1993165 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 1.5 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 5.7 | last meaningful line 0.5 h ago (716/716 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | prd-eco_20261120_185032_3498280-i1-1846100 | eco_20261120_185032_3498280-i1 | 5_2_route | 1.6 | last meaningful line 0.5 h ago (247/248 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 1.0 | last meaningful line 0.2 h ago (253/254 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261120_194249_3446526-i1t-3450960 | eco_20261120_194249_3446526-i1t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_3794061_ff_47620 | so_3794061_ff_47620 | signoff | 0.6 |  | NO-DATA: empty log |  |
| intel1 | so_3794061_tt_47620 | so_3794061_tt_47620 | signoff | 0.6 |  | NO-DATA: empty log |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2140/2140 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 17.9 | last meaningful line 3.3 h ago (225/232 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 17.9 | last meaningful line 2.8 h ago (226/232 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (3378/3378 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (600/600 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (206/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (2858/2858 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (559/559 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (413/413 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (1912/1912 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (1987/1987 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (1962/1962 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (418/418 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (427/427 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (436/436 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 5_1_grt | 4.3 | repair_Remaining best 337087 last 337087 rows 76 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (402/402 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | reg_fanout | 4.3 |  | NO-DATA: empty log |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 4.2 | last meaningful line 0.0 h ago (663/663 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 4.8 | drt_violations best 5813 last 5813 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 4.4 | drt_violations best 5942 last 5942 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_2_route | 4.4 | drt_violations best 675 last 675 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 2.9 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 2.2 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-3733052-18313 | 3733052 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 33.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 13.8 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 5_1_grt | 4.0 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 30.7 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 25.8 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 20.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 13.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 67.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 43.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 44.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 22.9 | last meaningful line 0.0 h ago (11710/11710 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 24.0 | last meaningful line 0.0 h ago (12247/12247 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 11.4 | last meaningful line 0.0 h ago (6151/6151 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 12.6 | last meaningful line 0.0 h ago (887/887 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 12.6 | last meaningful line 0.0 h ago (7123/7123 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 11.4 | last meaningful line 0.0 h ago (5588/5588 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 25.8 | last meaningful line 0.0 h ago (13373/13373 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 26.3 | last meaningful line 0.0 h ago (13406/13406 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 7.5 | drt_violations best 421 last 421 rows 19 | before-window best 48990, window best 421 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 18.0 | last meaningful line 0.1 h ago (1428/1428 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (4871/4871 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 15.1 | last meaningful line 0.0 h ago (8343/8343 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 15.3 | last meaningful line 0.0 h ago (8638/8638 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 9.6 | last meaningful line 0.0 h ago (918/918 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 8.6 | last meaningful line 0.0 h ago (686/686 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (592/592 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_1_grt | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (5483/5483 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 9.9 | last meaningful line 0.0 h ago (680/680 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 11.2 | last meaningful line 0.0 h ago (5857/5857 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1191/1191 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1110/1110 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 20.7 | last meaningful line 0.0 h ago (11698/11698 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1249/1249 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1294/1294 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (1334/1334 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1134/1134 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1184/1184 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (1192/1192 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (1412/1412 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (892/892 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1041/1041 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (1324/1324 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1117/1117 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (1328/1328 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | 5_2_route | 13.8 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1086/1086 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (902/902 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (1098/1098 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1108/1108 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | 5_2_route | 13.8 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (1344/1344 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 11.1 | drt_violations best 48 last 49 rows 29 | before-window best 91026, window best 48 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1426/1426 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 12.6 | last meaningful line 0.0 h ago (1430/1430 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (2179/2179 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (1435/1435 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | 5_1_grt | 13.2 | last meaningful line 7.4 h ago (213/1556 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 23.8 | last meaningful line 0.0 h ago (12745/12745 lines) | PROGRESS: log still growing |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 9.5 | drt_violations best 1 last 1 rows 42 | before-window best 72611, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (6429/6429 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 4_1_cts | 1.5 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (6723/6723 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (6496/6496 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (6284/6284 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (6358/6358 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | 5_1_grt | 4.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 30.9 | last meaningful line 0.0 h ago (1844/1844 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 26.0 | last meaningful line 0.0 h ago (1566/1566 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 21.5 | last meaningful line 0.0 h ago (1618/1618 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_1_grt | 4.4 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
