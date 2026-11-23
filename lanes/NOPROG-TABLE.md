# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 08:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 2, 'GRT-LABEL': 3, 'YOUNG': 93, 'NO-DATA': 7, 'EXCLUDED': 3, 'PROGRESS': 36}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | tt_setup_repair | 3.1 | repair_Violations best 12140 last 12140 rows 10 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -758.78 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 24.6 | grt rounds 2 overflow 5:14057 -> 10:13400 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -499.02 ps (< -300, gate TT >= -42); job age 24 | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | tt_setup_repair_grt | 6.4 | repair_Viol best 4914 last 4914 rows 3 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -341.50 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 41.2 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 34.7 | drt_violations best 1027 last 1170 rows 30 | before-window best 1027, window best 1170 | NO-PROGRESS: drt_violations best 1170 vs 1027 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | 5_1_grt | 7.2 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | 5_1_grt | 7.2 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 8.1 | grt rounds 2 overflow 5:89117 -> 10:282 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (268/1278 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (7085/7085 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | pregrt_ff_hold | 4.5 | repair_TNS best 351.902 last 351.902 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 4.5 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3747062 | ot_s81sl_leaf__t14 | 5_1_grt | 2.4 | last meaningful line 0.2 h ago (265/1271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t2-2430221 | serdes__t2 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (319/319 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 5_2_route | 8.1 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_2_route | 8.3 | drt_violations best 12274 last 12274 rows 2 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | otc-2367622-7114 | 2367622 | 3_3_place_gp | 0.2 | overflow best 0.5545 last 0.5545 rows 6 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2t-1170770 | eco_20261123_075519_12410-i2t | 5_2_route | 1.2 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1t-3090789 | eco_20261123_130918_3027414-i1t | 5_2_route | 3.0 | drt_violations best 4643 last 4643 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_152004_738176-i1t-1508677 | eco_20261123_152004_738176-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (252/253 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-fin-933314 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | 5_1_grt | 7.0 | repair_Remaining best 141170 last 141170 rows 77 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-204646 | dsdv_slice_c1x_C__t3 | selrange | 1.2 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 13.8 | last meaningful line 0.8 h ago (211/213 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 12.7 | last meaningful line 2.3 h ago (211/217 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_1_floorplan | 3.2 | last meaningful line 2.5 h ago (1424/1424 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 9.7 | last meaningful line 0.8 h ago (227/234 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 16.0 | drt_violations best 13171 last 13171 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 16.0 | drt_violations best 17015 last 17015 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 13.8 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 13.6 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | eco-abs-1246208 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-2840670 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 6.6 | drt_violations best 32 last 32 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1t-1139635 | eco_20261123_073408_3918836-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (287/463 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv0a45e191-grt-3032113 | col-h9-r1--t1--cl49d7a23e--pv0a45e191-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | 5_2_route | 3.1 | drt_violations best 9417 last 9417 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 4.2 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 6.6 | repair_TNS best 54572.8 last 54572.8 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4013616 | col_h9_r1__t1 | 5_1_grt | 2.8 | last meaningful line 0.2 h ago (1301/2394 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 6.7 | drt_violations best 172065 last 172065 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 6.5 | last meaningful line 2.5 h ago (211/216 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (8762/8762 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_3_place_gp | 3.9 | overflow best 0.0992 last 0.0992 rows 44 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3969309 | ot_s81sl_leaf__t47 | 5_1_grt | 2.9 | last meaningful line 0.8 h ago (270/1280 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | generate_abstract | 18.0 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-3050099 | slw_st_a_v2 | postcts_gate_TT | 3.7 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 8.1 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_2_route | 3.5 | drt_violations best 14086 last 14086 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1t-2913491 | eco_20261123_160238_2681508-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (185/185 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 6_report | 14.1 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-871345 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.7 | last meaningful line 0.7 h ago (134/134 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 14.1 | last meaningful line 4.0 h ago (211/220 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 4.8 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (4489/4489 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v3-1745589 | kv3_pc_v3 | 3_3_place_gp | 1.3 | overflow best 0.0995 last 0.0995 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 5.1 | repair_TNS best 122362 last 122362 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 2.7 | last meaningful line 0.5 h ago (9861/9861 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_c-98167 | sle_su_c | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7826 last 0.7826 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | generate_abstract | 8.5 | last meaningful line 0.0 h ago (515/515 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-932866 | slice_station__t27 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-978315 | slice_station__t37 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-slice_station__t41-976663 | slice_station__t41 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-slice_station__t43-981912 | slice_station__t43 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t44-963120 | slice_station__t44 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_2_route | 4.2 | drt_violations best 76 last 76 rows 5 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1t-81578 | eco_20261123_140713_549985-i1t | 5_2_route | 2.1 | drt_violations best 7895 last 7895 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 12.2 | drt_violations best 183055 last 183055 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 14.0 | last meaningful line 4.0 h ago (216/222 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 2.1 | last meaningful line 0.3 h ago (10919/10919 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 9.5 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-2164259 | phy__t1 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (165/165 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 9.3 | last meaningful line 0.2 h ago (1186/1191 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | postcts_gate_FF | 12.1 | last meaningful line 0.0 h ago (725/725 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 11.3 | repair_TNS best 36352.2 last 36352.2 rows 4 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | tt_setup_repair_grt | 8.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 11.2 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_2_route | 11.9 | drt_violations best 92724 last 92724 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 12.0 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 10.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-3128437-19746 | 3128437 | west_drc | 0.0 | last meaningful line 0.0 h ago (697/697 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-928970-21237 | 928970 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i1t-1010219 | eco_20261123_142403_3177550-i1t | 5_3_fillcell | 1.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-fin-411680 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1071/1071 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 0.9 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 6_report | 27.2 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 13.8 | drt_violations best 56749 last 56749 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-coll_ftm-625194 | coll_ftm | 5_2_route | 3.7 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 2.5 | last meaningful line -0.0 h ago (234/234 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 3.9 | last meaningful line 0.0 h ago (7118/7118 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | postcts_gate_FF | 11.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 6_report | 13.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_2_route | 12.6 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | postcts_gate_FF | 12.1 | last meaningful line 0.0 h ago (1505/1505 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 1.9 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_2_route | 3.9 | drt_violations best 15957 last 15957 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | so_157621_tt_1540 | so_157621_tt_1540 | sta | 0.0 | last meaningful line 0.0 h ago (11714/11714 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (161/161 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 4.2 | last meaningful line 0.3 h ago (211/217 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 7.9 | last meaningful line 1.0 h ago (200/209 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 3_3_place_gp | 6.7 | overflow best 0.0987 last 0.0987 rows 44 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-102653 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | ot-ucfvf-probe-2672355 | ot-ucfvf-probe | otrun | 4.2 | last meaningful line 4.1 h ago (3/3 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 2.9 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 1.6 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | otc-1101000-9044 | 1101000 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-1044491-12919 | 1044491 | - | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | otc-73947-15361 | 73947 | asbuilt.yosys | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3857880 | ot_s81sl_leaf__t14 | 5_1_grt | 2.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 11.3 | drt_violations best 19416 last 19416 rows 11 | before-window best 154752, window best 19416 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 77.2 | last meaningful line 0.4 h ago (1624/1624 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 9.4 | drt_violations best 1269 last 2144 rows 19 | before-window best 87459, window best 1269 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 13.8 | drt_violations best 3088 last 3088 rows 7 | before-window best 112571, window best 3088 | PROGRESS: drt_violations improved 97.3 % in window |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 16.1 | drt_violations best 23041 last 23041 rows 2 | before-window best 133507, window best 23041 | PROGRESS: drt_violations improved 82.7 % in window |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 16.0 | drt_violations best 16611 last 16611 rows 3 | before-window best 136566, window best 16611 | PROGRESS: drt_violations improved 87.8 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 16.0 | drt_violations best 11209 last 11209 rows 11 | before-window best 13880, window best 11209 | PROGRESS: drt_violations improved 19.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 12.6 | drt_violations best 51167 last 51167 rows 9 | before-window best 167955, window best 51167 | PROGRESS: drt_violations improved 69.5 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 13.0 | drt_violations best 55792 last 55792 rows 10 | before-window best 81717, window best 55792 | PROGRESS: drt_violations improved 31.7 % in window |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | 5_1_grt | 3.1 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 18.9 | drt_violations best 10 last 10 rows 23 | before-window best 409476, window best 10 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 13.9 | drt_violations best 65161 last 65161 rows 10 | before-window best 108964, window best 65161 | PROGRESS: drt_violations improved 40.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 24.6 | drt_violations best 25 last 25 rows 44 | before-window best 57, window best 25 | PROGRESS: drt_violations improved 56.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 28.0 | drt_violations best 7732 last 18575 rows 18 | before-window best 12904, window best 7732 | PROGRESS: drt_violations improved 40.1 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 15.5 | drt_violations best 14710 last 63695 rows 18 | before-window best 16941, window best 14710 | PROGRESS: drt_violations improved 13.2 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 11.5 | last meaningful line 1.5 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 9.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 8.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 8.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 8.2 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.1 | repair_TNS best 4059.18 last 4059.18 rows 6 | before-window best 5702.11, window best 4059.18 | PROGRESS: repair_TNS improved 28.8 % in window |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 27.5 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 82117 < best completed total 175829 (in-iter |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 27.2 | drt_violations best 37187 last 37187 rows 8 | before-window best 60023, window best 37187 | PROGRESS: drt_violations improved 38.0 % in window |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 25.7 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | PROGRESS: drt_violations: active iteration at 26896 < best completed total 109763 (in-iter |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 13.9 | drt_violations best 98568 last 98568 rows 4 | before-window best 344103, window best 98568 | PROGRESS: drt_violations improved 71.4 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 11.2 | drt_violations best 6392 last 6392 rows 3 | before-window best 90237, window best 6392 | PROGRESS: drt_violations improved 92.9 % in window |  |
| intel2 | dpkit-kv3_io_ft-67781 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 21.5 | drt_violations best 3303 last 3303 rows 13 | before-window best 327883, window best 3303 | PROGRESS: drt_violations improved 99.0 % in window |  |
