# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 05:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-LABEL': 49, 'YOUNG': 153, 'NO-DATA': 13, 'KEEP': 2, 'EXCLUDED': 5, 'PROGRESS': 22}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 34.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 34 | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_2_route | 12.6 | drt_violations best 54049 last 54049 rows 1 | before-window best 54049, window best 54049 | NO-PROGRESS: drt_violations best 54049 vs 54049 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 11.5 | grt rounds 6 overflow 5:4784 -> 10:1803 -> 15:1546 -> 20:1380 -> 25:1760 -> 30:1013 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | 5_1_grt | 31.1 | grt rounds 2 overflow 5:73344 -> 10:63335 | GRT-LABEL: DESIGN-FAIL: overflow 63335 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | 5_1_grt | 32.3 | grt rounds 3 overflow 5:54383 -> 10:54634 -> 15:70550 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 21.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 19.7 | grt rounds 3 overflow 5:62877 -> 10:60195 -> 15:49761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 19.6 | grt rounds 3 overflow 5:50202 -> 10:43421 -> 15:40646 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 39.9 | grt rounds 4 overflow 5:55847 -> 10:40235 -> 15:36916 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 34.1 | grt rounds 4 overflow 5:9414 -> 10:5163 -> 15:3337 -> 20:2951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 23.3 | grt rounds 4 overflow 5:50575 -> 10:40510 -> 15:34729 -> 20:37772 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2298207 | sle_st_a_v1 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:514 -> 10:158 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v1__clb036e152-2482353 | slw_st_a_v1 | 5_1_grt | 2.4 | grt rounds 3 overflow 5:6 -> 10:153 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v2__cl9f076a5c-2303577 | slw_st_a_v2 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:337 -> 10:106 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 8.5 | grt rounds 6 overflow 5:6375 -> 10:5827 -> 15:5482 -> 20:5460 -> 25:8886 -> 30:7683 | GRT-LABEL: DESIGN-FAIL: overflow 5827 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 13.2 | grt rounds 3 overflow 5:87834 -> 10:134399 -> 15:146439 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 18.2 | grt rounds 3 overflow 5:83767 -> 10:75075 -> 15:79226 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_serdes-4080505 | hd_serdes | 5_1_grt | 0.2 | grt rounds 6 overflow 5:7819 -> 10:3205 -> 15:1186 -> 20:653 -> 25:674 -> 30:655 | GRT-LABEL: DESIGN-FAIL: overflow 3205 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 7.6 | grt rounds 3 overflow 5:56566 -> 10:49891 -> 15:39905 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 7.6 | grt rounds 3 overflow 5:50865 -> 10:49002 -> 15:39825 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 17.3 | grt rounds 3 overflow 5:46954 -> 10:49745 -> 15:43557 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1938916 | ot_s81sl_leaf__t39 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:49932 -> 10:39149 -> 15:43598 | GRT-LABEL: DESIGN-FAIL: overflow 39149 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | 5_1_grt | 7.2 | grt rounds 3 overflow 5:47376 -> 10:38537 -> 15:33417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 13.3 | grt rounds 3 overflow 5:74124 -> 10:71036 -> 15:80466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3897522 | ot_s81sl_leaf__t39 | 5_1_grt | 6.3 | grt rounds 3 overflow 5:56824 -> 10:42171 -> 15:33727 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 8.8 | grt rounds 4 overflow 5:41190 -> 10:38976 -> 15:36628 -> 20:38201 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 8.8 | grt rounds 3 overflow 5:36298 -> 10:38247 -> 15:33126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1462158 | sle_st_a_v1 | 5_1_grt | 2.4 | grt rounds 3 overflow 5:357 -> 10:131 -> 15:165 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | 5_1_grt | 8.4 | grt rounds 5 overflow 5:597 -> 10:469 -> 15:188 -> 20:130 -> 25:33 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:17764 -> 10:14131 -> 15:12398 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 9.7 | grt rounds 4 overflow 5:3694 -> 10:1682 -> 15:1467 -> 20:1263 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_serdes-2995489 | hd_serdes | 5_1_grt | 2.0 | grt rounds 6 overflow 5:3975 -> 10:1860 -> 15:570 -> 20:555 -> 25:583 -> 30:574 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 21.3 | grt rounds 3 overflow 5:26937 -> 10:13137 -> 15:9000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2142214 | sle_st_a_v2 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:5970 -> 10:3207 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_st_a_v2__pv4242de79-2145962 | sle_st_a_v2 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:5695 -> 10:3247 | GRT-LABEL: DESIGN-FAIL: overflow 3247 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 32.0 | grt rounds 5 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 32.3 | grt rounds 4 overflow 5:34987 -> 10:30821 -> 15:26039 -> 20:23529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-3246974 | slw_st_a_v1 | 5_1_grt | 1.9 | grt rounds 2 overflow 5:2583 -> 10:1894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 5_1_grt | 9.3 | grt rounds 4 overflow 5:108182 -> 10:5739 -> 15:4546 -> 20:4559 | GRT-LABEL: DESIGN-FAIL: overflow 5739 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 9.3 | grt rounds 3 overflow 5:58379 -> 10:8161 -> 15:5636 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | 5_1_grt | 9.3 | grt rounds 2 overflow 5:76902 -> 10:9613 | GRT-LABEL: DESIGN-FAIL: overflow 9613 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_1_grt | 9.1 | grt rounds 4 overflow 5:65764 -> 10:184 -> 15:32 -> 20:11 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 5_1_grt | 9.1 | grt rounds 3 overflow 5:60653 -> 10:2745 -> 15:1939 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 14.8 | grt rounds 5 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:10993 -> 25:8231 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:33939 -> 10:32462 -> 15:25741 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 31.8 | grt rounds 4 overflow 5:50603 -> 10:41187 -> 15:38932 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 31.1 | grt rounds 3 overflow 5:56283 -> 10:53941 -> 15:50309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 12.5 | grt rounds 4 overflow 5:35006 -> 10:1235 -> 15:721 -> 20:1134 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 26.1 | grt rounds 2 overflow 5:60387 -> 10:47822 | GRT-LABEL: DESIGN-FAIL: overflow 47822 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 26.1 | grt rounds 2 overflow 5:61726 -> 10:48832 | GRT-LABEL: DESIGN-FAIL: overflow 48832 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 26.3 | grt rounds 6 overflow 5:12280 -> 10:11222 -> 15:13970 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 8.8 | drt_violations best 211425 last 211425 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_2_route | 8.8 | drt_violations best 25711 last 25711 rows 2 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 94229.2 last 94229.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 8.8 | last meaningful line 0.3 h ago (284/285 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | tt_setup_repair_grt | 2.2 | repair_Viol best 924 last 924 rows 55 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-1963245 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3390822 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 3_3_place_gp | 1.1 | overflow best 0.0981 last 0.0981 rows 50 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 5_1_grt | 9.7 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t13-1612665 | serdes__t13 | 2_4_floorplan_pdn | 2.0 | last meaningful line 1.5 h ago (130/130 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t15__cla3d02796-1334076 | serdes__t15 | 3_5_place_dp | 2.2 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-1602558 | serdes__t4 | 3_4_place_resized | 2.0 | repair_Remaining best 334610 last 334610 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_2_route | 11.0 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2491557 | sle_hc1 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-345106 | slice_station__t36 | 5_1_grt | 2.9 | last meaningful line 0.2 h ago (205/599 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (4622/4622 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | 5_2_route | 9.4 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 9.6 | drt_violations best 17057 last 17057 rows 8 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | otc-3263445-5692 | 3263445 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3263585-1329 | 3263585 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3263718-9964 | 3263718 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3263814-4580 | 3263814 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3263922-11421 | 3263922 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3263982-19330 | 3263982 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3277423-29725 | 3277423 | yosys3 | 1.0 | last meaningful line 0.0 h ago (240223/240223 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i2-1443445 | eco_20261120_233525_2680444-i2 | 5_2_route | 2.1 | drt_violations best 357 last 357 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | prd-fin-4030296 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-residual-i2r-368752 | residual-i2r | 5_2_route | 2.9 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 53578.3 last 53578.3 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 2.4 | repair_TNS best 385714 last 385714 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_2_route | 11.9 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_2_route | 11.8 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 4_1_cts | 2.5 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | postcts_gate_TT | 11.7 | last meaningful line 0.0 h ago (540/540 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_2_route | 14.0 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_2_route | 14.5 | drt_violations best 12346 last 12346 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | 4_1_cts | 2.3 | last meaningful line 0.1 h ago (4929/4929 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (5636/5636 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_2_route | 12.4 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 5_2_route | 14.0 | drt_violations best 86717 last 86717 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 5_2_route | 12.4 | drt_violations best 96415 last 96415 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_2_route | 14.3 | drt_violations best 92886 last 92886 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 5_2_route | 14.5 | drt_violations best 14070 last 14070 rows 2 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 5_2_route | 14.3 | drt_violations best 122050 last 122050 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | tt_setup_repair | 2.4 | repair_Remaining best 232784 last 232784 rows 137 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_2_route | 13.1 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_2_route | 14.3 | drt_violations best 69476 last 69476 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_2_route | 12.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 11.8 | drt_violations best 16539 last 16539 rows 8 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2-1815357 | eco_20261120_134605_3273412-i2 | 5_2_route | 2.9 | drt_violations best 16478 last 16478 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1-1137379 | eco_20261120_170022_4017640-i1 | 5_2_route | 6.0 | drt_violations best 2 last 2 rows 11 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2t-1141280 | eco_recover1120-i2t | 5_2_route | 6.0 | drt_violations best 3978 last 3978 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-3437769 | bk_sel__t2 | 3_3_place_gp | 1.0 | last meaningful line 0.3 h ago (21/21 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | 5_1_grt | 8.5 | last meaningful line 0.5 h ago (200/208 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t7-3724475 | dsdv_slice_c1x_C__t7 | 3_3_place_gp | 3.7 | overflow best 0.7506 last 0.7542 rows 15 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-hd_host_e-4081959 | hd_host_e | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (211/530 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 4_1_cts | 8.5 | last meaningful line 0.6 h ago (15606/15606 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 5.0 | repair_Violations best 16310 last 16347 rows 103 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 7.1 | last meaningful line 0.5 h ago (202/208 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | postcts_gate_TT | 8.8 | last meaningful line 0.1 h ago (1956/1956 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | tt_setup_repair | 2.4 | repair_Remaining best 315408 last 315408 rows 86 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_2_route | 8.8 | drt_violations best 76757 last 76757 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_2_route | 12.4 | drt_violations best 116511 last 116511 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_2_route | 12.4 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | 5_2_route | 8.6 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_2_route | 8.8 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 5_2_route | 12.4 | drt_violations best 75262 last 75262 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | postcts_gate_TT | 2.4 | last meaningful line 0.0 h ago (728/728 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 19.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261121_100942_929932-i1t-881383 | eco_20261121_100942_929932-i1t | 5_2_route | 2.8 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-slw-fe-v1--clfe325744--cldb4efe33-grt-561749 | slw-fe-v1--clfe325744--cldb4efe33-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-3625114 | cbn_q01 | 3_3_place_gp | 1.3 | overflow best 0.5153 last 0.517 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | 5_2_route | 8.4 | drt_violations best 135189 last 135189 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | postcts_gate_FF | 29.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 8.4 | drt_violations best 100396 last 100396 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 8.4 | drt_violations best 99683 last 99683 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | 5_2_route | 8.4 | drt_violations best 8638 last 8638 rows 3 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | 5_2_route | 8.4 | drt_violations best 8703 last 8703 rows 3 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | 5_2_route | 8.4 | drt_violations best 8703 last 8703 rows 3 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | 5_2_route | 8.4 | drt_violations best 10046 last 10046 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v1-3737021 | kv3_pv_v1 | 4_1_cts | 4.8 | last meaningful line 0.2 h ago (13319/13319 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2-3742293 | kv3_pv_v2 | 3_5_place_dp | 4.8 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2n-3736265 | kv3_pv_v2n | 3_5_place_dp | 4.8 | last meaningful line 0.1 h ago (108/108 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3-3744611 | kv3_pv_v3 | 3_4_place_resized | 4.8 | last meaningful line 0.2 h ago (736/736 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3743971 | kv3_pv_v3n | 3_4_place_resized | 4.8 | last meaningful line 0.2 h ago (730/730 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4-3749853 | kv3_pv_v4 | 3_5_place_dp | 4.8 | repair_Remaining best 723463 last 723463 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v4n-3749196 | kv3_pv_v4n | 3_4_place_resized | 4.8 | last meaningful line 0.2 h ago (697/697 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5-3751877 | kv3_pv_v5 | 3_4_place_resized | 4.8 | last meaningful line 0.2 h ago (648/648 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5n-3751077 | kv3_pv_v5n | 3_4_place_resized | 4.8 | last meaningful line 0.1 h ago (691/691 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v7-3753752 | kv3_pv_v7 | 3_3_place_gp | 4.7 | overflow best 0.099 last 0.099 rows 44 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 473699 last 473699 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3225942 | sle_hc1 | 3_3_place_gp | 1.6 | overflow best 0.2985 last 0.4062 rows 216 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3791681 | sle_hc2 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (386/386 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 3_3_place_gp | 1.9 | overflow best 0.1087 last 0.1087 rows 228 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-3417959 | slw_st_a_v1 | pregrt_ff_hold | 1.5 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 48.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbf_q00__cl870de686-604111 | cbf_q00 | 3_3_place_gp | 0.9 | overflow best 0.3665 last 0.3665 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 6_report | 19.8 | last meaningful line 0.0 h ago (382/382 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-423778 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 18698.1 last 18698.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-2147979 | col_h10_r1__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2939391 | dsdv_slice_c1x_C__t9 | 4_1_cts | 4.7 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_C__t1-2944273 | dsdv_slice_lepe_mu_C__t1 | 4_1_cts | 4.7 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.7 | repair_TNS best 746451 last 746451 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.5 | last meaningful line 0.5 h ago (226/1475 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-606014 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.0 | repair_Violations best 298 last 299 rows 75 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N-1375034 | hd_lep0N | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (80/80 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (5369/5369 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Eo-2936400 | kv3_hub_Eo | 3_4_place_resized | 2.0 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Wo-2840584 | kv3_hub_Wo | 4_1_cts | 4.8 | last meaningful line 0.3 h ago (6378/6378 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v12-2850495 | kv3_pv_v12 | 3_4_place_resized | 4.8 | last meaningful line 0.3 h ago (671/671 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t1-3235040 | ot_s81sl_kv_leaf__t1 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (2842/2842 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 11.5 | repair_Remaining best 348290 last 348290 rows 1 | YOUNG: evidence 3.2 h < 6 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-492382 | sle_ctl | 4_1_cts | 0.9 | last meaningful line 0.3 h ago (8650/8650 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-86131 | sle_ctl | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (8566/8566 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1414451 | sle_hc2 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (273/273 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-608839 | sle_st_a_v2 | pregrt_ff_hold | 0.8 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-1095767 | sle_su_l1 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t36-616051 | slice_station__t36 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4087/4087 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 6_report | 12.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_2_route | 13.4 | drt_violations best 82800 last 82800 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_2_route | 13.4 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_su_c__cl19bb38ef-676336 | slw_su_c | 3_4_place_resized | 0.8 | repair_Remaining best 37053 last 37053 rows 344 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 4.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 4.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_2_route | 6.0 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_125224_4071554-i1t-1606220 | eco_20261121_125224_4071554-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 5_2_route | 9.3 | drt_violations best 107580 last 107580 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_2_route | 9.3 | drt_violations best 87555 last 87555 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_2_route | 10.0 | drt_violations best 87377 last 87377 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 42259.4 last 42259.4 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 5_2_route | 9.1 | drt_violations best 826 last 826 rows 6 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_2_route | 9.1 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (2799/2799 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3458260 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.7 | last meaningful line 1.7 h ago (1/1 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-serdes__t15__cla2127225-4147451 | serdes__t15 | 3_1_place_gp_skip_io | 1.4 | overflow best 0.344 last 0.344 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | postplace_setup | 2.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | 3_5_place_dp | 3.5 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-85157 | slw_fe_v1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (5339/5339 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | tt_setup_measure | 2.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_1_grt | 2.2 | last meaningful line 1.5 h ago (251/353 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1-967583 | eco_20261120_192428_3309571-i1 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1-2282340 | eco_20261120_211023_313122-i1 | 5_2_route | 2.4 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-474231 | kv3_hgi_v1 | 3_3_place_gp | 0.8 | overflow best 0.0977 last 0.0977 rows 52 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 5_2_route | 12.6 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 5_2_route | 12.6 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | postcts_gate_FF | 12.6 | last meaningful line 0.0 h ago (477/477 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | tt_setup_repair_grt | 12.6 | repair_Viol best 95 last 95 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 5_2_route | 12.6 | drt_violations best 33356 last 33356 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | generate_abstract | 12.6 | last meaningful line 0.0 h ago (190/190 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_2_route | 12.6 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 5_2_route | 12.6 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 5_2_route | 12.6 | drt_violations best 154266 last 154266 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | postcts_gate_TT | 12.6 | last meaningful line 0.2 h ago (1275/1275 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_3_place_gp | 12.5 | overflow best 0.9819 last 0.9819 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | prd-count-p1_tc-1392033 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1-1499386 | eco_20261120_162132_484876-i1 | 5_2_route | 5.2 | drt_violations best 9 last 9 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1-1056647 | eco_20261120_174547_3236169-i1 | 5_2_route | 3.2 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1-2653275 | eco_20261120_182729_483429-i1 | 5_2_route | 2.2 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_1138910_ff_43415 | so_1138910_ff_43415 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | so_1138910_tt_43415 | so_1138910_tt_43415 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 29.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 21.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_1_grt | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_1_grt | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_1_grt | 5.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_1_grt | 5.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_1_grt | 5.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-1345689 | slw_fe_v2 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 15.7 | drt_violations best 87 last 218 rows 47 | before-window best 131, window best 87 | PROGRESS: drt_violations improved 33.6 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 26.2 | last meaningful line 1.6 h ago (1438/1438 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2301911 | col_h10_r1__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 5_2_route | 14.0 | drt_violations best 16877 last 16877 rows 3 | before-window best 143968, window best 16877 | PROGRESS: drt_violations improved 88.3 % in window |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 15.7 | drt_violations best 10156 last 10156 rows 14 | before-window best 117930, window best 10156 | PROGRESS: drt_violations improved 91.4 % in window |  |
| epyc7 | dpkit-native59-304297 | native59 | pregrt_ff_hold | 8.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | 5_2_route | 8.4 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 12.7 | drt_violations best 14441 last 14441 rows 13 | before-window best 124819, window best 14441 | PROGRESS: drt_violations improved 88.4 % in window |  |
| epyc7 | otc-3318552-10240 | 3318552 | 4_1_cts | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 6.7 | repair_Violations best 0 last 0 rows 61 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | 5_2_route | 8.4 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_2_route | 8.4 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-hd_host_w-2146702 | hd_host_w | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 9.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-3352856 | glue | 5_1_grt | 11.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | pregrt_ff_hold | 9.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-2229034 | sle_stm_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | tg2130-cts_terminal_pair_span_seeded-3880805 | tg2130-cts_terminal_pair_span_seeded | tg_cts | 1.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
