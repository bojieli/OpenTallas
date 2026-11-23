# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 08:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 2, 'GRT-LABEL': 5, 'YOUNG': 105, 'NO-DATA': 11, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:8198 -> 10:8148 | UNSIGNABLE: GRT overflow flat: overflow 8198 at iteration 5 -> 8148 at iteration 10: flat fo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | tt_setup_repair | 3.4 | repair_Violations best 150 last 170 rows 63 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -758.78 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 24.9 | grt rounds 2 overflow 5:14057 -> 10:13400 | UNSIGNABLE: 5_1_grt.log latest setup WNS -499.02 ps (< -300, gate TT >= -42); job age 24.9 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 41.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 8.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | 5_1_grt | 7.5 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | 5_1_grt | 7.4 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3747062 | ot_s81sl_leaf__t14 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:2073 -> 10:1458 | GRT-LABEL: DESIGN-FAIL: overflow 1458 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3969309 | ot_s81sl_leaf__t47 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:23016 -> 10:15816 | GRT-LABEL: DESIGN-FAIL: overflow 15816 at round 10 > 1000 |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 8.2 | grt rounds 2 overflow 5:11530 -> 10:1570 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (7141/7141 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | pregrt_ff_hold | 4.7 | repair_TNS best 351.902 last 351.902 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 4.8 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3857880 | ot_s81sl_leaf__t14 | 5_1_grt | 2.6 | last meaningful line 0.2 h ago (268/1275 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t2-2430221 | serdes__t2 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 5_2_route | 8.3 | last meaningful line 0.0 h ago (271/272 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_2_route | 8.6 | drt_violations best 7876 last 7876 rows 3 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | otc-2367622-7114 | 2367622 | 3_3_place_gp | 0.5 | overflow best 0.0984 last 0.0984 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | otc-2705414-4704 | 2705414 | place | 0.2 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i2t-1170770 | eco_20261123_075519_12410-i2t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1t-3090789 | eco_20261123_130918_3027414-i1t | 5_2_route | 3.3 | drt_violations best 4643 last 4643 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_152004_738176-i1t-1508677 | eco_20261123_152004_738176-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 14.3 | last meaningful line 1.3 h ago (211/214 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 13.2 | last meaningful line 2.8 h ago (211/218 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_1_floorplan | 3.7 | last meaningful line 3.0 h ago (1424/1424 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (1144/1144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 10.2 | last meaningful line 1.3 h ago (227/236 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 6_report | 16.5 | last meaningful line 0.0 h ago (948/948 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 16.5 | drt_violations best 11381 last 11381 rows 3 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 6_report | 16.5 | last meaningful line 0.0 h ago (1073/1073 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_2_route | 14.3 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 14.1 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | eco-abs-1246208 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-2037456 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_073408_3918836-i1t-1139635 | eco_20261123_073408_3918836-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (248/249 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-fin-2840670 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1009/1009 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | 5_2_route | 3.3 | drt_violations best 9417 last 9417 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 4.4 | drt_violations best 60059 last 60059 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 6.8 | repair_TNS best 54572.8 last 54572.8 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4013616 | col_h9_r1__t1 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (2508/2539 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 6.9 | drt_violations best 172065 last 172065 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 6.8 | last meaningful line 2.7 h ago (211/217 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_2_tapbal_grt | 1.8 | last meaningful line 0.1 h ago (48/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_3_place_gp | 4.2 | overflow best 0.0992 last 0.0992 rows 44 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (819/836 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 2.0 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 8.4 | last meaningful line 0.3 h ago (296/297 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_2_route | 3.8 | drt_violations best 14086 last 14086 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1t-2913491 | eco_20261123_160238_2681508-i1t | 5_2_route | 0.4 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_3450761_ff_84118 | so_3450761_ff_84118 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_3450761_tt_84118 | so_3450761_tt_84118 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-871345 | dsdv_slice_c1x_C__t10 | port_bind | 1.9 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 14.3 | last meaningful line 4.2 h ago (211/220 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 5.0 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (4609/4609 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v3-1745589 | kv3_pc_v3 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 3.0 | last meaningful line 0.8 h ago (9861/9861 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_c-98167 | sle_su_c | 3_1_place_gp_skip_io | 0.5 | overflow best 0.0992 last 0.0992 rows 52 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-slice_station__t12-1545450 | slice_station__t12 | 3_3_place_gp | 0.1 | overflow best 0.2479 last 0.2486 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t14-1549888 | slice_station__t14 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t20-1554161 | slice_station__t20 | 3_3_place_gp | 0.1 | overflow best 0.2575 last 0.2605 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t24__cl64811a5d-1581904 | slice_station__t24 | 3_3_place_gp | 0.1 | overflow best 0.3444 last 0.3444 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slice_station__t27-932866 | slice_station__t27 | 3_3_place_gp | 0.3 | overflow best 0.3338 last 0.3338 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t29__clc7772371-1616228 | slice_station__t29 | 3_3_place_gp | 0.1 | overflow best 0.3654 last 0.3654 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slice_station__t30__cl6a190133-1571837 | slice_station__t30 | 3_3_place_gp | 0.1 | overflow best 0.2619 last 0.2619 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t37-978315 | slice_station__t37 | 3_3_place_gp | 0.3 | overflow best 0.3422 last 0.3423 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t38-1603419 | slice_station__t38 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t41-976663 | slice_station__t41 | 3_3_place_gp | 0.3 | overflow best 0.2672 last 0.2672 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-1555774 | slice_station__t42 | 3_3_place_gp | 0.1 | last meaningful line -0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-981912 | slice_station__t43 | 3_3_place_gp | 0.3 | overflow best 0.265 last 0.265 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t44-963120 | slice_station__t44 | 3_3_place_gp | 0.3 | overflow best 0.2592 last 0.2794 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t47-1593334 | slice_station__t47 | 3_3_place_gp | 0.1 | overflow best 0.3281 last 0.3281 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slice_station__t49-2074686 | slice_station__t49 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (169/169 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-2043294 | slice_station__t50 | 1_synth | 0.0 | last meaningful line -0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-2069863 | slice_station__t50 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (206/206 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-2049512 | slice_station__t6 | 1_synth | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-2073347 | slice_station__t6 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t7__cl362204c4-1550762 | slice_station__t7 | 3_3_place_gp | 0.1 | overflow best 0.2556 last 0.2566 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t7__cl503f4913-1514430 | slice_station__t7 | 3_3_place_gp | 0.1 | overflow best 0.2417 last 0.2425 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t7__cl945bc067-2080852 | slice_station__t7 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2076901-15454 | 2076901 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_2_route | 4.4 | drt_violations best 41 last 41 rows 6 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1t-81578 | eco_20261123_140713_549985-i1t | 5_2_route | 2.4 | drt_violations best 7895 last 7895 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | so_1334474_ff_72185 | so_1334474_ff_72185 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_1334474_tt_72185 | so_1334474_tt_72185 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_1981151_ff_51054 | so_1981151_ff_51054 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_1981151_tt_51054 | so_1981151_tt_51054 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 12.4 | drt_violations best 183055 last 183055 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 14.3 | last meaningful line 4.3 h ago (216/223 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 2.3 | last meaningful line 0.5 h ago (10919/10919 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 9.8 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 9.5 | repair_TNS best 622.395 last 622.395 rows 5 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | postcts_gate_FF | 12.3 | last meaningful line 0.0 h ago (833/833 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 11.5 | grt_hold_TNS best 33416.3 last 33416.3 rows 3 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | postcts_gate_TT | 8.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_2_route | 11.5 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_2_route | 12.2 | drt_violations best 15904 last 15904 rows 2 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_2_route | 12.3 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 10.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3219182-8809 | 3219182 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3423441-15044 | 3423441 | west_drc | 0.1 | last meaningful line -0.0 h ago (2284/2284 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-928970-21237 | 928970 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2t-2017343 | eco-i2t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (281/281 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | relec-coll-s-epoch-hint-0724 | relec-coll-s-epoch-hint | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | so_3420887_ff_67642 | so_3420887_ff_67642 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1030/1030 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_3420887_tt_67642 | so_3420887_tt_67642 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1030/1030 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | generate_abstract | 27.7 | last meaningful line 0.0 h ago (342/342 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 14.3 | drt_violations best 9993 last 9993 rows 2 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_2_route | 3.0 | last meaningful line 0.2 h ago (247/248 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 4.4 | last meaningful line 0.2 h ago (7122/7122 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | postcts_gate_TT | 11.9 | last meaningful line 0.1 h ago (859/859 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | generate_abstract | 14.3 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_2_route | 13.1 | drt_violations best 70075 last 70075 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | postcts_gate_FF | 12.6 | last meaningful line -0.0 h ago (36351/36351 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-1191049-8343 | 1191049 | export_ss | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-599421-31596 | 599421 | 1_1_yosys_canonicalize | 0.2 | last meaningful line 0.1 h ago (223/223 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_2_route | 4.4 | drt_violations best 15957 last 15957 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (217/220 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 4.5 | last meaningful line 0.1 h ago (245/283 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 3_3_place_gp | 6.9 | overflow best 0.0987 last 0.0987 rows 44 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-67781 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-102653 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 3.2 | drt_violations best 19526 last 19526 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_2_route | 1.8 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 11.6 | drt_violations best 19416 last 19416 rows 11 | before-window best 39405, window best 19416 | PROGRESS: drt_violations improved 50.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 77.7 | last meaningful line 0.9 h ago (1624/1624 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | 5_1_grt | 7.5 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 9.9 | drt_violations best 1269 last 1810 rows 20 | before-window best 87459, window best 1269 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 14.3 | drt_violations best 2657 last 2657 rows 10 | before-window best 112571, window best 2657 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 16.6 | drt_violations best 7 last 7 rows 7 | before-window best 133507, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 16.5 | drt_violations best 11209 last 11209 rows 11 | before-window best 13880, window best 11209 | PROGRESS: drt_violations improved 19.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 13.1 | drt_violations best 50311 last 50311 rows 10 | before-window best 167955, window best 50311 | PROGRESS: drt_violations improved 70.0 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 13.5 | drt_violations best 55792 last 55792 rows 10 | before-window best 75867, window best 55792 | PROGRESS: drt_violations improved 26.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 22 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 19.2 | drt_violations best 7 last 7 rows 28 | before-window best 409476, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 14.2 | drt_violations best 65161 last 65161 rows 10 | before-window best 108964, window best 65161 | PROGRESS: drt_violations improved 40.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 24.9 | drt_violations best 25 last 25 rows 44 | before-window best 57, window best 25 | PROGRESS: drt_violations improved 56.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 28.3 | drt_violations best 7732 last 9662 rows 19 | before-window best 12904, window best 7732 | PROGRESS: drt_violations improved 40.1 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 15.8 | drt_violations best 14710 last 63695 rows 18 | before-window best 15880, window best 14710 | PROGRESS: drt_violations improved 7.4 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 11.7 | last meaningful line 1.7 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 9.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 8.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 8.5 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.3 | repair_TNS best 3113.16 last 3113.16 rows 9 | before-window best 5702.11, window best 3113.16 | PROGRESS: repair_TNS improved 45.4 % in window |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 28.0 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 64845 < best completed total 175829 (in-iter |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 27.7 | drt_violations best 37187 last 37187 rows 8 | before-window best 60023, window best 37187 | PROGRESS: drt_violations improved 38.0 % in window |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 26.2 | drt_violations best 15921 last 15921 rows 2 | before-window best 109763, window best 15921 | PROGRESS: drt_violations improved 85.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 14.4 | drt_violations best 98568 last 98568 rows 4 | before-window best 344103, window best 98568 | PROGRESS: drt_violations improved 71.4 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 11.7 | drt_violations best 3240 last 3240 rows 5 | before-window best 90237, window best 3240 | PROGRESS: drt_violations improved 96.4 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 21.7 | drt_violations best 3303 last 3303 rows 13 | before-window best 327883, window best 3303 | PROGRESS: drt_violations improved 99.0 % in window |  |
