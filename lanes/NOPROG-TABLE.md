# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 07:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 5, 'GRT-LABEL': 35, 'YOUNG': 123, 'NO-DATA': 18, 'EXCLUDED': 6, 'KEEP': 1, 'PROGRESS': 41}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 23.4 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 36.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 36 | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 18.0 | drt_violations best 87 last 201 rows 51 | before-window best 87, window best 201 | NO-PROGRESS: drt_violations best 201 vs 87 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 5_2_route | 14.9 | drt_violations best 96415 last 96415 rows 1 | before-window best 96415, window best 96415 | NO-PROGRESS: drt_violations best 96415 vs 96415 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-606014 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -891.39 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 5_2_route | 11.8 | drt_violations best 107580 last 107580 rows 1 | before-window best 107580, window best 107580 | NO-PROGRESS: drt_violations best 107580 vs 107580 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 5_2_route | 15.1 | drt_violations best 149465 last 149465 rows 1 | before-window best 149465, window best 149465 | NO-PROGRESS: drt_violations best 149465 vs 149465 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 5_2_route | 15.1 | drt_violations best 149962 last 149962 rows 1 | before-window best 149962, window best 149962 | NO-PROGRESS: drt_violations best 149962 vs 149962 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 21.9 | grt rounds 3 overflow 5:62877 -> 10:60664 -> 15:49761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 21.9 | grt rounds 4 overflow 5:50202 -> 10:43421 -> 15:40646 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 36.3 | grt rounds 4 overflow 5:8939 -> 10:4958 -> 15:3337 -> 20:2951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 25.8 | grt rounds 4 overflow 5:51489 -> 10:38067 -> 15:34729 -> 20:37772 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 11.0 | grt rounds 6 overflow 5:6375 -> 10:5827 -> 15:5482 -> 20:5460 -> 25:8886 -> 30:7683 | GRT-LABEL: DESIGN-FAIL: overflow 5827 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 15.7 | grt rounds 3 overflow 5:87834 -> 10:75300 -> 15:146439 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 20.7 | grt rounds 3 overflow 5:61289 -> 10:75075 -> 15:79226 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_serdes-4080505 | hd_serdes | 5_1_grt | 2.7 | grt rounds 6 overflow 5:7936 -> 10:3283 -> 15:1164 -> 20:653 -> 25:675 -> 30:655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 10.1 | grt rounds 3 overflow 5:51078 -> 10:48872 -> 15:39905 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 10.1 | grt rounds 3 overflow 5:50865 -> 10:49068 -> 15:39825 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 19.8 | grt rounds 3 overflow 5:46510 -> 10:49364 -> 15:43557 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:81129 -> 10:76153 | GRT-LABEL: DESIGN-FAIL: overflow 76153 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 15.8 | grt rounds 3 overflow 5:71046 -> 10:70742 -> 15:80466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 9.6 | grt rounds 3 overflow 5:91861 -> 10:71452 -> 15:82957 | GRT-LABEL: DESIGN-FAIL: overflow 71452 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 11.3 | grt rounds 4 overflow 5:41190 -> 10:38638 -> 15:36674 -> 20:38201 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 11.3 | grt rounds 3 overflow 5:34201 -> 10:37631 -> 15:33126 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 10.9 | grt rounds 4 overflow 5:20011 -> 10:14131 -> 15:12398 -> 20:11080 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 12.2 | grt rounds 5 overflow 5:4335 -> 10:1587 -> 15:1329 -> 20:1263 -> 25:1744 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_serdes-2625867 | hd_serdes | 5_1_grt | 1.8 | grt rounds 6 overflow 5:7569 -> 10:2911 -> 15:1153 -> 20:652 -> 25:686 -> 30:663 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_serdes-3513884 | hd_serdes | 5_1_grt | 1.1 | grt rounds 6 overflow 5:3970 -> 10:1947 -> 15:556 -> 20:559 -> 25:572 -> 30:564 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 23.8 | grt rounds 3 overflow 5:26652 -> 10:13431 -> 15:9000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_st_a_v1__cl67389ecd-1866893 | sle_st_a_v1 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:1203 -> 10:504 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-608839 | sle_st_a_v2 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:5552 -> 10:3241 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 34.5 | grt rounds 5 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 34.8 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:23529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 5_1_grt | 11.8 | grt rounds 5 overflow 5:108182 -> 10:5739 -> 15:4546 -> 20:4559 -> 25:4974 | GRT-LABEL: DESIGN-FAIL: overflow 5739 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:51463 -> 10:8263 -> 15:5295 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 5_1_grt | 11.6 | grt rounds 4 overflow 5:60653 -> 10:2745 -> 15:1916 -> 20:1917 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 17.3 | grt rounds 5 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10993 -> 25:8231 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 12.3 | grt rounds 3 overflow 5:32854 -> 10:32007 -> 15:25602 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 33.6 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 15.0 | grt rounds 4 overflow 5:35006 -> 10:1235 -> 15:721 -> 20:1026 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 28.6 | grt rounds 3 overflow 5:60387 -> 10:47822 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: overflow 47822 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 28.6 | grt rounds 2 overflow 5:61726 -> 10:48832 | GRT-LABEL: DESIGN-FAIL: overflow 48832 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 28.8 | grt rounds 6 overflow 5:11862 -> 10:11192 -> 15:10179 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 5_1_grt | 3.7 | last meaningful line 0.3 h ago (209/215 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3507811 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3151 last 0.3151 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 11.1 | drt_violations best 196822 last 196822 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | 5_2_route | 4.4 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-1963245 | dsdv_slice_c1x_C__t6 | 3_5_place_dp | 4.0 | last meaningful line 0.1 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3390822 | dsdv_slice_c1x_C__t8 | 3_1_place_gp_skip_io | 3.1 | overflow best 0.8313 last 0.8313 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984741 | dsdv_slice_lepe_mu_LP__t2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | 3_3_place_gp | 1.5 | overflow best 0.4987 last 0.4987 rows 17 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | pregrt_ff_hold | 3.3 | repair_TNS best 471985 last 471985 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_2_route | 13.3 | drt_violations best 99432 last 99432 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3913104 | slice_station__t36 | tt_setup_measure | 0.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-1345689 | slw_fe_v2 | 5_1_grt | 4.4 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | 6_report | 11.7 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | eco-abs-3449618 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.1 h ago (638/638 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | lrh-new-3824385 | lrh-new | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | lrh-old-3824295 | lrh-old | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261120_233525_2680444-i3t-2209286 | eco_20261120_233525_2680444-i3t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i2-420525 | eco_20261121_014354_2681516-i2 | 5_2_route | 2.2 | drt_violations best 351 last 351 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-69690 | cbf_q00 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.2064 last 0.2064 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2301911 | col_h10_r1__t1 | 5_1_grt | 5.0 | repair_Viol best 149 last 149 rows 2 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (210/212 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3129306 | col_h9_r2__t1 | 5_1_grt | 1.3 | last meaningful line 0.1 h ago (197/203 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-coll_core-221736 | coll_core | 3_3_place_gp | 0.6 | overflow best 0.6375 last 0.6375 rows 4 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_Ei-72198 | kv3_hub_Ei | 2_1_floorplan | 0.7 | last meaningful line 0.5 h ago (87/87 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Eo-3667498 | kv3_hub_Eo | 3_1_place_gp_skip_io | 1.0 | overflow best 0.8033 last 0.8033 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v4n-4044420 | kv3_pv_v4n | 2_1_floorplan | 0.8 | last meaningful line 0.2 h ago (395/395 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5n-4101656 | kv3_pv_v5n | 2_1_floorplan | 0.7 | last meaningful line 0.0 h ago (1419/1419 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v8-131218 | kv3_pv_v8 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (107/107 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_2_route | 14.4 | drt_violations best 102898 last 102898 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_2_route | 14.3 | drt_violations best 105345 last 105345 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 5_2_route | 14.2 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_2_route | 16.5 | drt_violations best 90792 last 90792 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3612/3612 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_2_route | 14.9 | drt_violations best 86224 last 86224 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 3_3_place_gp | 0.5 | overflow best 0.3718 last 0.3718 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 6_report | 16.5 | last meaningful line 0.1 h ago (640/640 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-569969 | slw_fw_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9984 last 0.9984 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | generate_abstract | 16.8 | last meaningful line 0.2 h ago (1015/1015 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | generate_abstract | 16.8 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clb036e152-4100253 | slw_st_a_v1 | tt_setup_repair | 0.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_2_route | 15.6 | drt_violations best 85069 last 85069 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_2_route | 14.9 | drt_violations best 71488 last 71488 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (6536/6537 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | obsgc_p2_qcsc_off | obsgc_p2_qcsc_off | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | obsgc_p2_qcsc_on | obsgc_p2_qcsc_on | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261120_134605_3273412-i3t-147310 | eco_20261120_134605_3273412-i3t | 5_1_grt | 0.6 | last meaningful line 0.4 h ago (233/1521 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 4.6 | drt_violations best 8867 last 8867 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1t-551142 | eco_20261121_070700_2142563-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2-3115487 | eco_recover1120-i2 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_965370_ff_61072 | so_965370_ff_61072 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_965370_tt_61072 | so_965370_tt_61072 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-glue-2463282 | glue | 3_3_place_gp | 0.6 | overflow best 0.0989 last 0.0989 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-3049707 | hd_lep0N | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 5_2_route | 11.3 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | 3_3_place_gp | 1.2 | overflow best 0.2985 last 0.4657 rows 238 | YOUNG: stage 1.0 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_2_route | 14.9 | drt_violations best 556 last 556 rows 4 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_2_route | 14.9 | drt_violations best 106832 last 106832 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | 5_2_route | 11.1 | drt_violations best 102237 last 102237 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2963444 | slw_sc_v2 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_2_route | 11.3 | drt_violations best 9752 last 9752 rows 2 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 6_report | 14.9 | last meaningful line 0.0 h ago (657/657 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 4.9 | drt_violations best 52 last 52 rows 6 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 22.1 |  | NO-DATA: no log found |  |
| epyc7 | ot-sc-eco-pinkeep-1440767 | ot-sc-eco-pinkeep | - | 1.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-2845655-11464 | 2845655 | gate.ys | 0.3 | last meaningful line 0.3 h ago (13950/13950 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1t-881383 | eco_20261121_100942_929932-i1t | 5_2_route | 5.3 | drt_violations best 152682 last 152682 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | 5_2_route | 10.9 | drt_violations best 73 last 73 rows 12 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t9-950441 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.5 h ago (129/129 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-hd_host_e-2793161 | hd_host_e | 5_2_route | 1.0 | drt_violations best 4303 last 4303 rows 3 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-3963353 | kv3_hg_v3 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.6324 last 0.6608 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3133/3133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3818815 | kv3_io_cor_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t12-3910368 | serdes__t12 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5423/5423 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | pregrt_ff_hold | 2.1 | repair_TNS best 17531.7 last 17531.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t51-719348 | slice_station__t51 | pregrt_ff_hold | 2.3 | repair_TNS best 171199 last 171199 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5139/5139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 52762.2 last 52762.2 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 4_1_cts | 4.4 | last meaningful line 0.0 h ago (5312/5312 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (5007/5007 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (4752/4752 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-3736166 | slw_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.2084 last 0.2084 rows 39 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 50.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-3942727-31370 | 3942727 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261121_140125_4181979-i1-2046754 | eco_20261121_140125_4181979-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (253/254 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | so_3970276_ff_73006 | so_3970276_ff_73006 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | so_3970276_tt_73006 | so_3970276_tt_73006 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.2 | repair_TNS best 227530 last 227530 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 10.0 | repair_Viol best 223 last 223 rows 474 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.5 | last meaningful line 0.4 h ago (234/458 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hg-3839520 | kv3_hg | 3_3_place_gp | 0.8 | overflow best 0.2167 last 0.2167 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_hg_v1p6-3773386 | kv3_hg_v1p6 | 3_3_place_gp | 0.9 | overflow best 0.8141 last 0.8141 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v2-70861 | kv3_pv_v2 | 2_1_floorplan | 0.4 | last meaningful line 0.1 h ago (386/386 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-3820867 | kv3_pv_v2n | 2_4_floorplan_pdn | 0.8 | last meaningful line 0.1 h ago (109/109 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3n-113758 | kv3_pv_v3n | 2_1_floorplan | 0.4 | repair_Viol best 1314 last 1314 rows 864 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-native59-46825 | native59 | 2_1_floorplan | 0.5 | last meaningful line 0.1 h ago (1359/1359 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 14.0 | repair_Remaining best 348290 last 348290 rows 1 | YOUNG: evidence 5.7 h < 6 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-492382 | sle_ctl | pregrt_ff_hold | 3.4 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (5449/5450 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-1095767 | sle_su_l1 | 5_1_grt | 3.0 | last meaningful line 0.2 h ago (220/634 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_2_route | 15.9 | drt_violations best 179096 last 179096 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 7.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 7.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 6.8 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_2_route | 8.5 | drt_violations best 11017 last 11017 rows 2 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_125224_4071554-i1t-1606220 | eco_20261121_125224_4071554-i1t | 5_2_route | 2.6 | drt_violations best 75 last 75 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i1-3833068 | eco_20261121_143815_74711-i1 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_367830_ff_1771 | so_367830_ff_1771 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_367830_tt_1771 | so_367830_tt_1771 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-kv3-hgi-v2--cle0015330-grt-1323854 | kv3-hgi-v2--cle0015330-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_1_grt | 3.9 | repair_TNS best 2.452 last 2.452 rows 17 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_2_route | 11.6 | drt_violations best 151954 last 151954 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 11.6 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3458260 | dsdv_slice_lepe_nh_mus_C__t1 | 3_3_place_gp | 4.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3-95521 | kv3_hg_v1p3 | 3_1_place_gp_skip_io | 1.0 | overflow best 0.3514 last 0.3514 rows 34 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v1p5-3878624 | kv3_hg_v1p5 | 3_3_place_gp | 1.3 | overflow best 0.7568 last 0.7568 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v3-3828697 | kv3_hgi_v3 | 3_4_place_resized | 1.3 | last meaningful line 0.1 h ago (218/218 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v5-10769 | kv3_hgi_v5 | 3_3_place_gp | 1.1 | overflow best 0.1328 last 0.1328 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-serdes__t15__cla2127225-4147451 | serdes__t15 | pregrt_ff_hold | 3.9 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | 4_1_cts | 6.0 | last meaningful line 0.2 h ago (8488/8488 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_1_grt | 11.8 | last meaningful line 1.0 h ago (218/1105 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-2229034 | sle_stm_v2 | 5_1_grt | 4.9 | repair_Remaining best 117830 last 117830 rows 282 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_1_grt | 4.7 | last meaningful line 4.0 h ago (251/353 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1-967583 | eco_20261120_192428_3309571-i1 | 5_2_route | 3.2 | drt_violations best 19520 last 19520 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-eco_20261121_062659_3791260-i1t-171230 | eco_20261121_062659_3791260-i1t | 5_2_route | 1.0 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | so_1052270_ff_1300 | so_1052270_ff_1300 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (237/237 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_1052270_tt_1300 | so_1052270_tt_1300 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (237/237 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | 5_2_route | 15.1 | drt_violations best 154522 last 154522 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 5_2_route | 15.1 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 5_2_route | 15.1 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_2_route | 15.1 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 5_2_route | 15.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | eco-abs-1610199 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1029/1029 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1-1056647 | eco_20261120_174547_3236169-i1 | 5_2_route | 5.7 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1-2653275 | eco_20261120_182729_483429-i1 | 5_2_route | 4.7 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | so_1418581_ff_56530 | so_1418581_ff_56530 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | so_1418581_tt_56530 | so_1418581_tt_56530 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc10 | otc-3879822-9943 | 3879822 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 24.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_1_grt | 3.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_1_grt | 3.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_2_route | 8.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_2_route | 8.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_2_route | 8.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 11.1 | drt_violations best 54269 last 54269 rows 3 | before-window best 211425, window best 54269 | PROGRESS: drt_violations improved 74.3 % in window |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_2_route | 11.1 | drt_violations best 20 last 20 rows 61 | before-window best 148062, window best 20 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc10 | dpkit-serdes__t15__cla3d02796-1334076 | serdes__t15 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 11.9 | drt_violations best 13349 last 13349 rows 12 | before-window best 114805, window best 13349 | PROGRESS: drt_violations improved 88.4 % in window |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 28.7 | last meaningful line 1.1 h ago (1442/1442 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-serdes__t14-2383247 | serdes__t14 | 3_5_place_dp | 1.8 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-serdes__t16-2549394 | serdes__t16 | 3_5_place_dp | 1.7 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 18.2 | drt_violations best 9480 last 9480 rows 16 | before-window best 15693, window best 9480 | PROGRESS: drt_violations improved 39.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 14.3 | drt_violations best 12080 last 12080 rows 12 | before-window best 116798, window best 12080 | PROGRESS: drt_violations improved 89.7 % in window |  |
| epyc7 | dpkit-kv3_io_cor_v1-2072739 | kv3_io_cor_v1 | 5_1_grt | 0.9 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 15.2 | drt_violations best 14002 last 14002 rows 14 | before-window best 21086, window best 14002 | PROGRESS: drt_violations improved 33.6 % in window |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | tg_cts | 9.2 | repair_Violations best 0 last 0 rows 32 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-cbx_q10__cl89936551_h-1010361 | cbx_q10 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 10.9 | drt_violations best 236 last 236 rows 16 | before-window best 100396, window best 236 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 10.9 | drt_violations best 109 last 109 rows 19 | before-window best 99683, window best 109 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_1_grt | 4.1 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-1220503 | slice_station__t40 | 5_1_grt | 1.9 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_ctl-2618359 | hd_ctl | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 12.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t1-3235040 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-86131 | sle_ctl | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t36-616051 | slice_station__t36 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | 5_1_grt | 4.4 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_2_route | 11.8 | drt_violations best 810 last 810 rows 4 | before-window best 87555, window best 810 | PROGRESS: drt_violations improved 99.1 % in window |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_2_route | 12.5 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | 5_1_grt | 4.1 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
