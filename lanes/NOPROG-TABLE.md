# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 02:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 24, 'YOUNG': 64, 'NO-DATA': 2, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 41}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | tt_setup_repair_grt | 56.3 | repair_Violations best 0 last 0 rows 20 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -666.51 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 11.5 | last meaningful line 9.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-788002 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | generate_abstract | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-794963 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_5_place_dp | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 41.4 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49497 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_su_c-3368948 | sle_su_c | 5_1_grt | 4.5 | grt rounds 2 overflow 5:29978 -> 10:8786 | GRT-LABEL: DESIGN-FAIL: overflow 8786 at round 10 > 1000 |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 55.8 | grt rounds 6 overflow 5:9444 -> 10:5570 -> 15:3582 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3919840 | sle_stm_v1 | 5_1_grt | 4.3 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:62130 -> 10:209 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 34.7 | grt rounds 3 overflow 5:63793 -> 10:65943 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 39.7 | grt rounds 3 overflow 5:60207 -> 10:62947 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 29.1 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 29.1 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 38.8 | grt rounds 4 overflow 5:82307 -> 10:49854 -> 15:42880 -> 20:44324 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 26.5 | grt rounds 4 overflow 5:111429 -> 10:74915 -> 15:54463 -> 20:61561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 34.8 | grt rounds 4 overflow 5:95257 -> 10:71565 -> 15:51030 -> 20:56703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 28.6 | grt rounds 4 overflow 5:105414 -> 10:69762 -> 15:50712 -> 20:58448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 12.4 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | clkgrt-base-1763391 | clkgrt-base | 5_1_grt | 1.7 | grt rounds 2 overflow 5:60327 -> 10:46634 | GRT-LABEL: DESIGN-FAIL: overflow 46634 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:87414 -> 10:72 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:40465 -> 10:379 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 30.2 | grt rounds 5 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 -> 25:22767 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-1503152 | col_h10_r1__t1 | 5_1_grt | 3.3 | grt rounds 8 overflow 15:407 -> 20:339 -> 25:206 -> 30:94 -> 35:43 -> 40:71 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 43 -> 71 |  |
| epyc9 | dpkit-kv3_hroot-3564680 | kv3_hroot | 5_1_grt | 1.5 | grt rounds 2 overflow 5:4295 -> 10:1894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 43.0 | grt rounds 5 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 53.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 36.5 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11809 -> 20:10993 -> 25:8231 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-3492603 | cbf_q00 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q11-437536 | cbf_q11 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | 5_2_route | 4.2 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 2.5 | drt_violations best 55 last 55 rows 17 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-1727564 | hd_lep0N_w | 4_2_tapbal_grt | 2.4 | last meaningful line 2.0 h ago (46/113 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 4.3 | drt_violations best 86318 last 86318 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-3608154 | sle_fe_v1 | 3_5_place_dp | 1.1 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_1_grt | 4.5 | last meaningful line 0.1 h ago (796/821 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (189/195 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-612802-27651 | 612802 | sta_r01 | 0.3 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-616218-14777 | 616218 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 2.9 | drt_violations best 144464 last 144464 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-cbx-q10--cl89936551-grt-186697 | cbx-q10--cl89936551-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3975776 | cbn_q11 | 3_3_place_gp | 0.4 | overflow best 0.6371 last 0.6371 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | 5_2_route | 4.2 | drt_violations best 12904 last 12904 rows 2 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor-579275 | kv3_io_cor | 5_2_route | 3.7 | drt_violations best 52695 last 52695 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_1_grt | 4.3 | repair_Remaining best 370633 last 370633 rows 93 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | 5_2_route | 4.3 | last meaningful line 0.0 h ago (259/260 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_1_grt | 4.2 | last meaningful line 0.4 h ago (263/869 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | clkgrt-base-2211516 | clkgrt-base | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 5_2_route | 13.0 | drt_violations best 100347 last 100347 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | generate_abstract | 13.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | generate_abstract | 13.3 | last meaningful line 0.0 h ago (295/295 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cl622f65d2-3184271 | cbn_q00 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 3.5 | last meaningful line 0.3 h ago (212/218 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | tt_setup_repair_grt | 14.4 | last meaningful line 2.3 h ago (18/18 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_2_route | 5.8 | drt_violations best 1432 last 1432 rows 24 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7152/7153 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-1456285 | kv3_hub_Wo | 3_5_place_dp | 2.1 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco-i1-2157331 | eco-i1 | 5_2_route | 1.3 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_1_grt | 2.6 | repair_Remaining best 18727 last 18727 rows 160 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 41 last 41 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-3141540 | hd_ctl | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N-734152 | hd_lep0N | 3_1_place_gp_skip_io | 0.5 | overflow best 0.2202 last 0.2202 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-hd_lep0N_w-724368 | hd_lep0N_w | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_1_grt | 4.4 | last meaningful line 1.0 h ago (221/1043 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | postcts_gate_TT | 5.1 | last meaningful line -0.0 h ago (63341/63341 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 4.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-1083044-31233 | 1083044 | gold.ys | 0.3 | last meaningful line 0.2 h ago (52269/52269 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4120075 | eco-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (279/279 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco2-i1-1371951 | eco2-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 3.3 | drt_violations best 20291 last 20291 rows 2 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | prd-eco_r7k6-i1-4060872 | eco_r7k6-i1 | 5_2_route | 1.1 | drt_violations best 6839 last 6839 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-1568542 | cbf_q00 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbf_q01-1926377 | cbf_q01 | 3_3_place_gp | 0.6 | overflow best 0.6739 last 0.6739 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbf_q01_s2-2255881 | cbf_q01_s2 | 3_3_place_gp | 0.5 | overflow best 0.5333 last 0.5333 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbf_q11-1769643 | cbf_q11 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2769684 | cbn_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6754 last 6754 rows 89 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1292926 | cbn_q01 | 3_4_place_resized | 1.1 | last meaningful line 0.1 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_1_grt | 3.1 | last meaningful line 0.1 h ago (1472/1502 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-hd_turn_a-2217018 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4923 last 4923 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | tt_setup_measure_grt | 3.8 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-1537459 | kv3_hub_Ei | 2_4_floorplan_pdn | 0.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc__cl5a95b461-2425782 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (61/61 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_1_grt | 5.1 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1731949-14727 | 1731949 | 3_4_place_resized | 0.8 | repair_Remaining best 256831 last 256831 rows 38 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 5.4 | drt_violations best 16712 last 16712 rows 5 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 8.8 | drt_violations best 170434 last 170434 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-802974 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_host_n-2200297 | hd_host_n | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (849/849 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | tt_setup_repair_grt | 48.1 | repair_Remaining best 34959 last 34959 rows 114 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-831540 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-3319414-6006 | 3319414 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-1061331-5517 | 1061331 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 43.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_1_grt | 4.2 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | pregrt_ff_hold | 4.2 | repair_Violations best 0 last 0 rows 9 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 6.3 | last meaningful line 0.0 h ago (871689/871689 lines) | PROGRESS: log still growing |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 6.1 | last meaningful line 0.0 h ago (1159155/1159155 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 47.7 | last meaningful line 0.2 h ago (1556/1556 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | pregrt_ff_hold | 4.3 | repair_Violations best 0 last 0 rows 21 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_1_grt | 4.2 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_1_grt | 4.2 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 14.1 | drt_violations best 52295 last 52295 rows 13 | before-window best 60771, window best 52295 | PROGRESS: drt_violations improved 13.9 % in window |  |
| epyc8 | dpkit-slice_station__t37-3216548 | slice_station__t37 | tt_setup_repair_grt | 4.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 13.9 | drt_violations best 939 last 939 rows 24 | before-window best 5832, window best 939 | PROGRESS: drt_violations improved 83.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 13.7 | drt_violations best 46518 last 46518 rows 13 | before-window best 60545, window best 46518 | PROGRESS: drt_violations improved 23.2 % in window |  |
| epyc8 | prd-eco-i1t-3166843 | eco-i1t | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-glue-344102 | glue | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | 5_1_grt | 3.8 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_io_ft-794585 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
