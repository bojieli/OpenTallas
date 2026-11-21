# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 09:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 4, 'NO-PROGRESS': 1, 'GRT-LABEL': 33, 'YOUNG': 119, 'NO-DATA': 24, 'EXCLUDED': 6, 'KEEP': 1, 'PROGRESS': 38}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 25.4 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 38.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 38 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | tt_setup_repair_grt | 11.5 | repair_Viol best 2727 last 2727 rows 565 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -413.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-606014 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.8 | repair_TNS best 15467.9 last 15467.9 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -891.39 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_2_route | 13.1 | drt_violations best 151954 last 151954 rows 1 | before-window best 151954, window best 151954 | NO-PROGRESS: drt_violations best 151954 vs 151954 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 23.9 | grt rounds 3 overflow 5:62877 -> 10:60664 -> 15:49611 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-serdes__t15__cla3d02796-1334076 | serdes__t15 | 5_1_grt | 6.4 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 23.9 | grt rounds 4 overflow 5:56489 -> 10:43421 -> 15:40646 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 38.3 | grt rounds 4 overflow 5:8939 -> 10:4958 -> 15:3391 -> 20:2951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 27.6 | grt rounds 4 overflow 5:51489 -> 10:38067 -> 15:34597 -> 20:37772 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v1__clb036e152-4100253 | slw_st_a_v1 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:576 -> 10:153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 12.7 | grt rounds 6 overflow 5:6375 -> 10:5827 -> 15:5482 -> 20:5460 -> 25:8886 -> 30:7683 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 17.5 | grt rounds 3 overflow 5:87834 -> 10:75300 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 22.4 | grt rounds 3 overflow 5:61289 -> 10:67332 -> 15:79226 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:50395 -> 10:48872 -> 15:39905 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:50865 -> 10:49068 -> 15:39825 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 21.6 | grt rounds 3 overflow 5:46265 -> 10:49134 -> 15:43296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 9.3 | grt rounds 3 overflow 5:81129 -> 10:76153 -> 15:54687 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 17.5 | grt rounds 3 overflow 5:71046 -> 10:70742 -> 15:50882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 11.3 | grt rounds 3 overflow 5:77758 -> 10:70141 -> 15:82957 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 13.1 | grt rounds 4 overflow 5:41190 -> 10:38638 -> 15:36674 -> 20:37813 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 13.0 | grt rounds 3 overflow 5:34201 -> 10:37631 -> 15:32951 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 12.4 | grt rounds 4 overflow 5:20011 -> 10:12763 -> 15:11530 -> 20:11080 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 13.7 | grt rounds 5 overflow 5:4335 -> 10:1587 -> 15:1329 -> 20:1156 -> 25:2073 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_serdes-2625867 | hd_serdes | 5_1_grt | 3.3 | grt rounds 6 overflow 5:7569 -> 10:2911 -> 15:1153 -> 20:652 -> 25:686 -> 30:663 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 25.3 | grt rounds 3 overflow 5:26652 -> 10:13378 -> 15:8965 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 36.0 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 36.3 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:23529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 5_1_grt | 13.3 | grt rounds 5 overflow 5:108182 -> 10:5739 -> 15:4546 -> 20:4559 -> 25:4974 | GRT-LABEL: DESIGN-FAIL: overflow 5739 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 13.3 | grt rounds 4 overflow 5:51463 -> 10:8263 -> 15:5295 -> 20:4273 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 5_1_grt | 13.1 | grt rounds 5 overflow 5:60653 -> 10:2745 -> 15:1916 -> 20:1917 -> 25:2418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 18.8 | grt rounds 5 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8231 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 13.8 | grt rounds 3 overflow 5:32854 -> 10:32007 -> 15:25602 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 35.1 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50242 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 16.8 | grt rounds 5 overflow 5:35006 -> 10:1235 -> 15:721 -> 20:1026 -> 25:797 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 30.4 | grt rounds 3 overflow 5:60387 -> 10:47822 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 30.4 | grt rounds 3 overflow 5:61726 -> 10:48832 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: overflow 48832 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 30.6 | grt rounds 6 overflow 5:13197 -> 10:11019 -> 15:10179 -> 20:10000 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 17453.2 last 17453.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3507811 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 36284.9 last 36284.9 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | 5_2_route | 6.4 | drt_violations best 13701 last 13701 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984741 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.0 | repair_TNS best 221214 last 221214 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | 4_1_cts | 3.5 | last meaningful line 0.2 h ago (10532/10532 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 3_5_place_dp | 1.9 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | generate_abstract | 15.3 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3913104 | slice_station__t36 | postcts_gate_TT | 2.1 | last meaningful line 0.0 h ago (1525/1525 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i3-2847283 | eco_20261120_233525_2680444-i3 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (240/269 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i3t-1349005 | eco_20261121_014354_2681516-i3t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_1_grt | 1.4 | repair_Remaining best 215109 last 215109 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | tg2130-gen-2248319 | tg2130-gen | 4_1_cts | 0.6 | repair_Violations best 109 last 130 rows 13 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2301911 | col_h10_r1__t1 | 5_2_route | 6.8 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3129306 | col_h9_r2__t1 | 5_2_route | 3.1 | last meaningful line 0.1 h ago (256/256 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 2_1_floorplan | 0.7 | last meaningful line 0.2 h ago (1415/1415 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-72198 | kv3_hub_Ei | 3_3_place_gp | 2.4 | overflow best 0.0987 last 0.0987 rows 44 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Eo-3667498 | kv3_hub_Eo | 3_4_place_resized | 2.8 | last meaningful line 0.3 h ago (470/470 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v1-1304161 | kv3_pv_v1 | 3_1_place_gp_skip_io | 1.5 | overflow best 0.8254 last 0.8254 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v4n-4044420 | kv3_pv_v4n | 3_3_place_gp | 2.5 | overflow best 0.7078 last 0.7104 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v5n-4101656 | kv3_pv_v5n | 3_1_place_gp_skip_io | 2.5 | overflow best 0.6759 last 0.6759 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-kv3_sys_c-1929757 | kv3_sys_c | 3_5_place_dp | 1.0 | last meaningful line 0.1 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_2_route | 16.1 | drt_violations best 102898 last 102898 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_2_route | 16.1 | drt_violations best 105345 last 105345 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 5_2_route | 15.9 | drt_violations best 91857 last 91857 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | 5_1_grt | 6.6 | last meaningful line 0.1 h ago (210/213 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_1_grt | 6.7 | last meaningful line 0.0 h ago (238/240 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | generate_abstract | 16.7 | last meaningful line 0.2 h ago (583/583 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (5013/5013 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 6_report | 16.7 | last meaningful line 0.1 h ago (1060/1060 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | pregrt_ff_hold | 6.7 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v2-2660942 | slw_sc_v2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.178 last 0.191 rows 49 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_1_grt | 6.7 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_2_route | 16.7 | drt_violations best 8414 last 8414 rows 2 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | hold_gate | 3.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3139937-10079 | 3139937 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-3139939-87 | 3139939 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-3139948-17961 | 3139948 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-3139954-5937 | 3139954 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-3140001-9209 | 3140001 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261120_134605_3273412-i3t-147310 | eco_20261120_134605_3273412-i3t | 5_2_route | 2.4 | drt_violations best 17755 last 17755 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 3.6 | drt_violations best 72780 last 72780 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 6.4 | drt_violations best 3 last 5 rows 30 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1t-551142 | eco_20261121_070700_2142563-i1t | 5_2_route | 2.1 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1t-1786242 | eco_20261121_080323_3018643-i1t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2-3115487 | eco_recover1120-i2 | 5_2_route | 3.1 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | so_2864375_ff_48210 | so_2864375_ff_48210 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | so_2864375_tt_48210 | so_2864375_tt_48210 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | so_3013619_ff_39610 | so_3013619_ff_39610 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3013619_tt_39610 | so_3013619_tt_39610 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-bk_sel__t2-3570513 | bk_sel__t2 | 3_3_place_gp | 1.4 | overflow best 0.227 last 0.227 rows 41 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-bk_sel__t2-3749761 | bk_sel__t2 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-549685 | cbf_q00 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.902 last 0.9082 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-coll_core-403986 | coll_core | 3_3_place_gp | 0.5 | overflow best 0.625 last 0.625 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-3049707 | hd_lep0N | 3_5_place_dp | 1.9 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-4080505 | hd_serdes | tt_setup_repair_grt | 4.5 | last meaningful line 0.3 h ago (15/15 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_spn-86625 | hd_spn | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_io_cor_v1-2072739 | kv3_io_cor_v1 | 5_2_route | 2.7 | last meaningful line 0.1 h ago (252/253 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-126252 | kv3_pv_v5 | 2_1_floorplan | 0.7 | last meaningful line 0.2 h ago (1419/1419 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t16-3705242 | serdes__t16 | 3_3_place_gp | 1.3 | overflow best 0.8205 last 0.8205 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 5_2_route | 13.0 | drt_violations best 77104 last 77104 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | 4_1_cts | 3.0 | last meaningful line 0.2 h ago (5131/5131 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-319942 | sle_sc_v1 | 3_3_place_gp | 0.6 | overflow best 0.3728 last 0.3728 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | generate_abstract | 16.7 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_2_route | 16.7 | drt_violations best 9 last 9 rows 7 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | generate_abstract | 12.8 | last meaningful line 0.1 h ago (312/312 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-28507 | slw_sc_v1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 6.6 | drt_violations best 4 last 4 rows 40 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 23.8 |  | NO-DATA: no log found |  |
| epyc7 | ot-sc-eco-pinkeep-1440767 | ot-sc-eco-pinkeep | - | 3.1 |  | NO-DATA: no log found |  |
| epyc7 | ot-sc-eco-pinkeep-452342 | ot-sc-eco-pinkeep | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261121_100942_929932-i1t-881383 | eco_20261121_100942_929932-i1t | 5_2_route | 7.0 | drt_violations best 22124 last 22124 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | so_308683_ff_51250 | so_308683_ff_51250 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc7 | so_308683_tt_51250 | so_308683_tt_51250 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc8 | clkgrt-base-940398 | clkgrt-base | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-clkfirst-942175 | clkgrt-clkfirst | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-hook-1261552 | clkgrt-hook | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-nondr-945214 | clkgrt-nondr | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-resaware-943509 | clkgrt-resaware | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t9-950441 | dsdv_slice_c1x_C__t9 | 3_3_place_gp | 3.6 | overflow best 0.7816 last 0.7816 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-4122597 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.4 | repair_TNS best 123920 last 123920 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-glue-504992 | glue | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (275/275 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_2_route | 1.6 | drt_violations best 860 last 860 rows 10 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-3963353 | kv3_hg_v3 | 3_5_place_dp | 1.5 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3818815 | kv3_io_cor_v1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3-3975648 | kv3_pv_v3 | 3_1_place_gp_skip_io | 1.5 | overflow best 0.7891 last 0.7891 rows 20 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v4-4030403 | kv3_pv_v4 | 3_1_place_gp_skip_io | 1.5 | overflow best 0.8121 last 0.8121 rows 13 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-34918 | kv3_pv_v6 | 2_1_floorplan | 1.3 | last meaningful line 0.8 h ago (1179/1179 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t14-231016 | serdes__t14 | 3_3_place_gp | 1.2 | overflow best 0.8549 last 0.8549 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (4575/4575 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-1220503 | slice_station__t40 | 5_2_route | 3.4 | last meaningful line 0.2 h ago (251/252 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | hold_gate | 3.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-3736166 | slw_st_a_v2 | 5_1_grt | 1.7 | repair_Remaining best 163814 last 163814 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 52.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-3942727-31370 | 3942727 | orfs_synth | 1.5 | last meaningful line 1.5 h ago (428/428 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | otc-559540-13695 | 559540 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261121_140125_4181979-i1-2046754 | eco_20261121_140125_4181979-i1 | 5_2_route | 2.9 | drt_violations best 53 last 53 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-kv3-hg-v1p6-grt-1606052 | kv3-hg-v1p6-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_1_grt | 2.7 | repair_TNS best 14197.7 last 14197.7 rows 5 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.7 | repair_TNS best 227530 last 227530 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | tt_setup_repair_grt | 10.0 | repair_Viol best 2476 last 2476 rows 236 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-2618359 | hd_ctl | pregrt_ff_hold | 3.3 | repair_Violations best 195 last 195 rows 6 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-3513884 | hd_serdes | tt_setup_repair_grt | 2.6 | repair_Viol best 585 last 585 rows 60 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | pregrt_ff_hold | 1.3 | repair_TNS best 210366 last 210366 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | pregrt_ff_hold | 5.9 | repair_Violations best 1203 last 1203 rows 22 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3n-113758 | kv3_pv_v3n | 3_3_place_gp | 1.9 | last meaningful line 0.0 h ago (595/595 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-492382 | sle_ctl | 5_1_grt | 4.9 | last meaningful line 0.0 h ago (215/221 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-86131 | sle_ctl | 5_1_grt | 5.2 | repair_Viol best 558 last 558 rows 37 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | 4_1_cts | 3.3 | last meaningful line 0.1 h ago (5515/5515 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-1095767 | sle_su_l1 | tt_setup_repair_grt | 4.5 | repair_Remaining best 244695 last 244695 rows 71 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-slice_station__t36-616051 | slice_station__t36 | 5_1_grt | 4.8 | repair_Viol best 26 last 26 rows 11 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | 5_2_route | 5.9 | last meaningful line 0.0 h ago (252/253 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_2_route | 17.4 | drt_violations best 22873 last 22873 rows 3 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 8.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 8.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 8.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_2_route | 10.0 | drt_violations best 39 last 39 rows 50 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i1-3833068 | eco_20261121_143815_74711-i1 | 5_2_route | 2.3 | drt_violations best 1158 last 1158 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_154823_2000128-i1-767217 | eco_20261121_154823_2000128-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (256/256 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-fin-1606220 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (299/299 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | ap-ageom-kw-dsdv-slice-lepe-nh-mus-C--t1-dump-2763633 | dsdv-slice-lepe-nh-mus-C--t1-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-dsdv-slice-lepe-nh-mus-C--t1-grt-2763633 | dsdv-slice-lepe-nh-mus-C--t1-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 13.1 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | tt_setup_repair_grt | 5.6 | last meaningful line 0.0 h ago (341/341 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg-2345328 | kv3_hg | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p5-3878624 | kv3_hg_v1p5 | 3_5_place_dp | 2.8 | last meaningful line 0.5 h ago (46/46 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-serdes__t15__cla2127225-4147451 | serdes__t15 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (203/206 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | tt_setup_repair | 7.5 | repair_Viol best 631 last 631 rows 575 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_1_grt | 13.3 | last meaningful line 0.2 h ago (1251/1303 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | 5_1_grt | 6.4 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1-967583 | eco_20261120_192428_3309571-i1 | 5_2_route | 4.7 | drt_violations best 6883 last 6883 rows 5 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3448184 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8911 last 0.9157 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t39-3371903 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.3 | overflow best 0.5366 last 0.5366 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-serdes__t4-2773288 | serdes__t4 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.8854 last 0.8854 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 5_2_route | 16.8 | drt_violations best 86249 last 86249 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 5_2_route | 16.9 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t37-3254344 | slice_station__t37 | 3_3_place_gp | 0.4 | overflow best 0.3418 last 0.3418 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_2_route | 16.9 | drt_violations best 82738 last 82738 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 5_2_route | 16.8 | drt_violations best 88159 last 88159 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | eco-abs-3672577 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (920/920 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1-2653275 | eco_20261120_182729_483429-i1 | 5_2_route | 6.4 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | prd-eco_20261121_072804_212710-i1t-1822102 | eco_20261121_072804_212710-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-2335388-30734 | 2335388 | - | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 25.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_1_grt | 5.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_1_grt | 5.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_2_route | 9.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_2_route | 9.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_2_route | 9.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 13.1 | drt_violations best 30561 last 30561 rows 6 | before-window best 211425, window best 30561 | PROGRESS: drt_violations improved 85.5 % in window |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 5_1_grt | 5.7 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 13.1 | drt_violations best 37186 last 37186 rows 2 | before-window best 196822, window best 37186 | PROGRESS: drt_violations improved 81.1 % in window |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 13.9 | drt_violations best 11104 last 11104 rows 14 | before-window best 39950, window best 11104 | PROGRESS: drt_violations improved 72.2 % in window |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 30.5 | last meaningful line 0.3 h ago (1487/1487 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_1_grt | 6.6 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 19.9 | drt_violations best 9406 last 49919 rows 18 | before-window best 11994, window best 9406 | PROGRESS: drt_violations improved 21.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 16.1 | drt_violations best 11011 last 11011 rows 13 | before-window best 34316, window best 11011 | PROGRESS: drt_violations improved 67.9 % in window |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 17.0 | drt_violations best 13507 last 13507 rows 15 | before-window best 16834, window best 13507 | PROGRESS: drt_violations improved 19.8 % in window |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | tg_cts | 10.9 | repair_Violations best 0 last 0 rows 32 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-cbx_q10__cl89936551_h-1010361 | cbx_q10 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 12.4 | drt_violations best 24 last 24 rows 39 | before-window best 100396, window best 24 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 12.4 | drt_violations best 55 last 55 rows 24 | before-window best 99683, window best 55 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-4110897 | kv3_hroot | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_1_grt | 5.6 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t51-719348 | slice_station__t51 | 5_1_grt | 3.8 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | tt_setup_repair_grt | 5.4 | repair_Violations best 0 last 0 rows 21 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | 5_1_grt | 6.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-2229034 | sle_stm_v2 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_1_grt | 6.2 | last meaningful line 5.5 h ago (251/353 lines) | PROGRESS: log still growing |  |
