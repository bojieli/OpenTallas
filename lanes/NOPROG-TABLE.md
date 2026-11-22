# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 06:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'CANCEL-NOW': 3, 'GRT-LABEL': 15, 'NO-DATA': 14, 'YOUNG': 235, 'EXCLUDED': 4, 'KEEP': 1, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | tt_setup_repair_grt | 16.7 | repair_Violations best 0 last 0 rows 12 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -634.51 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 15.7 | last meaningful line 14.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 14.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-885482 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1921258 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1921258-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 8.0 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 45.4 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 59.8 | grt rounds 6 overflow 5:9167 -> 10:5212 -> 15:3582 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 3.7 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 39.0 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 43.9 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 33.3 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 33.3 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 43.1 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 32.8 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 7.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 5_1_grt | 2.6 | grt rounds 2 overflow 5:4716 -> 10:2224 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 57.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 40.5 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t45-grt-2592275 | ot-s81sl-leaf--t45-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-1676750 | bk_sel__t2 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2137948 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8529 last 0.8529 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1885856 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 5998 last 5998 rows 11 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r1__t1__cl49d7a23e__pva2370bfd-1863667 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 1701 last 1701 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1896572 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 6.2 | last meaningful line 0.5 h ago (199/205 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4171/4171 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 6.5 | drt_violations best 28 last 30 rows 55 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 8.3 | drt_violations best 4754 last 4754 rows 15 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_1_yosys_canonicalize | 0.5 | last meaningful line 0.1 h ago (353/353 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 1.9 | last meaningful line 0.8 h ago (198/207 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t56-924245 | ot_s81sl_leaf__t56 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | tt_setup_repair | 1.9 | repair_Violations best 90 last 147 rows 72 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-920556 | ot_s81sl_leaf__t66 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (182/182 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (547/547 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 8.5 | drt_violations best 48857 last 48857 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 8.3 | last meaningful line 0.3 h ago (1645/1673 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 8.2 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | postcts_gate_FF | 8.2 | last meaningful line -0.0 h ago (22805/22805 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 3.7 | last meaningful line 0.5 h ago (199/205 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-1830850-11608 | 1830850 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 4.3 | last meaningful line 0.5 h ago (199/205 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1t-2778713 | eco_20261122_144137_2274607-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.3 h ago (201/211 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.8 h ago (198/217 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.8 h ago (196/220 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.7 h ago (126/126 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (134/134 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (133/133 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.7 h ago (130/130 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (125/125 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (143/143 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (143/143 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2767328 | dsdv_slice_lepw_mus_C__t1 | selrange | 1.9 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 1.9 | repair_TNS best 449415 last 449415 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (4919/4919 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | pregrt_ff_hold | 1.9 | repair_Violations best 1463 last 1476 rows 57 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (200/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | pregrt_ff_hold | 1.9 | repair_TNS best 151011 last 151011 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (200/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | pregrt_ff_hold | 1.9 | repair_Violations best 1042 last 1042 rows 119 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (3341/3341 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 1.9 | last meaningful line 0.5 h ago (202/209 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (197/203 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (203/206 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (198/204 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 1.9 | repair_Violations best 10760 last 10808 rows 106 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | pregrt_ff_hold | 1.9 | repair_Violations best 395 last 481 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (201/202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | pregrt_ff_hold | 1.9 | repair_TNS best 7449.9 last 7449.9 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (200/203 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 1.9 | last meaningful line 0.5 h ago (201/206 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | tt_setup_repair | 1.9 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (203/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | tt_setup_repair | 1.9 | repair_Violations best 85 last 98 rows 148 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (4935/4935 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | tt_setup_repair | 1.9 | repair_Viol best 40 last 40 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (6085/6085 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (201/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | postcts_gate_FF | 8.5 | last meaningful line 0.1 h ago (864/864 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_1_grt | 8.5 | last meaningful line 0.7 h ago (213/977 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_1_grt | 8.5 | last meaningful line 0.2 h ago (1062/1079 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 8.5 | last meaningful line 3.0 h ago (220/1507 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 8.5 | repair_TNS best 60061.4 last 60061.4 rows 5 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | postcts_gate_TT | 8.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 8.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-809242-17895 | 809242 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | otc-850004-7309 | 850004 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_2_route | 1.5 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h10-r0-p4--t1--pvcc166a6d-dump-4036646 | col-h10-r0-p4--t1--pvcc166a6d-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-col-h10-r0-p4--t1--pvcc166a6d-grt-4036646 | col-h10-r0-p4--t1--pvcc166a6d-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-1937834 | bk_sel__t2 | 3_4_place_resized | 1.1 | last meaningful line 0.1 h ago (273/273 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3946946 | col_h10_r0_p1__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (285/285 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2435818 | col_h10_r0_p1__t1 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2701296 | col_h10_r0_p4__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2702252 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.7 | overflow best 0.4653 last 0.4653 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-2530162 | col_h9_r0_p3__t1 | 3_4_place_resized | 0.8 | last meaningful line 0.1 h ago (234/234 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-145913 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.4 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | selrange | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2813014 | ot_s81sl_kv_leaf__t1 | synth_odb_v | 0.7 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t2-2226719 | ot_s81sl_leaf__t2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-3941151 | ot_s81sl_leaf__t22 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (298/298 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-2257710 | ot_s81sl_leaf__t33 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t42-3847498 | ot_s81sl_leaf__t42 | 2_4_floorplan_pdn | 0.1 | last meaningful line -0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3944811 | ot_s81sl_leaf__t47 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-2261606 | ot_s81sl_leaf__t55 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (4647/4647 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t62-2347072 | ot_s81sl_leaf__t62 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 2_4_floorplan_pdn | 1.9 | last meaningful line 1.3 h ago (130/130 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (9034/9034 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | postcts_gate_FF | 8.5 | last meaningful line 0.1 h ago (375/375 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | postcts_gate_TT | 8.5 | last meaningful line -0.0 h ago (7574/7574 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_1_grt | 2.7 | last meaningful line 0.1 h ago (569/594 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 8.5 | drt_violations best 91576 last 91576 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | eco-abs-3392298 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (293/293 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2025592-2928 | 2025592 | gen_lint_yosys | 1.1 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | otc-2039494-11393 | 2039494 | gen_lint_yosys | 1.1 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | otc-4062234-19114 | 4062234 | ot_bind_native_c008213169f4e7710f011b5c | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_2_route | 3.4 | drt_violations best 213 last 213 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3891436 | col_h10_r1__t1 | 3_5_place_dp | 0.9 | repair_Violations best 855598 last 855598 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (210/219 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_1_grt | 2.5 | last meaningful line 0.4 h ago (247/347 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 7.7 | drt_violations best 21351 last 21351 rows 2 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_1_floorplan | 1.5 | last meaningful line 1.0 h ago (1424/1424 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 3.8 | repair_TNS best 230637 last 230637 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t4-3684447 | ot_s81sl_kv_leaf__t4 | 2_1_floorplan | 1.0 | repair_Viol best 1304 last 1304 rows 571 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3703022 | ot_s81sl_leaf__t14 | 3_3_place_gp | 1.0 | last meaningful line 0.2 h ago (86/86 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-3703972 | ot_s81sl_leaf__t44 | 3_3_place_gp | 1.0 | overflow best 0.2961 last 0.2961 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t58-3789284 | ot_s81sl_leaf__t58 | 3_3_place_gp | 1.0 | overflow best 0.342 last 0.342 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-558414 | ot_s81sl_leaf__t65 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (173/173 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t70-823669 | ot_s81sl_leaf__t70 | 2_3_floorplan_tapcell | 0.3 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-3908746 | ot_s81sl_leaf__t75 | 3_2_place_iop | 0.9 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3421882 | slice_station__t6 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | eco-abs-3115347 | eco-abs | generate_abstract | 1.2 | last meaningful line 1.0 h ago (656/656 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | otc-3158239-32486 | 3158239 | qwen_compute.t.slw_sc_v1__cl64543eaf__cl4590432d | 1.2 | last meaningful line 0.7 h ago (4/4 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco-i1-3698803 | eco-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (241/242 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 6.6 | drt_violations best 75008 last 75008 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 4.4 | last meaningful line 0.3 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 60299.1 last 60299.1 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 8.4 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N_w-3142338 | hd_lep0N_w | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8746 last 0.8746 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v3-3967683 | kv3_pc_v3 | 3_3_place_gp | 1.9 | overflow best 0.099 last 0.099 rows 47 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v3-3969057 | kv3_pc_v3 | 3_3_place_gp | 1.9 | overflow best 0.0997 last 0.0997 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-3404799 | ot_s81sl_leaf__t17 | 1_1_yosys_canonicalize | 0.0 | last meaningful line -0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3142036 | ot_s81sl_leaf__t25 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.7119 last 0.7119 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3365653 | ot_s81sl_leaf__t25 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (285/285 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t30-3137826 | ot_s81sl_leaf__t30 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t37-3328014 | ot_s81sl_leaf__t37 | 2_1_floorplan | 0.0 | last meaningful line -0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t4-3132073 | ot_s81sl_leaf__t4 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (505/505 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (199/206 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t41-3152229 | ot_s81sl_leaf__t41 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t5-3148460 | ot_s81sl_leaf__t5 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (584/584 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3324313 | ot_s81sl_leaf__t53 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl501e5681-3130636 | ot_s81sl_leaf__t54 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3149759 | ot_s81sl_leaf__t54 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (559/559 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (2999/2999 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | pregrt_ff_hold | 1.9 | repair_Violations best 8004 last 8013 rows 125 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | postcts_gate_TT | 8.4 | last meaningful line -0.0 h ago (89725/89725 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | postcts_gate_TT | 8.4 | last meaningful line 0.0 h ago (721/721 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | postcts_gate_FF | 8.8 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t18-3326899 | slice_station__t18 | 2_1_floorplan | 0.0 | last meaningful line -0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-3325426 | slice_station__t29 | 2_4_floorplan_pdn | 0.0 | last meaningful line -0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | postcts_gate_TT | 8.4 | last meaningful line 0.2 h ago (855/855 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | postcts_gate_TT | 8.4 | last meaningful line 0.1 h ago (855/855 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 8.4 | drt_violations best 107 last 126 rows 27 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 4.3 | drt_violations best 83927 last 83927 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | prd-fin-3578697 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_3383117_ff_38177 | so_3383117_ff_38177 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_3383117_tt_38177 | so_3383117_tt_38177 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (3123/3123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3818192 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.867 last 0.867 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3477317 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.7 | overflow best 0.3528 last 0.366 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3660762 | col_h10_r1__t1 | 3_4_place_resized | 0.6 | repair_Remaining best 79534 last 79534 rows 23 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | 5_1_grt | 3.2 | last meaningful line 0.8 h ago (203/208 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 3.1 | last meaningful line 0.8 h ago (203/208 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 31666.7 last 31666.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 71892 last 71892 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-3916912 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.6819 last 0.6819 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-3945629 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6626 last 0.6626 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 57376.2 last 57376.2 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 55205.4 last 55205.4 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 7.1 | drt_violations best 86218 last 86218 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.5 h ago (198/210 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-581356 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 277 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (6657/6657 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.3 h ago (126/126 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | selrange | 1.9 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | selrange | 1.9 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.3 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 2.0 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (402/402 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 2.0 | last meaningful line 0.3 h ago (28/28 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 1.9 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (4412/4412 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-eng__t1-3282689 | eng__t1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_5_place_dp | 2.0 | last meaningful line 1.3 h ago (41/41 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 7.8 | drt_violations best 28005 last 28005 rows 3 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 0.5 | last meaningful line 0.3 h ago (7084/7084 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 3_4_place_resized | 2.0 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 1.9 | repair_TNS best 293138 last 293138 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 1.9 | repair_TNS best 332496 last 332496 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t46-3487755 | ot_s81sl_leaf__t46 | 3_3_place_gp | 0.7 | overflow best 0.598 last 0.598 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t61-353186 | ot_s81sl_leaf__t61 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t67-376168 | ot_s81sl_leaf__t67 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t71-3526655 | ot_s81sl_leaf__t71 | 3_3_place_gp | 0.6 | overflow best 0.4904 last 0.503 rows 30 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | 5_1_grt | 2.7 | last meaningful line 0.1 h ago (1192/1195 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 3_3_place_gp | 1.9 | overflow best 0.3073 last 0.3073 rows 39 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 9.1 | drt_violations best 70451 last 70451 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_1_grt | 8.7 | last meaningful line 0.1 h ago (1228/1234 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | otc-2047425-5864 | 2047425 | gen_lint_yosys | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-3428097-1823 | 3428097 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-543307-27678 | 543307 | ot_s81_sstn_payload536__orig | 0.1 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 4.9 | drt_violations best 58 last 58 rows 12 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel2 | ap-ageom-kw-col-h10-r1--t1--cl95b37463--pv6a7ae122-grt-2812217 | col-h10-r1--t1--cl95b37463--pv6a7ae122-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | ap-ageom-kw-col-h10-r1--t1--cl95b37463--pva3a8bfd1-grt-2793172 | col-h10-r1--t1--cl95b37463--pva3a8bfd1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-541108 | col_h10_r0_p4__t1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-1953647 | col_h10_r2__t1 | 3_4_place_resized | 0.4 | repair_Remaining best 14292 last 14292 rows 56 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-2844003 | col_h9_r0_p2__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (193/193 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.1 h ago (196/209 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-558541 | col_h9_r0_p2__t1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (193/193 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-581574 | col_h9_r0_p2__t1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-685457 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.8 | overflow best 0.3727 last 0.3727 rows 29 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-595613 | col_h9_r0_p4__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-2511805 | col_h9_r0_p6__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2637008 | coll_ftm | 5_2_route | 1.7 | last meaningful line 0.1 h ago (236/237 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_kv512_C__t1-524813 | dsdv_slice_kv512_C__t1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.9963 last 0.9963 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.3 | last meaningful line 0.1 h ago (186/199 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 3_1_place_gp_skip_io | 2.6 | overflow best 0.3364 last 0.3364 rows 36 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-gunit__t1-533357 | gunit__t1 | 3_5_place_dp | 0.9 | last meaningful line 0.3 h ago (40/40 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N_w-880189 | hd_lep0N_w | 4_2_tapbal_grt | 0.7 | last meaningful line 0.3 h ago (46/57 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2374283 | hd_turn_a | 5_1_grt | 0.2 | repair_Remaining best 5899 last 5899 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-921223 | hd_turn_a | 5_2_route | 0.7 | drt_violations best 5492 last 5492 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-304550 | kv3_io_ft | 5_2_route | 1.0 | last meaningful line 0.0 h ago (215/216 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t1-3886007 | ot_s81sl_kv_leaf__t1 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (339/339 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (210/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.7 | repair_TNS best 306043 last 306043 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-2405593 | ot_s81sl_leaf__t1 | 3_1_place_gp_skip_io | 0.2 | last meaningful line -0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1642535 | ot_s81sl_leaf__t28 | 3_3_place_gp | 0.6 | overflow best 0.5004 last 0.5055 rows 10 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t3-2358697 | ot_s81sl_leaf__t3 | 3_1_place_gp_skip_io | 0.2 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-544494 | ot_s81sl_leaf__t43 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t52-643025 | ot_s81sl_leaf__t52 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (233/233 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t57-2441533 | ot_s81sl_leaf__t57 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8571 last 0.8571 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t60-1673352 | ot_s81sl_leaf__t60 | 3_3_place_gp | 0.6 | overflow best 0.466 last 0.466 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t7-637595 | ot_s81sl_leaf__t7 | 3_3_place_gp | 0.8 | overflow best 0.5721 last 0.5748 rows 13 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t8-508307 | ot_s81sl_leaf__t8 | 3_3_place_gp | 0.9 | overflow best 0.5814 last 0.5814 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-1723438 | ot_s81sl_leaf__t9 | 3_3_place_gp | 0.6 | overflow best 0.5793 last 0.5796 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-seqhost__t1-430619 | seqhost__t1 | 3_3_place_gp | 0.9 | overflow best 0.8716 last 0.8728 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3114107 | slice_station__t12 | 6_report | 1.5 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-247573 | slice_station__t51 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i1t-261967 | eco_20261122_054330_1688646-i1t | 5_2_route | 1.0 | drt_violations best 4216 last 4216 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | so_2775270_ff_70753 | so_2775270_ff_70753 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_2775270_tt_70753 | so_2775270_tt_70753 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-4062551-16572 | 4062551 | ot_bind_native_ace0ac3bb6e2b00ea5fa48a9 | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-1332959-26355 | 1332959 | asbuilt.yosys | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-1367868-22957 | 1367868 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-1410918-25294 | 1410918 | - | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 47.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 6.9 | drt_violations best 28 last 28 rows 14 | before-window best 144464, window best 28 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 52.0 | last meaningful line 2.4 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_1_grt | 2.0 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 8.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 8.5 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 8.5 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 8.5 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_1_grt | 8.5 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 18.4 | drt_violations best 49344 last 49344 rows 15 | before-window best 53583, window best 49344 | PROGRESS: drt_violations improved 7.9 % in window |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 4.4 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 17.9 | drt_violations best 597 last 1350 rows 31 | before-window best 1045, window best 597 | PROGRESS: drt_violations improved 42.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 17.7 | drt_violations best 45146 last 45146 rows 14 | before-window best 50163, window best 45146 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | tt_setup_repair_grt | 9.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 7.3 | drt_violations best 8841 last 8841 rows 10 | before-window best 85188, window best 8841 | PROGRESS: drt_violations improved 89.6 % in window |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 7.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 9.4 | drt_violations best 11187 last 11187 rows 10 | before-window best 152197, window best 11187 | PROGRESS: drt_violations improved 92.6 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 12.8 | drt_violations best 23 last 23 rows 53 | before-window best 170434, window best 23 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
