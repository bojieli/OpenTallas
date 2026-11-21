# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 04:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'GRT-LABEL': 47, 'YOUNG': 184, 'NO-DATA': 12, 'KEEP': 2, 'EXCLUDED': 7, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | tt_setup_repair_grt | 22.5 | repair_Remaining best 11838 last 11838 rows 118 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -725.34 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 10.5 | grt rounds 5 overflow 5:4784 -> 10:1803 -> 15:1546 -> 20:1380 -> 25:1760 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | 5_1_grt | 30.1 | grt rounds 2 overflow 5:73344 -> 10:63335 | GRT-LABEL: DESIGN-FAIL: overflow 63335 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | 5_1_grt | 31.3 | grt rounds 3 overflow 5:54383 -> 10:54634 -> 15:70550 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 20.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:27938 -> 10:20130 -> 15:13125 -> 20:11071 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 18.7 | grt rounds 3 overflow 5:62592 -> 10:60195 -> 15:49761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | 5_1_grt | 8.7 | grt rounds 3 overflow 5:63064 -> 10:57996 -> 15:49395 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 18.6 | grt rounds 3 overflow 5:50202 -> 10:43421 -> 15:40646 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 38.9 | grt rounds 4 overflow 5:55847 -> 10:40235 -> 15:36916 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 33.1 | grt rounds 4 overflow 5:9414 -> 10:5163 -> 15:3337 -> 20:2951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 33.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 22.3 | grt rounds 3 overflow 5:50575 -> 10:40510 -> 15:34729 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 7.5 | grt rounds 6 overflow 5:6375 -> 10:5827 -> 15:5482 -> 20:5460 -> 25:8886 -> 30:7683 | GRT-LABEL: DESIGN-FAIL: overflow 5827 at round 10 > 1000 |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | 5_1_grt | 6.4 | grt rounds 3 overflow 5:20901 -> 10:21344 -> 15:20413 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 12.2 | grt rounds 3 overflow 5:87834 -> 10:134399 -> 15:146439 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 17.2 | grt rounds 3 overflow 5:83767 -> 10:75075 -> 15:79226 | GRT-LABEL: DESIGN-FAIL: overflow 75075 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 6.6 | grt rounds 3 overflow 5:56566 -> 10:49891 -> 15:39905 | GRT-LABEL: DESIGN-FAIL: overflow 49891 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 6.6 | grt rounds 3 overflow 5:57966 -> 10:49002 -> 15:39825 | GRT-LABEL: DESIGN-FAIL: overflow 49002 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 16.3 | grt rounds 3 overflow 5:46675 -> 10:49745 -> 15:43557 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1938916 | ot_s81sl_leaf__t39 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:49932 -> 10:39149 | GRT-LABEL: DESIGN-FAIL: overflow 39149 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:46001 -> 10:38537 -> 15:33417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 12.3 | grt rounds 3 overflow 5:74124 -> 10:72264 -> 15:80466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3897522 | ot_s81sl_leaf__t39 | 5_1_grt | 5.3 | grt rounds 3 overflow 5:58007 -> 10:41023 -> 15:33727 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 7.8 | grt rounds 4 overflow 5:38551 -> 10:38976 -> 15:36628 -> 20:38201 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 7.8 | grt rounds 3 overflow 5:36298 -> 10:38247 -> 15:33847 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | 5_1_grt | 7.4 | grt rounds 4 overflow 5:597 -> 10:469 -> 15:188 -> 20:130 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 7.4 | grt rounds 3 overflow 5:17764 -> 10:14131 -> 15:12515 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 29.6 | grt rounds 5 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 -> 25:36016 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 8.7 | grt rounds 4 overflow 5:3694 -> 10:1682 -> 15:1467 -> 20:1311 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_serdes-2995489 | hd_serdes | 5_1_grt | 1.0 | grt rounds 3 overflow 5:3975 -> 10:23216 -> 15:17501 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 20.3 | grt rounds 3 overflow 5:27194 -> 10:13137 -> 15:9484 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 31.0 | grt rounds 5 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 31.3 | grt rounds 4 overflow 5:30207 -> 10:30821 -> 15:26039 -> 20:23529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:108182 -> 10:5739 -> 15:4546 | GRT-LABEL: DESIGN-FAIL: overflow 5739 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:58379 -> 10:9469 -> 15:5636 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_1_grt | 8.1 | grt rounds 4 overflow 5:65764 -> 10:184 -> 15:32 -> 20:11 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 5_1_grt | 8.1 | grt rounds 3 overflow 5:60653 -> 10:2621 -> 15:1939 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 13.8 | grt rounds 4 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:10993 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 8.8 | grt rounds 3 overflow 5:33939 -> 10:32462 -> 15:25641 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 30.8 | grt rounds 4 overflow 5:50603 -> 10:41187 -> 15:38869 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 30.1 | grt rounds 3 overflow 5:56283 -> 10:53941 -> 15:50309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 11.5 | grt rounds 4 overflow 5:35006 -> 10:1235 -> 15:721 -> 20:1134 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 25.1 | grt rounds 2 overflow 5:60387 -> 10:47822 | GRT-LABEL: DESIGN-FAIL: overflow 47822 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 25.1 | grt rounds 2 overflow 5:61726 -> 10:48832 | GRT-LABEL: DESIGN-FAIL: overflow 48832 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 25.3 | grt rounds 6 overflow 5:24897 -> 10:17088 -> 15:13970 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | 5_1_grt | 28.8 | grt rounds 3 overflow 5:74839 -> 10:73559 -> 15:66169 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 5_1_grt | 11.6 | grt rounds 3 overflow 5:41481 -> 10:43965 -> 15:39210 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 7.8 | drt_violations best 211425 last 211425 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_2_route | 7.8 | drt_violations best 148062 last 148062 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.1 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 7.8 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-1963245 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_n-2434743 | hd_host_n | 5_2_route | 0.6 | last meaningful line 0.1 h ago (229/230 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1633659 | hd_lep0N | 3_3_place_gp | 1.0 | last meaningful line 0.3 h ago (178/178 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 2_1_floorplan | 0.1 | repair_Viol best 3186 last 3186 rows 409 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t52-3043381 | ot_s81sl_leaf__t52 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8948 last 0.9212 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-serdes__t13-1612665 | serdes__t13 | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.5 h ago (130/130 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t15__cla3d02796-1334076 | serdes__t15 | 3_1_place_gp_skip_io | 1.2 | overflow best 0.5975 last 0.5975 rows 34 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-1602558 | serdes__t4 | 3_1_place_gp_skip_io | 1.0 | overflow best 0.9287 last 0.9294 rows 19 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_2_route | 10.0 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2491557 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.6506 last 0.6506 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_sc_v3-2491265 | sle_sc_v3 | 3_3_place_gp | 0.5 | overflow best 0.0991 last 0.0991 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slice_station__t36-345106 | slice_station__t36 | tt_setup_repair | 1.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-2453536 | slice_station__t51 | 3_3_place_gp | 0.6 | overflow best 0.2524 last 0.2618 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-1345689 | slw_fe_v2 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (4134/4134 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 3_5_place_dp | 1.2 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | 5_2_route | 8.4 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 8.6 | drt_violations best 21316 last 21316 rows 4 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (3673/3673 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1711598-631 | 1711598 | equiv | 1.0 | last meaningful line 0.0 h ago (792800/792800 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i2-1443445 | eco_20261120_233525_2680444-i2 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i2t-4030296 | eco_20261121_014354_2681516-i2t | 5_2_route | 2.3 | drt_violations best 42292 last 42292 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-residual-i2r-368752 | residual-i2r | 5_2_route | 1.9 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2301911 | col_h10_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 25016.8 last 25016.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3406/3406 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 1.4 | repair_TNS best 385714 last 385714 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-2464568 | sle_ctl | 3_4_place_resized | 1.4 | repair_Remaining best 193877 last 193877 rows 112 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_2_route | 10.9 | last meaningful line 0.0 h ago (270/270 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_2_route | 10.8 | last meaningful line 0.2 h ago (264/264 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 3_3_place_gp | 1.5 | overflow best 0.2044 last 0.2044 rows 273 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2298207 | sle_st_a_v1 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (206/216 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 5_1_grt | 10.7 | last meaningful line 0.0 h ago (1263/1263 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_2_route | 13.0 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_2_route | 13.5 | drt_violations best 81088 last 81088 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | 3_3_place_gp | 1.3 | overflow best 0.0998 last 0.0998 rows 50 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5238/5238 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_2_route | 11.4 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 5_2_route | 13.0 | drt_violations best 86717 last 86717 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 5_2_route | 11.4 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_2_route | 13.3 | drt_violations best 92886 last 92886 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 5_2_route | 13.5 | drt_violations best 100791 last 100791 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 5_2_route | 13.3 | drt_violations best 122050 last 122050 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (4676/4676 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 5_2_route | 13.0 | drt_violations best 22552 last 22552 rows 2 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clb036e152-2482353 | slw_st_a_v1 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__cl9f076a5c-2303577 | slw_st_a_v2 | 5_1_grt | 1.5 | repair_Remaining best 112209 last 112209 rows 26 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_2_route | 12.1 | last meaningful line 0.2 h ago (262/262 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | hold_gate | 1.4 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_2_route | 13.3 | drt_violations best 69476 last 69476 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_2_route | 11.4 | last meaningful line 0.2 h ago (261/261 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 10.8 | drt_violations best 21478 last 21478 rows 4 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2-1815357 | eco_20261120_134605_3273412-i2 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1-1137379 | eco_20261120_170022_4017640-i1 | 5_2_route | 5.0 | drt_violations best 67 last 67 rows 6 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 1.1 | last meaningful line 0.2 h ago (263/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2t-1141280 | eco_recover1120-i2t | 5_2_route | 5.0 | drt_violations best 3978 last 3978 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | so_4076121_ff_54363 | so_4076121_ff_54363 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_4076121_tt_54363 | so_4076121_tt_54363 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | 5_1_grt | 7.5 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t7-3724475 | dsdv_slice_c1x_C__t7 | 1_2_yosys | 2.7 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 4_1_cts | 7.5 | last meaningful line 0.8 h ago (15604/15604 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 6.1 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | tt_setup_repair_grt | 7.8 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5466/5466 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1462158 | sle_st_a_v1 | 5_1_grt | 1.4 | last meaningful line 0.3 h ago (204/210 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_2_route | 7.8 | drt_violations best 76757 last 76757 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | 5_2_route | 7.4 | drt_violations best 57070 last 57070 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_2_route | 11.4 | last meaningful line 0.5 h ago (288/289 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_2_route | 11.4 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | postcts_gate_FF | 7.6 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_2_route | 7.8 | last meaningful line 0.4 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 5_2_route | 11.4 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 18.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-3318552-10240 | 3318552 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1t-881383 | eco_20261121_100942_929932-i1t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | tg_cts | 5.7 | repair_Violations best 81 last 110 rows 17 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-3625114 | cbn_q01 | 2_1_floorplan | 0.3 | repair_Viol best 1128 last 1128 rows 781 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p1__t1__pv697f40c9-2930737 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.8 | overflow best 0.1986 last 0.1986 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | 5_2_route | 7.4 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 28.2 | repair_Viol best 2054 last 2054 rows 949 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 17.2 | repair_Viol best 1026 last 1026 rows 758 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 7.4 | drt_violations best 100396 last 100396 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 7.4 | drt_violations best 99683 last 99683 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | 5_2_route | 7.4 | drt_violations best 81412 last 81412 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | 5_2_route | 7.4 | drt_violations best 81345 last 81345 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | 5_2_route | 7.4 | drt_violations best 81345 last 81345 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | 5_2_route | 7.4 | drt_violations best 81345 last 81345 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | 5_2_route | 7.4 | drt_violations best 83701 last 83701 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-hd_host_e-3219616 | hd_host_e | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi-3684423 | kv3_hgi | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (476/476 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v1-3737021 | kv3_pv_v1 | 3_5_place_dp | 3.8 | last meaningful line 0.1 h ago (108/108 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2-3742293 | kv3_pv_v2 | 3_4_place_resized | 3.8 | last meaningful line 0.1 h ago (664/664 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2n-3736265 | kv3_pv_v2n | 3_3_place_gp | 3.8 | overflow best 0.0996 last 0.0996 rows 43 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3-3744611 | kv3_pv_v3 | 3_3_place_gp | 3.8 | overflow best 0.0977 last 0.0977 rows 43 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3743971 | kv3_pv_v3n | 3_3_place_gp | 3.8 | overflow best 0.1982 last 0.2526 rows 34 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4-3749853 | kv3_pv_v4 | 3_3_place_gp | 3.8 | overflow best 0.0994 last 0.0994 rows 43 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-3749196 | kv3_pv_v4n | 3_3_place_gp | 3.8 | overflow best 0.0998 last 0.0998 rows 43 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5-3751877 | kv3_pv_v5 | 3_3_place_gp | 3.8 | overflow best 0.0941 last 0.0941 rows 41 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5n-3751077 | kv3_pv_v5n | 3_3_place_gp | 3.8 | overflow best 0.0991 last 0.0991 rows 43 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v7-3753752 | kv3_pv_v7 | 3_3_place_gp | 3.7 | overflow best 0.2011 last 0.2071 rows 35 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-3375912 | sle_hc0 | 3_3_place_gp | 0.5 | overflow best 0.6477 last 0.6477 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3225942 | sle_hc1 | 3_3_place_gp | 0.6 | overflow best 0.6522 last 0.6522 rows 29 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3791681 | sle_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-3241503 | sle_su_l1 | 3_3_place_gp | 0.6 | overflow best 0.0996 last 0.0996 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_2_route | 7.4 | drt_violations best 19055 last 19055 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3497231 | slice_station__t6 | 3_3_place_gp | 0.4 | overflow best 0.3109 last 0.3109 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3671746 | slw_fe_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 3_3_place_gp | 0.9 | overflow best 0.3039 last 0.3478 rows 48 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3006639 | slw_hc3 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-3417959 | slw_st_a_v1 | 3_5_place_dp | 0.5 | last meaningful line -0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 47.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 7.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 7.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 7.4 |  | NO-DATA: no log found |  |
| epyc8 | so_3755382_ff_46997 | so_3755382_ff_46997 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_3755382_tt_46997 | so_3755382_tt_46997 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-1970468 | cbf_q00 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-2147979 | col_h10_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 14804.7 last 14804.7 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2939391 | dsdv_slice_c1x_C__t9 | 3_3_place_gp | 3.7 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3000844 | dsdv_slice_c3x_C__t1 | 4_1_cts | 3.7 | last meaningful line 0.1 h ago (3506/3506 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_C__t1-2944273 | dsdv_slice_lepe_mu_C__t1 | 3_3_place_gp | 3.7 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (5422/5422 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.5 | repair_TNS best 175458 last 175458 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.0 | repair_TNS best 215095 last 215095 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_w-2146702 | hd_host_w | pregrt_ff_hold | 1.5 | repair_TNS best 91140.4 last 91140.4 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 3_3_place_gp | 0.9 | overflow best 0.0981 last 0.0981 rows 50 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_hub_Eo-2936400 | kv3_hub_Eo | 3_1_place_gp_skip_io | 1.0 | overflow best 0.4136 last 0.4136 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_hub_Wo-2840584 | kv3_hub_Wo | 3_5_place_dp | 3.8 | last meaningful line 0.3 h ago (112/112 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v12-2850495 | kv3_pv_v12 | 3_3_place_gp | 3.8 | overflow best 0.0995 last 0.0995 rows 43 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t1-3235040 | ot_s81sl_kv_leaf__t1 | 3_3_place_gp | 0.9 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 10.5 | repair_Remaining best 348290 last 348290 rows 1 | YOUNG: evidence 2.2 h < 6 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-86131 | sle_ctl | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3138115 | sle_hc0 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2142214 | sle_st_a_v2 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (203/211 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_a_v2__pv4242de79-2145962 | sle_st_a_v2 | 5_1_grt | 1.5 | last meaningful line 0.5 h ago (203/212 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | generate_abstract | 11.5 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_2_route | 11.4 | drt_violations best 81923 last 81923 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_2_route | 12.4 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | tt_setup_measure_grt | 12.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_2_route | 5.0 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_111032_3330019-i1t-3416789 | eco_20261121_111032_3330019-i1t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_2_route | 8.3 | drt_violations best 87555 last 87555 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_2_route | 9.0 | drt_violations best 87377 last 87377 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 2151 last 2151 rows 14 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 5_2_route | 8.1 | drt_violations best 17236 last 17236 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | 5_1_grt | 8.3 | last meaningful line 1.0 h ago (209/218 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_2_route | 8.1 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | 3_3_place_gp | 0.6 | overflow best 0.4324 last 0.4492 rows 26 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3458260 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | 5_1_grt | 10.5 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-1702648 | serdes__t14 | 3_3_place_gp | 1.7 | overflow best 0.6753 last 0.6753 rows 31 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-serdes__t15__cla2127225-4147451 | serdes__t15 | 1_2_yosys | 0.4 | last meaningful line 0.3 h ago (316/316 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | 3_1_place_gp_skip_io | 1.3 | overflow best 0.7303 last 0.7303 rows 29 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | 3_4_place_resized | 2.5 | last meaningful line 0.2 h ago (458/458 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-2229034 | sle_stm_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (4645/4645 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | 6_report | 8.8 | last meaningful line 0.1 h ago (374/374 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-85157 | slw_fe_v1 | 3_2_place_iop | 0.3 | last meaningful line -0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3816939 | slw_hc3 | 3_3_place_gp | 0.6 | overflow best 0.1951 last 0.1951 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3836392 | slw_hc3 | 3_3_place_gp | 0.6 | overflow best 0.1936 last 0.1936 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5936/5936 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-3486279 | tt_ctlm | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-2831293 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (251/353 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1-2282340 | eco_20261120_211023_313122-i1 | 5_1_grt | 1.4 | last meaningful line 0.6 h ago (233/1218 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | tg2130-cts_terminal_followers-2825975 | tg2130-cts_terminal_followers | tg_cts | 1.1 | repair_Violations best 376 last 376 rows 18 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | tg2130-cts_terminal_pair_span_seeded-3880805 | tg2130-cts_terminal_pair_span_seeded | tg_cts | 0.5 | repair_Violations best 363 last 686 rows 28 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 5_2_route | 11.6 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | postcts_gate_TT | 11.6 | last meaningful line 0.0 h ago (496/496 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 5_1_grt | 11.6 | last meaningful line 2.3 h ago (222/1189 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_3_fillcell | 11.6 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t40__clc8fb2c8c-62880 | slice_station__t40 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_2_route | 11.6 | drt_violations best 54049 last 54049 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 5_2_route | 11.6 | drt_violations best 33356 last 33356 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 5_2_route | 11.6 | drt_violations best 1529 last 1529 rows 2 | YOUNG: evidence 6.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | postcts_gate_TT | 11.6 | last meaningful line -0.0 h ago (73469/73469 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 5_2_route | 11.6 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 5_2_route | 11.6 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | postcts_gate_FF | 11.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_1_place_gp_skip_io | 11.5 | overflow best 0.2105 last 0.3108 rows 453 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1-1392033 | eco_20261120_155439_476619-i1 | 5_2_route | 4.2 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1-1499386 | eco_20261120_162132_484876-i1 | 5_2_route | 4.2 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1-1056647 | eco_20261120_174547_3236169-i1 | 5_2_route | 2.2 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1-2653275 | eco_20261120_182729_483429-i1 | 5_1_grt | 1.2 | last meaningful line 0.3 h ago (234/1269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | so_3779725_ff_75162 | so_3779725_ff_75162 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_3779725_tt_75162 | so_3779725_tt_75162 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 28.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-992030 | sle_ctl | 4_1_cts | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-4037404-26825 | 4037404 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 20.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_1_grt | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_1_grt | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_1_grt | 4.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_1_grt | 4.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_1_grt | 4.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | pregrt_ff_hold | 8.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | otc-1304968-10705 | 1304968 | 4_1_cts | 1.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 14.7 | drt_violations best 87 last 243 rows 45 | before-window best 153, window best 87 | PROGRESS: drt_violations improved 43.1 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 25.2 | last meaningful line 0.6 h ago (1438/1438 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 16.8 | last meaningful line 1.3 h ago (1398/1398 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 14.7 | drt_violations best 10948 last 10948 rows 13 | before-window best 117930, window best 10948 | PROGRESS: drt_violations improved 90.7 % in window |  |
| epyc7 | dpkit-native59-304297 | native59 | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 11.7 | drt_violations best 15574 last 15574 rows 12 | before-window best 124819, window best 15574 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 4_1_cts | 0.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-2637667-13664 | 2637667 | 4_1_cts | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_2_route | 18.8 | drt_violations best 28 last 31 rows 26 | before-window best 219997, window best 28 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 8.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-3246974 | slw_st_a_v1 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 13.3 | last meaningful line 0.0 h ago (1080/1080 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | pregrt_ff_hold | 8.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | otc-3903570-18186 | 3903570 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | tg2130-cts_fixed_5294-2231613 | tg2130-cts_fixed_5294 | tg_cts | 1.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
