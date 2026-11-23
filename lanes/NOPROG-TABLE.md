# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 09:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 2, 'GRT-LABEL': 3, 'NO-DATA': 9, 'YOUNG': 109, 'PROGRESS': 35}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | tt_setup_repair_grt | 5.7 | repair_Remaining best 140267 last 140267 rows 47 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -343.63 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 42.7 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 11.0 | repair_TNS best 421499 last 421499 rows 1 | before-window best 421499, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-KV-PV-SINKSPR |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 11.5 | grt rounds 2 overflow 5:43627 -> 10:30741 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 5_1_grt | 6.1 | grt rounds 2 overflow 5:102125 -> 10:67 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 9.4 | grt rounds 2 overflow 5:11530 -> 10:1570 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
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
| epyc2 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv3a0a8b60-grt-3868525 | col-h9-r1--t1--cl49d7a23e--pv3a0a8b60-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3900914 | col_h9_r1__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3399753 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-3749481 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 15.5 | last meaningful line 2.5 h ago (211/215 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 14.4 | last meaningful line 4.0 h ago (211/220 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_1_place_gp_skip_io | 4.9 | overflow best 0.5354 last 0.5354 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | generate_abstract | 17.8 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | generate_abstract | 17.8 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 15.6 | drt_violations best 155489 last 155489 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 15.4 | drt_violations best 19584 last 19584 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | eco-abs-3092443 | eco-abs | generate_abstract | 0.7 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2t-3323150 | eco_20261122_164248_3895049-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (238/356 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_092856_2078955-i1-3664424 | eco_20261123_092856_2078955-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_3548432_ff_99716 | so_3548432_ff_99716 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | so_3548432_tt_99716 | so_3548432_tt_99716 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | so_3630214_ff_37991 | so_3630214_ff_37991 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (977/977 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | so_3630214_tt_37991 | so_3630214_tt_37991 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (977/977 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 5.7 | drt_violations best 10190 last 10190 rows 2 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 429406 last 429406 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 8.2 | drt_violations best 37506 last 37506 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 8.0 | last meaningful line 4.0 h ago (211/218 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-4158953 | hd_ctl | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_2_tapbal_grt | 3.0 | last meaningful line 1.3 h ago (48/54 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3630066 | hd_lep0N | 3_3_place_gp | 1.1 | overflow best 0.3422 last 0.3422 rows 24 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-4154426 | hd_lep0N_w | 4_2_tapbal_grt | 0.7 | last meaningful line 0.3 h ago (46/67 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_4_place_resized | 5.4 | last meaningful line 0.5 h ago (695/695 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 3.3 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 9.6 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 3.9 | drt_violations best 556 last 556 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1t-2913491 | eco_20261123_160238_2681508-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1t-259914 | eco_20261123_171842_3718765-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (251/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-fin-3256093 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (834/834 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-871345 | dsdv_slice_c1x_C__t10 | 3_5_place_dp | 3.2 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 6.3 | repair_TNS best 37684 last 37684 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 2.6 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 4.2 | last meaningful line 0.3 h ago (9993/9993 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t12-3181944 | slice_station__t12 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (3985/3985 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3029/3029 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3655/3655 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3816/3816 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | tt_setup_repair | 0.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | 5_1_grt | 0.5 | repair_Remaining best 87687 last 87687 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (260/454 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl362204c4-739195 | slice_station__t7 | 3_3_place_gp | 0.1 | overflow best 0.2574 last 0.2584 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t7__cl503f4913-3142679 | slice_station__t7 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl945bc067-3551157 | slice_station__t7 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (158/158 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1t-2511984 | eco_20261123_163717_2005956-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 1.0 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-fin-81578 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 13.7 | drt_violations best 33830 last 33830 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl23f6a148-767022 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8517 last 8517 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 3.6 | last meaningful line 0.3 h ago (11052/11052 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-157767 | phy__t1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (209/452 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 10.8 | last meaningful line 0.1 h ago (1291/1297 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_2_route | 13.6 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_2_route | 9.8 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 12.7 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | generate_abstract | 13.4 | last meaningful line 0.0 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 13.5 | drt_violations best 103153 last 103153 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 11.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-750026-17077 | 750026 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-844207-8788 | 844207 | orfs_synth | 0.1 | last meaningful line 0.1 h ago (391/391 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-851812-29364 | 851812 | orfs_synth | 0.1 | last meaningful line 0.1 h ago (370/370 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-857592-10227 | 857592 | orfs_synth | 0.1 | last meaningful line 0.1 h ago (505/505 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-875736-2496 | 875736 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-914260-27088 | 914260 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (607/607 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 2.5 | last meaningful line 0.3 h ago (292/293 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i1-3529532 | eco_20261123_142403_3177550-i1 | 5_2_route | 1.2 | drt_violations best 5231 last 5231 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 2.4 |  | NO-DATA: no log found |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | 5_1_grt | 5.4 | last meaningful line 0.5 h ago (298/1305 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 4.2 | drt_violations best 60213 last 60213 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 5.7 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-native59-2836475 | native59 | 2_1_floorplan | 0.5 | repair_Viol best 18805 last 18805 rows 904 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | postcts_gate_FF | 13.1 | last meaningful line 0.1 h ago (859/859 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__clcedefe91-3226730 | slice_station__t30 | 3_3_place_gp | 0.1 | overflow best 0.2177 last 0.2195 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slice_station__t31-3227242 | slice_station__t31 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_2_route | 14.3 | drt_violations best 3240 last 3240 rows 3 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 13.8 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-2359243-22693 | 2359243 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-2452779-29048 | 2452779 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-2759871-31481 | 2759871 | 2_1_floorplan | 0.5 | last meaningful line 0.3 h ago (1404/1404 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-2885480-28772 | 2885480 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-3032456-14921 | 3032456 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3099315-18388 | 3099315 | 2_1_floorplan | 0.2 | last meaningful line 0.2 h ago (189/189 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3333117-8872 | 3333117 | 2_1_floorplan | 0.0 | repair_Viol best 2436 last 2436 rows 61 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 3.6 | drt_violations best 42348 last 42348 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2-2683723 | eco_20261122_165619_1517073-i2 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (161/161 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1263597 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2649503 | kv3_io_ft | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2343147 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 4.4 | drt_violations best 70 last 70 rows 4 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 3.1 | drt_violations best 40447 last 40447 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t2-2430221 | serdes__t2 | 3_5_place_dp | 1.4 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 12.6 | drt_violations best 19416 last 19416 rows 11 | before-window best 28584, window best 19416 | PROGRESS: drt_violations improved 32.1 % in window |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 11.2 | drt_violations best 1269 last 1568 rows 23 | before-window best 87459, window best 1269 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 15.5 | drt_violations best 1983 last 1983 rows 13 | before-window best 112571, window best 1983 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 17.8 | drt_violations best 10583 last 10583 rows 12 | before-window best 12997, window best 10583 | PROGRESS: drt_violations improved 18.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 14.4 | drt_violations best 48060 last 48060 rows 11 | before-window best 71122, window best 48060 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 14.8 | drt_violations best 52820 last 52820 rows 11 | before-window best 62246, window best 52820 | PROGRESS: drt_violations improved 15.1 % in window |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1t-1139635 | eco_20261123_073408_3918836-i1t | 5_2_route | 2.2 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 8.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 20.4 | drt_violations best 5 last 5 rows 43 | before-window best 409476, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 15.4 | drt_violations best 60407 last 60407 rows 11 | before-window best 71216, window best 60407 | PROGRESS: drt_violations improved 15.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 26.1 | drt_violations best 21 last 23 rows 51 | before-window best 53, window best 21 | PROGRESS: drt_violations improved 60.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 29.5 | drt_violations best 7732 last 9662 rows 19 | before-window best 9545, window best 7732 | PROGRESS: drt_violations improved 19.0 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 17.0 | drt_violations best 14710 last 63695 rows 18 | before-window best 15880, window best 14710 | PROGRESS: drt_violations improved 7.4 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 13.0 | last meaningful line 3.0 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t47-118217 | slice_station__t47 | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 15.5 | last meaningful line 5.5 h ago (216/225 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 10.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 9.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 13.6 | repair_TNS best 264.438 last 264.438 rows 5 | before-window best 498.308, window best 264.438 | PROGRESS: repair_TNS improved 46.9 % in window |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 12.8 | repair_TNS best 24128 last 24128 rows 4 | before-window best 27016.7, window best 24128 | PROGRESS: repair_TNS improved 10.7 % in window |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 29.2 | drt_violations best 33068 last 33068 rows 2 | before-window best 175829, window best 33068 | PROGRESS: drt_violations improved 81.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 29.0 | drt_violations best 36675 last 36675 rows 9 | before-window best 40912, window best 36675 | PROGRESS: drt_violations improved 10.4 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 27.5 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 15.6 | drt_violations best 93635 last 93635 rows 5 | before-window best 344103, window best 93635 | PROGRESS: drt_violations improved 72.8 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 12.9 | drt_violations best 2273 last 2273 rows 10 | before-window best 90237, window best 2273 | PROGRESS: drt_violations improved 97.5 % in window |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 5.7 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 23.0 | drt_violations best 2425 last 2425 rows 15 | before-window best 88165, window best 2425 | PROGRESS: drt_violations improved 97.2 % in window |  |
