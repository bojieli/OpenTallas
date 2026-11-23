# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 10:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 2, 'GRT-LABEL': 2, 'YOUNG': 105, 'NO-DATA': 9, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_2_tapbal_grt | 3.8 | last meaningful line 2.0 h ago (48/55 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -1073.03 ps (< -300, gate TT >= -42); job age 3.8  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 43.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 16.5 | grt rounds 2 overflow 5:107169 -> 10:119481 | UNSIGNABLE: GRT overflow flat: overflow 107169 at iteration 5 -> 119481 at iteration 10: fla | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 11.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 12.5 | grt rounds 2 overflow 5:43627 -> 10:30741 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 10.4 | grt rounds 2 overflow 5:11530 -> 10:1570 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-1260429 | bk_sel__t2 | 3_3_place_gp | 0.5 | overflow best 0.2035 last 0.2063 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 5.6 | repair_TNS best 5467.48 last 5467.48 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-439143 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.1 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 6_report | 10.6 | last meaningful line 0.2 h ago (306/306 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t24__cleece78ec-86117 | slice_station__t24 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (239/240 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-810171 | slice_station__t36 | 3_5_place_dp | 0.8 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1132991-30340 | 1132991 | cts_diag | 0.6 | repair_Violations best 24108 last 24119 rows 49 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | otc-1554701-25583 | 1554701 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (1769/1773 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-1599237-22322 | 1599237 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (6232/6232 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-1765481-28496 | 1765481 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3664/3664 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1788311-31505 | 1788311 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-274226-16996 | 274226 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (8660/8660 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | otc-3834020-29448 | 3834020 | cts_0904 | 1.7 | last meaningful line 0.1 h ago (4554/4554 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | otc-923617-6053 | 923617 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2-3082261 | eco_20261122_223531_3628570-i2 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2-1211453 | eco_20261123_075519_12410-i2 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (230/1357 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1-366371 | eco_20261123_130918_3027414-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_152004_738176-i1-681184 | eco_20261123_152004_738176-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (248/249 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3399753 | dsdv_slice_c1x_C__t5 | 3_2_place_iop | 1.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-3749481 | dsdv_slice_c1x_C__t8 | reg_fanout | 1.2 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 16.5 | last meaningful line 3.5 h ago (211/216 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_3_place_gp | 5.9 | overflow best 0.099 last 0.099 rows 44 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-kv3_sys_c-534011 | kv3_sys_c | 3_3_place_gp | 0.4 | overflow best 0.4547 last 0.4606 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 16.6 | drt_violations best 12780 last 12780 rows 3 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 6_report | 16.4 | last meaningful line 0.1 h ago (306/306 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-1059943-23684 | 1059943 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-356178-19590 | 356178 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2t-3323150 | eco_20261122_164248_3895049-i2t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2t-153753 | eco_20261122_190506_3875261-i2t | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (237/1404 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1-176552 | eco_20261123_073408_3918836-i1 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (244/245 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_092856_2078955-i1-3664424 | eco_20261123_092856_2078955-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1t-768660 | eco_20261123_102841_2122262-i1t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1t-830727 | eco_20261123_103136_2028090-i1t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_223507_tt_79083 | so_223507_tt_79083 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (1034/1034 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 6_report | 6.4 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_1_grt | 8.8 | last meaningful line 0.2 h ago (164/164 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 429406 last 429406 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 8.9 | drt_violations best 5873 last 5873 rows 4 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 8.8 | last meaningful line 4.7 h ago (211/219 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-1435114 | dsdv_slice_lepe_mu_LP__t2 | 3_3_place_gp | 0.1 | overflow best 0.7346 last 0.7397 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_ctl-865079 | hd_ctl | pregrt_ff_hold | 0.6 | repair_TNS best 30003.5 last 30003.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-943411 | hd_lep0N | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1374589 | hd_lep0N_w | 3_1_place_gp_skip_io | 0.2 | overflow best 0.1416 last 0.1416 rows 40 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_4_place_resized | 6.2 | last meaningful line 1.2 h ago (695/695 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 4.0 | last meaningful line 4.0 h ago (3/3 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-291376 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 10.4 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1-896574 | eco_20261123_124118_879330-i1 | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (299/353 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1t-2913491 | eco_20261123_160238_2681508-i1t | 5_2_route | 2.4 | drt_violations best 38903 last 38903 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_2_route | 1.3 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1t-259914 | eco_20261123_171842_3718765-i1t | 5_2_route | 1.2 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 3.6 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 5.2 | last meaningful line 0.4 h ago (9995/9995 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | postcts_gate_TT | 1.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | pregrt_ff_hold | 1.3 | repair_TNS best 783.214 last 783.214 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | tt_setup_repair_grt | 1.5 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | tt_setup_repair_grt | 1.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t47-118217 | slice_station__t47 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (239/240 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | tt_setup_repair_grt | 1.6 | last meaningful line 0.0 h ago (317/317 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | tt_setup_repair_grt | 1.4 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (237/238 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl503f4913-3142679 | slice_station__t7 | generate_abstract | 1.9 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl945bc067-3551157 | slice_station__t7 | 6_report | 1.7 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1-1751532 | eco_20261123_140713_549985-i1 | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (299/1666 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1t-2511984 | eco_20261123_163717_2005956-i1t | 5_2_route | 2.1 | drt_violations best 79754 last 79754 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 2.0 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 14.7 | drt_violations best 2323 last 2323 rows 5 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl23f6a148-767022 | kv3_pc_v1 | 3_3_place_gp | 1.1 | overflow best 0.1718 last 0.1718 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 4.6 | last meaningful line 0.3 h ago (11103/11103 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | tt_setup_repair_grt | 14.6 | repair_Remaining best 146207 last 146207 rows 218 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-phy__t1-157767 | phy__t1 | tt_setup_repair_grt | 1.6 | last meaningful line 0.1 h ago (14/14 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_2_route | 11.8 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_2_route | 14.6 | drt_violations best 105357 last 105357 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_2_route | 10.8 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 13.7 | drt_violations best 137246 last 137246 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 14.5 | drt_violations best 14008 last 14008 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | otc-1043173-6524 | 1043173 | gold_b.ys | 0.9 | last meaningful line 0.7 h ago (67868/67868 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 12.5 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 3.5 | drt_violations best 922 last 922 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i2t-1786386 | eco_20261123_142403_3177550-i2t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | qc-coll-s-reform-maplec-1123 | qc-coll-s-reform-maplec | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 3.4 |  | NO-DATA: no log found |  |
| epyc9 | so_1690960_ff_32516 | so_1690960_ff_32516 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | so_1690960_tt_32516 | so_1690960_tt_32516 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | dpkit-kv3_hgi_v4-3428093 | kv3_hgi_v4 | 3_3_place_gp | 0.7 | overflow best 0.2486 last 0.2486 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 5.0 | drt_violations best 60213 last 60213 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-3848070 | kv3_hroot | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 6_report | 28.2 | last meaningful line 0.3 h ago (1074/1074 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 6.4 | last meaningful line 0.5 h ago (153/153 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-native59-2836475 | native59 | 3_3_place_gp | 1.2 | overflow best 0.2985 last 0.429 rows 83 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | postcts_gate_FF | 13.9 | last meaningful line 0.3 h ago (1865/1865 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t31-3856690 | slice_station__t31 | 3_3_place_gp | 0.3 | overflow best 0.2868 last 0.3032 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | generate_abstract | 15.1 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 14.6 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | otc-2759871-31481 | 2759871 | 3_3_place_gp | 1.3 | overflow best 0.1596 last 0.2376 rows 253 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | otc-2885480-28772 | 2885480 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-3099315-18388 | 3099315 | 3_3_place_gp | 1.0 | overflow best 0.1596 last 0.2376 rows 253 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | otc-3333117-8872 | 3333117 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-3804001-18379 | 3804001 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (135407/135407 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-4139598-25950 | 4139598 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 4.4 | drt_violations best 1541 last 1541 rows 3 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2-2683723 | eco_20261122_165619_1517073-i2 | 5_2_route | 1.3 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (212/218 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 6.7 | repair_Viol best 54 last 54 rows 4 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3375490 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2649503 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | fosa-wf3-4153988 | fosa-wf3 | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | prd-count-p1_tc-694865 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 4.1 | drt_violations best 40447 last 40447 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t2-1469567 | serdes__t2 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 13.8 | drt_violations best 17052 last 17052 rows 12 | before-window best 25044, window best 17052 | PROGRESS: drt_violations improved 31.9 % in window |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 12.2 | drt_violations best 1269 last 5559 rows 26 | before-window best 3561, window best 1269 | PROGRESS: drt_violations improved 64.4 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 16.5 | drt_violations best 1814 last 1814 rows 15 | before-window best 112571, window best 1814 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 18.8 | drt_violations best 9667 last 9667 rows 13 | before-window best 12793, window best 9667 | PROGRESS: drt_violations improved 24.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 15.4 | drt_violations best 45446 last 45446 rows 12 | before-window best 56731, window best 45446 | PROGRESS: drt_violations improved 19.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 15.8 | drt_violations best 51322 last 51322 rows 12 | before-window best 58202, window best 51322 | PROGRESS: drt_violations improved 11.8 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-4154426 | hd_lep0N_w | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 21.2 | drt_violations best 5 last 5 rows 44 | before-window best 409476, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 16.2 | drt_violations best 60407 last 60407 rows 11 | before-window best 69042, window best 60407 | PROGRESS: drt_violations improved 12.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 27.1 | drt_violations best 21 last 23 rows 51 | before-window best 40, window best 21 | PROGRESS: drt_violations improved 47.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 30.5 | drt_violations best 7590 last 7590 rows 20 | before-window best 9545, window best 7590 | PROGRESS: drt_violations improved 20.5 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 18.0 | drt_violations best 14710 last 63695 rows 18 | before-window best 15247, window best 14710 | PROGRESS: drt_violations improved 3.5 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 14.0 | last meaningful line 4.0 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 7.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 10.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 12.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 13.8 | grt_hold_TNS best 16472.3 last 16472.3 rows 6 | before-window best 47272.6, window best 16472.3 | PROGRESS: grt_hold_TNS improved 65.2 % in window |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 30.0 | drt_violations best 21144 last 21144 rows 3 | before-window best 175829, window best 21144 | PROGRESS: drt_violations improved 88.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 29.7 | drt_violations best 34800 last 34800 rows 10 | before-window best 40912, window best 34800 | PROGRESS: drt_violations improved 14.9 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 16.4 | drt_violations best 91811 last 91811 rows 6 | before-window best 151194, window best 91811 | PROGRESS: drt_violations improved 39.3 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 13.7 | drt_violations best 1960 last 1960 rows 11 | before-window best 90237, window best 1960 | PROGRESS: drt_violations improved 97.8 % in window |  |
| intel2 | dpkit-coll_ftm-1263597 | coll_ftm | 5_2_route | 2.2 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 24.0 | drt_violations best 2178 last 2178 rows 17 | before-window best 64401, window best 2178 | PROGRESS: drt_violations improved 96.6 % in window |  |
