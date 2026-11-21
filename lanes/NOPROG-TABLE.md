# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 06:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 4, 'GRT-LABEL': 38, 'YOUNG': 154, 'NO-DATA': 13, 'EXCLUDED': 7, 'KEEP': 2, 'PROGRESS': 27}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 22.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 35.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 35 | UNSIGNABLE (hub cancels after the report hour) |
| epyc2 | dpkit-slw_st_a_v2__cl9f076a5c-2303577 | slw_st_a_v2 | postcts_gate_FF | 3.5 | last meaningful line 0.0 h ago (55/55 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -333.62 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | tt_setup_repair | 3.3 | repair_Viol best 1306 last 1306 rows 5 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -384.31 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 5_1_grt | 10.7 | grt rounds 3 overflow 5:4856 -> 10:9992 -> 15:4800 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 20.7 | grt rounds 3 overflow 5:62877 -> 10:60664 -> 15:49761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 20.6 | grt rounds 3 overflow 5:50202 -> 10:43421 -> 15:40646 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 35.1 | grt rounds 4 overflow 5:8939 -> 10:4958 -> 15:3337 -> 20:2951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 24.3 | grt rounds 4 overflow 5:50575 -> 10:40510 -> 15:34729 -> 20:37772 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2298207 | sle_st_a_v1 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:514 -> 10:158 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 9.5 | grt rounds 6 overflow 5:6375 -> 10:5827 -> 15:5482 -> 20:5460 -> 25:8886 -> 30:7683 | GRT-LABEL: DESIGN-FAIL: overflow 5827 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 14.2 | grt rounds 3 overflow 5:87834 -> 10:75300 -> 15:146439 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 19.2 | grt rounds 3 overflow 5:61289 -> 10:75075 -> 15:79226 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_serdes-4080505 | hd_serdes | 5_1_grt | 1.2 | grt rounds 6 overflow 5:7936 -> 10:3283 -> 15:1164 -> 20:653 -> 25:675 -> 30:655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:51078 -> 10:49891 -> 15:39905 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:50865 -> 10:49002 -> 15:39825 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 18.3 | grt rounds 3 overflow 5:46510 -> 10:49541 -> 15:43557 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 14.3 | grt rounds 3 overflow 5:71046 -> 10:71036 -> 15:80466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 8.1 | grt rounds 2 overflow 5:91861 -> 10:71452 | GRT-LABEL: DESIGN-FAIL: overflow 71452 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 9.8 | grt rounds 4 overflow 5:41190 -> 10:38638 -> 15:36628 -> 20:38201 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:34201 -> 10:38247 -> 15:33126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1462158 | sle_st_a_v1 | 5_1_grt | 3.4 | grt rounds 4 overflow 5:357 -> 10:131 -> 15:61 -> 20:28 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:17764 -> 10:14131 -> 15:12398 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-3417959 | slw_st_a_v1 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:2687 -> 10:1973 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 10.7 | grt rounds 5 overflow 5:3694 -> 10:1682 -> 15:1467 -> 20:1263 -> 25:1744 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 22.3 | grt rounds 3 overflow 5:26937 -> 10:13431 -> 15:9000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-608839 | sle_st_a_v2 | 5_1_grt | 1.8 | grt rounds 2 overflow 5:5552 -> 10:3241 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2142214 | sle_st_a_v2 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:5970 -> 10:3207 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_st_a_v2__pv4242de79-2145962 | sle_st_a_v2 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:5695 -> 10:3247 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 33.0 | grt rounds 5 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 33.3 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:26039 -> 20:23529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-3246974 | slw_st_a_v1 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:2583 -> 10:1894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 5_1_grt | 10.3 | grt rounds 4 overflow 5:108182 -> 10:5739 -> 15:4546 -> 20:4559 | GRT-LABEL: DESIGN-FAIL: overflow 5739 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 10.3 | grt rounds 3 overflow 5:51463 -> 10:8161 -> 15:5636 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 5_1_grt | 10.1 | grt rounds 3 overflow 5:60653 -> 10:2745 -> 15:1916 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 15.8 | grt rounds 5 overflow 5:17839 -> 10:13916 -> 15:11809 -> 20:10993 -> 25:8231 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 10.8 | grt rounds 3 overflow 5:32854 -> 10:32007 -> 15:25741 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 32.1 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 13.5 | grt rounds 4 overflow 5:35006 -> 10:1235 -> 15:721 -> 20:1026 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 27.1 | grt rounds 2 overflow 5:60387 -> 10:47822 | GRT-LABEL: DESIGN-FAIL: overflow 47822 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 27.1 | grt rounds 2 overflow 5:61726 -> 10:48832 | GRT-LABEL: DESIGN-FAIL: overflow 48832 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 27.3 | grt rounds 6 overflow 5:11862 -> 10:11222 -> 15:10201 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 9.8 | drt_violations best 69258 last 69258 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 94229.2 last 94229.2 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 9.8 | last meaningful line 0.5 h ago (290/291 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | 5_2_route | 3.2 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-1963245 | dsdv_slice_c1x_C__t6 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.8341 last 0.846 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3390822 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.5 h ago (128/128 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1588170 | hd_lep0N | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (80/80 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (80/80 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5313/5313 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-1655344 | kv3_sys_c | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t13-1612665 | serdes__t13 | 3_1_place_gp_skip_io | 3.0 | overflow best 0.9318 last 0.9318 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_2_route | 12.0 | drt_violations best 99432 last 99432 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-345106 | slice_station__t36 | 5_1_grt | 3.9 | last meaningful line 1.2 h ago (205/673 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t6__cl0755c26e-1628176 | slice_station__t6 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | tt_setup_measure | 3.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | 5_2_route | 10.4 | drt_violations best 90815 last 90815 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 10.6 | drt_violations best 16045 last 16045 rows 10 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | eco-abs-1951010 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i2-420525 | eco_20261121_014354_2681516-i2 | 5_2_route | 0.9 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-residual-i2r-368752 | residual-i2r | 5_2_route | 3.9 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-col-h9-r2--t1--cl774acf45--pv11b6518d-grt-2847189 | col-h9-r2--t1--cl774acf45--pv11b6518d-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2301911 | col_h10_r1__t1 | 5_1_grt | 3.5 | last meaningful line 0.3 h ago (201/210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 3.4 | repair_TNS best 385714 last 385714 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t12-2447527 | serdes__t12 | 1_synth | 0.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-2383247 | serdes__t14 | synth_odb_v | 0.3 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t16-2549394 | serdes__t16 | 1_2_yosys | 0.2 | last meaningful line 0.2 h ago (319/319 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_2_route | 12.9 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_2_route | 12.8 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 4_1_cts | 3.5 | last meaningful line 0.1 h ago (5217/5217 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | postcts_gate_FF | 12.7 | last meaningful line 0.0 h ago (1165/1165 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_2_route | 15.0 | drt_violations best 90792 last 90792 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 6_report | 15.5 | last meaningful line 0.1 h ago (792/792 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | tt_setup_measure | 3.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t18-2457189 | slice_station__t18 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2094 last 0.2094 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slice_station__t45-2399834 | slice_station__t45 | 3_3_place_gp | 0.3 | overflow best 0.3216 last 0.3221 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | pregrt_ff_hold | 3.4 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_2_route | 13.4 | drt_violations best 86224 last 86224 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 5_2_route | 15.0 | drt_violations best 12946 last 12946 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 5_2_route | 13.4 | drt_violations best 96415 last 96415 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 6_report | 15.5 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 5_2_route | 15.3 | drt_violations best 16826 last 16826 rows 2 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 6_report | 15.0 | last meaningful line 0.1 h ago (895/895 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_2_route | 14.1 | drt_violations best 85069 last 85069 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_2_route | 15.3 | drt_violations best 69476 last 69476 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_2_route | 13.4 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (247/1009 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 3.1 | drt_violations best 8867 last 8867 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | prd-fin-1141280 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (748/748 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t7-3724475 | dsdv_slice_c1x_C__t7 | 4_1_cts | 4.7 | last meaningful line -0.0 h ago (2298/2298 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_host_e-4081959 | hd_host_e | 5_2_route | 1.2 | drt_violations best 32821 last 32821 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-kv3_io_cor_v1-232937 | kv3_io_cor_v1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (3374/3374 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 6.0 | last meaningful line 0.3 h ago (202/206 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | postcts_gate_FF | 9.8 | last meaningful line -0.0 h ago (32492/32492 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_2_route | 13.4 | drt_violations best 116511 last 116511 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_2_route | 13.4 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | 5_2_route | 9.6 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_2_route | 9.8 | drt_violations best 74258 last 74258 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 5_2_route | 13.4 | drt_violations best 75262 last 75262 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 3.4 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 20.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-1192474-63 | 1192474 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (105295/105295 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-1297562-29828 | 1297562 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261121_100942_929932-i1t-881383 | eco_20261121_100942_929932-i1t | 5_2_route | 3.8 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | so_1112771_ff_99037 | so_1112771_ff_99037 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_1112771_tt_99037 | so_1112771_tt_99037 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | ap-ageom-kw-kv3-hroot-grt-1786644 | kv3-hroot-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbx_q10__cl89936551_h-1010361 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.1769 last 0.1769 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | 5_2_route | 9.4 | drt_violations best 135189 last 135189 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 9.4 | drt_violations best 1304 last 1304 rows 6 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 9.4 | drt_violations best 1256 last 1256 rows 6 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t9-950441 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-1647793 | dsdv_slice_lepe_mu_LP__t2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7045 last 0.7045 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v5-1751492 | kv3_hgi_v5 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1421/1421 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2-3742293 | kv3_pv_v2 | 4_1_cts | 5.8 | last meaningful line 0.5 h ago (16072/16072 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2n-3736265 | kv3_pv_v2n | 4_1_cts | 5.8 | last meaningful line 0.2 h ago (10025/10025 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3-3744611 | kv3_pv_v3 | 3_5_place_dp | 5.8 | last meaningful line 0.3 h ago (140/140 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3743971 | kv3_pv_v3n | 3_5_place_dp | 5.8 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4-3749853 | kv3_pv_v4 | 4_1_cts | 5.8 | last meaningful line 0.0 h ago (99/99 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-3749196 | kv3_pv_v4n | 3_5_place_dp | 5.8 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5-3751877 | kv3_pv_v5 | 3_5_place_dp | 5.8 | last meaningful line 0.2 h ago (146/146 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5n-3751077 | kv3_pv_v5n | 3_5_place_dp | 5.8 | last meaningful line 0.1 h ago (108/108 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v7-3753752 | kv3_pv_v7 | 3_4_place_resized | 5.7 | last meaningful line 0.8 h ago (615/615 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 4532.36 last 4532.36 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-772752 | sle_ctl | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (235/235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5231/5231 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3225942 | sle_hc1 | 3_5_place_dp | 2.6 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4692/4692 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-1220503 | slice_station__t40 | tt_setup_keep | 0.4 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t51-719348 | slice_station__t51 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (233/233 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-1241781 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.3387 last 0.3387 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4986/4986 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 4_1_cts | 2.9 | last meaningful line 0.0 h ago (5123/5123 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (402/402 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__clf4365a62-1621494 | slw_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.0999 last 0.0999 rows 45 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-1572785-11947 | 1572785 | orfs_synth | 0.3 | last meaningful line 0.3 h ago (266/266 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-1663909-4032 | 1663909 | orfs_synth | 0.2 | last meaningful line 0.2 h ago (428/428 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 49.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-976874-9201 | 976874 | orfs_synth | 0.6 | last meaningful line 0.5 h ago (266/266 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | so_1520764_ff_37564 | so_1520764_ff_37564 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_1520764_tt_37564 | so_1520764_tt_37564 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-kv3-hub-Eo-dump-2962512 | kv3-hub-Eo-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-kv3-hub-Eo-grt-2962512 | kv3-hub-Eo-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-423778 | col_h10_r0_p4__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (205/207 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.7 | repair_TNS best 746451 last 746451 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.5 | repair_Viol best 223 last 223 rows 159 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-606014 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.8 | repair_TNS best 92883.1 last 92883.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.0 | repair_Remaining best 184908 last 184908 rows 100 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-2618359 | hd_ctl | 3_3_place_gp | 0.3 | overflow best 0.3004 last 0.3339 rows 99 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-hd_host_w-2146702 | hd_host_w | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (180/186 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N-1375034 | hd_lep0N | 3_3_place_gp | 1.3 | overflow best 0.5853 last 0.5853 rows 2 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-hd_serdes-2625867 | hd_serdes | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4634/4634 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-2995489 | hd_serdes | postcts_gate_TT | 3.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | pregrt_ff_hold | 2.9 | repair_TNS best 471985 last 471985 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v12-2850495 | kv3_pv_v12 | 3_5_place_dp | 5.8 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t1-3235040 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 329635 last 329635 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.5 | repair_Remaining best 348290 last 348290 rows 1 | YOUNG: evidence 4.2 h < 6 h |  |
| epyc9 | dpkit-serdes__t4-2371086 | serdes__t4 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-492382 | sle_ctl | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (8706/8706 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-86131 | sle_ctl | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (8592/8592 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (5344/5344 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3533 last 0.3533 rows 43 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-1095767 | sle_su_l1 | pregrt_ff_hold | 1.5 | repair_TNS best 949180 last 949180 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-slice_station__t36-616051 | slice_station__t36 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | generate_abstract | 13.4 | last meaningful line 0.2 h ago (553/553 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_2_route | 14.4 | drt_violations best 12637 last 12637 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_2_route | 14.4 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (4707/4707 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-2965992-12627 | 2965992 | probe3.client | 0.0 | last meaningful line 0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 5.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 5.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 5.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_2_route | 7.0 | drt_violations best 84216 last 84216 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_125224_4071554-i1t-1606220 | eco_20261121_125224_4071554-i1t | 5_2_route | 1.1 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 5_2_route | 10.3 | drt_violations best 107580 last 107580 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_2_route | 10.3 | drt_violations best 87555 last 87555 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_2_route | 11.0 | drt_violations best 87377 last 87377 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (199/205 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_2_route | 10.1 | last meaningful line 0.5 h ago (287/288 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | postcts_gate_FF | 10.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3458260 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 2.7 | last meaningful line 0.7 h ago (131/131 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | tt_setup_measure_grt | 12.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-serdes__t15__cla2127225-4147451 | serdes__t15 | postplace_setup | 2.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | 4_1_cts | 4.5 | last meaningful line 0.1 h ago (124/124 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_1_grt | 10.3 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 31344.1 last 31344.1 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_1_grt | 3.2 | last meaningful line 2.5 h ago (251/353 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1-967583 | eco_20261120_192428_3309571-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1-2282340 | eco_20261120_211023_313122-i1 | 5_2_route | 3.4 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-coll_core-1539857 | coll_core | 3_3_place_gp | 1.0 | overflow best 0.1134 last 0.1134 rows 43 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t31-1745043 | ot_s81sl_leaf__t31 | 3_3_place_gp | 0.8 | overflow best 0.6032 last 0.6032 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 5_2_route | 13.6 | drt_violations best 154522 last 154522 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 5_2_route | 13.6 | drt_violations best 149465 last 149465 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 5_2_route | 13.6 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | postcts_gate_TT | 13.6 | last meaningful line 0.1 h ago (1032/1032 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_3_fillcell | 13.6 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_2_route | 13.6 | last meaningful line 0.3 h ago (259/260 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1540109 | slw_fw_v1 | 3_3_place_gp | 1.0 | overflow best 0.0991 last 0.0991 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 5_2_route | 13.6 | drt_violations best 149962 last 149962 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 5_2_route | 13.6 | drt_violations best 154266 last 154266 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | postcts_gate_FF | 13.6 | last meaningful line 0.2 h ago (1258/1258 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | eco-abs-3042987 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (1029/1029 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1-1499386 | eco_20261120_162132_484876-i1 | 5_2_route | 6.2 | drt_violations best 9 last 9 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1-1056647 | eco_20261120_174547_3236169-i1 | 5_2_route | 4.2 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1-2653275 | eco_20261120_182729_483429-i1 | 5_2_route | 3.2 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | otc-1176755-3982 | 1176755 | asbuilt.yosys | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-1529811-17468 | 1529811 | asbuilt.yosys | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 30.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 22.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_1_grt | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_1_grt | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_1_grt | 6.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_1_grt | 6.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_1_grt | 6.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_2_route | 9.8 | drt_violations best 30 last 30 rows 17 | before-window best 148062, window best 30 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1088094 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 30 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-serdes__t15__cla3d02796-1334076 | serdes__t15 | 4_1_cts | 3.2 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-1345689 | slw_fe_v2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 16.7 | drt_violations best 87 last 414 rows 50 | before-window best 124, window best 87 | PROGRESS: drt_violations improved 29.8 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 27.2 | last meaningful line 0.9 h ago (1440/1440 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_2_route | 15.3 | drt_violations best 14822 last 14822 rows 2 | before-window best 92886, window best 14822 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 16.7 | drt_violations best 9588 last 9588 rows 15 | before-window best 21067, window best 9588 | PROGRESS: drt_violations improved 54.5 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 12.8 | drt_violations best 15044 last 15044 rows 10 | before-window best 116798, window best 15044 | PROGRESS: drt_violations improved 87.1 % in window |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2-1815357 | eco_20261120_134605_3273412-i2 | 5_2_route | 3.9 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-native59-304297 | native59 | pregrt_ff_hold | 9.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_2_route | 9.8 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 13.7 | drt_violations best 14441 last 14441 rows 13 | before-window best 38403, window best 14441 | PROGRESS: drt_violations improved 62.4 % in window |  |
| epyc7 | otc-3318552-10240 | 3318552 | 4_1_cts | 2.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 7.7 | repair_Violations best 0 last 0 rows 61 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 10.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_a_v1__cl67389ecd-1866893 | sle_st_a_v1 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | 5_1_grt | 2.9 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 5_2_route | 10.1 | drt_violations best 0 last 0 rows 15 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-2229034 | sle_stm_v2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 5_2_route | 13.6 | drt_violations best 2228 last 2228 rows 3 | before-window best 33356, window best 2228 | PROGRESS: drt_violations improved 93.3 % in window |  |
