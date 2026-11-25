# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 01:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 5, 'GRT-LABEL': 3, 'YOUNG': 117, 'NO-DATA': 24, 'PROGRESS': 36}. Hosts without report: ['intel1'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | tt_setup_repair_grt | 5.7 | repair_Remaining best 334880 last 334880 rows 16 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -800.35 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | tt_setup_repair_grt | 5.6 | repair_Violations best 0 last 0 rows 13 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -1103.89 ps (< -300, gate TT >= -42); j | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 6.7 | repair_TNS best 40160.3 last 40160.3 rows 1 | before-window best 40160.3, window best 40160.3 | NO-PROGRESS: repair_TNS best 40160.3 vs 40160.3 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-GLUE-IMAGES decides; |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 11.6 | repair_TNS best 145595 last 145595 rows 1 | before-window best 145595, window best 145595 | NO-PROGRESS: repair_TNS best 145595 vs 145595 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 8.3 | last meaningful line 8.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 6.4 | last meaningful line 6.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | tt_setup_repair_grt | 8.5 | last meaningful line 0.0 h ago (541/541 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -614.38 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | otc-120424-12773 | 120424 | signoff | 6.9 | last meaningful line 6.8 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 11.7 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 6.8 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 13.5 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 7.4 | last meaningful line 1.8 h ago (305/1314 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 7.4 | last meaningful line 2.3 h ago (287/1297 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | tt_setup_repair | 7.8 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | postcts_gate_FF | 5.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 5.2 | repair_TNS best 169360 last 169360 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 15.5 | drt_violations best 416066 last 416066 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 12.3 | drt_violations best 13130 last 13130 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 12.7 | drt_violations best 149411 last 149411 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 13.3 | drt_violations best 171 last 171 rows 10 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 14.4 | drt_violations best 272423 last 272423 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 14.4 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 14.5 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | postcts_gate_TT | 13.1 | last meaningful line 0.1 h ago (845/845 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-3240895 | slw_st_a_v1 | 2_1_floorplan | 0.1 | repair_Viol best 2328 last 2328 rows 577 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 12.2 | drt_violations best 13998 last 13998 rows 3 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 8.7 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 11.2 | drt_violations best 18820 last 18820 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | smp-3371771 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | smp-3415978 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | smp-3429142 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | ap-ageom-kw-kv3-pv-v4ne-grt-656502 | kv3-pv-v4ne-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc11 | ap-ageom-kw-kv3-pv-v8e-grt-656647 | kv3-pv-v8e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 11.3 | drt_violations best 166686 last 166686 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 12.3 | drt_violations best 16914 last 16914 rows 3 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 11.0 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 2.3 | last meaningful line 0.2 h ago (8462/8462 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | eco-abs-3419890 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 14.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-701258-11435 | 701258 | lec | 1.6 | LEC last write 1.6 h ago | YOUNG: evidence 1.6 h < 6 h |  |
| epyc11 | otc-701492-14947 | 701492 | lec | 1.6 | LEC last write 1.6 h ago | YOUNG: evidence 1.6 h < 6 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 3.4 | drt_violations best 18 last 18 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (295/379 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080337_31727-i1-2053095 | eco_20261125_080337_31727-i1 | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (289/361 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | prd-fin-1425156 | fin | 6_1_fill | 0.1 | last meaningful line 0.1 h ago (12/12 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | smp-718367 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | smp-734187 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | smp-801663 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | so_2564279_ff_84503 | so_2564279_ff_84503 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc11 | so_2564279_tt_84503 | so_2564279_tt_84503 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc11 | so_275066_ff_698 | so_275066_ff_698 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc11 | so_275066_tt_698 | so_275066_tt_698 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc11 | so_3752716_ff_56220 | so_3752716_ff_56220 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (908/908 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | so_3752716_tt_56220 | so_3752716_tt_56220 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (908/908 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_2_route | 5.3 | last meaningful line -0.0 h ago (13/13 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | postcts_gate_TT | 4.3 | last meaningful line -0.0 h ago (868/868 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 6_report | 9.0 | last meaningful line -0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h15_n9_s11_bt3_synth0-453315 | sta_region_nb0_h15_n9_s11_bt3_synth0 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (923/1246 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h17_n7_s8_bt3_synth0-454974 | sta_region_nb0_h17_n7_s8_bt3_synth0 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (927/1256 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h18_n7_s8_bt3_synth0-454093 | sta_region_nb0_h18_n7_s8_bt3_synth0 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (921/1174 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-2040585-24869 | 2040585 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | otc-2141451-19773 | 2141451 | eq13_q5 | 0.0 | last meaningful line -0.0 h ago (676812/676812 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2141706-2239 | 2141706 | eq13_q5 | 0.0 | last meaningful line -0.0 h ago (676801/676801 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2142399-12236 | 2142399 | eq13_q0 | 0.0 | last meaningful line -0.0 h ago (677614/677614 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2143124-4001 | 2143124 | eq13_q1 | 0.0 | last meaningful line -0.0 h ago (678200/678200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2143963-13902 | 2143963 | eq13_q7 | 0.0 | last meaningful line -0.0 h ago (679213/679214 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2145854-13065 | 2145854 | eq13_q5 | 0.0 | last meaningful line -0.0 h ago (676757/676757 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2146793-25418 | 2146793 | eq13_q0 | 0.0 | last meaningful line -0.0 h ago (677511/677511 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2147754-15378 | 2147754 | eq13_q4 | 0.0 | last meaningful line -0.0 h ago (676749/676749 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1-226978 | eco_20261124_204708_4151707-i1 | 5_2_route | 0.8 | last meaningful line -0.0 h ago (19/19 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| epyc2 | prd-fin-2033351 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 13.9 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 2.9 | last meaningful line 0.2 h ago (5258/5258 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2521918 | sle_sc_v3 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (3601/3601 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_1_grt | 1.2 | repair_Remaining best 48266 last 48266 rows 101 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3811/3812 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | generate_abstract | 15.9 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_3_fillcell | 16.0 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (4535/4535 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5260/5260 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_1_grt | 2.8 | repair_Remaining best 234741 last 234741 rows 203 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 2.8 | last meaningful line 0.0 h ago (260/261 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_2_route | 1.9 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2t-915490 | eco_20261124_235631_1843084-i2t | 5_3_fillcell | 2.3 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1t-3004488 | eco_20261125_073945_2252980-i1t | 5_2_route | 1.6 | last meaningful line 0.0 h ago (261/262 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (295/322 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-fin-4028039 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_2070661_ff_89885 | so_2070661_ff_89885 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_2070661_tt_89885 | so_2070661_tt_89885 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 17.1 | drt_violations best 320246 last 320246 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 6_report | 17.1 | last meaningful line 0.1 h ago (70/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 6_report | 17.1 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 17.1 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 5.3 | drt_violations best 16767 last 16767 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1-3306668 | eco_20261125_025941_3548303-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_071225_3873455-i1-1532615 | eco_20261125_071225_3873455-i1 | 5_2_route | 2.0 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i1-1572735 | eco_20261125_082653_3900765-i1 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (291/384 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 14.0 |  | NO-DATA: no log found |  |
| epyc8 | so_1547311_ff_10462 | so_1547311_ff_10462 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_1547311_tt_10462 | so_1547311_tt_10462 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | lec | 3.0 | LEC last write 0.4 h ago | YOUNG: evidence 3.0 h < 6 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | lec | 2.5 | LEC last write 0.0 h ago | YOUNG: evidence 2.5 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 5.1 | LEC last write 0.1 h ago | YOUNG: evidence 5.1 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3316/3316 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 150413 last 150413 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | lec | 4.4 | LEC last write 0.1 h ago | YOUNG: evidence 4.4 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 1450.9 last 1450.9 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (94/94 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 3.5 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (136/136 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-107375 | ot_s81sl_leaf__t1 | 3_3_place_gp | 0.9 | last meaningful line 0.0 h ago (1483/1483 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t23-3736910 | ot_s81sl_leaf__t23 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9047 last 0.9217 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3495886 | ot_s81sl_leaf__t25 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3531/3531 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-3466782 | ot_s81sl_leaf__t32 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.4986 last 0.4986 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t21-3663770 | slice_station__t21 | generate_abstract | 2.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | lec | 0.4 | LEC last write 0.0 h ago | YOUNG: evidence 0.4 h < 6 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3000/3000 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3588/3588 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 14.2 | drt_violations best 2440 last 2440 rows 11 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261125_090100_666856-i1-787277 | eco_20261125_090100_666856-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | ap-ageom-kw-kv3-pv-v1e-grt-533144 | kv3-pv-v1e-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | ap-ageom-kw-kv3-pv-v8-grt-409741 | kv3-pv-v8-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | ap-ageom-kw-kv3-pv-v8e-grt-387584 | kv3-pv-v8e-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3587886 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 29798 last 29798 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-74909 | hd_turn_a | 5_2_route | 0.2 | last meaningful line -0.0 h ago (220/221 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-705307 | kv3_pc_v1 | rtl_lint_flat | 0.0 | last meaningful line 0.0 h ago (8/8 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-707215 | kv3_pc_v1 | rtl_lint | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7-2379649 | kv3_pv_v7 | 3_5_place_dp | 0.9 | last meaningful line -0.0 h ago (35/35 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7e-3092815 | kv3_pv_v7e | 3_3_place_gp | 0.7 | overflow best 0.5163 last 0.527 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pve-3092926 | kv3_pve | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1249478 | slice_station__t12 | generate_abstract | 1.2 | last meaningful line -0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 8.6 | drt_violations best 154733 last 154733 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | otc-586571-16666 | 586571 | eq13_q15 | 0.0 | last meaningful line -0.0 h ago (684198/684199 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-587388-23610 | 587388 | eq13_out | 0.0 | last meaningful line -0.0 h ago (676772/676772 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-588235-2866 | 588235 | eq13_out | 0.0 | last meaningful line -0.0 h ago (676570/676570 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-589455-4151 | 589455 | eq13_q10 | 0.0 | last meaningful line -0.0 h ago (678507/678507 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-590647-21131 | 590647 | eq13_out | 0.0 | last meaningful line -0.0 h ago (675348/675348 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-591923-11783 | 591923 | eq13_out | 0.0 | last meaningful line -0.0 h ago (674938/674939 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-594090-20209 | 594090 | eq13_q9 | 0.0 | last meaningful line -0.0 h ago (676812/676812 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-595468-17605 | 595468 | eq13_q15 | 0.0 | last meaningful line 0.0 h ago (684000/684000 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 6.0 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 15.7 | drt_violations best 84312 last 84312 rows 2 | before-window best 329677, window best 84312 | PROGRESS: drt_violations improved 74.4 % in window |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 28.2 | drt_violations best 14980 last 63558 rows 18 | before-window best 15279, window best 14980 | PROGRESS: drt_violations: falling inside the active iteration (63558 -> 53045) |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | lec | 6.0 | LEC last write 0.0 h ago | PROGRESS: LEC still writing |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 7.1 | drt_violations best 0 last 0 rows 2 | PROGRESS: drt_violations reached 0 |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_1_grt | 0.7 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 20.5 | drt_violations best 6824 last 6824 rows 15 | before-window best 18538, window best 6824 | PROGRESS: drt_violations improved 63.2 % in window |  |
| epyc2 | prd-eco_20261124_230804_491597-i1-1072574 | eco_20261124_230804_491597-i1 | 5_2_route | 2.1 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 40.9 | drt_violations best 6858 last 6858 rows 21 | before-window best 7726, window best 6858 | PROGRESS: drt_violations improved 11.2 % in window |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | pregrt_ff_hold | 8.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 25.6 | drt_violations best 2761 last 2761 rows 17 | before-window best 4070, window best 2761 | PROGRESS: drt_violations improved 32.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 21.8 | drt_violations best 8422 last 8422 rows 11 | before-window best 116309, window best 8422 | PROGRESS: drt_violations improved 92.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 20.4 | drt_violations best 21738 last 21738 rows 6 | before-window best 510309, window best 21738 | PROGRESS: drt_violations improved 95.7 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 15.8 | drt_violations best 75027 last 75027 rows 4 | before-window best 412199, window best 75027 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 20.2 | drt_violations best 13313 last 13313 rows 8 | before-window best 457993, window best 13313 | PROGRESS: drt_violations improved 97.1 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 25.8 | drt_violations best 62636 last 62636 rows 11 | before-window best 66691, window best 62636 | PROGRESS: drt_violations improved 6.1 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 21.9 | drt_violations best 52514 last 52514 rows 9 | before-window best 59441, window best 52514 | PROGRESS: drt_violations improved 11.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 2.4 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 17.1 | drt_violations best 17758 last 17758 rows 2 | before-window best 129389, window best 17758 | PROGRESS: drt_violations improved 86.3 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 17.1 | drt_violations best 93397 last 93397 rows 3 | before-window best 478667, window best 93397 | PROGRESS: drt_violations improved 80.5 % in window |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 17.1 | drt_violations best 131388 last 131388 rows 1 | before-window best 131388, window best 131388 | PROGRESS: drt_violations: active iteration at 37787 < best completed total 131388 (in-iter |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 17.1 | drt_violations best 1038 last 1038 rows 4 | before-window best 127432, window best 1038 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 17.1 | drt_violations best 19013 last 19013 rows 2 | before-window best 152943, window best 19013 | PROGRESS: drt_violations improved 87.6 % in window |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 17.1 | drt_violations best 25161 last 25161 rows 2 | before-window best 146375, window best 25161 | PROGRESS: drt_violations improved 82.8 % in window |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 17.1 | drt_violations best 22164 last 22164 rows 2 | before-window best 138449, window best 22164 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 17.1 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 124362 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 17.0 | drt_violations best 52545 last 52545 rows 6 | before-window best 379431, window best 52545 | PROGRESS: drt_violations improved 86.2 % in window |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 17.1 | drt_violations best 14953 last 14953 rows 3 | before-window best 141263, window best 14953 | PROGRESS: drt_violations improved 89.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 17.1 | drt_violations best 9525 last 9525 rows 15 | before-window best 20520, window best 9525 | PROGRESS: drt_violations improved 53.6 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 5 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 13.8 | drt_violations best 1371 last 1577 rows 29 | before-window best 1594, window best 1371 | PROGRESS: drt_violations improved 14.0 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 14.0 | drt_violations best 62620 last 62620 rows 4 | before-window best 474459, window best 62620 | PROGRESS: drt_violations improved 86.8 % in window |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 15.6 | drt_violations best 96187 last 96187 rows 2 | before-window best 367946, window best 96187 | PROGRESS: drt_violations improved 73.9 % in window |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 15.8 | drt_violations best 9816 last 9816 rows 7 | before-window best 406352, window best 9816 | PROGRESS: drt_violations improved 97.6 % in window |  |
