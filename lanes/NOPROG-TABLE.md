# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 21:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-LABEL': 43, 'YOUNG': 207, 'NO-DATA': 6, 'KEEP': 4, 'EXCLUDED': 3, 'PROGRESS': 68}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | 5_1_grt | 4.3 | grt rounds 6 overflow 5:359 -> 10:243 -> 15:219 -> 20:198 -> 25:181 -> 30:182 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 30: 181 -> 182 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 28.4 | grt rounds 3 overflow 5:110819 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 24.8 | grt rounds 3 overflow 5:52450 -> 10:50446 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 13.9 | grt rounds 6 overflow 5:16689 -> 10:10032 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: overflow 10032 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 13.6 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 23.5 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 23.9 | grt rounds 6 overflow 5:6728 -> 10:2817 -> 15:2382 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 13.9 | grt rounds 4 overflow 5:54288 -> 10:47834 -> 15:40008 -> 20:41318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:74610 -> 10:60436 | GRT-LABEL: DESIGN-FAIL: overflow 60436 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 22.1 | grt rounds 4 overflow 5:26008 -> 10:17168 -> 15:15441 -> 20:14966 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 24.1 | grt rounds 4 overflow 5:79148 -> 10:67538 -> 15:55180 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 24.1 | grt rounds 5 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 -> 25:40097 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 32.7 | grt rounds 4 overflow 5:46983 -> 10:40238 -> 15:37035 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_1_grt | 2.4 | grt rounds 4 overflow 5:998 -> 10:763 -> 15:741 -> 20:704 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 5_1_grt | 9.9 | grt rounds 6 overflow 5:2761 -> 10:2433 -> 15:2287 -> 20:2095 -> 25:2087 -> 30:2077 | GRT-LABEL: DESIGN-FAIL: overflow 2433 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 16.3 | grt rounds 6 overflow 5:6798 -> 10:4941 -> 15:2610 -> 20:2287 -> 25:3051 -> 30:2207 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | 5_1_grt | 7.1 | grt rounds 1 overflow 5:7402 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_1_grt | 5.9 | grt rounds 6 overflow 5:7819 -> 10:3205 -> 15:1186 -> 20:653 -> 25:674 -> 30:655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 1.6 | grt rounds 3 overflow 5:46351 -> 10:38944 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: overflow 38944 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 1.5 | grt rounds 3 overflow 5:42154 -> 10:42391 -> 15:36226 | GRT-LABEL: DESIGN-FAIL: overflow 42391 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 34.5 | grt rounds 4 overflow 5:20926 -> 10:7287 -> 15:6367 -> 20:6089 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 22.0 | grt rounds 3 overflow 5:29589 -> 10:6636 -> 15:6011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 22.0 | grt rounds 3 overflow 5:59133 -> 10:59535 -> 15:50667 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 15.0 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 23.3 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 22.0 | grt rounds 4 overflow 5:41921 -> 10:44894 -> 15:44490 -> 20:47845 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 34.5 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48548 -> 20:49962 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 28.3 | grt rounds 3 overflow 5:70746 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 62.6 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 30.7 | grt rounds 4 overflow 5:49170 -> 10:53420 -> 15:44462 -> 20:46531 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 13.8 | grt rounds 3 overflow 5:26741 -> 10:13870 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 30.7 | grt rounds 4 overflow 5:32226 -> 10:18865 -> 15:17126 -> 20:16680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:54696 -> 10:6171 | GRT-LABEL: DESIGN-FAIL: overflow 6171 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 12.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | 5_1_grt | 1.8 | grt rounds 6 overflow 5:48103 -> 10:17709 -> 15:15585 -> 20:16567 -> 25:14112 -> 30:13066 | GRT-LABEL: DESIGN-FAIL: overflow 17709 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:24849 -> 10:18037 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 23.3 | grt rounds 4 overflow 5:27548 -> 10:10273 -> 15:5389 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:46455 -> 10:50347 -> 15:47470 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 32.4 | grt rounds 3 overflow 5:48908 -> 10:43065 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 24.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 24.3 | grt rounds 3 overflow 5:44318 -> 10:39317 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 23.6 | grt rounds 3 overflow 5:55450 -> 10:54127 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 19.1 | grt rounds 5 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (287/287 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_2_route | 4.3 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (376/376 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (315/315 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (516/516 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (422/422 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (204/205 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (309/309 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (285/285 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2072/2072 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.8 h ago (134/134 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-3316818 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.3 h ago (126/126 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 13.6 | last meaningful line 5.5 h ago (198/207 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (300/300 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (1974/1974 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1627/1627 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (893/893 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (390/390 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_2_route | 1.9 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1-3809500 | eco_20261120_185639_3224747-i1 | 5_2_route | 3.8 | drt_violations best 607 last 607 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1-102804 | eco_20261120_233525_2680444-i1 | 5_2_route | 1.1 | last meaningful line 0.3 h ago (261/262 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_021137_2680521-i1t-410323 | eco_20261121_021137_2680521-i1t | 5_2_route | 3.5 | drt_violations best 126076 last 126076 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (2022/2022 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (1519/1519 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1562/1562 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1645/1645 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-528316 | dsdv_slice_c1x_C__t4 | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (292/292 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (503/503 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (625/625 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (408/408 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_2_route | 7.1 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | postcts_gate_TT | 4.6 | last meaningful line -0.0 h ago (13449/13449 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (551/551 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (566/566 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | 5_1_grt | 7.5 | last meaningful line 0.2 h ago (1044/1076 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-1646967 | slice_station__t24 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (273/273 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (2139/2139 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (472/472 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (586/586 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (517/517 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (603/603 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1637/1637 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (500/500 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 5_1_grt | 7.1 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (587/587 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (517/517 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (443/443 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 8.4 | last meaningful line 0.0 h ago (269/270 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (352/352 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 1_synth | 3.5 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 3.6 | last meaningful line 0.0 h ago (633/633 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 3.6 | last meaningful line 0.0 h ago (621/621 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1-1701387 | eco_20261120_134605_3273412-i1 | 5_2_route | 3.0 | drt_violations best 328 last 328 rows 3 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 4.7 | drt_violations best 9541 last 9541 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 2.2 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-fin-1663436 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-sc-v2-grt-2128436 | sle-sc-v2-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-203995 | bk_sel__t2 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (372/372 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-24246 | cbn_q01 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | tt_setup_repair | 1.2 | repair_Violations best 41 last 191 rows 23 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551_h-1352700 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.1602 last 0.1602 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1098/1098 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 6.0 | last meaningful line 4.3 h ago (198/207 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 7.4 | last meaningful line 0.0 h ago (510/510 lines) | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 9.6 | last meaningful line 0.3 h ago (15778/15778 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 9.6 | last meaningful line 0.6 h ago (15684/15684 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 3_3_place_gp | 1.3 | overflow best 0.6759 last 0.6759 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 7.4 | last meaningful line 0.6 h ago (15719/15719 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-native59-304297 | native59 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5275/5275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-2004800 | ot_s81sl_leaf__t31 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8151 last 0.8295 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-114116 | ot_s81sl_leaf__t39 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1223391 | ot_s81sl_leaf__t39 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-26511 | serdes__t13 | 2_4_floorplan_pdn | 1.4 | last meaningful line 0.8 h ago (130/130 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t14-1210893 | serdes__t14 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (92/92 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t15__cla3d02796-1209421 | serdes__t15 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (92/92 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t2-910161 | serdes__t2 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.8607 last 0.8753 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5384/5384 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (283/283 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__cl95cd1d0c-520320 | slw_fe_v1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-476577 | slw_fe_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_1_grt | 5.2 | repair_Remaining best 308986 last 308986 rows 137 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (567/567 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 5_2_route | 7.4 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (374/374 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_c__cl19bb38ef-1029122 | slw_su_c | 3_3_place_gp | 0.7 | overflow best 0.2181 last 0.2181 rows 40 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-slw_su_c__cl92142dac-981697 | slw_su_c | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 5.5 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 12.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-1274539-5086 | 1274539 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | 3_3_place_gp | 1.2 | overflow best 0.3013 last 0.3013 rows 30 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (708/708 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (625/625 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (571/571 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (525/525 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (581/581 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (346/346 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-4193397 | coll_core | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (350/350 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-4168642 | ot_s81sl_leaf__t45 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-4159358 | slice_station__t37 | 5_1_grt | 1.2 | repair_Viol best 26 last 26 rows 22 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 40.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbn_q00__cl622f65d2-1991949 | cbn_q00 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | 5_2_route | 2.4 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (388/388 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (2681/2681 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (974/974 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 5.0 | repair_Remaining best 186006 last 186006 rows 9 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v1__cl7479a5ec-2241453 | sle_sc_v1 | 3_3_place_gp | 0.3 | overflow best 0.3724 last 0.3724 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_sc_v3-1495801 | sle_sc_v3 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_a_v1__cl67389ecd-2426431 | sle_st_a_v1 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2351039 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.4898 last 0.4956 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_su_c-1608544 | sle_su_c | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-2169241 | sle_su_l1 | 3_3_place_gp | 0.3 | overflow best 0.4669 last 0.4669 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2455/2455 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-2405020 | slice_station__t40 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.998 last 0.998 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2405596 | slice_station__t40 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9979 last 0.9979 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2419/2419 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1858017 | slw_fe_v1 | 3_3_place_gp | 0.5 | overflow best 0.4373 last 0.4373 rows 21 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 4.9 | repair_TNS best 3.49 last 3.49 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2212686 | slw_fe_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-1953943 | slw_fe_v2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7458 last 0.7458 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 5.9 | repair_TNS best 713.565 last 713.565 rows 8 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1544367 | slw_fw_v1 | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-2337581 | slw_hc1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_b_v1__cle6023ec2-2581094 | slw_st_b_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_su_l0__cl1a1c1f8f-2458913 | slw_su_l0 | 3_3_place_gp | 0.1 | overflow best 0.5382 last 0.5382 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 105.7 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1-1722084 | eco_20261120_185716_1464729-i1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (246/502 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2018480 | cbn_q00 | 5_1_grt | 2.5 | last meaningful line 0.2 h ago (260/312 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | 5_2_route | 13.0 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (3482/3482 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (610/610 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (688/688 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (695/695 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (1091/1091 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (456/456 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (3346/3346 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (3411/3411 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (276/276 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (324/324 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 3.1 | last meaningful line 1.2 h ago (131/131 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | 3_3_place_gp | 5.5 | overflow best 0.2636 last 0.2636 rows 38 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (440/440 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | 3_4_place_resized | 5.5 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (1581/1581 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (889/889 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 6.8 | last meaningful line 0.0 h ago (413/413 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (966/966 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (337/337 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 9.6 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 3.6 | last meaningful line 0.0 h ago (615/615 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 3.1 | last meaningful line 0.2 h ago (596/596 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 3.4 | last meaningful line 0.2 h ago (619/619 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 3.7 | last meaningful line 0.5 h ago (618/618 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 2.5 | last meaningful line 0.3 h ago (484/484 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_185032_3498280-i1-1846100 | eco_20261120_185032_3498280-i1 | 5_2_route | 2.6 | last meaningful line 0.4 h ago (255/256 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-eco_20261120_194249_3446526-i1t-3450960 | eco_20261120_194249_3446526-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1t-1859870 | eco_20261120_211023_313122-i1t | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (931/933 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2740/2740 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 18.9 | last meaningful line 4.3 h ago (225/233 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 18.9 | last meaningful line 3.8 h ago (226/233 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (659/659 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (548/548 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (619/619 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 5_1_grt | 5.4 | last meaningful line 1.5 h ago (228/955 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (473/473 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2512/2512 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2585/2585 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | postcts_gate_TT | 5.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (526/526 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2562/2562 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (478/478 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (487/487 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (496/496 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (576/576 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (462/462 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 2_4_floorplan_pdn | 5.3 | last meaningful line 0.2 h ago (22/22 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 5.8 | drt_violations best 5813 last 5813 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 5.4 | drt_violations best 5942 last 5942 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1-3186007 | eco_20261120_162140_2433056-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 3.9 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 3.2 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 34.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 31.7 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 21.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 14.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 68.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 44.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 45.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 23.9 | last meaningful line 0.0 h ago (12310/12310 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 25.0 | last meaningful line 0.0 h ago (12847/12847 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 12.4 | last meaningful line 0.0 h ago (6751/6751 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 13.6 | last meaningful line 0.0 h ago (947/947 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 13.6 | last meaningful line 0.0 h ago (7723/7723 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 12.4 | last meaningful line 0.0 h ago (6188/6188 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 26.8 | last meaningful line 0.0 h ago (13973/13973 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 27.3 | last meaningful line 0.0 h ago (14006/14006 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 8.5 | drt_violations best 159 last 159 rows 23 | before-window best 48990, window best 159 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1t-3571482 | eco_20261121_014354_2681516-i1t | 5_2_route | 4.0 | drt_violations best 0 last 0 rows 12 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 19.0 | last meaningful line 1.1 h ago (1428/1428 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 10.0 | last meaningful line 0.0 h ago (5461/5461 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (8943/8943 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 10.6 | last meaningful line 0.0 h ago (1030/1030 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 9.6 | last meaningful line 0.0 h ago (746/746 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (652/652 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_1_grt | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 10.0 | last meaningful line 0.0 h ago (6073/6073 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (740/740 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 10.1 | last meaningful line 0.0 h ago (5878/5878 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 12.2 | last meaningful line 0.0 h ago (6457/6457 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1266/1266 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 22.0 | last meaningful line 0.0 h ago (12448/12448 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1323/1323 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.2 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1369/1369 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | 5_2_route | 15.1 | drt_violations best 2033 last 2033 rows 6 | before-window best 136964, window best 2033 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1209/1209 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1259/1259 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | 5_2_route | 15.1 | drt_violations best 2044 last 2044 rows 6 | before-window best 136743, window best 2044 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 15.1 | last meaningful line 0.0 h ago (1487/1487 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (966/966 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1115/1115 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 11.5 | last meaningful line 0.0 h ago (1192/1192 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1161/1161 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (977/977 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (1173/1173 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 11.5 | last meaningful line 0.0 h ago (1183/1183 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | cpr2c2-col_C2-2177706 | cpr2c2-col_C2 | cpr_ab | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (2599/2599 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 12.1 | drt_violations best 35 last 35 rows 54 | before-window best 91026, window best 35 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | 5_2_route | 14.3 | drt_violations best 364 last 364 rows 5 | before-window best 151250, window best 364 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 13.6 | last meaningful line 0.0 h ago (1490/1490 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (2239/2239 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (1495/1495 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 14.2 | last meaningful line 0.0 h ago (7541/7541 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 24.5 | last meaningful line 0.0 h ago (13302/13302 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 24.8 | last meaningful line 0.0 h ago (13345/13345 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 6.8 | last meaningful line 0.0 h ago (883/883 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | 5_2_route | 12.9 | drt_violations best 483 last 483 rows 4 | before-window best 82677, window best 483 | PROGRESS: drt_violations improved 99.4 % in window |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (559/559 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (1460/1460 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (7096/7096 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (6884/6884 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 12.9 | last meaningful line 0.0 h ago (6958/6958 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 6.7 | last meaningful line 1.5 h ago (716/716 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 31.9 | last meaningful line 0.0 h ago (1904/1904 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 27.0 | last meaningful line 0.0 h ago (1625/1625 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 22.5 | last meaningful line 0.0 h ago (1677/1677 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (3978/3978 lines) | PROGRESS: log still growing |  |
