# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 11:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'YOUNG': 97, 'NO-DATA': 21, 'EXCLUDED': 1, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 44.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 31.3 | drt_violations best 7590 last 7590 rows 20 | before-window best 7732, window best 7590 | NO-PROGRESS: drt_violations best 7590 vs 7732 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FAM-S81-COL-H9R0-R4 dec |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 12.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 11.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 5_1_grt | 6.5 | last meaningful line 0.1 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 6.4 | repair_TNS best 5467.48 last 5467.48 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-439143 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.8 h ago (132/132 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-1788311-31505 | 1788311 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (8502/8502 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-274226-16996 | 274226 | cts_0928 | 2.0 | last meaningful line 0.3 h ago (8690/8690 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | otc-3834020-29448 | 3834020 | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (4663/4663 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2-3082261 | eco_20261122_223531_3628570-i2 | 5_2_route | 3.0 | drt_violations best 15 last 15 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2-1211453 | eco_20261123_075519_12410-i2 | 5_2_route | 1.3 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1-366371 | eco_20261123_130918_3027414-i1 | 5_2_route | 1.9 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_152004_738176-i1-681184 | eco_20261123_152004_738176-i1 | 5_2_route | 1.7 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | so_2537766_ff_10240 | so_2537766_ff_10240 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc10 | so_2537766_tt_10240 | so_2537766_tt_10240 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-1266566 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 0.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-1222805 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 0.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-3749481 | dsdv_slice_c1x_C__t8 | 3_3_place_gp | 1.9 | overflow best 0.241 last 0.241 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 17.3 | last meaningful line 4.3 h ago (211/217 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_3_place_gp | 6.7 | overflow best 0.099 last 0.099 rows 44 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | otc-356178-19590 | 356178 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2t-3323150 | eco_20261122_164248_3895049-i2t | 5_2_route | 2.2 | last meaningful line 0.1 h ago (284/285 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2t-1118869 | eco_20261122_181101_3945375-i2t | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (235/1294 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2t-153753 | eco_20261122_190506_3875261-i2t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (269/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1-176552 | eco_20261123_073408_3918836-i1 | 5_2_route | 1.5 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_092856_2078955-i1-3664424 | eco_20261123_092856_2078955-i1 | 5_2_route | 2.0 | drt_violations best 112 last 112 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1t-768660 | eco_20261123_102841_2122262-i1t | 5_1_grt | 1.0 | last meaningful line 0.5 h ago (235/1403 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1t-830727 | eco_20261123_103136_2028090-i1t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1504418_ff_65145 | so_1504418_ff_65145 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_1504418_tt_65145 | so_1504418_tt_65145 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_1890035_ff_68002 | so_1890035_ff_68002 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_1890035_tt_68002 | so_1890035_tt_68002 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_1_grt | 9.8 | last meaningful line 1.0 h ago (272/1291 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 429406 last 429406 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 9.9 | drt_violations best 1623 last 1623 rows 12 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.5 | overflow best 0.6546 last 0.6546 rows 46 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2160074 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4142/4142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2345808 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3861/3861 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mu_LP__t2-2655672 | dsdv_slice_lepw_mu_LP__t2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mus_LP__t2-2656003 | dsdv_slice_lepw_mus_LP__t2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-4154426 | hd_lep0N_w | postcts_gate_TT | 2.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_5_place_dp | 7.2 | last meaningful line 0.5 h ago (141/141 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-1629928 | kv3_pv_v5n | 3_3_place_gp | 0.9 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5ne-1567175 | kv3_pv_v5ne | 3_3_place_gp | 1.0 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 11.4 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1-896574 | eco_20261123_124118_879330-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1-2430323 | eco_20261123_160238_2681508-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (256/778 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_2_route | 2.3 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1t-259914 | eco_20261123_171842_3718765-i1t | 5_2_route | 2.1 | drt_violations best 43428 last 43428 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i1t-1905995 | eco_20261123_184706_2375049-i1t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_2406467_ff_27076 | so_2406467_ff_27076 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_2406467_tt_27076 | so_2406467_tt_27076 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 4.4 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 5_1_grt | 14.7 | last meaningful line 0.0 h ago (169/169 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 6.0 | last meaningful line 1.0 h ago (9996/9996 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (248/248 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 5_2_route | 2.3 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 5_2_route | 2.1 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t47-118217 | slice_station__t47 | 5_2_route | 2.1 | drt_violations best 1204 last 1204 rows 2 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | tt_setup_measure_grt | 2.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_2_route | 2.4 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 5_2_route | 2.1 | last meaningful line 0.0 h ago (245/245 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (253/254 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (251/252 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_2_route | 1.9 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1-1751532 | eco_20261123_140713_549985-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1t-2511984 | eco_20261123_163717_2005956-i1t | 5_2_route | 2.8 | drt_violations best 10 last 10 rows 8 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 2.8 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 5.3 | last meaningful line 0.0 h ago (11134/11134 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-157767 | phy__t1 | postcts_gate_TT | 2.3 | last meaningful line 0.1 h ago (16/16 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_2_route | 12.5 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_2_route | 15.3 | drt_violations best 13880 last 13880 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_2_route | 11.5 | drt_violations best 101560 last 101560 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 14.5 | drt_violations best 137246 last 137246 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | otc-1043173-6524 | 1043173 | gold_b.ys | 1.6 | last meaningful line 1.5 h ago (67868/67868 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 13.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2463102-27505 | 2463102 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2464713-7726 | 2464713 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2466341-14082 | 2466341 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2467290-23821 | 2467290 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2604268-17213 | 2604268 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2605620-20437 | 2605620 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2618999-2095 | 2618999 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 4.2 | drt_violations best 922 last 922 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i2t-1786386 | eco_20261123_142403_3177550-i2t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (259/260 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1t-2251452 | eco_20261123_190031_3093983-i1t | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (239/290 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | qc-coll-s-reform-maplec-1123 | qc-coll-s-reform-maplec | - | 1.2 |  | NO-DATA: no log found |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 4.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-hdctl_counted_fsmhint | relec1122-ml-hdctl_counted_fsmhint | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-hdctl_r8_fsmhint | relec1122-ml-hdctl_r8_fsmhint | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-19056 | dsdv_slice_c1x_C__t4 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-459624 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p2-1101356 | kv3_hg_v1p2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 6.0 | drt_violations best 10436 last 10436 rows 3 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 6_report | 29.2 | last meaningful line 1.3 h ago (1074/1074 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 7.4 | last meaningful line 0.6 h ago (156/156 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-native59-2836475 | native59 | 3_4_place_resized | 2.2 | last meaningful line 0.2 h ago (333/333 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 14.9 | last meaningful line 0.1 h ago (268/268 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-983140 | slice_station__t12 | 3_3_place_gp | 0.2 | overflow best 0.2245 last 0.2443 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 15.6 | drt_violations best 71799 last 71799 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | otc-2759871-31481 | 2759871 | 3_5_place_dp | 2.3 | last meaningful line 0.2 h ago (29/29 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3099315-18388 | 3099315 | 3_5_place_dp | 2.0 | last meaningful line 0.2 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3333117-8872 | 3333117 | 3_5_place_dp | 1.8 | last meaningful line 0.8 h ago (29/29 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-4139598-25950 | 4139598 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-571036-12201 | 571036 | signoff | 0.5 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-825770-15992 | 825770 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2-876871 | eco_20261122_143408_943433-i2 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (245/1285 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2-2683723 | eco_20261122_165619_1517073-i2 | 5_2_route | 2.3 | drt_violations best 2118 last 2118 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 2.3 | repair_Viol best 1637 last 1637 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | postcts_gate_FF | 7.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-370750 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3375490 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-370081 | kv3_io_ft | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (423/423 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-13167 | slice_station__t12 | 5_2_route | 0.7 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | fosa-lk-cls-1051814 | fosa-lk-cls | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | fosa-replay1-177800 | fosa-replay1 | - | 0.6 |  | NO-DATA: no log found |  |
| intel2 | prd-eco_20261123_051704_3678821-i1-811516 | eco_20261123_051704_3678821-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1-995418 | eco_20261123_063813_234645-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | s81kvt2_closed_eq | s81kvt2_closed_eq | otrun | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3392306-16711 | 3392306 | ot_bind_native_9cf5557ac3df006753d4677f | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 7.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slice_station__t24__cleece78ec-86117 | slice_station__t24 | 5_2_route | 2.1 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc10 | otc-1132991-30340 | 1132991 | cts_diag | 1.3 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | otc-1554701-25583 | 1554701 | 5_1_grt | 1.0 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 14.6 | drt_violations best 17052 last 17052 rows 12 | before-window best 24490, window best 17052 | PROGRESS: drt_violations improved 30.4 % in window |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 12.9 | drt_violations best 1269 last 5559 rows 26 | before-window best 2013, window best 1269 | PROGRESS: drt_violations improved 37.0 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 17.3 | drt_violations best 1794 last 1794 rows 16 | before-window best 112571, window best 1794 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 19.5 | drt_violations best 9667 last 9667 rows 13 | before-window best 12416, window best 9667 | PROGRESS: drt_violations improved 22.1 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 16.1 | drt_violations best 45446 last 45446 rows 12 | before-window best 53530, window best 45446 | PROGRESS: drt_violations improved 15.1 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 16.5 | drt_violations best 51322 last 51322 rows 12 | before-window best 57442, window best 51322 | PROGRESS: drt_violations improved 10.7 % in window |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 9.8 | last meaningful line 5.7 h ago (211/220 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_ctl-865079 | hd_ctl | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 22.2 | drt_violations best 5 last 5 rows 46 | before-window best 85945, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 17.2 | drt_violations best 57558 last 57558 rows 12 | before-window best 66623, window best 57558 | PROGRESS: drt_violations improved 13.6 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 27.9 | drt_violations best 21 last 23 rows 51 | before-window best 40, window best 21 | PROGRESS: drt_violations improved 47.5 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 8.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 18.8 | drt_violations best 14710 last 31045 rows 19 | before-window best 15104, window best 14710 | PROGRESS: drt_violations improved 2.6 % in window |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 7.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_1_grt | 2.1 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_1_grt | 2.1 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 15.4 | drt_violations best 382 last 382 rows 12 | before-window best 183055, window best 382 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 14.5 | grt_hold_TNS best 11464.4 last 11464.4 rows 7 | before-window best 47272.6, window best 11464.4 | PROGRESS: grt_hold_TNS improved 75.7 % in window |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 15.3 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 31.0 | drt_violations best 58 last 58 rows 16 | before-window best 175829, window best 58 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 30.7 | drt_violations best 31217 last 31217 rows 11 | before-window best 39043, window best 31217 | PROGRESS: drt_violations improved 20.0 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 17.4 | drt_violations best 90552 last 90552 rows 7 | before-window best 151194, window best 90552 | PROGRESS: drt_violations improved 40.1 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 14.7 | drt_violations best 1731 last 1731 rows 13 | before-window best 90237, window best 1731 | PROGRESS: drt_violations improved 98.1 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 24.7 | drt_violations best 2178 last 9488 rows 18 | before-window best 11060, window best 2178 | PROGRESS: drt_violations improved 80.3 % in window |  |
