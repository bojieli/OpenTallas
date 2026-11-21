# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 21:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-LABEL': 44, 'YOUNG': 219, 'NO-DATA': 11, 'KEEP': 5, 'EXCLUDED': 3, 'PROGRESS': 62}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | 5_1_grt | 3.8 | grt rounds 6 overflow 5:359 -> 10:243 -> 15:219 -> 20:198 -> 25:181 -> 30:182 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 30: 181 -> 182 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 27.9 | grt rounds 3 overflow 5:110819 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 24.3 | grt rounds 3 overflow 5:52450 -> 10:50446 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 13.4 | grt rounds 6 overflow 5:16689 -> 10:10032 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: overflow 10032 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 13.1 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 23.0 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 23.4 | grt rounds 6 overflow 5:6728 -> 10:2817 -> 15:2382 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 13.4 | grt rounds 4 overflow 5:54288 -> 10:46937 -> 15:40008 -> 20:41318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:74610 -> 10:60436 | GRT-LABEL: DESIGN-FAIL: overflow 60436 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 21.6 | grt rounds 4 overflow 5:26008 -> 10:17168 -> 15:15441 -> 20:14966 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 23.6 | grt rounds 4 overflow 5:79148 -> 10:67538 -> 15:55180 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 23.6 | grt rounds 5 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 -> 25:40097 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 32.2 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 5_1_grt | 9.4 | grt rounds 6 overflow 5:2761 -> 10:2433 -> 15:2287 -> 20:2095 -> 25:2087 -> 30:2077 | GRT-LABEL: DESIGN-FAIL: overflow 2433 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | 5_1_grt | 6.6 | grt rounds 1 overflow 5:7402 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | 5_1_grt | 9.5 | grt rounds 6 overflow 5:3688 -> 10:2561 -> 15:2268 -> 20:1901 -> 25:1852 -> 30:1871 | GRT-LABEL: DESIGN-FAIL: overflow 2561 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_1_grt | 5.4 | grt rounds 6 overflow 5:7819 -> 10:3205 -> 15:1186 -> 20:653 -> 25:674 -> 30:655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | 5_1_grt | 6.9 | grt rounds 3 overflow 5:49203 -> 10:42518 -> 15:36551 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 1.1 | grt rounds 3 overflow 5:46351 -> 10:38944 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: overflow 38944 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 1.0 | grt rounds 3 overflow 5:43490 -> 10:42391 -> 15:36226 | GRT-LABEL: DESIGN-FAIL: overflow 42391 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 34.0 | grt rounds 4 overflow 5:20926 -> 10:7287 -> 15:6367 -> 20:6089 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 21.5 | grt rounds 3 overflow 5:29589 -> 10:6636 -> 15:6011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 21.5 | grt rounds 3 overflow 5:59133 -> 10:59535 -> 15:50667 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 14.5 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 22.8 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 21.5 | grt rounds 4 overflow 5:41921 -> 10:44894 -> 15:44490 -> 20:47845 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 34.0 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48548 -> 20:49962 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 5_1_grt | 4.8 | grt rounds 6 overflow 5:667 -> 10:490 -> 15:482 -> 20:368 -> 25:198 -> 30:45 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | 5_1_grt | 4.8 | grt rounds 6 overflow 5:667 -> 10:490 -> 15:482 -> 20:368 -> 25:198 -> 30:45 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 28.1 | grt rounds 3 overflow 5:70746 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 62.4 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 30.4 | grt rounds 4 overflow 5:49170 -> 10:53420 -> 15:44462 -> 20:46531 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 13.5 | grt rounds 3 overflow 5:26741 -> 10:13870 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 30.4 | grt rounds 4 overflow 5:32226 -> 10:18865 -> 15:17126 -> 20:16680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 12.3 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | 5_1_grt | 1.3 | grt rounds 6 overflow 5:18796 -> 10:17709 -> 15:15585 -> 20:16567 -> 25:14112 -> 30:13066 | GRT-LABEL: DESIGN-FAIL: overflow 17709 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 12.3 | grt rounds 3 overflow 5:24849 -> 10:18037 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 22.8 | grt rounds 4 overflow 5:27548 -> 10:10273 -> 15:5389 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 12.3 | grt rounds 3 overflow 5:46455 -> 10:50347 -> 15:47470 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 31.9 | grt rounds 3 overflow 5:48908 -> 10:43065 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 23.8 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 23.8 | grt rounds 3 overflow 5:44318 -> 10:39317 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 23.1 | grt rounds 3 overflow 5:55450 -> 10:54127 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 18.6 | grt rounds 5 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_2_route | 3.8 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (346/346 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (285/285 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (3007/3007 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (239/239 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1772/1772 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-3316818 | dsdv_slice_c1x_C__t7 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 3_3_place_gp | 1.9 | overflow best 0.3714 last 0.3714 rows 31 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 13.1 | last meaningful line 5.0 h ago (198/206 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-4062983 | kv3_hub_Eo | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1176/1176 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1674/1674 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1337/1337 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (5105/5105 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (920/920 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (360/360 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1-3809500 | eco_20261120_185639_3224747-i1 | 5_2_route | 3.3 | drt_violations best 607 last 607 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1-102804 | eco_20261120_233525_2680444-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (255/256 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1t-3571482 | eco_20261121_014354_2681516-i1t | 5_2_route | 3.5 | drt_violations best 76 last 76 rows 6 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_021137_2680521-i1t-410323 | eco_20261121_021137_2680521-i1t | 5_2_route | 3.0 | drt_violations best 126076 last 126076 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1722/1722 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-1320857 | col_h10_r2__t1 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (1395/1395 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1262/1262 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1347/1347 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (1850/1850 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-528316 | dsdv_slice_c1x_C__t4 | 3_3_place_gp | 3.1 | overflow best 0.6753 last 0.6753 rows 26 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (473/473 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (595/595 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (588/588 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (424/424 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (521/521 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (536/536 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (550/550 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-1646967 | slice_station__t24 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (243/243 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (1839/1839 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_1_grt | 4.7 | last meaningful line 0.3 h ago (241/249 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (556/556 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (487/487 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (573/573 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1337/1337 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (470/470 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (465/465 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (557/557 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (487/487 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (569/569 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (415/415 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (322/322 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 3_3_place_gp | 6.5 | overflow best 0.8255 last 0.8255 rows 36 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 3.0 | last meaningful line 0.3 h ago (612/612 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 3.1 | last meaningful line 0.0 h ago (557/557 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 3.1 | last meaningful line 0.0 h ago (546/546 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1-1701387 | eco_20261120_134605_3273412-i1 | 5_2_route | 2.5 | drt_violations best 14967 last 14967 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 4.2 | drt_violations best 128283 last 128283 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slw-st-b-v2--pva66d0f22--pvb80e2003-grt-1408922 | slw-st-b-v2--pva66d0f22--pvb80e2003-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-203995 | bk_sel__t2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5532/5532 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-24246 | cbn_q01 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (6009/6009 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5862/5862 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551_h-1352700 | cbx_q10 | 2_1_floorplan | 0.1 | repair_Viol best 847 last 847 rows 105 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 5.5 | last meaningful line 3.8 h ago (198/206 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-3946520 | kv3_hgi_v8 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5331/5331 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-3997172 | kv3_hgi_v8 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5131/5131 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_io_cor_v1-86377 | kv3_io_cor_v1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 9.1 | last meaningful line 0.8 h ago (15774/15774 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 9.1 | last meaningful line 0.1 h ago (15684/15684 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.8528 last 0.8528 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 6.9 | last meaningful line 0.1 h ago (15719/15719 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-native59-304297 | native59 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5213/5213 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 9.6 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-114116 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.8 | overflow best 0.527 last 0.5297 rows 20 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1223391 | ot_s81sl_leaf__t39 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9178 last 0.9178 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-serdes__t13-26511 | serdes__t13 | 2_4_floorplan_pdn | 0.9 | last meaningful line 0.3 h ago (130/130 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t14-1210893 | serdes__t14 | 1_2_yosys | 0.1 | last meaningful line 0.1 h ago (313/313 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t15__cla3d02796-1209421 | serdes__t15 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (319/319 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t2-910161 | serdes__t2 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5380/5380 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-489474 | sle_sc_v2 | 3_3_place_gp | 0.6 | overflow best 0.2201 last 0.3031 rows 38 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-992384 | sle_st_a_v1 | 3_3_place_gp | 0.3 | overflow best 0.4982 last 0.4982 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_1_grt | 1.0 | last meaningful line 0.4 h ago (222/853 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3106/3106 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__cl95cd1d0c-520320 | slw_fe_v1 | 3_3_place_gp | 0.6 | overflow best 0.3189 last 0.3189 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-476577 | slw_fe_v2 | 3_3_place_gp | 0.6 | overflow best 0.3071 last 0.3071 rows 29 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (358/358 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (537/537 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (641/641 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clb036e152-782740 | slw_st_a_v1 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-973300 | slw_st_a_v1 | 3_3_place_gp | 0.3 | overflow best 0.3527 last 0.363 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-1135463 | slw_st_a_v2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.758 last 0.8333 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_1_grt | 1.0 | repair_Remaining best 306068 last 306068 rows 126 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_c__cl19bb38ef-1029122 | slw_su_c | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_c__cl92142dac-981697 | slw_su_c | stage_odb_cap | 0.3 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 5.0 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 11.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-1274539-5086 | 1274539 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_423851_ff_37193 | so_423851_ff_37193 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (1028/1028 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | so_423851_tt_37193 | so_423851_tt_37193 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (1028/1028 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-dsdv-slice-c1x-C--t10-grt-558020 | dsdv-slice-c1x-C--t10-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (678/678 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (670/670 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (549/549 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (597/597 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (541/541 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (495/495 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (551/551 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (375/375 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-4193397 | coll_core | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | pregrt_ff_hold | 0.7 | repair_Violations best 83 last 155 rows 95 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-4168642 | ot_s81sl_leaf__t45 | pregrt_ff_hold | 0.7 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | 5_1_grt | 0.7 | repair_Remaining best 121177 last 121177 rows 86 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-slice_station__t37-4159358 | slice_station__t37 | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (183/185 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 40.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-dsdv-slice-c3x-C--t1-grt-2216853 | dsdv-slice-c3x-C--t1-grt | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (476/476 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-r2-c1x-t1-grt-2030352 | r2-c1x-t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | cpr2c2-col_C2-2177706 | cpr2c2-col_C2 | cpr_ab | 0.0 | last meaningful line 0.0 h ago (2824/2824 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-cbn_q00__cl622f65d2-1991949 | cbn_q00 | 2_1_floorplan | 0.2 | repair_Viol best 1241 last 1241 rows 338 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | tt_setup_repair_grt | 2.1 | repair_Viol best 2250 last 2250 rows 63 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | 5_2_route | 13.5 | drt_violations best 151250 last 151250 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (302/302 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | 3_3_place_gp | 4.7 | overflow best 0.3754 last 0.3754 rows 35 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | 3_1_place_gp_skip_io | 4.1 | overflow best 0.4018 last 0.4018 rows 34 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (2531/2531 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 2.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 4.8 | last meaningful line 2.3 h ago (202/226 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t12-3735264 | serdes__t12 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v1__cl7479a5ec-2241453 | sle_sc_v1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (216/216 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v3-1495801 | sle_sc_v3 | 3_3_place_gp | 0.5 | overflow best 0.1932 last 0.1932 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-1958656 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.5159 last 0.5159 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-sle_st_a_v2__pv4242de79-1729446 | sle_st_a_v2 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_c-1608544 | sle_su_c | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6807 last 0.6807 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-2169241 | sle_su_l1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2305/2305 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (2269/2269 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1858017 | slw_fe_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 4.7 | last meaningful line 3.5 h ago (268/1456 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2212686 | slw_fe_v1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (382/382 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-1953943 | slw_fe_v2 | 2_2_floorplan_macro | 0.2 | last meaningful line -0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 5.6 | repair_TNS best 978.309 last 978.309 rows 4 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (421/421 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1544367 | slw_fw_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8213 last 0.8213 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 105.4 |  | NO-DATA: empty log |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2018480 | cbn_q00 | 5_1_grt | 2.0 | last meaningful line 1.0 h ago (206/230 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 4_1_cts | 1.3 | last meaningful line -0.0 h ago (3103/3103 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 4_1_cts | 1.3 | repair_Violations best 32 last 48 rows 19 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (791/791 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 3_3_place_gp | 1.1 | overflow best 0.445 last 0.445 rows 4 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 3_3_place_gp | 1.1 | overflow best 0.3304 last 0.3429 rows 33 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | 3_3_place_gp | 1.1 | overflow best 0.2297 last 0.2297 rows 39 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (294/294 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 2.6 | last meaningful line 0.7 h ago (131/131 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | sdc_lint | 1.5 | last meaningful line 1.5 h ago (1/1 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | 3_3_place_gp | 5.0 | overflow best 0.7595 last 0.7609 rows 5 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | 3_3_place_gp | 5.2 | overflow best 0.6386 last 0.6386 rows 25 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1281/1281 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (175/177 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 6.3 | last meaningful line 0.0 h ago (345/345 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | pregrt_ff_hold | 1.8 | repair_Violations best 9897 last 9897 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 3_4_place_resized | 1.3 | repair_Remaining best 251013 last 251013 rows 166 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (651/651 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 9.1 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 3.1 | last meaningful line 0.3 h ago (589/589 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 2.6 | last meaningful line 0.5 h ago (455/455 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 2.9 | last meaningful line 0.0 h ago (470/470 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 3.2 | last meaningful line 0.1 h ago (618/618 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | stage_odb_cap | 6.3 | last meaningful line 0.2 h ago (40/40 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 2.0 | last meaningful line 0.0 h ago (457/457 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 6.2 | last meaningful line 1.0 h ago (716/716 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_185032_3498280-i1-1846100 | eco_20261120_185032_3498280-i1 | 5_2_route | 2.1 | last meaningful line 0.4 h ago (251/252 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_194249_3446526-i1t-3450960 | eco_20261120_194249_3446526-i1t | 5_2_route | 1.2 | last meaningful line 0.2 h ago (256/257 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | so_3794061_ff_47620 | so_3794061_ff_47620 | signoff | 1.1 |  | NO-DATA: empty log |  |
| intel1 | so_3794061_tt_47620 | so_3794061_tt_47620 | signoff | 1.1 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | 5_1_grt | 4.9 | repair_Viol best 580 last 580 rows 11 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2440/2440 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 18.4 | last meaningful line 3.8 h ago (225/232 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 18.4 | last meaningful line 3.3 h ago (226/232 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (630/630 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (518/518 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 5_1_grt | 4.9 | last meaningful line 0.7 h ago (229/861 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (458/458 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (443/443 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2212/2212 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | pregrt_ff_hold | 4.9 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2410/2410 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (730/759 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2262/2262 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (448/448 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (457/457 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (466/466 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (546/546 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 2_1_floorplan | 4.8 | last meaningful line 0.1 h ago (90/90 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 5.3 | drt_violations best 5813 last 5813 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 4.9 | drt_violations best 5942 last 5942 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 3.4 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 2.7 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | prd-fin-160659 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 34.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 5_1_grt | 4.7 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 31.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 21.4 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 14.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 68.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 44.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 45.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 23.4 | last meaningful line 0.0 h ago (12010/12010 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 24.5 | last meaningful line 0.0 h ago (12547/12547 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (6451/6451 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (917/917 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (7423/7423 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (5888/5888 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 26.3 | last meaningful line 0.0 h ago (13673/13673 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 26.8 | last meaningful line 0.0 h ago (13706/13706 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 8.0 | drt_violations best 169 last 169 rows 22 | before-window best 48990, window best 169 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 18.5 | last meaningful line 0.6 h ago (1428/1428 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | 5_1_grt | 9.5 | last meaningful line 0.0 h ago (511/515 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 15.6 | last meaningful line 0.0 h ago (8643/8643 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (8938/8938 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 10.1 | last meaningful line 0.0 h ago (972/972 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (716/716 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (622/622 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (550/550 lines) | PROGRESS: log still growing |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 5.7 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (710/710 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (6157/6157 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1236/1236 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 21.5 | last meaningful line 0.0 h ago (12148/12148 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1294/1294 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1339/1339 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (1379/1379 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1179/1179 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1229/1229 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | 5_2_route | 14.6 | drt_violations best 16312 last 16312 rows 3 | before-window best 136743, window best 16312 | PROGRESS: drt_violations improved 88.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (1457/1457 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (937/937 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1086/1086 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 11.0 | last meaningful line 0.0 h ago (1162/1162 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1131/1131 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (947/947 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (1143/1143 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 11.0 | last meaningful line 0.0 h ago (1153/1153 lines) | PROGRESS: log still growing |  |
| epyc9 | cpr1930-col_C-1360461 | cpr1930-col_C | cpr_ab | 0.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 12.1 | last meaningful line 0.0 h ago (2584/2584 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 11.8 | drt_violations best 39 last 39 rows 48 | before-window best 91026, window best 39 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 14.0 | last meaningful line 0.0 h ago (1471/1471 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (1475/1475 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 13.5 | last meaningful line 0.0 h ago (2224/2224 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 13.9 | last meaningful line 0.0 h ago (7391/7391 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 24.3 | last meaningful line 0.0 h ago (13152/13152 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 24.5 | last meaningful line 0.0 h ago (13195/13195 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 6.5 | last meaningful line 0.8 h ago (872/872 lines) | PROGRESS: log still growing |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1-1722084 | eco_20261120_185716_1464729-i1 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 12.5 | last meaningful line 0.0 h ago (6729/6729 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | 4_1_cts | 1.3 | repair_Violations best 0 last 0 rows 7 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 12.4 | last meaningful line 0.0 h ago (7023/7023 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (529/529 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (1340/1340 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (6796/6796 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (6584/6584 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 12.4 | last meaningful line 0.0 h ago (6658/6658 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 31.4 | last meaningful line 0.0 h ago (1874/1874 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 26.5 | last meaningful line 0.0 h ago (1596/1596 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 22.0 | last meaningful line 0.0 h ago (1647/1647 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 7.1 | last meaningful line 0.0 h ago (3678/3678 lines) | PROGRESS: log still growing |  |
