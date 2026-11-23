# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 12:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'GRT-LABEL': 2, 'YOUNG': 89, 'NO-DATA': 12, 'PROGRESS': 25}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 10.5 | last meaningful line 6.5 h ago (211/220 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (FAM-S81-SLICE-R6 decide |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 45.2 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 13.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 12.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 15.3 | repair_TNS best 7184.78 last 7184.78 rows 1 | before-window best 7184.78, window best 7184.78 | NO-PROGRESS: repair_TNS best 7184.78 vs 7184.78 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 5_1_grt | 15.5 | grt rounds 1 overflow 5:13375 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 7.9 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 5_1_grt | 7.3 | last meaningful line 0.5 h ago (200/207 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 7.1 | repair_TNS best 5467.48 last 5467.48 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-439143 | dsdv_slice_lepw_mus_C__t1 | 2_4_floorplan_pdn | 2.6 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 5_1_grt | 8.4 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t24__cleece78ec-86117 | slice_station__t24 | 6_report | 2.9 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1788311-31505 | 1788311 | cts_diag | 1.6 | last meaningful line 0.0 h ago (8844/8844 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | otc-274226-16996 | 274226 | 4_1_cts | 2.8 | last meaningful line 0.5 h ago (8689/8689 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-681184 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2-3082261 | eco_20261122_223531_3628570-i2 | 5_2_route | 3.7 | drt_violations best 15 last 15 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1-366371 | eco_20261123_130918_3027414-i1 | 5_2_route | 2.7 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | so_2537766_ff_10240 | so_2537766_ff_10240 | signoff | 1.1 |  | NO-DATA: empty log |  |
| epyc2 | ap-ageom-kw-dsdv-slice-c1x-C--t8-grt-2397792 | dsdv-slice-c1x-C--t8-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-1266566 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.1 | last meaningful line 0.5 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-1222805 | dsdv_slice_c1x_C__t3 | port_bind | 1.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 17.8 | last meaningful line 4.8 h ago (211/218 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_3_place_gp | 7.2 | overflow best 0.099 last 0.099 rows 44 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | ot-canary-2448892 | ot-canary | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-2072262-2525 | 2072262 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-356178-19590 | 356178 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-3664424 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2t-3323150 | eco_20261122_164248_3895049-i2t | 5_2_route | 2.7 | drt_violations best 5498 last 5498 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2t-1118869 | eco_20261122_181101_3945375-i2t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2t-153753 | eco_20261122_190506_3875261-i2t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1-176552 | eco_20261123_073408_3918836-i1 | 5_2_route | 2.0 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1t-768660 | eco_20261123_102841_2122262-i1t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1t-830727 | eco_20261123_103136_2028090-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | so_1890035_ff_68002 | so_1890035_ff_68002 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | so_1890035_tt_68002 | so_1890035_tt_68002 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_1_grt | 10.6 | last meaningful line 0.7 h ago (1316/2499 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 429406 last 429406 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 10.7 | drt_violations best 1396 last 1572 rows 18 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.3 | last meaningful line 0.1 h ago (36/36 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mu_LP__t2-2655672 | dsdv_slice_lepw_mu_LP__t2 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mus_LP__t2-2656003 | dsdv_slice_lepw_mus_LP__t2 | 3_3_place_gp | 0.8 | overflow best 0.2562 last 0.2562 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_5_place_dp | 7.9 | last meaningful line 1.3 h ago (141/141 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-1629928 | kv3_pv_v5n | 3_4_place_resized | 1.7 | last meaningful line 0.0 h ago (484/484 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5ne-1567175 | kv3_pv_v5ne | 3_4_place_resized | 1.7 | last meaningful line 0.0 h ago (465/465 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-3253569-9085 | 3253569 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_124118_879330-i1-896574 | eco_20261123_124118_879330-i1 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1-2430323 | eco_20261123_160238_2681508-i1 | 5_2_route | 1.0 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_2_route | 3.0 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1t-259914 | eco_20261123_171842_3718765-i1t | 5_2_route | 2.9 | drt_violations best 17 last 17 rows 4 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i1t-1905995 | eco_20261123_184706_2375049-i1t | 5_2_route | 1.4 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 5.1 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 8.4 | last meaningful line 0.5 h ago (1319/2098 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_2_route | 3.2 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | postcts_gate_TT | 2.8 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | postcts_gate_TT | 2.9 | last meaningful line 0.0 h ago (681/681 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 2.8 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_2_route | 3.1 | last meaningful line 0.1 h ago (254/255 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (254/255 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | 5_2_route | 3.0 | drt_violations best 16050 last 16050 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | 5_2_route | 3.0 | drt_violations best 16940 last 16940 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (291/292 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1-1751532 | eco_20261123_140713_549985-i1 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1-1884148 | eco_20261123_163717_2005956-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 3.5 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 6.1 | last meaningful line 0.8 h ago (11134/11134 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_2_route | 13.3 | last meaningful line 0.1 h ago (284/285 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_2_route | 16.1 | drt_violations best 199 last 199 rows 4 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_2_route | 12.3 | drt_violations best 101560 last 101560 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 15.2 | drt_violations best 23102 last 23102 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | generate_abstract | 16.0 | last meaningful line 0.1 h ago (775/775 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | 5_1_grt | 5.9 | last meaningful line 0.1 h ago (1515/1568 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 14.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-2604268-17213 | 2604268 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_bc-1786386 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-2017343 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1t-2251452 | eco_20261123_190031_3093983-i1t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | qc-coll-s-reform-maplec-1123 | qc-coll-s-reform-maplec | - | 2.0 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-hdctl_counted_fsmhint | relec1122-ml-hdctl_counted_fsmhint | - | 1.2 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-hdctl_r8_fsmhint | relec1122-ml-hdctl_r8_fsmhint | - | 1.2 |  | NO-DATA: no log found |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-19056 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.1 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-459624 | dsdv_slice_c1x_C__t6 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p2-1101356 | kv3_hg_v1p2 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (525/525 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 6.5 | drt_violations best 354 last 354 rows 10 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | generate_abstract | 29.7 | last meaningful line 0.0 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 15.4 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 16.1 | drt_violations best 71799 last 71799 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_3_place.otrun | 0.4 | last meaningful line 0.3 h ago (4/4 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-1434812-2009 | 1434812 | orfs_synth | 0.3 | last meaningful line 0.2 h ago (453/453 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-2759871-31481 | 2759871 | 3_5_place_dp | 2.8 | last meaningful line 0.7 h ago (29/29 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-3099315-18388 | 3099315 | 3_5_place_dp | 2.5 | last meaningful line 0.5 h ago (29/29 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-3333117-8872 | 3333117 | 3_5_place_dp | 2.3 | last meaningful line 1.3 h ago (29/29 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | otc-571036-12201 | 571036 | signoff | 1.0 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-825770-15992 | 825770 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2-876871 | eco_20261122_143408_943433-i2 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2-2683723 | eco_20261122_165619_1517073-i2 | 5_2_route | 2.8 | drt_violations best 2118 last 2118 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 2.8 | repair_Viol best 1637 last 1637 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-370750 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3375490 | dsdv_slice_lepe_nh_mus_C__t1 | 3_3_place_gp | 2.2 | overflow best 0.6896 last 0.6896 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-1689060 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-370081 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | fosa-replay1-177800 | fosa-replay1 | - | 1.4 |  | NO-DATA: no log found |  |
| intel2 | prd-eco_20261123_051704_3678821-i1-811516 | eco_20261123_051704_3678821-i1 | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (292/1362 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1-995418 | eco_20261123_063813_234645-i1 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 8.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 15.3 | drt_violations best 15220 last 15220 rows 13 | before-window best 22330, window best 15220 | PROGRESS: drt_violations improved 31.8 % in window |  |
| epyc10 | prd-eco_20261123_075519_12410-i2-1211453 | eco_20261123_075519_12410-i2 | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 13.4 | drt_violations best 1269 last 2976 rows 27 | before-window best 1674, window best 1269 | PROGRESS: drt_violations improved 24.2 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 17.8 | drt_violations best 1794 last 1794 rows 16 | before-window best 112571, window best 1794 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 20.0 | drt_violations best 9239 last 9239 rows 14 | before-window best 12416, window best 9239 | PROGRESS: drt_violations improved 25.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 16.6 | drt_violations best 44158 last 44158 rows 13 | before-window best 52441, window best 44158 | PROGRESS: drt_violations improved 15.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 17.0 | drt_violations best 50150 last 50150 rows 13 | before-window best 56852, window best 50150 | PROGRESS: drt_violations improved 11.8 % in window |  |
| epyc7 | dpkit-hd_ctl-865079 | hd_ctl | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 22.9 | drt_violations best 5 last 5 rows 49 | before-window best 1983, window best 5 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 17.9 | drt_violations best 57558 last 57558 rows 12 | before-window best 66623, window best 57558 | PROGRESS: drt_violations improved 13.6 % in window |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 12.1 | drt_violations best 16012 last 16012 rows 2 | before-window best 105749, window best 16012 | PROGRESS: drt_violations improved 84.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 28.6 | drt_violations best 20 last 20 rows 54 | before-window best 39, window best 20 | PROGRESS: drt_violations improved 48.7 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 32.0 | drt_violations best 6907 last 6907 rows 21 | before-window best 7732, window best 6907 | PROGRESS: drt_violations improved 10.7 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 8.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 19.5 | drt_violations best 14710 last 31045 rows 19 | before-window best 15104, window best 14710 | PROGRESS: drt_violations improved 2.6 % in window |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 6.7 | last meaningful line 1.7 h ago (9996/9996 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 16.2 | drt_violations best 99 last 99 rows 16 | before-window best 183055, window best 99 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 31.5 | drt_violations best 36 last 36 rows 32 | before-window best 175829, window best 36 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 31.2 | drt_violations best 31217 last 31217 rows 11 | before-window best 38016, window best 31217 | PROGRESS: drt_violations improved 17.9 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 17.9 | drt_violations best 90552 last 90552 rows 7 | before-window best 132000, window best 90552 | PROGRESS: drt_violations improved 31.4 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 15.2 | drt_violations best 1253 last 1253 rows 14 | before-window best 90237, window best 1253 | PROGRESS: drt_violations improved 98.6 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 25.5 | drt_violations best 2178 last 9488 rows 18 | before-window best 7398, window best 2178 | PROGRESS: drt_violations improved 70.6 % in window |  |
