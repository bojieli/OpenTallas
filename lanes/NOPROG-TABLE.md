# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 03:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 15, 'NO-DATA': 36, 'YOUNG': 138, 'EXCLUDED': 3, 'PROGRESS': 35}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 36.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 7.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 19.9 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 5_1_grt | 19.9 | grt rounds 2 overflow 5:13717 -> 10:12993 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1483343 | col_h9_r0_p4__t1 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:63165 -> 10:2796 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 11.5 | grt rounds 2 overflow 5:46621 -> 10:43275 | GRT-LABEL: DESIGN-FAIL: overflow 43275 at round 10 > 1000 |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | 5_1_grt | 8.1 | grt rounds 2 overflow 5:5704 -> 10:3958 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 5_1_grt | 4.9 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t11-3893305 | ot_s81sl_leaf__t11 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 10.1 | grt rounds 2 overflow 5:1586 -> 10:260 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | 5_1_grt | 2.7 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 5_1_grt | 7.3 | grt rounds 1 overflow 5:26610 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 22.7 | grt rounds 6 overflow 5:805 -> 10:203 -> 15:132 -> 20:64 -> 25:77 -> 30:61 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 22.7 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 9.3 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 18.9 | grt rounds 3 overflow 5:88799 -> 10:83085 -> 15:86608 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-cbx-q10--cl89936551-h-grt-317839 | cbx-q10--cl89936551-h-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-2787287 | bk_sel__t2 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-388109 | coll_core | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (588/588 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | pregrt_ff_hold | 2.5 | repair_TNS best 1.6027e+06 last 1.6027e+06 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | pregrt_ff_hold | 2.5 | repair_TNS best 1.62065e+06 last 1.62065e+06 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | pregrt_ff_hold | 2.4 | repair_TNS best 1.62065e+06 last 1.62065e+06 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | pregrt_ff_hold | 2.4 | repair_TNS best 1.6027e+06 last 1.6027e+06 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-hd_st_n4-158454 | hd_st_n4 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3877061 | hd_st_n4 | 5_2_route | 3.1 | drt_violations best 20355 last 20355 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 5_2_route | 2.5 | last meaningful line 0.1 h ago (248/249 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3e-3821788 | kv3_pv_v3e | 3_5_place_dp | 3.1 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 3_1_place_gp_skip_io | 21.2 | overflow best 0.949 last 0.949 rows 33 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3642617 | ot_s81sl_leaf__t43 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3893/3893 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t73-3464910 | ot_s81sl_leaf__t73 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4128/4128 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_1_grt | 3.6 | repair_Remaining best 171512 last 171512 rows 238 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_2_route | 11.6 | drt_violations best 21826 last 21826 rows 3 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t12-4037092 | slice_station__t12 | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (387/411 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | laughing_keller | laughing_keller | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3082835-5546 | 3082835 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-3874152-20216 | 3874152 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-4116113-30783 | 4116113 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-418992-3071 | 418992 | build_bcast_mut_srx2_hc | 0.1 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-418993-13434 | 418993 | build_bcast_mut_srx2_hc | 0.1 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-418995-17951 | 418995 | build_bcast_mut_srx2_hc | 0.1 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-98077-22969 | 98077 | build_bcast_bcast_srx0 | 0.3 | last meaningful line 0.1 h ago (622/622 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 6.6 | drt_violations best 28584 last 28584 rows 3 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc10 | prd-fin-3218186 | fin | 6_1_fill | 0.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | so_223643_ff_4634 | so_223643_ff_4634 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (627/627 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_223643_tt_4634 | so_223643_tt_4634 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (627/627 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_3632401_ff_5796 | so_3632401_ff_5796 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (1034/1034 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | so_3632401_tt_5796 | so_3632401_tt_5796 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (1034/1034 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 9.3 | last meaningful line 0.5 h ago (214/219 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 144649 last 144649 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2056070 | col_h10_r1__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 108409 last 108409 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 5_2_route | 9.0 | drt_violations best 85064 last 85064 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 8.6 | last meaningful line 3.5 h ago (207/214 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 8.2 | last meaningful line 0.0 h ago (1498/1498 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 4.9 | drt_violations best 87459 last 87459 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 3.5 | last meaningful line 0.3 h ago (256/257 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_4_place_resized | 4.9 | last meaningful line 0.2 h ago (779/779 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_4_place_resized | 5.4 | last meaningful line 0.5 h ago (740/740 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-3941275 | ot_s81sl_leaf__t1 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (159/159 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 9.3 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-1430945 | ot_s81sl_leaf__t36 | 5_1_grt | 2.5 | last meaningful line 0.5 h ago (205/212 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-3842605 | ot_s81sl_leaf__t7 | 5_1_grt | 3.5 | last meaningful line 1.0 h ago (204/213 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | postcts_gate_FF | 11.5 | last meaningful line 0.2 h ago (833/833 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | postcts_gate_FF | 11.5 | last meaningful line 0.2 h ago (814/814 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 11.5 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_1_grt | 9.1 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 8.1 | drt_violations best 71122 last 71122 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 8.5 | drt_violations best 62246 last 62246 rows 4 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 4.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2436152-11731 | 2436152 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-2438095-32195 | 2438095 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 4.3 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_2_route | 4.5 | drt_violations best 735 last 735 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 2.1 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_1_grt | 1.5 | last meaningful line 0.7 h ago (239/1422 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 1.8 | last meaningful line 0.0 h ago (106/106 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-836163 | col_h9_r0_p5__t1 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 155482 last 155482 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (3363/3363 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | 4_1_cts | 4.6 | last meaningful line 0.1 h ago (6488/6488 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | 4_2_tapbal_grt | 1.7 | last meaningful line 1.3 h ago (46/132 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-1251911 | hd_st_n4 | 5_2_route | 3.1 | drt_violations best 18611 last 18611 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-2829569 | hd_st_n4 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (239/240 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-1064320 | kv3_pv_v1 | 3_4_place_resized | 3.2 | last meaningful line 0.3 h ago (640/640 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 3_4_place_resized | 3.6 | last meaningful line 0.2 h ago (712/712 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 13.3 | drt_violations best 135433 last 135433 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_2_route | 14.2 | drt_violations best 144858 last 144858 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | generate_abstract | 14.3 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 14.2 | drt_violations best 409476 last 409476 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 12.8 | drt_violations best 72487 last 72487 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 9.2 | drt_violations best 76194 last 76194 rows 4 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | otc-1330851-9544 | 1330851 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2287405-27505 | 2287405 | signoff | 2.4 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | otc-254531-30458 | 254531 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 4.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2-3585488 | eco_20261122_215654_330309-i2 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (249/249 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i2-2223567 | eco_20261122_220050_168828-i2 | 5_2_route | 2.5 | drt_violations best 4066 last 4066 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 3.4 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | so_159924_ff_71985 | so_159924_ff_71985 | signoff_20261123_103406_1530301 | 0.9 |  | NO-DATA: empty log |  |
| epyc8 | ap-ageom-kw-kv3-hgi-v2--cle0015330-grt-2533254 | kv3-hgi-v2--cle0015330-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-hub-Wo-grt-2718820 | kv3-hub-Wo-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbf_q00__cl1b5a6458-757482 | cbf_q00 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1669 last 0.1669 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-cbf_q11-815128 | cbf_q11 | 3_3_place_gp | 0.8 | overflow best 0.5471 last 0.5471 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 6_report | 19.4 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1919292 | col_h9_r0_p2__t1 | 5_1_grt | 3.8 | last meaningful line 0.5 h ago (1316/2432 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 9.4 | drt_violations best 136200 last 136200 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_2_route | 9.3 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2205610 | dsdv_slice_c1x_C__t1 | 3_1_place_gp_skip_io | 3.7 | overflow best 0.5487 last 0.5487 rows 32 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | 3_1_place_gp_skip_io | 3.9 | overflow best 0.6374 last 0.6374 rows 31 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 3.8 | last meaningful line 0.5 h ago (210/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 9.3 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | 5_2_route | 11.8 | drt_violations best 82647 last 82647 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v5-2058350 | kv3_hgi_v5 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (485/485 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v8-3855514 | kv3_hgi_v8 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 11.8 | drt_violations best 91531 last 91531 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | 5_3_fillcell | 6.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2054469 | kv3_pc_v1 | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (5040/5040 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5416/5416 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (8752/8752 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_5_place_dp | 6.2 | last meaningful line 0.3 h ago (58/58 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | 5_1_grt | 4.2 | last meaningful line 1.2 h ago (233/950 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_1_grt | 3.8 | last meaningful line 0.1 h ago (728/741 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | otc-2782238-22763 | 2782238 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-slw_hc3_cld86_mainlec | relec1122-ml-slw_hc3_cld86_mainlec | - | 0.9 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-kv3-pv-dump-1502345 | kv3-pv-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-kv3-pv-grt-1502345 | kv3-pv-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_2_route | 5.0 | drt_violations best 51230 last 51230 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 7.4 | last meaningful line 1.2 h ago (267/1519 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 9.3 | last meaningful line 0.5 h ago (165/165 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 4.6 | repair_TNS best 236158 last 236158 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 3.4 | repair_TNS best 309828 last 309828 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 3_5_place_dp | 4.6 | last meaningful line 0.5 h ago (57/57 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 3_4_place_resized | 4.5 | last meaningful line 0.3 h ago (714/714 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_3_place_gp | 3.4 | overflow best 0.2839 last 0.2839 rows 28 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 4.8 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.3 | repair_Remaining best 354110 last 354110 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t33-1533302 | ot_s81sl_leaf__t33 | 5_1_grt | 2.6 | last meaningful line 0.1 h ago (192/205 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t68-124972 | ot_s81sl_leaf__t68 | pregrt_ff_hold | 0.9 | repair_TNS best 102058 last 102058 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | pregrt_ff_hold | 6.5 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_1_grt | 7.2 | last meaningful line 0.3 h ago (1872/1894 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | lrc-qgrt-3979888 | lrc-qgrt | qgrt | 3.7 | last meaningful line 3.5 h ago (44/59 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 5.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1661483-30301 | 1661483 | - | 5.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2062537-15369 | 2062537 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-2908826-5237 | 2908826 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-2909264-658 | 2909264 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3879808-1968 | 3879808 | gate.ys | 1.2 | last meaningful line 1.0 h ago (22052/22052 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_2_route | 3.3 | last meaningful line 0.4 h ago (296/297 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3t-3335435 | eco_20261122_180231_342380-i3t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-residual-i4r-2209462 | residual-i4r | 5_2_route | 2.3 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | pvr7-pv8-hifo-3975570 | pvr7-pv8-hifo | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-slw_hc3_clccfc_mainlec | relec1122-ml-slw_hc3_clccfc_mainlec | - | 1.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3408616 | col_h10_r0_p1__t1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (243/243 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 9.3 | drt_violations best 52562 last 52562 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 23.0 | last meaningful line 1.0 h ago (294/295 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 9.3 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 6.9 | last meaningful line 0.1 h ago (147/147 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 7.7 | last meaningful line 5.5 h ago (48/58 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_3_place_gp | 6.3 | overflow best 0.0999 last 0.0999 rows 43 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_1_grt | 6.9 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 9.3 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_1_grt | 8.1 | last meaningful line 0.5 h ago (136/136 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_1_grt | 7.6 | last meaningful line 0.4 h ago (250/879 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 9.4 | drt_violations best 344103 last 344103 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | otc-3494356-28288 | 3494356 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3555606-14599 | 3555606 | orfs_synth | 0.3 | last meaningful line 0.3 h ago (4254/4254 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-589898-30912 | 589898 | - | 5.5 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 5.5 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 5.3 |  | NO-DATA: no log found |  |
| intel1 | prd-count-p1_tc-380897 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 6.7 | last meaningful line 0.5 h ago (295/296 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 4.9 | drt_violations best 7877 last 7877 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 14.7 | drt_violations best 1406 last 1406 rows 7 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 186769 last 186769 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1679354 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_1_floorplan | 1.9 | last meaningful line 1.5 h ago (1424/1424 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 4_1_cts | 3.7 | last meaningful line 0.1 h ago (9413/9413 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 6_report | 16.8 | last meaningful line 0.0 h ago (1077/1077 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slw_su_l1__clcc9d0155-1330098 | slw_su_l1 | 3_3_place_gp | 0.1 | overflow best 0.1353 last 0.1353 rows 44 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | fableunc-ctl-1574286 | fableunc-ctl | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | fableunc-ctl-1575206 | fableunc-ctl | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | gracious_jang | gracious_jang | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | magical_kapitsa | magical_kapitsa | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | sleepy_ganguly | sleepy_ganguly | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-450336-16169 | 450336 | asbuilt.yosys | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-2335892-7062 | 2335892 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-1507547-12460 | 1507547 | - | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_st_n4-3814785 | hd_st_n4 | 5_2_route | 3.1 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc10 | dpkit-hd_turn_a-4010477 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 72.7 | last meaningful line 0.2 h ago (1618/1618 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 11.5 | last meaningful line 5.8 h ago (208/216 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 9.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | tt_setup_repair | 5.2 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_1_grt | 9.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 11.5 | drt_violations best 12997 last 12997 rows 8 | before-window best 154966, window best 12997 | PROGRESS: drt_violations improved 91.6 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 19.9 | drt_violations best 55 last 63 rows 26 | before-window best 4181, window best 55 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 23.3 | drt_violations best 9545 last 9545 rows 16 | before-window best 14242, window best 9545 | PROGRESS: drt_violations improved 33.0 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 10.8 | drt_violations best 15880 last 15880 rows 14 | before-window best 61476, window best 15880 | PROGRESS: drt_violations improved 74.2 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 6.7 | last meaningful line 0.3 h ago (12263/12263 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | 5_2_route | 4.6 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 15.3 | drt_violations best 20 last 71 rows 30 | before-window best 22, window best 20 | PROGRESS: drt_violations improved 9.1 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 22.7 | drt_violations best 24731 last 24731 rows 3 | before-window best 195281, window best 24731 | PROGRESS: drt_violations improved 87.3 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 22.7 | drt_violations best 40912 last 40912 rows 4 | before-window best 210671, window best 40912 | PROGRESS: drt_violations improved 80.6 % in window |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 21.2 | last meaningful line 1.0 h ago (291/292 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t15-2887177 | ot_s81sl_leaf__t15 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 30.2 | drt_violations best 1027 last 1512 rows 27 | before-window best 1120, window best 1027 | PROGRESS: drt_violations improved 8.3 % in window |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_io_ft-673287 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 16.7 | drt_violations best 88165 last 88165 rows 2 | before-window best 327883, window best 88165 | PROGRESS: drt_violations improved 73.1 % in window |  |
