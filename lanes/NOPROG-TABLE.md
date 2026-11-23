# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 09:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 3, 'GRT-LABEL': 3, 'YOUNG': 114, 'NO-DATA': 19, 'EXCLUDED': 1, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | 5_1_grt | 4.2 | grt rounds 2 overflow 5:8198 -> 10:8148 | UNSIGNABLE: GRT overflow flat: overflow 8198 at iteration 5 -> 8148 at iteration 10: flat fo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | tt_setup_repair_grt | 25.4 | repair_Violations best 39 last 45 rows 22 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -1099.97 ps (< -300, gate TT >= -42); j | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 42.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 8.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.6 | repair_TNS best 2477.76 last 2477.76 rows 1 | before-window best 2477.76, window best 2477.76 | NO-PROGRESS: repair_TNS best 2477.76 vs 2477.76 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FAM-S81-MISC-R4 decides |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | 5_1_grt | 5.2 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 10.7 | grt rounds 2 overflow 5:43627 -> 10:30741 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 8.7 | grt rounds 2 overflow 5:11530 -> 10:1570 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3196104 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.4 | overflow best 0.3162 last 0.3176 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3328962 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3154 last 0.3154 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (7232/7232 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 3.9 | repair_TNS best 924724 last 924724 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 5.3 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t2-2430221 | serdes__t2 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.2803 last 0.2803 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 6_report | 9.1 | last meaningful line 0.1 h ago (959/959 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3392923 | slice_station__t36 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (361/361 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t52-3523691 | slice_station__t52 | 3_2_place_iop | 0.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-2367622-7114 | 2367622 | place | 1.0 | last meaningful line 0.1 h ago (993/993 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-2705414-4704 | 2705414 | place | 0.7 | last meaningful line 0.0 h ago (1007/1007 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-3131557-3816 | 3131557 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-3204193-1763 | 3204193 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-3090789 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2-3082261 | eco_20261122_223531_3628570-i2 | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (235/253 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2t-1170770 | eco_20261123_075519_12410-i2t | 5_2_route | 1.9 | drt_violations best 101 last 101 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_152004_738176-i1t-1508677 | eco_20261123_152004_738176-i1t | 5_2_route | 1.6 | drt_violations best 1789 last 1789 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-col-h9-r1--t1--clf32cde8d--pv387d6579-grt-2953573 | col-h9-r1--t1--clf32cde8d--pv387d6579-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2925568 | col_h9_r1__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3589 last 3589 rows 697 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 14.8 | last meaningful line 1.8 h ago (211/214 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 13.7 | last meaningful line 3.3 h ago (211/219 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_4_floorplan_pdn | 4.2 | last meaningful line 0.2 h ago (175/175 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2548393 | kv3_sys_c | 3_3_place_gp | 0.3 | overflow best 0.641 last 0.641 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 6_report | 17.1 | last meaningful line 0.2 h ago (1072/1072 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 6_report | 17.0 | last meaningful line 0.1 h ago (1070/1070 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | generate_abstract | 17.0 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 14.8 | drt_violations best 155489 last 155489 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 14.6 | drt_violations best 152818 last 152818 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | eco-abs-2399230 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.2 h ago (971/971 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-2442642-28038 | 2442642 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-2501645-16924 | 2501645 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-2851436-24762 | 2851436 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1t-1139635 | eco_20261123_073408_3918836-i1t | 5_2_route | 1.4 | drt_violations best 1789 last 1789 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | prd-fin-2037456 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (1070/1070 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | so_2587059_ff_28409 | so_2587059_ff_28409 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | so_2587059_tt_28409 | so_2587059_tt_28409 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | so_2926738_ff_35445 | so_2926738_ff_35445 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2926738_tt_35445 | so_2926738_tt_35445 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | 6_1_fill | 3.8 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 4.9 | drt_violations best 60059 last 60059 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.6 | last meaningful line 0.0 h ago (61/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4013616 | col_h9_r1__t1 | postcts_gate_FF | 3.6 | last meaningful line 0.0 h ago (536/536 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 7.4 | drt_violations best 172065 last 172065 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 7.3 | last meaningful line 3.2 h ago (211/217 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_2_tapbal_grt | 2.3 | last meaningful line 0.5 h ago (48/51 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3630066 | hd_lep0N | 3_1_place_gp_skip_io | 0.4 | overflow best 0.4809 last 0.4809 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_4_place_resized | 4.7 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | tt_setup_measure_grt | 3.9 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dtrial-clock-4030744 | dtrial-clock | ctree_FF | 0.0 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-4028104-20675 | 4028104 | otrun | 0.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 2.5 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 8.9 | last meaningful line 0.5 h ago (298/299 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_2_route | 4.3 | drt_violations best 37 last 37 rows 5 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 3.1 | drt_violations best 556 last 556 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1t-2913491 | eco_20261123_160238_2681508-i1t | 5_2_route | 0.9 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_3450761_ff_84118 | so_3450761_ff_84118 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_3450761_tt_84118 | so_3450761_tt_84118 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pva2370bfd-2928201 | col_h9_r1__t1 | 3_2_place_iop | 0.2 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-871345 | dsdv_slice_c1x_C__t10 | 3_1_place_gp_skip_io | 2.4 | overflow best 0.3226 last 0.3226 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 14.8 | last meaningful line 4.8 h ago (211/220 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 5.5 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | tt_setup_repair | 1.9 | repair_Violations best 98 last 758 rows 52 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 3.5 | last meaningful line 0.2 h ago (9948/9948 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_c-98167 | sle_su_c | 3_3_place_gp | 1.0 | overflow best 0.1964 last 0.2025 rows 44 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-slice_station__t12-3181944 | slice_station__t12 | tt_setup_repair | 0.1 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t41-976663 | slice_station__t41 | 3_5_place_dp | 0.8 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-981912 | slice_station__t43 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-2074686 | slice_station__t49 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-2069863 | slice_station__t50 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl503f4913-3142679 | slice_station__t7 | tt_setup_repair | 0.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2076901-15454 | 2076901 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-2589646-18511 | 2589646 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-2597209-24399 | 2597209 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-2655894-29242 | 2655894 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-3389120-21250 | 3389120 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-50076 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1t-81578 | eco_20261123_140713_549985-i1t | 5_2_route | 2.9 | drt_violations best 7895 last 7895 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1t-2511984 | eco_20261123_163717_2005956-i1t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (236/913 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 12.7 | drt_violations best 183055 last 183055 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 14.5 | last meaningful line 4.5 h ago (216/223 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 2.6 | last meaningful line 0.8 h ago (10919/10919 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 10.0 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 8.7 | last meaningful line 0.0 h ago (454/460 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 9.8 | repair_TNS best 329.729 last 329.729 rows 10 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | postcts_gate_FF | 12.6 | last meaningful line -0.0 h ago (25514/25514 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 11.8 | repair_TNS best 33416.3 last 33416.3 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | postcts_gate_TT | 8.8 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 11.7 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_2_route | 12.4 | drt_violations best 15904 last 15904 rows 2 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 12.5 | last meaningful line 0.0 h ago (273/274 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 10.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-3717770-25074 | 3717770 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3718222-168 | 3718222 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3760323-29411 | 3760323 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3770058-2473 | 3770058 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3804526-22793 | 3804526 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (391/391 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-3826945-12291 | 3826945 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (370/370 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-3831863-17850 | 3831863 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (505/505 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-928970-21237 | 928970 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i1-3529532 | eco_20261123_142403_3177550-i1 | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (230/582 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 1.4 |  | NO-DATA: no log found |  |
| epyc9 | so_3420887_ff_67642 | so_3420887_ff_67642 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_3420887_tt_67642 | so_3420887_tt_67642 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 14.8 | drt_violations best 1393 last 1393 rows 8 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 3.5 | last meaningful line 0.2 h ago (253/254 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 4.9 | last meaningful line 0.2 h ago (7320/7320 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | postcts_gate_TT | 12.4 | last meaningful line 0.0 h ago (1865/1865 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t31-2409576 | slice_station__t31 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_2_route | 13.6 | drt_violations best 70075 last 70075 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 13.1 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-2359243-22693 | 2359243 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-2452779-29048 | 2452779 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 2.9 | drt_violations best 42348 last 42348 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-fin-304945 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | so_2158499_ff_16392 | so_2158499_ff_16392 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_2158499_tt_16392 | so_2158499_tt_16392 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_2487451_ff_83364 | so_2487451_ff_83364 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | so_2487451_tt_83364 | so_2487451_tt_83364 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 5_1_grt | 5.3 | last meaningful line 0.5 h ago (217/225 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 5.0 | repair_Remaining best 27182 last 27182 rows 158 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1263597 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-1641814 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 3_3_place_gp | 7.4 | overflow best 0.0987 last 0.0987 rows 44 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-67781 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 3.7 | drt_violations best 19526 last 19526 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 2.3 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | so_1903669_ff_38429 | so_1903669_ff_38429 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_1903669_tt_38429 | so_1903669_tt_38429 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | otc-3392194-17193 | 3392194 | - | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 12.1 | drt_violations best 19416 last 19416 rows 11 | before-window best 28584, window best 19416 | PROGRESS: drt_violations improved 32.1 % in window |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 10.4 | drt_violations best 1269 last 1728 rows 21 | before-window best 87459, window best 1269 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | 5_1_grt | 3.4 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 14.8 | drt_violations best 2057 last 2057 rows 12 | before-window best 112571, window best 2057 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 17.0 | drt_violations best 10583 last 10583 rows 12 | before-window best 13388, window best 10583 | PROGRESS: drt_violations improved 21.0 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 13.6 | drt_violations best 50311 last 50311 rows 10 | before-window best 78520, window best 50311 | PROGRESS: drt_violations improved 35.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 14.0 | drt_violations best 52820 last 52820 rows 11 | before-window best 75867, window best 52820 | PROGRESS: drt_violations improved 30.4 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 19.7 | drt_violations best 5 last 5 rows 37 | before-window best 409476, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 14.7 | drt_violations best 65161 last 65161 rows 10 | before-window best 76194, window best 65161 | PROGRESS: drt_violations improved 14.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 25.4 | drt_violations best 25 last 25 rows 44 | before-window best 56, window best 25 | PROGRESS: drt_violations improved 55.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 28.8 | drt_violations best 7732 last 9662 rows 19 | before-window best 12904, window best 7732 | PROGRESS: drt_violations improved 40.1 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 16.3 | drt_violations best 14710 last 63695 rows 18 | before-window best 15880, window best 14710 | PROGRESS: drt_violations improved 7.4 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 12.2 | last meaningful line 2.2 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 9.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 8.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 28.5 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 55928 < best completed total 175829 (in-iter |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 28.2 | drt_violations best 37187 last 37187 rows 8 | before-window best 60023, window best 37187 | PROGRESS: drt_violations improved 38.0 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 26.7 | drt_violations best 15921 last 15921 rows 2 | before-window best 109763, window best 15921 | PROGRESS: drt_violations improved 85.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 14.9 | drt_violations best 93635 last 93635 rows 5 | before-window best 344103, window best 93635 | PROGRESS: drt_violations improved 72.8 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 12.2 | drt_violations best 2611 last 2611 rows 7 | before-window best 90237, window best 2611 | PROGRESS: drt_violations improved 97.1 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 22.2 | drt_violations best 2944 last 2944 rows 14 | before-window best 88165, window best 2944 | PROGRESS: drt_violations improved 96.7 % in window |  |
