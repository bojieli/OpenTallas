# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 09:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'GRT-LABEL': 3, 'NO-DATA': 9, 'YOUNG': 108, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | tt_setup_repair_grt | 5.7 | repair_Remaining best 140267 last 140267 rows 47 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -343.63 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 42.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | tt_setup_repair | 5.4 | repair_Viol best 6195 last 6195 rows 4 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -1222.99 ps (< -300, gate TT >= -42); job a | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 11.2 | grt rounds 2 overflow 5:43627 -> 10:30741 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:102125 -> 10:67 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 9.2 | grt rounds 2 overflow 5:11530 -> 10:1570 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-slice-station--t52-grt-261859 | slice-station--t52-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-98467 | bk_sel__t2 | 2_1_floorplan | 0.1 | repair_Viol best 3776 last 3776 rows 376 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 1.7 | repair_TNS best 129247 last 129247 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 4.4 | repair_TNS best 924724 last 924724 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 5.8 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 5_2_route | 9.3 | drt_violations best 88524 last 88524 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t24__cleece78ec-86117 | slice_station__t24 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1440/1440 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3392923 | slice_station__t36 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-274226-16996 | 274226 | cts_0928 | 0.0 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3834020-29448 | 3834020 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4440/4440 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-3912573-32237 | 3912573 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-4042710-1276 | 4042710 | cts_0914 | 0.3 | last meaningful line 0.0 h ago (3906/3906 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-1508677 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2-3082261 | eco_20261122_223531_3628570-i2 | 5_1_grt | 1.0 | last meaningful line 0.5 h ago (235/1294 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2t-1170770 | eco_20261123_075519_12410-i2t | 5_2_route | 2.4 | drt_violations best 101 last 101 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-fin-3090789 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (449/449 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | so_250350_ff_2367 | so_250350_ff_2367 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | so_250350_tt_2367 | so_250350_tt_2367 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-3453813 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.3333 last 0.3464 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3399753 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 15.3 | last meaningful line 2.3 h ago (211/215 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 14.2 | last meaningful line 3.8 h ago (211/220 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_4_floorplan_pdn | 4.7 | last meaningful line 0.7 h ago (175/175 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | tt_setup_repair_grt | 3.9 | repair_Viol best 219 last 219 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | generate_abstract | 17.6 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | generate_abstract | 17.5 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 15.3 | drt_violations best 155489 last 155489 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 15.1 | drt_violations best 152818 last 152818 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | eco-abs-3092443 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2t-3323150 | eco_20261122_164248_3895049-i2t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1t-1139635 | eco_20261123_073408_3918836-i1t | 5_2_route | 1.9 | drt_violations best 1789 last 1789 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | so_3548432_ff_99716 | so_3548432_ff_99716 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3548432_tt_99716 | so_3548432_tt_99716 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3630214_ff_37991 | so_3630214_ff_37991 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (977/977 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_3630214_tt_37991 | so_3630214_tt_37991 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (977/977 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 5.4 | drt_violations best 60059 last 60059 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 7.9 | drt_violations best 172065 last 172065 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 7.8 | last meaningful line 3.7 h ago (211/218 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-4158953 | hd_ctl | 3_3_place_gp | 0.4 | overflow best 0.2988 last 0.5541 rows 130 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_2_tapbal_grt | 2.8 | last meaningful line 1.0 h ago (48/53 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3630066 | hd_lep0N | 3_3_place_gp | 0.9 | last meaningful line 0.2 h ago (196/196 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-4154426 | hd_lep0N_w | 4_2_tapbal_grt | 0.4 | last meaningful line 0.0 h ago (46/51 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_4_place_resized | 5.2 | last meaningful line 0.2 h ago (695/695 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 3.0 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 9.4 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 3.6 | drt_violations best 556 last 556 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1t-2913491 | eco_20261123_160238_2681508-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1t-259914 | eco_20261123_171842_3718765-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-fin-3256093 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-871345 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 2.9 | overflow best 0.1994 last 0.1994 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 6.0 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 2.4 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 4.0 | last meaningful line 0.1 h ago (9993/9993 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t12-3181944 | slice_station__t12 | postcts_gate_TT | 0.6 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | pregrt_ff_hold | 0.5 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3641/3641 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3107/3107 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2716/2717 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (3278/3278 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t47-118217 | slice_station__t47 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1860/1860 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3504/3504 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3178/3178 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2700/2700 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | pregrt_ff_hold | 0.3 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl503f4913-3142679 | slice_station__t7 | postcts_gate_TT | 0.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl945bc067-3551157 | slice_station__t7 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (450/480 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-2076901-15454 | 2076901 | gen_lint_yosys | 1.0 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | otc-2589646-18511 | 2589646 | gen_lint_yosys | 0.8 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | otc-2597209-24399 | 2597209 | gen_lint_yosys | 0.8 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | otc-2655894-29242 | 2655894 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | otc-469218-30553 | 469218 | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-81578 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1t-2511984 | eco_20261123_163717_2005956-i1t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 0.8 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | prd-fin-50076 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (61/61 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 13.4 | drt_violations best 183055 last 183055 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 3.3 | last meaningful line 0.1 h ago (11052/11052 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 10.8 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-157767 | phy__t1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (165/165 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 10.5 | repair_TNS best 27.784 last 27.784 rows 9 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_2_route | 13.3 | last meaningful line 0.0 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 12.5 | repair_TNS best 27016.7 last 27016.7 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_2_route | 9.5 | last meaningful line 0.0 h ago (269/269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 12.5 | last meaningful line 0.2 h ago (288/289 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 6_report | 13.2 | last meaningful line 0.1 h ago (1073/1073 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 13.3 | last meaningful line 0.1 h ago (287/288 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 11.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-270986-6387 | 270986 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-349452-30016 | 349452 | orfs_synth | 0.2 | last meaningful line 0.2 h ago (370/370 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-472895-6086 | 472895 | orfs_synth | 0.1 | last meaningful line 0.1 h ago (607/607 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 2.2 | last meaningful line 0.2 h ago (290/291 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i1-3529532 | eco_20261123_142403_3177550-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (258/259 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 2.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pve3ab90e7-2788719 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.2533 last 0.2746 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (298/1302 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 4.0 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-native59-2836475 | native59 | synth_odb_v | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | postcts_gate_FF | 12.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_2_route | 14.1 | drt_violations best 6175 last 6175 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 13.6 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-2359243-22693 | 2359243 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | otc-2452779-29048 | 2452779 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-2610275-27266 | 2610275 | asbuilt.yosys | 0.4 | last meaningful line 0.0 h ago (227067/227067 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-2759871-31481 | 2759871 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (1404/1404 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-2885480-28772 | 2885480 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3032456-14921 | 3032456 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 3.4 | drt_violations best 42348 last 42348 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2-2683723 | eco_20261122_165619_1517073-i2 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (253/504 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 5.5 | repair_TNS best 87.254 last 87.254 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1263597 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2320782 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 3_3_place_gp | 7.9 | overflow best 0.0987 last 0.0987 rows 44 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 4.2 | drt_violations best 19526 last 19526 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 2.8 | drt_violations best 40447 last 40447 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t2-2430221 | serdes__t2 | 3_5_place_dp | 1.4 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 12.6 | drt_violations best 19416 last 19416 rows 11 | before-window best 28584, window best 19416 | PROGRESS: drt_violations improved 32.1 % in window |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 10.9 | drt_violations best 1269 last 1693 rows 22 | before-window best 87459, window best 1269 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 15.3 | drt_violations best 1983 last 1983 rows 13 | before-window best 112571, window best 1983 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 17.5 | drt_violations best 10583 last 10583 rows 12 | before-window best 12997, window best 10583 | PROGRESS: drt_violations improved 18.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 14.1 | drt_violations best 48060 last 48060 rows 11 | before-window best 71122, window best 48060 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 14.5 | drt_violations best 52820 last 52820 rows 11 | before-window best 62246, window best 52820 | PROGRESS: drt_violations improved 15.1 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 7.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 20.2 | drt_violations best 5 last 5 rows 43 | before-window best 409476, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 15.2 | drt_violations best 60407 last 60407 rows 11 | before-window best 76194, window best 60407 | PROGRESS: drt_violations improved 20.7 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 25.9 | drt_violations best 23 last 23 rows 47 | before-window best 55, window best 23 | PROGRESS: drt_violations improved 58.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 29.3 | drt_violations best 7732 last 9662 rows 19 | before-window best 9545, window best 7732 | PROGRESS: drt_violations improved 19.0 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-3501815 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 33 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 16.8 | drt_violations best 14710 last 63695 rows 18 | before-window best 15880, window best 14710 | PROGRESS: drt_violations improved 7.4 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 12.7 | last meaningful line 2.7 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | pregrt_ff_hold | 0.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 15.3 | last meaningful line 5.3 h ago (216/224 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 10.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 9.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 13.3 | repair_TNS best 548.089 last 548.089 rows 12 | before-window best 2477.76, window best 548.089 | PROGRESS: repair_TNS improved 77.9 % in window |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 29.0 | drt_violations best 33068 last 33068 rows 2 | before-window best 175829, window best 33068 | PROGRESS: drt_violations improved 81.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 28.7 | drt_violations best 36675 last 36675 rows 9 | before-window best 40912, window best 36675 | PROGRESS: drt_violations improved 10.4 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 27.2 | drt_violations best 12443 last 12443 rows 3 | before-window best 109763, window best 12443 | PROGRESS: drt_violations improved 88.7 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 15.4 | drt_violations best 93635 last 93635 rows 5 | before-window best 344103, window best 93635 | PROGRESS: drt_violations improved 72.8 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 12.7 | drt_violations best 2373 last 2373 rows 9 | before-window best 90237, window best 2373 | PROGRESS: drt_violations improved 97.4 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 22.7 | drt_violations best 2425 last 2425 rows 15 | before-window best 88165, window best 2425 | PROGRESS: drt_violations improved 97.2 % in window |  |
| intel2 | dpkit-slice_station__t12-2343147 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
