# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 20:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 5, 'NO-PROGRESS': 2, 'GRT-LABEL': 3, 'YOUNG': 108, 'NO-DATA': 34, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | postcts_gate_FF | 8.5 | last meaningful line 0.0 h ago (22/22 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -408.59 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 36.6 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best 13 | NO-PROGRESS: drt_violations best 13 vs 13 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 9.3 | grt rounds 4 overflow 5:128855 -> 10:3237 -> 15:2296 -> 20:2337 | UNSIGNABLE: GRT overflow flat: overflow 2296 at iteration 15 -> 2337 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 15.8 | grt rounds 8 overflow 15:1367 -> 20:1472 -> 25:1063 -> 30:774 -> 35:659 -> 40:652 | UNSIGNABLE: GRT overflow flat: overflow 659 at iteration 35 -> 652 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 15.7 | grt rounds 8 overflow 15:1394 -> 20:1584 -> 25:1212 -> 30:970 -> 35:768 -> 40:889 | UNSIGNABLE: GRT overflow flat: overflow 768 at iteration 35 -> 889 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 15.9 | grt rounds 8 overflow 15:1427 -> 20:1597 -> 25:1148 -> 30:913 -> 35:770 -> 40:787 | UNSIGNABLE: GRT overflow flat: overflow 770 at iteration 35 -> 787 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 31.9 | drt_violations best 1 last 1 rows 47 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 6.5 | grt rounds 4 overflow 5:3923 -> 10:2178 -> 15:1693 -> 20:894 | GRT-LABEL: DESIGN-FAIL: overflow 2178 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 11.5 | grt rounds 6 overflow 5:130016 -> 10:3224 -> 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 | GRT-LABEL: DESIGN-FAIL: overflow 3224 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 12.9 | grt rounds 9 overflow 20:1502 -> 25:1102 -> 30:804 -> 35:688 -> 40:714 -> 45:641 | GRT-LABEL: DESIGN-FAIL: overflow 2188 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-3470788 | col_h9_r2__t1 | 3_1_place_gp_skip_io | 0.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3140082 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 1.7 | last meaningful line 0.1 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3152819 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 1.7 | last meaningful line 0.1 h ago (109/109 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3157172 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 1.7 | last meaningful line 0.1 h ago (109/109 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t10-2771062 | ot_s81sl_leaf__t10 | 3_3_place_gp | 0.3 | last meaningful line 0.1 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t24__cl2456157b-3491902 | ot_s81sl_leaf__t24 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (1054/1054 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cldc737267-713682 | slw_hc2 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 1.4 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-32da6c3b9dec | lecq9-32da6c3b9dec | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-c351666358dc | lecq9-c351666358dc | - | 0.5 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 2.0 | last meaningful line 0.0 h ago (33/34 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 11.4 | drt_violations best 392 last 396 rows 33 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc11 | lecaf-hc0-487 | lecaf-hc0 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_2_route | 8.4 | drt_violations best 228359 last 228359 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc12 | otc-209901-23622 | 209901 | asbuilt.yosys | 0.4 | last meaningful line 0.1 h ago (242584/242584 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | prd-eco_20261126_031548_650250-i1-2936422 | eco_20261126_031548_650250-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-coll_n-4156948 | coll_n | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (1000/1000 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-coll_ucie-4156864 | coll_ucie | 3_3_place_gp | 0.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_ctl-2980421 | hd_ctl | 5_2_route | 2.9 | drt_violations best 4596 last 4596 rows 3 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p4__ret4_es_4-3437284 | kv3_hg_v1p4__ret4_es_4 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2649 last 0.2649 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-4027604 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8516 last 8516 rows 17 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 11.6 | drt_violations best 26226 last 26226 rows 5 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3710191 | sle_hc0 | 3_3_place_gp | 0.2 | overflow best 0.9444 last 0.9444 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3697755 | sle_hc0 | 3_3_place_gp | 0.2 | overflow best 0.9401 last 0.9401 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4872/4872 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (6303/6303 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t30__cl1653104c-3863131 | slice_station__t30 | 3_4_place_resized | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | pregrt_ff_hold | 2.9 | repair_TNS best 4556.18 last 4556.18 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1t-2801726 | eco_20261125_200405_3323313-i1t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 15.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 15.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 15.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-4039941 | col_h9_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 1215 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1700011 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3768357 | col_h9_r0_p3__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-4137527 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 394 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1487255 | col_h9_r0_p5__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-3048984 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.4 | overflow best 0.4841 last 0.4841 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv9da72aa7-59078 | col_h9_r0_p6__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 918 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4593e8e5-4101364 | col_h9_r1__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv637e5d47-3915646 | col_h9_r1__t1 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-3422879 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.1978 last 0.1978 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-3576224 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.2591 last 0.2591 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvac06e607-3640467 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.3609 last 0.3609 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-3833689 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.5329 last 0.5329 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r1__t1__clf32cde8d__pvee46d7b8-132554 | col_h9_r1__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-80995 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 273 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-66998 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 2770 last 2770 rows 1283 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-3778249 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.3984 last 0.3984 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-3428843 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 89 last 89 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3327555 | dsdv_slice_kv512_C__t1 | 2_1_floorplan | 0.3 | repair_Viol best 2813 last 2813 rows 784 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2307190 | ot_s81sl_kv_leaf__t1 | 3_3_place_gp | 0.5 | overflow best 0.2 last 0.2 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 6_report | 15.0 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | tt_setup_repair_grt | 10.2 | repair_Viol best 32057 last 32057 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | lecaf-colls-ctl | lecaf-colls-ctl | - | 0.9 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-0ce42cbdc4b0 | lecq9-0ce42cbdc4b0 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-1b3200859cc9 | lecq9-1b3200859cc9 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-59017ec270a7 | lecq9-59017ec270a7 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-1572699-31485 | 1572699 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-1892608-7747 | 1892608 | signoff | 1.9 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | otc-1927948-12220 | 1927948 | gen_lint_yosys | 0.6 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-382371 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8337 last 0.8337 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2000119 | col_h9_r0_p1__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1476523 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 195 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-4037292 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.4 | overflow best 0.5162 last 0.5162 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-870586 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8417 last 0.8417 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv082a7609-1182483 | col_h9_r0_p6__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (438/438 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-419762 | col_h9_r1__t1 | 3_4_place_resized | 0.3 | repair_Remaining best 71551 last 71551 rows 33 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-1765671 | col_h9_r1__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (233/233 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-538704 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4037 last 0.405 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv5ffbfb8b-933291 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.5329 last 0.5329 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-369324 | col_h9_r1__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1815335 | col_h9_r2__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-1235249 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (8457/8457 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t3-1774923 | ot_s81sl_kv_leaf__t3 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-683481 | ot_s81sl_leaf__t33 | 3_1_place_gp_skip_io | 0.2 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 10.4 | drt_violations best 9504 last 9504 rows 4 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | lecaf-hc3xl-afda1e-5 | lecaf-hc3xl-afda1e | - | 1.0 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-125656921876 | lecq9 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-8d66d58fbf89 | lecq9-8d66d58fbf89 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-9add37347d49 | lecq9-9add37347d49 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-c8c740c6d798 | lecq9-c8c740c6d798 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1294537-1483 | 1294537 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1530472-10583 | 1530472 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1589750-5019 | 1589750 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-2229784-26324 | 2229784 | gen_lint_yosys | 0.8 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | otc-2719199-22681 | 2719199 | gen_lint_yosys | 0.7 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | otc-2899154-16798 | 2899154 | gen_lint_yosys | 0.6 | last meaningful line 0.1 h ago (9/9 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 4.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-4174262-4961 | 4174262 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-877014-30307 | 877014 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-884136-28032 | 884136 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-941401-14145 | 941401 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3-312208 | eco_20261125_104318_3955073-i3 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1t-928710 | eco_20261126_033711_2888564-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 9.4 | drt_violations best 174634 last 174634 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | tt_setup_measure_grt | 10.8 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 8.9 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 13.0 | last meaningful line 0.5 h ago (295/296 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 9.4 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 10.0 | last meaningful line 0.5 h ago (287/288 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 10.2 | drt_violations best 171015 last 171015 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 9.4 | drt_violations best 934 last 934 rows 12 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 162182 last 162182 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 9.9 | last meaningful line 0.2 h ago (162/162 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 11.5 | last meaningful line 1.3 h ago (277/1283 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_020316_3686099-i1t-150182 | eco_20261126_020316_3686099-i1t | 5_2_route | 2.7 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | ap-ageom-kw-kv3-hub-Wo-dump-111057 | kv3-hub-Wo-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-1305241 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.9 | overflow best 0.4128 last 0.4128 rows 18 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 10.3 | drt_violations best 167111 last 167111 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 10.4 | drt_violations best 59568 last 59568 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_phy-3158276 | kv3_phy | 5_2_route | 1.8 | drt_violations best 5103 last 5103 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_SD_v1-3706384 | kv3_sys_SD_v1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (243/244 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-3994132 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (342/342 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_2_route | 10.9 | drt_violations best 75122 last 75122 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3756903 | slw_hc3 | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 6_report | 10.3 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | eco-abs-4030377 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 0.6 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-edda9501c230 | lecq9-edda9501c230 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | otc-178621-11182 | 178621 | - | 4.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | flow | 2.0 | last meaningful line 0.0 h ago (4251/4251 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 5.3 |  | NO-DATA: no log found |  |
| intel1 | otc-681953-5114 | 681953 | - | 1.2 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 4.6 | last meaningful line 4.5 h ago (3/3 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 4.8 | drt_violations best 10221 last 10221 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3900738 | coll_ftm | abstract_exact | 2.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_serdes-2767259 | hd_serdes | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6__ret4_wn_6-2758773 | kv3_hg_v1p6__ret4_wn_6 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 3_3_place_gp | 3.1 | overflow best 0.0999 last 0.0999 rows 48 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1558093 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3690925 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8517 last 8517 rows 471 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3488734 | sle_hc0 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9984 last 0.9984 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-717052 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2986 last 2986 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-2946484 | slice_station__t51 | 3_3_place_gp | 0.4 | overflow best 0.1998 last 0.1998 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3633925 | slw_hc0 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 10.2 | drt_violations best 211273 last 211273 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pvf390b1f5-3026641 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 33.9 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 11.5 | repair_TNS best 38.095 last 38.095 rows 11 | before-window best 141.471, window best 38.095 | PROGRESS: repair_TNS improved 73.1 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 11.5 | drt_violations best 3472 last 3472 rows 7 | before-window best 255884, window best 3472 | PROGRESS: drt_violations improved 98.6 % in window |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 5_1_grt | 2.9 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv7808008f-3071367 | col_h9_r0_p6__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-3421139 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-3346414 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-serdes__t4-2394583 | serdes__t4 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 19.2 | drt_violations best 3875 last 3875 rows 15 | before-window best 78321, window best 3875 | PROGRESS: drt_violations improved 95.1 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 19.2 | drt_violations best 16003 last 16003 rows 12 | before-window best 121225, window best 16003 | PROGRESS: drt_violations improved 86.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 19.6 | drt_violations best 724 last 724 rows 23 | before-window best 77096, window best 724 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 12.4 | drt_violations best 11519 last 11519 rows 16 | before-window best 33693, window best 11519 | PROGRESS: drt_violations improved 65.8 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-31533 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 11.4 | drt_violations best 22097 last 22097 rows 3 | before-window best 174806, window best 22097 | PROGRESS: drt_violations improved 87.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 13.0 | drt_violations best 15 last 15 rows 21 | before-window best 176025, window best 15 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 22.0 | drt_violations best 398 last 398 rows 22 | before-window best 135197, window best 398 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 19.2 | drt_violations best 77076 last 77076 rows 3 | before-window best 470122, window best 77076 | PROGRESS: drt_violations improved 83.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 11.0 | drt_violations best 43234 last 43234 rows 2 | before-window best 176573, window best 43234 | PROGRESS: drt_violations improved 75.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 13.0 | drt_violations best 5497 last 5497 rows 9 | before-window best 178781, window best 5497 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 23.9 | drt_violations best 390 last 390 rows 54 | before-window best 446, window best 390 | PROGRESS: drt_violations improved 12.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 11.5 | drt_violations best 44089 last 44089 rows 2 | before-window best 178567, window best 44089 | PROGRESS: drt_violations improved 75.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 12.8 | drt_violations best 377 last 377 rows 29 | before-window best 158828, window best 377 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 1038 last 1038 rows 11 | before-window best 159056, window best 1038 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 11.5 | drt_violations best 882 last 882 rows 15 | before-window best 157970, window best 882 | PROGRESS: drt_violations improved 99.4 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 15.9 | repair_TNS best 2731.45 last 2731.45 rows 11 | before-window best 3373.18, window best 2731.45 | PROGRESS: repair_TNS improved 19.0 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 15.9 | drt_violations best 6482 last 6482 rows 9 | before-window best 178263, window best 6482 | PROGRESS: drt_violations improved 96.4 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 15.8 | drt_violations best 369 last 371 rows 28 | before-window best 159843, window best 369 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 15.8 | drt_violations best 379 last 379 rows 23 | before-window best 159806, window best 379 | PROGRESS: drt_violations improved 99.8 % in window |  |
