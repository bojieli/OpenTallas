# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 17:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'GRT-LABEL': 39, 'YOUNG': 231, 'NO-DATA': 12, 'KEEP': 9, 'EXCLUDED': 3, 'PROGRESS': 54}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (3254/3254 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -1491.99 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 24.4 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 20.8 | grt rounds 2 overflow 5:87024 -> 10:50446 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 9.9 | grt rounds 5 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 9.6 | grt rounds 3 overflow 5:46508 -> 10:46203 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 19.5 | grt rounds 4 overflow 5:27623 -> 10:16733 -> 15:13155 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 19.9 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:43983 -> 10:46937 -> 15:40008 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 18.1 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:15441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 20.1 | grt rounds 4 overflow 5:57640 -> 10:67281 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 20.1 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 28.7 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | phscan-4140488 | phscan | 5_1_grt | 0.3 | grt rounds 4 overflow 5:57640 -> 10:67281 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 12.3 | grt rounds 6 overflow 5:6798 -> 10:4941 -> 15:2610 -> 20:2287 -> 25:3051 -> 30:2207 | GRT-LABEL: DESIGN-FAIL: overflow 4941 at round 10 > 1000 |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | 5_1_grt | 6.0 | grt rounds 6 overflow 5:12227 -> 10:8336 -> 15:4776 -> 20:1436 -> 25:480 -> 30:459 | GRT-LABEL: DESIGN-FAIL: overflow 8336 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 4.1 | grt rounds 4 overflow 5:30377 -> 10:16662 -> 15:14043 -> 20:13888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 4.0 | grt rounds 3 overflow 5:38116 -> 10:38946 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 1.5 | grt rounds 6 overflow 5:727 -> 10:550 -> 15:542 -> 20:538 -> 25:186 -> 30:90 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 30.3 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 17.7 | grt rounds 3 overflow 5:29589 -> 10:6637 -> 15:5987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 17.7 | grt rounds 3 overflow 5:59583 -> 10:59412 -> 15:50422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 10.8 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 19.1 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20564 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 17.7 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 30.3 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48404 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 24.6 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 25.7 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 58.9 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 26.9 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 10.0 | grt rounds 3 overflow 5:31334 -> 10:16178 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 26.9 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 8.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 8.8 | grt rounds 3 overflow 5:24921 -> 10:17867 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 19.3 | grt rounds 4 overflow 5:27316 -> 10:11628 -> 15:6221 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 8.8 | grt rounds 3 overflow 5:48001 -> 10:50111 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 28.4 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 20.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 20.3 | grt rounds 3 overflow 5:43779 -> 10:38620 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 19.6 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 15.1 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-dsdv-slice-iq-C--t1-grt-3150268 | dsdv-slice-iq-C--t1-grt | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (496/496 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-bk_sel__t2-3066975 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.91 last 0.9657 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-cbf_q00__cl870de686-2936376 | cbf_q00 | 2_1_floorplan | 0.3 | repair_Viol best 1128 last 1128 rows 1196 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3105141 | col_h10_r0_p1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-2967333 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3506 last 0.3506 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2967143 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4198 last 0.4198 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2978644 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.421 last 0.421 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | 6_report | 8.3 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2950738 | col_h10_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.2411 last 0.2411 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl8b686b3e-2951245 | col_h10_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.212 last 0.2206 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | stage_odb_cap | 0.3 | last meaningful line 0.1 h ago (1345/1345 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-3187088 | col_h9_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 1253 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3218206 | col_h9_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 1187 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3222995 | col_h9_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 1163 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2941587 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9194 last 0.9205 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3120804 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9291 last 0.9291 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3064457 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8778 last 0.9073 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3352541 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 589 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3126619 | col_h9_r0_p3__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3270764 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 609 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3089382 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3051672 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9358 last 0.9358 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3368604 | col_h9_r0_p4__t1 | 2_1_floorplan | 0.1 | repair_Viol best 5231 last 5231 rows 823 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-2944201 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.615 last 0.615 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8544 last 0.8762 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 9.6 | last meaningful line 1.5 h ago (198/201 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.599 last 0.599 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 6_report | 21.1 | last meaningful line 0.1 h ago (989/989 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3235470-31032 | 3235470 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 4.5 | drt_violations best 2068 last 2068 rows 9 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 2.1 | drt_violations best 61156 last 61156 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1t-1628432 | eco_20261121_003008_2139459-i1t | 5_2_route | 1.2 | drt_violations best 42454 last 42454 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | prd-fin-735514 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (675/675 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_3523275_ff_48568 | so_3523275_ff_48568 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | so_3523275_tt_48568 | so_3523275_tt_48568 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | ap-ageom-kw-cbf-q00-s2-grt-3490948 | cbf-q00-s2-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (368/368 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-coll-core-grt-3293178 | coll-core-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-kv-leaf--t3-grt-3670891 | ot-s81sl-kv-leaf--t3-grt | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t59-grt-3305881 | ot-s81sl-leaf--t59-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (2838/2838 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | 1_synth | 0.0 | last meaningful line -0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cld01bb4ae-2550296 | col_h10_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 561374 last 561398 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 8.2 | drt_violations best 9518 last 9518 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (3071/3071 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 1.0 h ago (132/132 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | 1_2_yosys | 2.5 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.8 h ago (131/131 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | 1_2_yosys | 2.0 | last meaningful line 0.0 h ago (231/231 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-1636745 | gunit__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (496/496 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t1-3583234 | ot_s81sl_kv_leaf__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (106/106 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 6.6 | last meaningful line 0.0 h ago (602/602 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (507/507 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (413/413 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (2004/2004 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-3326726 | serdes__t14 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (313/313 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t16-3293794 | serdes__t16 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (319/319 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t1__clfe1f0815-3630425 | serdes__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (152/152 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4657/4657 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4905/4905 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4521/4522 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (194/195 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3856/3856 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5378/5379 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (329/329 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t25-3307284 | slice_station__t25 | 3_1_place_gp_skip_io | 0.2 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (5536/5536 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (348/348 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (430/430 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5008/5008 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (4505/4505 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (366/366 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (350/350 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (278/278 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (362/362 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (6006/6006 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (341/341 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | pregrt_ff_hold | 0.6 | repair_Violations best 41639 last 41639 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 3.0 | last meaningful line 0.2 h ago (761/761 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | port_bind | 6.8 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 6.0 | last meaningful line 0.5 h ago (858/858 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 3.1 | last meaningful line 0.0 h ago (476/476 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 2.5 | last meaningful line 0.5 h ago (456/456 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | eco-abs-3387491 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (332/332 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-1886341-12002 | 1886341 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 6.2 | drt_violations best 34 last 34 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_2_route | 3.9 | drt_violations best 23257 last 23257 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (265/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-3208392 | cbf_q00 | 3_3_place_gp | 1.2 | overflow best 0.2176 last 0.2176 rows 35 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-3976533 | cbn_q01 | 3_3_place_gp | 0.9 | overflow best 0.663 last 0.663 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (3683/3683 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3208672 | cbn_q01 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (168/168 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 2.0 | last meaningful line 0.3 h ago (198/199 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3830158 | hd_lep0N | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (11386/11386 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | tt_setup_repair | 1.9 | repair_Viol best 333 last 333 rows 208 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-2363517 | kv3_pv_v2 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (856/856 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 5.6 | last meaningful line 0.6 h ago (15715/15715 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 5.6 | last meaningful line 0.3 h ago (15621/15621 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 3.4 | last meaningful line 0.1 h ago (15097/15097 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 8.3 | last meaningful line 0.6 h ago (15761/15761 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-native59-2890501 | native59 | 3_3_place_gp | 1.5 | overflow best 0.2977 last 0.476 rows 172 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3490/3490 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | tt_setup_repair | 2.0 | repair_Violations best 5224 last 5224 rows 24 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (443/443 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3233970 | sle_st_b_v1 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5523/5523 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_2_route | 9.0 | drt_violations best 9912 last 9912 rows 2 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | 5_1_grt | 3.4 | repair_Remaining best 316729 last 316729 rows 86 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_2_route | 3.4 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5144/5144 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5177/5177 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-3208717 | slw_hc0 | 4_1_cts | 1.2 | last meaningful line 0.3 h ago (5306/5306 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3263016 | slw_st_b_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5263/5263 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-791387 | slw_stm_v1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (4724/4724 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 8.3 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | so_3872085_ff_46988 | so_3872085_ff_46988 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc7 | so_3872085_tt_46988 | so_3872085_tt_46988 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (1011/1011 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (930/930 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (1069/1069 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (1114/1114 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (954/954 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (1004/1004 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (712/712 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (861/861 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (937/937 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | 5_2_route | 10.8 | drt_violations best 13103 last 13103 rows 2 | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (906/906 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (918/918 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (928/928 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 6.7 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 36.7 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-gunit--t1-grt-1613804 | gunit--t1-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (740/740 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | tt_setup_repair_grt | 19.2 | repair_Viol best 390 last 390 rows 140 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 8.3 | drt_violations best 91026 last 91026 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 14646 last 14646 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (199/202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.5 h ago (125/125 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | sdc_lint | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 4_1_cts | 2.2 | last meaningful line -0.0 h ago (2892/2892 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-4082127 | hd_host_n | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (664/664 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t38-890997 | ot_s81sl_leaf__t38 | 3_3_place_gp | 0.6 | overflow best 0.5271 last 0.5433 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | tt_setup_repair | 1.3 | repair_Viol best 1303 last 1303 rows 237 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-1275480 | ot_s81sl_leaf__t40 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-3958052 | serdes__t15 | 3_1_place_gp_skip_io | 1.3 | overflow best 0.3706 last 0.3706 rows 40 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | tt_setup_repair_grt | 9.7 | repair_Remaining best 371495 last 371495 rows 84 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | postcts_gate_FF | 9.7 | last meaningful line 0.0 h ago (829/829 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3635/3635 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 1.2 | last meaningful line 0.1 h ago (237/243 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 2.1 | repair_TNS best 10148.2 last 10148.2 rows 6 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (214/214 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (5189/5189 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t6-1947287 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 2.2 | last meaningful line 0.1 h ago (457/457 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t3-1340352 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 3.0 | last meaningful line 0.0 h ago (543/543 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 101.9 |  | NO-DATA: empty log |  |
| epyc9 | otc-4021631-12869 | 4021631 | gen_lint_yosys | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 6.8 | drt_violations best 72611 last 72611 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | ap-ageom-kw-cbf-q01-grt-3416499 | cbf-q01-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-sle-ctl--cl503337ff--padE0-grt-3335384 | sle-ctl--cl503337ff--padE0-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-slw-fw-v3-grt-3342811 | slw-fw-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 8.9 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3373537 | col_h9_r0_p5__t1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-1492344 | coll_ftc | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 1.5 | last meaningful line 1.5 h ago (1/1 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.7 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 1.5 | last meaningful line 1.5 h ago (1/1 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (103/103 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (872/872 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (500/500 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.8 | last meaningful line 0.0 h ago (171/171 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t7-3312277 | ot_s81sl_leaf__t7 | 2_1_floorplan | 0.1 | last meaningful line -0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2480956 | sle_fe_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.3948 last 0.3948 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 20.8 | drt_violations best 81847 last 81847 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 21.5 | drt_violations best 13232 last 13232 rows 2 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 6_report | 21.5 | last meaningful line -0.0 h ago (900/900 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | postcts_gate_FF | 5.6 | last meaningful line 0.1 h ago (674/674 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 2.8 | last meaningful line 0.0 h ago (477/477 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 6.1 | last meaningful line 1.3 h ago (653/653 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 4.1 | last meaningful line 0.1 h ago (648/648 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.7 | last meaningful line 1.0 h ago (414/414 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | tt_setup_repair | 1.4 | repair_Viol best 1753 last 1753 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-361000 | col_h9_r0_p1__t1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 2.6 | last meaningful line 1.3 h ago (133/133 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 2.6 | last meaningful line 1.3 h ago (129/129 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | stage_odb_cap | 3.6 | last meaningful line 0.1 h ago (52/52 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | tt_setup_repair | 1.3 | repair_Viol best 667 last 667 rows 44 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 14.9 | last meaningful line 0.3 h ago (225/227 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 14.9 | last meaningful line 0.2 h ago (170/170 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-186299 | ot_s81sl_leaf__t24 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | pregrt_ff_hold | 3.6 | repair_Violations best 4188 last 4196 rows 52 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (423/423 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | tt_setup_repair | 1.3 | repair_Violations best 489 last 859 rows 52 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-162109 | serdes__t1 | 3_1_place_gp_skip_io | 1.4 | overflow best 0.4824 last 0.4824 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (5852/5852 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5584/5584 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | 6_report | 21.1 | last meaningful line 0.0 h ago (431/431 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5249/5249 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (216/216 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t25-270940 | slice_station__t25 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (346/346 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | tt_setup_measure | 1.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5029/5029 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5625/5625 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | pregrt_ff_hold | 1.3 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (5448/5448 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 1.3 | last meaningful line 0.0 h ago (352/352 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 2.6 | last meaningful line 0.0 h ago (489/489 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 3.6 | last meaningful line 0.0 h ago (623/623 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 1.2 | last meaningful line 0.0 h ago (294/294 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 1.4 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_1_grt | 1.4 | last meaningful line 0.5 h ago (232/1515 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | so_1092125_ff_92768 | so_1092125_ff_92768 | stage_odb_cap | 0.8 | last meaningful line 0.7 h ago (1222/1222 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | so_1092125_tt_92768 | so_1092125_tt_92768 | stage_odb_cap | 0.8 | last meaningful line 0.7 h ago (1222/1222 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | so_1262589_ff_95579 | so_1262589_ff_95579 | stage_odb_cap | 0.6 | last meaningful line 0.5 h ago (1230/1230 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | so_1262589_tt_95579 | so_1262589_tt_95579 | stage_odb_cap | 0.6 | last meaningful line 0.5 h ago (1230/1230 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | so_617331_ff_41679 | so_617331_ff_41679 | generate_abstract | 1.1 | last meaningful line 1.0 h ago (357/357 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | so_617331_tt_41679 | so_617331_tt_41679 | generate_abstract | 1.1 | last meaningful line 1.0 h ago (357/357 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | generate_abstract | 8.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 30.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 10.8 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 10.8 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | pregrt_ff_hold | 1.2 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 27.9 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 23.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 17.9 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 10.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 64.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 40.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 41.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (529/529 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | stage_odb_cap | 9.5 | last meaningful line 0.0 h ago (654/654 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 19.9 | last meaningful line 0.0 h ago (9910/9910 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 21.0 | last meaningful line 0.0 h ago (10447/10447 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 18.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (4361/4361 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 9.6 | last meaningful line 0.0 h ago (708/708 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 9.6 | last meaningful line 0.0 h ago (5323/5323 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (3798/3798 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 22.8 | last meaningful line 0.0 h ago (11573/11573 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 23.3 | last meaningful line 0.0 h ago (11606/11606 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 12.2 | drt_violations best 44 last 44 rows 15 | before-window best 1304, window best 44 | PROGRESS: drt_violations improved 96.6 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 15.0 | last meaningful line 0.4 h ago (1381/1381 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (6990/6990 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 12.1 | last meaningful line 0.0 h ago (6553/6553 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (501/501 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 8.3 | repair_TNS best 147771 last 147771 rows 7 | before-window best 151978, window best 147771 | PROGRESS: repair_TNS improved 2.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (4067/4067 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 26.8 | drt_violations best 10168 last 22918 rows 19 | before-window best 10389, window best 10168 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026 | dsdv_bksel_c_rfda3pt | 5_1_grt | 2.2 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 17.7 | last meaningful line 0.0 h ago (9908/9908 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1155/1155 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1013/1013 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1232/1232 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1144/1144 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (984/984 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1149/1149 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1110/1110 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1155/1155 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (937/937 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1164/1164 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 8.6 | last meaningful line 0.0 h ago (2374/2374 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 10.5 | last meaningful line 0.0 h ago (1262/1262 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1265/1265 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 10.0 | last meaningful line 0.0 h ago (2014/2014 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 10.0 | last meaningful line 0.0 h ago (1270/1270 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (5291/5291 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 20.8 | last meaningful line 0.0 h ago (11052/11052 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 21.0 | last meaningful line 0.0 h ago (11095/11095 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (4629/4629 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 8.8 | drt_violations best 9299 last 9299 rows 3 | before-window best 73630, window best 9299 | PROGRESS: drt_violations improved 87.4 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 8.9 | last meaningful line 0.0 h ago (4923/4923 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 9.4 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (575/575 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (4529/4529 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (4696/4696 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (4484/4484 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 8.9 | last meaningful line 0.0 h ago (4568/4568 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 8.8 | drt_violations best 2114 last 2114 rows 2 | before-window best 19623, window best 2114 | PROGRESS: drt_violations improved 89.2 % in window |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 27.9 | last meaningful line 0.0 h ago (1665/1665 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-182001 | col_h9_r0_p6__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 23.0 | last meaningful line 0.0 h ago (1387/1387 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 18.5 | last meaningful line 0.0 h ago (1438/1438 lines) | PROGRESS: log still growing |  |
