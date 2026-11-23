# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 07:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 8, 'YOUNG': 95, 'NO-DATA': 8, 'EXCLUDED': 1, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 40.7 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | 5_1_grt | 6.7 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | 5_1_grt | 6.7 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 24.1 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 7.6 | grt rounds 2 overflow 5:89117 -> 10:282 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | 5_1_grt | 5.9 | grt rounds 2 overflow 5:4750 -> 10:2668 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-3050099 | slw_st_a_v2 | 5_1_grt | 3.2 | grt rounds 2 overflow 5:6512 -> 10:1487 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 10.9 | grt rounds 2 overflow 5:53 -> 10:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 5_1_grt | 7.9 | grt rounds 2 overflow 5:40940 -> 10:33065 | GRT-LABEL: DESIGN-FAIL: overflow 33065 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-coll-core-grt-1880171 | coll-core-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 1.9 | repair_TNS best 193064 last 193064 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 4_1_cts | 2.6 | last meaningful line 0.0 h ago (3697/3697 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | pregrt_ff_hold | 4.0 | repair_TNS best 351.902 last 351.902 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 4.0 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3747062 | ot_s81sl_leaf__t14 | pregrt_ff_hold | 1.9 | repair_TNS best 607474 last 607474 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3857880 | ot_s81sl_leaf__t14 | pregrt_ff_hold | 1.8 | repair_TNS best 580264 last 580264 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | postcts_gate_FF | 7.6 | last meaningful line 0.1 h ago (778/778 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_2_route | 7.8 | drt_violations best 80958 last 80958 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | otc-1922023-29399 | 1922023 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | prd-count-p1_tc-933314 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2t-1170770 | eco_20261123_075519_12410-i2t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (249/249 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1t-3090789 | eco_20261123_130918_3027414-i1t | 5_2_route | 2.5 | drt_violations best 4643 last 4643 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_152004_738176-i1t-1508677 | eco_20261123_152004_738176-i1t | 5_2_route | 0.4 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | 5_1_grt | 6.5 | last meaningful line 0.5 h ago (272/1283 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-204646 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 13.3 | last meaningful line 0.3 h ago (211/212 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 12.2 | last meaningful line 1.8 h ago (211/217 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_1_floorplan | 2.7 | last meaningful line 2.0 h ago (1424/1424 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 13.3 | drt_violations best 5882 last 5882 rows 4 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 9.2 | last meaningful line 0.3 h ago (227/230 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 15.5 | drt_violations best 18433 last 18433 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 15.5 | drt_violations best 110443 last 110443 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 15.5 | drt_violations best 22270 last 22270 rows 2 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 13.3 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 13.1 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 6.1 | drt_violations best 32 last 32 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_2_route | 5.5 | drt_violations best 312 last 312 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | prd-fin-2533130 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_218733_ff_54147 | so_218733_ff_54147 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (562/562 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | so_218733_tt_54147 | so_218733_tt_54147 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (562/562 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | so_894541_ff_79624 | so_894541_ff_79624 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_894541_tt_79624 | so_894541_tt_79624 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | 5_2_route | 2.6 | drt_violations best 57589 last 57589 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2684878 | col_h10_r2__t1 | 6_report | 3.5 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 6.1 | repair_TNS best 325624 last 325624 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 6.0 | last meaningful line 2.0 h ago (211/216 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (8661/8661 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3723533 | hd_lep0N_w | postcts_gate_TT | 2.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_3_place_gp | 3.4 | overflow best 0.0992 last 0.0992 rows 44 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3969309 | ot_s81sl_leaf__t47 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (270/1276 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | generate_abstract | 17.5 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 7.6 | last meaningful line 0.2 h ago (290/291 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_2_route | 3.0 | drt_violations best 14086 last 14086 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-871345 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 8.1 | last meaningful line 4.7 h ago (210/219 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 13.6 | last meaningful line 3.5 h ago (211/219 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 4.3 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4447/4448 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v3-1745589 | kv3_pc_v3 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.1271 last 0.1271 rows 47 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 4.6 | repair_TNS best 122362 last 122362 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (9861/9861 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_2_route | 8.0 | drt_violations best 416 last 416 rows 4 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | otc-2626664-25440 | 2626664 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-3209002-6415 | 3209002 | drc | 0.1 | last meaningful line -0.0 h ago (3929/3929 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-3324242-13315 | 3324242 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_2_route | 3.7 | drt_violations best 47255 last 47255 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1t-81578 | eco_20261123_140713_549985-i1t | 5_2_route | 1.6 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-kv3-pv-v5n-grt-2483585 | kv3-pv-v5n-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 11.7 | drt_violations best 183055 last 183055 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 13.5 | last meaningful line 3.5 h ago (216/222 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 1.6 | last meaningful line 1.0 h ago (10548/10548 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 9.0 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.7 | last meaningful line 2.0 h ago (242/291 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 11.6 | repair_TNS best 6083.42 last 6083.42 rows 10 | YOUNG: evidence 5.9 h < 6 h |  |
| epyc9 | dpkit-phy__t1-2164259 | phy__t1 | hold_gate | 0.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 8.8 | repair_TNS best 1409.84 last 1409.84 rows 5 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | postcts_gate_TT | 11.6 | last meaningful line -0.0 h ago (17481/17481 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 10.8 | repair_TNS best 41704.4 last 41704.4 rows 5 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | postcts_gate_TT | 10.7 | last meaningful line 0.1 h ago (934/934 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_2_route | 11.4 | drt_violations best 92724 last 92724 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | postcts_gate_FF | 11.5 | last meaningful line 0.0 h ago (845/845 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 9.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-928970-21237 | 928970 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (244/1065 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3-411680 | eco_20261122_180231_342380-i3 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (289/290 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i1t-1010219 | eco_20261123_142403_3177550-i1t | 5_2_route | 1.3 | drt_violations best 63292 last 63292 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_3_fillcell | 26.7 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 13.3 | drt_violations best 56749 last 56749 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-coll_ftm-625194 | coll_ftm | 5_2_route | 3.2 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | tt_setup_repair_grt | 2.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 3.4 | last meaningful line 0.4 h ago (7097/7097 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | tt_setup_repair_grt | 10.9 | last meaningful line 0.0 h ago (819/819 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_2_route | 12.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | postcts_gate_FF | 11.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3694090-15501 | 3694090 | gate.ys | 0.2 | last meaningful line 0.2 h ago (24857/24857 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 1.4 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_2_route | 3.4 | drt_violations best 15957 last 15957 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 5_1_grt | 4.1 | last meaningful line 0.8 h ago (216/225 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3986477 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 7.4 | last meaningful line 0.5 h ago (200/206 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 3_3_place_gp | 6.2 | overflow best 0.0987 last 0.0987 rows 44 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-1999785 | ot_s81sl_leaf__t2 | 5_1_grt | 4.0 | last meaningful line 1.5 h ago (214/223 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | ot-ucfvf-probe-2672355 | ot-ucfvf-probe | otrun | 3.7 | last meaningful line 3.6 h ago (3/3 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 2.4 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (274/274 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2046912-6231 | 2046912 | asbuilt.yosys | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 10.8 | drt_violations best 21163 last 21163 rows 10 | before-window best 154752, window best 21163 | PROGRESS: drt_violations improved 86.3 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 76.7 | last meaningful line 1.1 h ago (1622/1622 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 8.9 | drt_violations best 1269 last 4017 rows 18 | before-window best 87459, window best 1269 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 15.6 | drt_violations best 23041 last 23041 rows 2 | before-window best 133507, window best 23041 | PROGRESS: drt_violations improved 82.7 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 15.5 | drt_violations best 11209 last 11209 rows 11 | before-window best 14532, window best 11209 | PROGRESS: drt_violations improved 22.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 12.1 | drt_violations best 51167 last 51167 rows 9 | before-window best 167955, window best 51167 | PROGRESS: drt_violations improved 69.5 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 12.5 | drt_violations best 56276 last 56276 rows 9 | before-window best 168344, window best 56276 | PROGRESS: drt_violations improved 66.6 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4013616 | col_h9_r1__t1 | 5_1_grt | 2.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | 5_1_grt | 2.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 18.4 | drt_violations best 60 last 60 rows 17 | before-window best 409476, window best 60 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 13.4 | drt_violations best 65161 last 65161 rows 10 | before-window best 125495, window best 65161 | PROGRESS: drt_violations improved 48.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 13.6 | drt_violations best 11 last 11 rows 57 | before-window best 136200, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 24.1 | drt_violations best 28 last 28 rows 40 | before-window best 57, window best 28 | PROGRESS: drt_violations improved 50.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 27.5 | drt_violations best 7732 last 18575 rows 18 | before-window best 12904, window best 7732 | PROGRESS: drt_violations improved 40.1 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 15.0 | drt_violations best 14710 last 63695 rows 18 | before-window best 18065, window best 14710 | PROGRESS: drt_violations improved 18.6 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 11.0 | last meaningful line 1.0 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 8.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_1_grt | 7.8 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 27.0 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 94774 < best completed total 175829 (in-iter |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 26.7 | drt_violations best 37704 last 37704 rows 7 | before-window best 71586, window best 37704 | PROGRESS: drt_violations improved 47.3 % in window |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 25.2 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | PROGRESS: drt_violations: active iteration at 44809 < best completed total 109763 (in-iter |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 13.3 | drt_violations best 31401 last 31401 rows 1 | before-window best 31401, window best 31401 | PROGRESS: drt_violations: active iteration at 4831 < best completed total 31401 (in-iterat |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 13.4 | drt_violations best 132000 last 132000 rows 3 | before-window best 344103, window best 132000 | PROGRESS: drt_violations improved 61.6 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 34.2 | drt_violations best 1027 last 1170 rows 30 | before-window best 1060, window best 1027 | PROGRESS: drt_violations improved 3.1 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 10.7 | drt_violations best 10507 last 10507 rows 2 | before-window best 90237, window best 10507 | PROGRESS: drt_violations improved 88.4 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 21.0 | drt_violations best 3528 last 3528 rows 12 | before-window best 327883, window best 3528 | PROGRESS: drt_violations improved 98.9 % in window |  |
