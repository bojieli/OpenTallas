# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 17:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 4, 'NO-PROGRESS': 3, 'GRT-LABEL': 38, 'YOUNG': 214, 'NO-DATA': 11, 'KEEP': 9, 'EXCLUDED': 3, 'PROGRESS': 64}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | postcts_gate_FF | 5.0 | last meaningful line 0.0 h ago (16/16 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -600.63 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2903/2903 lines) | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -446.29 ps (< -300, gate TT >= -42); job age 5. | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (3235/3235 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -687.56 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2804/2804 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -1491.99 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 8.0 | drt_violations best 73630 last 73630 rows 1 | before-window best 73630, window best 73630 | NO-PROGRESS: drt_violations best 73630 vs 73630 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 19.8 | drt_violations best 76548 last 76548 rows 1 | before-window best 76548, window best 76548 | NO-PROGRESS: drt_violations best 76548 vs 76548 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 21.2 | drt_violations best 144324 last 144324 rows 1 | before-window best 144324, window best 144324 | NO-PROGRESS: drt_violations best 144324 vs 144324 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 23.7 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 20.0 | grt rounds 2 overflow 5:87024 -> 10:50446 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 9.1 | grt rounds 5 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:46508 -> 10:46073 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 18.8 | grt rounds 4 overflow 5:24414 -> 10:16733 -> 15:13155 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 19.1 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 9.1 | grt rounds 3 overflow 5:43983 -> 10:46937 -> 15:39542 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t30-921459 | ot_s81sl_leaf__t30 | 5_1_grt | 19.6 | grt rounds 6 overflow 5:32680 -> 10:26052 -> 15:21293 -> 20:20131 -> 25:28075 -> 30:22084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 17.4 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:16053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 19.4 | grt rounds 3 overflow 5:57640 -> 10:67281 -> 15:55315 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 19.4 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40887 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 27.9 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:36858 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 22.1 | grt rounds 4 overflow 5:9213 -> 10:5212 -> 15:3426 -> 20:3173 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:30377 -> 10:16662 -> 15:14043 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 3.2 | grt rounds 3 overflow 5:38116 -> 10:39840 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 17.2 | grt rounds 3 overflow 5:29640 -> 10:6637 -> 15:5987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 17.2 | grt rounds 3 overflow 5:59583 -> 10:59412 -> 15:50422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 10.3 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 18.6 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20564 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 17.2 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:80612 -> 10:60387 -> 15:48404 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_1_grt | 7.8 | grt rounds 3 overflow 5:45755 -> 10:1 -> 15:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 23.8 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 24.9 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 58.1 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 26.2 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 9.3 | grt rounds 3 overflow 5:31334 -> 10:16178 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: overflow 16178 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 26.2 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 8.0 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 8.0 | grt rounds 3 overflow 5:24921 -> 10:17867 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 18.5 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6221 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 8.0 | grt rounds 3 overflow 5:48001 -> 10:50564 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 27.7 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 19.5 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 19.5 | grt rounds 3 overflow 5:43779 -> 10:38620 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 18.9 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 14.3 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pv5b623e07-1880851 | col_h10_r0_p4__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_iq_C__t1-2048142 | dsdv_slice_iq_C__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (364/364 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 8.9 | last meaningful line 0.8 h ago (198/200 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v8-2974046 | kv3_pv_v8 | tt_setup_repair | 18.2 | repair_Viol best 5660 last 5660 rows 293 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 5_2_route | 20.3 | drt_violations best 12534 last 12534 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1t-735514 | eco_20261120_185639_3224747-i1t | 5_2_route | 6.0 | drt_violations best 6137 last 6137 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 3.7 | drt_violations best 3038 last 3038 rows 3 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 1.4 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1t-1628432 | eco_20261121_003008_2139459-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (245/246 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-col-h9-r0-p5--t1--pveda1ecc9-grt-1884308 | col-h9-r0-p5--t1--pveda1ecc9-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-glue-grt-1881983 | glue-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t14-grt-1885169 | ot-s81sl-leaf--t14-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t34-grt-1956865 | ot-s81sl-leaf--t34-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t54--cl706d9749-grt-1957478 | ot-s81sl-leaf--t54--cl706d9749-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t74-grt-1883945 | ot-s81sl-leaf--t74-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q00_s2-1641925 | cbf_q00_s2 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (212/212 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01-1639008 | cbf_q01 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (2388/2388 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 5_1_grt | 4.9 | last meaningful line 2.3 h ago (200/226 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 5.2 | last meaningful line 2.8 h ago (199/228 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 5.2 | last meaningful line 2.8 h ago (199/228 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 7.5 | drt_violations best 66844 last 66844 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (2621/2621 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (2789/2790 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-coll_core-3054314 | coll_core | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (127/127 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-1636745 | gunit__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 5.8 | last meaningful line 0.0 h ago (498/498 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-3072949 | ot_s81sl_kv_leaf__t3 | 3_3_place_gp | 1.1 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (462/462 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (299/299 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (368/368 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t59-3020126 | ot_s81sl_leaf__t59 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1554/1554 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (298/298 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5480/5480 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (304/304 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4367/4368 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (321/321 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (219/219 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-2148023 | slw_hc2 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (238/238 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (305/305 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (4868/4868 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (317/317 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5923/5923 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (296/296 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 2.3 | last meaningful line 0.3 h ago (587/587 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 5.3 | last meaningful line 0.0 h ago (676/676 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.3 | last meaningful line 0.3 h ago (435/435 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 1.8 | last meaningful line 0.0 h ago (434/434 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | otc-1886341-12002 | 1886341 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3048695-18646 | 3048695 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-1014755 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 5.5 | drt_violations best 34 last 34 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_2_route | 3.2 | drt_violations best 23257 last 23257 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1535015_ff_98124 | so_1535015_ff_98124 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (392/392 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_1535015_tt_98124 | so_1535015_tt_98124 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (392/392 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_1736710_ff_72587 | so_1736710_ff_72587 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (6388/6388 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1736710_tt_72587 | so_1736710_tt_72587 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (6388/6388 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-3208392 | cbf_q00 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9343 last 0.9343 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbf_q01_s2-1971223 | cbf_q01_s2 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4992/4992 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3208512 | cbf_q11 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7283 last 0.7283 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-3976533 | cbn_q01 | 2_1_floorplan | 0.1 | repair_Viol best 1128 last 1128 rows 218 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3208672 | cbn_q01 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200-3501165 | cbx_q10 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-3500998 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (101/101 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | tt_setup_repair | 1.2 | repair_Viol best 93 last 93 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-3830158 | hd_lep0N | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 3_3_place_gp | 1.2 | overflow best 0.7336 last 0.7336 rows 29 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-2363517 | kv3_pv_v2 | 3_1_place_gp_skip_io | 1.1 | overflow best 0.7763 last 0.7763 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 4.9 | last meaningful line 0.3 h ago (15711/15712 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 4.9 | last meaningful line 0.2 h ago (15617/15618 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 3_5_place_dp | 2.6 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 7.6 | last meaningful line 0.5 h ago (15759/15759 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-native59-2890501 | native59 | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (391/391 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (3040/3040 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3264/3264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t60-1971113 | ot_s81sl_leaf__t60 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4133/4133 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3192703 | sle_fw_v2 | 3_3_place_gp | 0.4 | overflow best 0.2961 last 0.2961 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3233970 | sle_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5411/5412 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_2_route | 8.2 | drt_violations best 84515 last 84515 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (439/439 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4904/4905 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4937/4938 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-3208717 | slw_hc0 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5248/5249 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (197/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3263016 | slw_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5180/5180 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-791387 | slw_stm_v1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (335/335 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4634/4634 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (195/208 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 7.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_3872085_ff_46988 | so_3872085_ff_46988 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_3872085_tt_46988 | so_3872085_tt_46988 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | postcts_gate_TT | 6.2 | last meaningful line 0.0 h ago (1103/1103 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (900/900 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (1039/1039 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (1084/1084 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | 5_2_route | 6.2 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (974/974 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (682/682 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (831/831 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (907/907 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (876/876 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (692/692 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (888/888 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (898/898 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 6.2 | last meaningful line 0.5 h ago (269/270 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 36.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbx_q10__cl94a12200-20237 | cbx_q10 | 3_3_place_gp | 0.5 | overflow best 0.436 last 0.436 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 7.6 | drt_violations best 91026 last 91026 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | tt_setup_repair | 0.5 | repair_Viol best 197 last 197 rows 234 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-34019 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6139 last 0.6139 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.5 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-3235380 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.6 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-glue-1948074 | glue | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-gunit__t1-3341748 | gunit__t1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (576/576 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 3_3_place_gp | 1.4 | overflow best 0.2985 last 0.3617 rows 345 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_e-18162 | hd_host_e | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-4082127 | hd_host_n | tt_setup_repair_grt | 0.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-1734167 | hd_mesh | 5_1_grt | 7.5 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.5 | overflow best 0.5576 last 0.5576 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t70-23212 | ot_s81sl_leaf__t70 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-3958052 | serdes__t15 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | 5_1_grt | 9.7 | repair_TNS best 4142.14 last 4142.14 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-4078399 | slice_station__t6 | 3_3_place_gp | 0.5 | overflow best 0.3122 last 0.3128 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 1.4 | last meaningful line 0.4 h ago (215/698 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (4068/4068 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (4826/4826 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t6-1947287 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 1.4 | last meaningful line 0.0 h ago (365/365 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 2.3 | last meaningful line 0.5 h ago (456/456 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 101.2 |  | NO-DATA: empty log |  |
| epyc9 | otc-4021631-12869 | 4021631 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 6.0 | drt_violations best 72611 last 72611 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | postcts_gate_FF | 22.1 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 8.2 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 8.6 | drt_violations best 11374 last 11374 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-1492344 | coll_ftc | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (692/692 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 3_3_place_gp | 3.7 | overflow best 0.3077 last 0.3077 rows 27 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.0 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 8.0 | drt_violations best 19623 last 19623 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 20.1 | drt_violations best 81847 last 81847 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 20.8 | drt_violations best 100416 last 100416 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | postcts_gate_TT | 4.9 | last meaningful line 0.2 h ago (697/697 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 2.0 | last meaningful line 0.1 h ago (457/457 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 5.3 | last meaningful line 0.6 h ago (653/653 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 3.4 | last meaningful line 0.0 h ago (524/524 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.0 | last meaningful line 0.3 h ago (414/414 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-cbn_q01__cld9ff4c40-2195882 | cbn_q01 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (324/324 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-361000 | col_h9_r0_p1__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-168013 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.6 | overflow best 0.3784 last 0.3784 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-359064 | col_h9_r0_p2__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-286613 | col_h9_r0_p2__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-291993 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.874 last 0.874 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-232337 | col_h9_r0_p5__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-182001 | col_h9_r0_p6__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (133/133 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (129/129 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 2.8 | last meaningful line 1.2 h ago (126/126 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 14.1 | last meaningful line 0.2 h ago (168/168 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-186299 | ot_s81sl_leaf__t24 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1150/1150 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | hold_gate | 1.8 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3941/3941 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (618/618 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-162109 | serdes__t1 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5679/5679 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5519/5519 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5167/5167 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 3_3_place_gp | 0.6 | overflow best 0.7774 last 0.7774 rows 12 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | 3_3_place_gp | 0.6 | overflow best 0.4027 last 0.4027 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-slice_station__t18-351808 | slice_station__t18 | 3_3_place_gp | 0.5 | overflow best 0.4253 last 0.4253 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t25-270940 | slice_station__t25 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.5628 last 0.5628 rows 37 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t29__clc7772371-261662 | slice_station__t29 | 3_3_place_gp | 0.6 | overflow best 0.324 last 0.326 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4081/4081 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3817/3817 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4917/4918 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 4_1_cts | 0.6 | last meaningful line 0.2 h ago (5560/5560 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4171/4171 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5365/5365 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (177/177 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 1.8 | last meaningful line 0.2 h ago (455/455 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 2.8 | last meaningful line 0.3 h ago (612/612 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_1_grt | 1.1 | last meaningful line 0.4 h ago (232/1363 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (169/169 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | so_1092125_ff_92768 | so_1092125_ff_92768 | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (1222/1222 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_1092125_tt_92768 | so_1092125_tt_92768 | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (1222/1222 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_23570_ff_47706 | so_23570_ff_47706 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1196/1196 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_23570_tt_47706 | so_23570_tt_47706 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1196/1196 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_542676_ff_7656 | so_542676_ff_7656 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1309/1309 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_542676_tt_7656 | so_542676_tt_7656 | stage_odb_cap | 0.4 | last meaningful line 0.3 h ago (1309/1309 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_617331_ff_41679 | so_617331_ff_41679 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (357/357 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_617331_tt_41679 | so_617331_tt_41679 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (357/357 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | stage_odb_cap | 7.6 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 29.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 10.3 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 10.3 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 4_1_cts | 0.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 27.2 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 22.3 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 17.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 9.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 64.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 40.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 40.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (4151/4151 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2331179 | col_h10_r2__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (4135/4135 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (484/484 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (609/609 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-2685046 | col_h9_r2__t1 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (475/475 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 19.1 | last meaningful line 0.0 h ago (9460/9460 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 20.3 | last meaningful line 0.0 h ago (9997/9997 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 18.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (3911/3911 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 8.9 | last meaningful line 0.0 h ago (663/663 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 8.8 | last meaningful line 0.0 h ago (4883/4883 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (3350/3350 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 22.6 | last meaningful line 0.0 h ago (11156/11156 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 11.4 | drt_violations best 68 last 68 rows 13 | before-window best 26786, window best 68 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 14.2 | last meaningful line 1.4 h ago (1379/1379 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 11.5 | last meaningful line 0.0 h ago (6540/6540 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 11.3 | last meaningful line 0.0 h ago (6103/6103 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 11.5 | last meaningful line 0.0 h ago (6398/6398 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 6.1 | last meaningful line 0.5 h ago (879/879 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (456/456 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 7.6 | repair_TNS best 155545 last 155545 rows 5 | before-window best 158870, window best 155545 | PROGRESS: repair_TNS improved 2.1 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (3617/3617 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 26.1 | drt_violations best 10168 last 22918 rows 19 | before-window best 10389, window best 10168 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026 | dsdv_bksel_c_rfda3pt | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 165 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 17.2 | last meaningful line 0.0 h ago (9608/9608 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1125/1125 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (983/983 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1202/1202 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1114/1114 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (954/954 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1119/1119 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1080/1080 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1122/1122 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1125/1125 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (908/908 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (1134/1134 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 18.4 | last meaningful line 0.0 h ago (1258/1258 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-882202 | col_h10_r0_p1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (1255/1255 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (1217/1217 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (1220/1220 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1969/1969 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1226/1226 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (4579/4579 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (4576/4576 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_sc_v2-1792546 | sle_sc_v2 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (3756/3756 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 20.0 | last meaningful line 0.0 h ago (10612/10612 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 20.3 | last meaningful line 0.0 h ago (10645/10645 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (4189/4189 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (4483/4483 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (531/531 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4089/4089 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4256/4256 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4044/4044 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (4118/4118 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 20.8 | drt_violations best 11535 last 11535 rows 2 | before-window best 89452, window best 11535 | PROGRESS: drt_violations improved 87.1 % in window |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 27.2 | last meaningful line 0.0 h ago (1620/1620 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 22.2 | last meaningful line 0.0 h ago (1342/1342 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 14.1 | repair_Violations best 3168 last 3210 rows 144 | before-window best 54561, window best 3168 | PROGRESS: repair_Violations improved 94.2 % in window |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 17.8 | last meaningful line 0.0 h ago (1394/1394 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t30-232707 | ot_s81sl_leaf__t30 | 3_5_place_dp | 0.6 | repair_Violations best 0 last 0 rows 36 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 20.3 | last meaningful line 0.0 h ago (1210/1210 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 20.3 | last meaningful line 0.0 h ago (1210/1210 lines) | PROGRESS: log still growing |  |
