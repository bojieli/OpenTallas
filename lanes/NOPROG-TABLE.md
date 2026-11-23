# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 10:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 4, 'GRT-LABEL': 4, 'YOUNG': 98, 'NO-DATA': 11, 'EXCLUDED': 1, 'PROGRESS': 40}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_2_tapbal_grt | 3.5 | last meaningful line 1.8 h ago (48/55 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -1073.03 ps (< -300, gate TT >= -42); job age 3.5  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 43.2 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 16.0 | last meaningful line 6.0 h ago (216/225 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (FAM-S81-DSDV-R1 decides |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 11.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 11.5 | repair_TNS best 421499 last 421499 rows 1 | before-window best 421499, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-KV-PV-SINKSPR |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 14.7 | grt rounds 2 overflow 5:79519 -> 10:58103 | GRT-LABEL: DESIGN-FAIL: overflow 58103 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 11.7 | grt rounds 2 overflow 5:43627 -> 10:30741 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:24595 -> 10:17047 | GRT-LABEL: DESIGN-FAIL: overflow 17047 at round 10 > 1000 |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 9.9 | grt rounds 2 overflow 5:11530 -> 10:1570 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 5.1 | repair_TNS best 924724 last 924724 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-439143 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 6.5 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 5_2_route | 10.1 | drt_violations best 6143 last 6143 rows 3 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t24__cleece78ec-86117 | slice_station__t24 | postcts_gate_FF | 0.9 | last meaningful line 0.0 h ago (678/678 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t30__clcedefe91-897059 | slice_station__t30 | 3_4_place_resized | 0.2 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-810171 | slice_station__t36 | 3_3_place_gp | 0.3 | overflow best 0.4065 last 0.4072 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | otc-1132991-30340 | 1132991 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1248808-2300 | 1248808 | ot_bind_native_50cbf650117b18109931fc8d | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-274226-16996 | 274226 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (8632/8632 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | otc-3834020-29448 | 3834020 | cts_0904 | 1.2 | last meaningful line 0.0 h ago (4548/4548 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | otc-818491-29096 | 818491 | 3_3_place_gp | 0.3 | overflow best 0.1267 last 0.1841 rows 181 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | otc-923617-6053 | 923617 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2-3082261 | eco_20261122_223531_3628570-i2 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2-1211453 | eco_20261123_075519_12410-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1-366371 | eco_20261123_130918_3027414-i1 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (295/1364 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_152004_738176-i1-681184 | eco_20261123_152004_738176-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (288/454 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3399753 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 0.7 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-3749481 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 15.8 | last meaningful line 2.8 h ago (211/216 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_3_place_gp | 5.2 | overflow best 0.4954 last 0.4954 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 15.8 | drt_violations best 19724 last 19724 rows 2 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 15.6 | drt_violations best 19584 last 19584 rows 2 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | eco-abs-3092443 | eco-abs | generate_abstract | 0.9 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2t-3323150 | eco_20261122_164248_3895049-i2t | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (238/1545 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-fin-1139635 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_3548432_ff_99716 | so_3548432_ff_99716 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc2 | so_4099588_ff_48410 | so_4099588_ff_48410 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_4099588_tt_48410 | so_4099588_tt_48410 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_72353_ff_80831 | so_72353_ff_80831 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_72353_tt_80831 | so_72353_tt_80831 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 6.2 | drt_violations best 12 last 12 rows 6 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_1_grt | 8.6 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 429406 last 429406 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 8.7 | drt_violations best 22714 last 22714 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 8.5 | last meaningful line 4.5 h ago (211/219 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 2_1_floorplan | 0.3 | repair_Viol best 8957 last 8957 rows 141 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-822390 | dsdv_slice_lepe_mu_LP__t2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3738 last 0.3738 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_ctl-865079 | hd_ctl | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3141/3141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-943411 | hd_lep0N | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7489 last 0.7791 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_4_place_resized | 5.9 | last meaningful line 1.0 h ago (695/695 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 3.8 | last meaningful line 3.8 h ago (3/3 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 10.1 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1-896574 | eco_20261123_124118_879330-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (178/178 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 4.4 | drt_violations best 556 last 556 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1t-2913491 | eco_20261123_160238_2681508-i1t | 5_2_route | 2.2 | drt_violations best 38903 last 38903 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (234/1303 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1t-259914 | eco_20261123_171842_3718765-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 3.1 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 4.7 | last meaningful line 0.8 h ago (9993/9993 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4070/4070 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 5_1_grt | 0.9 | last meaningful line 0.2 h ago (275/517 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (3717/3717 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t44-1589478 | slice_station__t44 | 3_3_place_gp | 0.2 | overflow best 0.2644 last 0.2644 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t47-118217 | slice_station__t47 | postcts_gate_FF | 0.9 | last meaningful line 0.0 h ago (790/790 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (560/585 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | postcts_gate_FF | 1.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl503f4913-3142679 | slice_station__t7 | 5_2_route | 1.4 | drt_violations best 4970 last 4970 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-slice_station__t7__cl945bc067-3551157 | slice_station__t7 | 5_2_route | 1.2 | drt_violations best 4398 last 4398 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_1_grt | 0.6 | last meaningful line 0.4 h ago (262/878 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1-1751532 | eco_20261123_140713_549985-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1t-2511984 | eco_20261123_163717_2005956-i1t | 5_2_route | 1.6 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 1.5 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 14.2 | drt_violations best 33830 last 33830 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl23f6a148-767022 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8584 last 0.8915 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 4.1 | last meaningful line 0.8 h ago (11052/11052 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | tt_setup_measure_grt | 11.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_2_route | 14.1 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_2_route | 10.3 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 13.2 | drt_violations best 137246 last 137246 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | generate_abstract | 13.9 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 14.0 | drt_violations best 103153 last 103153 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | otc-1043173-6524 | 1043173 | gold_b.ys | 0.4 | last meaningful line 0.3 h ago (67868/67868 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1377936-8989 | 1377936 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1426976-4775 | 1426976 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-1429205-18079 | 1429205 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 12.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 3.0 | drt_violations best 922 last 922 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | prd-fin-3529532 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 2.9 |  | NO-DATA: no log found |  |
| intel1 | dpkit-kv3_hgi_v4-3428093 | kv3_hgi_v4 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7662 last 0.7662 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 4.7 | drt_violations best 60213 last 60213 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-3848070 | kv3_hroot | 2_1_floorplan | 0.1 | repair_Viol best 780 last 780 rows 304 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 6_report | 28.0 | last meaningful line 0.1 h ago (1074/1074 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 6.2 | last meaningful line 0.2 h ago (153/153 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-native59-2836475 | native59 | 3_3_place_gp | 1.0 | overflow best 0.6374 last 0.6374 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | postcts_gate_FF | 13.6 | last meaningful line 0.0 h ago (1865/1865 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t31-3856690 | slice_station__t31 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 6_report | 14.8 | last meaningful line 0.1 h ago (193/193 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 14.3 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-2359243-22693 | 2359243 | gen_lint_yosys | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-2452779-29048 | 2452779 | gen_lint_yosys | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-2759871-31481 | 2759871 | 3_3_place_gp | 1.0 | overflow best 0.2118 last 0.4887 rows 127 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | otc-2885480-28772 | 2885480 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-3099315-18388 | 3099315 | 3_3_place_gp | 0.7 | overflow best 0.2118 last 0.4051 rows 93 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | otc-3333117-8872 | 3333117 | 3_3_place_gp | 0.5 | overflow best 0.2118 last 0.6816 rows 155 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | otc-3804001-18379 | 3804001 | asbuilt.yosys | 0.1 | last meaningful line 0.1 h ago (11/11 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 4.1 | drt_violations best 42348 last 42348 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2-2683723 | eco_20261122_165619_1517073-i2 | 5_2_route | 1.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (212/215 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1263597 | coll_ftm | 5_2_route | 1.7 | drt_violations best 10172 last 10172 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3375490 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3301890 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2649503 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2343147 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 4.9 | drt_violations best 27 last 27 rows 5 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 3.6 | drt_violations best 40447 last 40447 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | otc-832085-28248 | 832085 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t2-473058 | serdes__t2 | 4_1_cts | 0.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | otc-914286-4967 | 914286 | run | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 13.3 | drt_violations best 17052 last 17052 rows 12 | before-window best 25896, window best 17052 | PROGRESS: drt_violations improved 34.2 % in window |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 11.4 | drt_violations best 1269 last 1568 rows 23 | before-window best 22132, window best 1269 | PROGRESS: drt_violations improved 94.3 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 15.8 | drt_violations best 1983 last 1983 rows 13 | before-window best 112571, window best 1983 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 18.0 | drt_violations best 10583 last 10583 rows 12 | before-window best 12997, window best 10583 | PROGRESS: drt_violations improved 18.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 14.6 | drt_violations best 48060 last 48060 rows 11 | before-window best 71122, window best 48060 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 15.0 | drt_violations best 52820 last 52820 rows 11 | before-window best 62246, window best 52820 | PROGRESS: drt_violations improved 15.1 % in window |  |
| epyc2 | prd-eco_20261123_092856_2078955-i1-3664424 | eco_20261123_092856_2078955-i1 | 5_1_grt | 0.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-hd_lep0N_w-4154426 | hd_lep0N_w | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 20.9 | drt_violations best 5 last 5 rows 44 | before-window best 409476, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 15.9 | drt_violations best 60407 last 60407 rows 11 | before-window best 71216, window best 60407 | PROGRESS: drt_violations improved 15.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 26.6 | drt_violations best 21 last 23 rows 51 | before-window best 47, window best 21 | PROGRESS: drt_violations improved 55.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 30.0 | drt_violations best 7590 last 7590 rows 20 | before-window best 9545, window best 7590 | PROGRESS: drt_violations improved 20.5 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 17.5 | drt_violations best 14710 last 63695 rows 18 | before-window best 15247, window best 14710 | PROGRESS: drt_violations improved 3.5 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 13.5 | last meaningful line 3.5 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t12-3181944 | slice_station__t12 | 5_2_route | 1.3 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 5_1_grt | 1.0 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_1_grt | 1.1 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 5_1_grt | 0.9 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 10.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 14.1 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-phy__t1-157767 | phy__t1 | 5_1_grt | 1.1 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 13.3 | repair_TNS best 20739.8 last 20739.8 rows 2 | before-window best 21514, window best 20739.8 | PROGRESS: repair_TNS improved 3.6 % in window |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 29.7 | drt_violations best 21144 last 21144 rows 3 | before-window best 175829, window best 21144 | PROGRESS: drt_violations improved 88.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 29.5 | drt_violations best 34800 last 34800 rows 10 | before-window best 40912, window best 34800 | PROGRESS: drt_violations improved 14.9 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pve3ab90e7-3479131 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 16.1 | drt_violations best 91811 last 91811 rows 6 | before-window best 344103, window best 91811 | PROGRESS: drt_violations improved 73.3 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 13.4 | drt_violations best 1960 last 1960 rows 11 | before-window best 90237, window best 1960 | PROGRESS: drt_violations improved 97.8 % in window |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 23.5 | drt_violations best 2223 last 2223 rows 16 | before-window best 64401, window best 2223 | PROGRESS: drt_violations improved 96.5 % in window |  |
