# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 17:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 2, 'GRT-LABEL': 40, 'YOUNG': 218, 'NO-DATA': 10, 'KEEP': 9, 'EXCLUDED': 3, 'PROGRESS': 59}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (3053/3053 lines) | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -446.29 ps (< -300, gate TT >= -42); job age 5. | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (2954/2954 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -1491.99 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 20.0 | drt_violations best 76548 last 76548 rows 1 | before-window best 76548, window best 76548 | NO-PROGRESS: drt_violations best 76548 vs 76548 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 21.4 | drt_violations best 144324 last 144324 rows 1 | before-window best 144324, window best 144324 | NO-PROGRESS: drt_violations best 144324 vs 144324 before window: < 2 % in 6 h | CANCELLED |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 23.9 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 20.3 | grt rounds 2 overflow 5:87024 -> 10:50446 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 9.4 | grt rounds 5 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 9.1 | grt rounds 3 overflow 5:46508 -> 10:46073 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 19.0 | grt rounds 4 overflow 5:27623 -> 10:16733 -> 15:13155 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 19.4 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 9.4 | grt rounds 3 overflow 5:43983 -> 10:46937 -> 15:39542 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t30-921459 | ot_s81sl_leaf__t30 | 5_1_grt | 19.8 | grt rounds 6 overflow 5:32680 -> 10:26052 -> 15:21293 -> 20:20131 -> 25:28075 -> 30:22084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 17.6 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:16053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 19.6 | grt rounds 3 overflow 5:57640 -> 10:67281 -> 15:55315 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 19.6 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 28.2 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_1_grt | 3.9 | grt rounds 6 overflow 5:1144 -> 10:980 -> 15:961 -> 20:863 -> 25:428 -> 30:141 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | 5_1_grt | 5.5 | grt rounds 5 overflow 5:5106 -> 10:1814 -> 15:1782 -> 20:1614 -> 25:1541 | GRT-LABEL: DESIGN-FAIL: overflow 1814 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 3.6 | grt rounds 3 overflow 5:30377 -> 10:16662 -> 15:14043 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 3.5 | grt rounds 3 overflow 5:38116 -> 10:39840 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 1.0 | grt rounds 6 overflow 5:727 -> 10:550 -> 15:623 -> 20:549 -> 25:185 -> 30:90 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 17.2 | grt rounds 3 overflow 5:29640 -> 10:6637 -> 15:5987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 17.2 | grt rounds 3 overflow 5:59583 -> 10:59412 -> 15:50422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 10.3 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 18.6 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20564 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 17.2 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:80612 -> 10:60387 -> 15:48404 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_1_grt | 8.1 | grt rounds 3 overflow 5:45755 -> 10:1 -> 15:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 24.1 | grt rounds 2 overflow 5:78093 -> 10:63859 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 25.2 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 58.4 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 26.4 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 9.5 | grt rounds 3 overflow 5:31334 -> 10:16178 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: overflow 16178 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 26.4 | grt rounds 3 overflow 5:26917 -> 10:19209 -> 15:17126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 8.3 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:24921 -> 10:17867 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 18.8 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6221 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:48001 -> 10:50564 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 27.9 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 19.8 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 19.8 | grt rounds 3 overflow 5:43779 -> 10:38620 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 19.1 | grt rounds 2 overflow 5:59628 -> 10:54127 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 14.6 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pv5b623e07-1880851 | col_h10_r0_p4__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-2330364 | col_h10_r2__t1 | 5_2_route | 7.8 | drt_violations best 9961 last 9961 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-2690073 | col_h9_r1__t1 | 5_2_route | 9.0 | drt_violations best 11917 last 11917 rows 3 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_iq_C__t1-2048142 | dsdv_slice_iq_C__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (424/424 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 9.1 | last meaningful line 1.0 h ago (198/201 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v8-2974046 | kv3_pv_v8 | tt_setup_repair | 18.4 | repair_Violations best 3327 last 3327 rows 29 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | 5_2_route | 20.6 | drt_violations best 12534 last 12534 rows 2 | YOUNG: evidence 6.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 4.0 | drt_violations best 2392 last 2392 rows 5 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 1.6 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1t-1628432 | eco_20261121_003008_2139459-i1t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-cbn-q00--cld7bf7197-grt-2262469 | cbn-q00--cld7bf7197-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t12-grt-2349839 | ot-s81sl-leaf--t12-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t35-grt-2342818 | ot-s81sl-leaf--t35-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q00_s2-1641925 | cbf_q00_s2 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2538/2538 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | 5_1_grt | 5.1 | last meaningful line 2.5 h ago (200/228 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 5.4 | last meaningful line 3.0 h ago (199/229 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 5.4 | last meaningful line 3.0 h ago (199/229 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 7.7 | drt_violations best 66844 last 66844 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (2771/2771 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (183/183 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-coll_core-3054314 | coll_core | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.5 h ago (131/131 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (127/127 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.7 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-1636745 | gunit__t1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 6.1 | last meaningful line 0.0 h ago (532/532 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-3072949 | ot_s81sl_kv_leaf__t3 | 3_3_place_gp | 1.3 | overflow best 0.659 last 0.659 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (477/477 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (314/314 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (383/383 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t59-3020126 | ot_s81sl_leaf__t59 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (1704/1704 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4284/4284 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3521/3521 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (282/282 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (299/299 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5507/5507 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (319/319 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (4703/4703 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 4_1_cts | 0.7 | last meaningful line 0.2 h ago (4449/4449 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (233/233 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-2148023 | slw_hc2 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (4895/4895 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (332/332 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5977/5977 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2121/2121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 2.5 | last meaningful line 0.5 h ago (587/587 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 5.5 | last meaningful line 0.1 h ago (858/858 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.6 | last meaningful line 0.5 h ago (435/435 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 2.0 | last meaningful line 0.2 h ago (456/456 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | otc-1886341-12002 | 1886341 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 5.7 | drt_violations best 34 last 34 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_2_route | 3.4 | drt_violations best 23257 last 23257 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-fin-1014755 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1535015_ff_98124 | so_1535015_ff_98124 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (392/392 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_1535015_tt_98124 | so_1535015_tt_98124 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (392/392 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-3208392 | cbf_q00 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.479 last 0.479 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-cbf_q01_s2-1971223 | cbf_q01_s2 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (5122/5122 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3208512 | cbf_q11 | 3_3_place_gp | 0.7 | overflow best 0.5542 last 0.5542 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-3976533 | cbn_q01 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3208672 | cbn_q01 | 3_3_place_gp | 0.7 | overflow best 0.5431 last 0.5431 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200-3501165 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.2388 last 0.2388 rows 32 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-3500998 | dsdv_slice_lepe_nh_mus_LP__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-4138114 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8082 last 0.8206 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3830158 | hd_lep0N | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (11000/11000 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 3_3_place_gp | 1.4 | overflow best 0.0992 last 0.0992 rows 53 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (241/241 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (241/241 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-2363517 | kv3_pv_v2 | 3_1_place_gp_skip_io | 1.4 | overflow best 0.1386 last 0.1386 rows 39 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 5.1 | last meaningful line 0.1 h ago (15715/15715 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 5.1 | last meaningful line 0.3 h ago (15617/15618 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 2.9 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 7.8 | last meaningful line 0.2 h ago (15761/15761 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-native59-2890501 | native59 | 3_3_place_gp | 1.0 | overflow best 0.5403 last 0.5403 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (3190/3190 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3382/3382 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (414/414 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3192703 | sle_fw_v2 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | postcts_gate_TT | 7.7 | last meaningful line -0.0 h ago (50795/50795 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3233970 | sle_st_b_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5468/5468 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_2_route | 8.5 | drt_violations best 84515 last 84515 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5090/5090 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5123/5123 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-3208717 | slw_hc0 | 4_1_cts | 0.7 | last meaningful line 0.2 h ago (5252/5252 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (402/402 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3263016 | slw_st_b_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5234/5234 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-791387 | slw_stm_v1 | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (350/350 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4688/4688 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 7.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (265/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | so_3872085_ff_46988 | so_3872085_ff_46988 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | so_3872085_tt_46988 | so_3872085_tt_46988 | signoff | 0.4 |  | NO-DATA: empty log |  |
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
| epyc9 | ap-ageom-kw-dsdv-slice-kv512-C--t1-grt-1032161 | dsdv-slice-kv512-C--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t30-grt-879312 | ot-s81sl-leaf--t30-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbx_q10__cl94a12200-20237 | cbx_q10 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 7.8 | drt_violations best 91026 last 91026 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 14646 last 14646 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | pregrt_ff_hold | 1.7 | repair_Violations best 918 last 918 rows 14 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 14646 last 14646 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-34019 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.7 | overflow best 0.4401 last 0.4401 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 1.7 | last meaningful line 0.1 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-gunit__t1-3341748 | gunit__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (636/636 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 3_3_place_gp | 1.7 | overflow best 0.2985 last 0.3704 rows 423 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_e-18162 | hd_host_e | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (183/185 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-4082127 | hd_host_n | 5_2_route | 0.8 | last meaningful line 0.0 h ago (214/214 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-1734167 | hd_mesh | 5_1_grt | 7.8 | last meaningful line 0.0 h ago (184/193 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t38-890997 | ot_s81sl_leaf__t38 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9908 last 0.9908 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t70-23212 | ot_s81sl_leaf__t70 | 3_3_place_gp | 0.7 | overflow best 0.6055 last 0.6121 rows 6 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-3958052 | serdes__t15 | 3_1_place_gp_skip_io | 0.8 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | 5_1_grt | 9.9 | repair_TNS best 3411.26 last 3411.26 rows 5 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 3_3_place_gp | 0.8 | overflow best 0.329 last 0.3468 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | 3_3_place_gp | 0.7 | overflow best 0.2524 last 0.2626 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-4078399 | slice_station__t6 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (180/180 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 1.6 | last meaningful line 0.7 h ago (215/716 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (4072/4072 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5132/5133 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t6-1947287 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 1.7 | last meaningful line 0.0 h ago (416/416 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 2.5 | last meaningful line 0.0 h ago (469/469 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 101.4 |  | NO-DATA: empty log |  |
| epyc9 | otc-4021631-12869 | 4021631 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 6.3 | drt_violations best 72611 last 72611 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | postcts_gate_TT | 22.3 | last meaningful line 0.1 h ago (466/466 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 8.4 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 8.9 | drt_violations best 8339 last 8339 rows 3 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-1492344 | coll_ftc | 3_3_place_gp | 0.6 | overflow best 0.4324 last 0.4523 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (290/290 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (752/752 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 3_3_place_gp | 4.0 | overflow best 0.1945 last 0.1945 rows 34 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.3 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2480956 | sle_fe_v1 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 8.3 | drt_violations best 19623 last 19623 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 20.3 | drt_violations best 81847 last 81847 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 21.0 | drt_violations best 100416 last 100416 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | postcts_gate_TT | 5.1 | last meaningful line 0.1 h ago (1496/1496 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 2.3 | last meaningful line 0.3 h ago (457/457 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 5.6 | last meaningful line 0.8 h ago (653/653 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 3.6 | last meaningful line 0.0 h ago (549/549 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.2 | last meaningful line 0.5 h ago (414/414 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-cbn_q01__cld9ff4c40-2195882 | cbn_q01 | 3_4_place_resized | 2.1 | repair_Remaining best 6706 last 6706 rows 247 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-361000 | col_h9_r0_p1__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-168013 | col_h9_r0_p2__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-359064 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.8 | overflow best 0.3363 last 0.3366 rows 21 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-286613 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.8 | overflow best 0.3369 last 0.3369 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-291993 | col_h9_r0_p3__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-232337 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.8 | overflow best 0.3346 last 0.3851 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.8 h ago (133/133 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | 1_2_yosys | 3.1 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 14.4 | last meaningful line 0.3 h ago (169/169 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 14.4 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-186299 | ot_s81sl_leaf__t24 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1290/1290 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (393/393 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4147/4147 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (768/768 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-162109 | serdes__t1 | 2_4_floorplan_pdn | 0.9 | last meaningful line 0.3 h ago (92/92 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5706/5706 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5573/5573 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5194/5194 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 3_3_place_gp | 0.9 | overflow best 0.1212 last 0.1212 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | 3_4_place_resized | 0.9 | repair_Remaining best 284066 last 284066 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slice_station__t18-351808 | slice_station__t18 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t25-270940 | slice_station__t25 | 3_3_place_gp | 0.8 | overflow best 0.4758 last 0.4758 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4135/4135 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 3_3_place_gp | 0.9 | overflow best 0.2359 last 0.2359 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3844/3844 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (4973/4973 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5614/5614 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4200/4200 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5392/5392 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 2.1 | last meaningful line 0.3 h ago (455/455 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 3.1 | last meaningful line 0.5 h ago (612/612 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 0.7 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_1_grt | 1.3 | last meaningful line 0.7 h ago (232/1544 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_1_grt | 0.9 | last meaningful line 0.2 h ago (232/263 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | so_1092125_ff_92768 | so_1092125_ff_92768 | stage_odb_cap | 0.3 | last meaningful line 0.3 h ago (1222/1222 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | so_1092125_tt_92768 | so_1092125_tt_92768 | stage_odb_cap | 0.3 | last meaningful line 0.3 h ago (1222/1222 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | so_1262589_ff_95579 | so_1262589_ff_95579 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (1230/1230 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_1262589_tt_95579 | so_1262589_tt_95579 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (1230/1230 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_23570_ff_47706 | so_23570_ff_47706 | stage_odb_cap | 0.9 | last meaningful line 0.8 h ago (1196/1196 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | so_23570_tt_47706 | so_23570_tt_47706 | stage_odb_cap | 0.9 | last meaningful line 0.8 h ago (1196/1196 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | so_542676_ff_7656 | so_542676_ff_7656 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1309/1309 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_542676_tt_7656 | so_542676_tt_7656 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1309/1309 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_617331_ff_41679 | so_617331_ff_41679 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (357/357 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | so_617331_tt_41679 | so_617331_tt_41679 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (357/357 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2236867 | col_h10_r2__t1 | stage_odb_cap | 7.9 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 30.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 10.3 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 10.3 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | pregrt_ff_hold | 0.7 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 27.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 22.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 17.4 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 10.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 64.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 40.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 41.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2331179 | col_h10_r2__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4285/4285 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (499/499 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-2685046 | col_h9_r2__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (490/490 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 19.4 | last meaningful line 0.0 h ago (9610/9610 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 20.5 | last meaningful line 0.0 h ago (10147/10147 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 18.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (4061/4061 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (678/678 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (5033/5033 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (3500/3500 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 22.3 | last meaningful line 0.0 h ago (11273/11273 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 22.8 | last meaningful line 0.0 h ago (11306/11306 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 11.7 | drt_violations best 68 last 68 rows 13 | before-window best 2217, window best 68 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1t-735514 | eco_20261120_185639_3224747-i1t | 5_2_route | 6.3 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 14.5 | last meaningful line 1.6 h ago (1379/1379 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (6690/6690 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 11.6 | last meaningful line 0.0 h ago (6253/6253 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (6538/6538 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 6.3 | last meaningful line 0.8 h ago (879/879 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (471/471 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 7.8 | repair_TNS best 153044 last 153044 rows 8 | before-window best 158870, window best 153044 | PROGRESS: repair_TNS improved 3.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 26.3 | drt_violations best 10168 last 22918 rows 19 | before-window best 10389, window best 10168 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026 | dsdv_bksel_c_rfda3pt | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 34 | PROGRESS: repair_TNS reached 0 |  |
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
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 18.7 | last meaningful line 0.0 h ago (1273/1273 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 10.0 | last meaningful line 0.0 h ago (1232/1232 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (1235/1235 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 9.5 | last meaningful line 0.0 h ago (1984/1984 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 9.5 | last meaningful line 0.0 h ago (1241/1241 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (4729/4729 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2364413 | sle_fw_v2 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (4726/4726 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 20.3 | last meaningful line 0.0 h ago (10762/10762 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 20.5 | last meaningful line 0.0 h ago (10795/10795 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (4329/4329 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 8.3 | drt_violations best 14020 last 14020 rows 2 | before-window best 73630, window best 14020 | PROGRESS: drt_violations improved 81.0 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (4623/4623 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (545/545 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4229/4229 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4396/4396 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4184/4184 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (4268/4268 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 21.0 | drt_violations best 7013 last 7013 rows 3 | before-window best 89452, window best 7013 | PROGRESS: drt_violations improved 92.2 % in window |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 27.4 | last meaningful line 0.0 h ago (1635/1635 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-182001 | col_h9_r0_p6__t1 | 4_1_cts | 0.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 22.5 | last meaningful line 0.0 h ago (1357/1357 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 18.0 | last meaningful line 0.0 h ago (1409/1409 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 20.6 | last meaningful line 0.0 h ago (1225/1225 lines) | PROGRESS: log still growing |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_1_grt | 0.9 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
