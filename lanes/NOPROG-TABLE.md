# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 06:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-STUCK': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 15, 'NO-DATA': 8, 'YOUNG': 234, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 22}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | tt_setup_repair_grt | 16.2 | last meaningful line 0.0 h ago (27/27 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -562.93 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 15.2 | last meaningful line 13.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 13.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 46.5 | grt rounds 6 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 -> 30:9582 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:7397 -> 25:22417 -> 30:9582; best 958 | REPORT-ONLY: lane-own kit (fable-fix-s81-leaf-2140 |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-885482 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_1_grt | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 7.5 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 44.9 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 59.3 | grt rounds 6 overflow 5:9167 -> 10:5212 -> 15:3582 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 3.2 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 38.5 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 43.4 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 32.8 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 32.8 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 42.6 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 32.3 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 7.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 7.0 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 5_1_grt | 2.1 | grt rounds 2 overflow 5:4716 -> 10:2224 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 57.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 40.0 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8231 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv36da905c-grt-1576546 | col-h9-r1--t1--cl49d7a23e--pv36da905c-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-1676750 | bk_sel__t2 | 1_synth | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | pregrt_ff_hold | 2.4 | repair_Violations best 15375 last 15375 rows 13 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1032630 | col_h10_r1__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-1525191 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (208/208 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-1495887 | col_h9_r2__t1 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 5.7 | last meaningful line 0.0 h ago (199/201 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3628903 | coll_core | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | 6_report | 5.6 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 6.0 | drt_violations best 28 last 30 rows 55 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 7.8 | drt_violations best 4948 last 4948 rows 14 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 1.4 | last meaningful line 0.3 h ago (198/204 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t45-823513 | ot_s81sl_leaf__t45 | 3_3_place_gp | 0.5 | last meaningful line 0.2 h ago (54/54 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t56-924245 | ot_s81sl_leaf__t56 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4183/4183 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-920556 | ot_s81sl_leaf__t66 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (382/382 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | pregrt_ff_hold | 1.4 | repair_Violations best 1822 last 1877 rows 63 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | tt_setup_measure_grt | 7.6 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-591522 | slice_station__t37 | 3_3_place_gp | 0.6 | overflow best 0.3418 last 0.3418 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 8.0 | drt_violations best 48857 last 48857 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | postcts_gate_FF | 7.7 | last meaningful line 0.1 h ago (1845/1845 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | postcts_gate_FF | 7.7 | last meaningful line 0.1 h ago (485/485 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (199/201 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 3.8 | last meaningful line 0.0 h ago (199/201 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 6.4 | drt_violations best 4420 last 4420 rows 11 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-dsdv-slice-lepw-mus-LP--t2-grt-1655883 | dsdv-slice-lepw-mus-LP--t2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (198/210 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (198/207 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (196/210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (125/125 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (125/125 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2767328 | dsdv_slice_lepw_mus_C__t1 | selrange | 1.4 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-gunit__t1-2764618 | gunit__t1 | 5_1_grt | 1.4 | last meaningful line 1.0 h ago (197/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | hold_gate | 1.5 | last meaningful line -0.0 h ago (4/4 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | tt_setup_repair | 1.4 | last meaningful line 0.0 h ago (418/418 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3468/3468 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | pregrt_ff_hold | 1.4 | repair_TNS best 123200 last 123200 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | pregrt_ff_hold | 1.4 | repair_TNS best 76020 last 76020 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (3582/3582 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (202/204 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (3429/3429 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | pregrt_ff_hold | 1.4 | repair_Violations best 5964 last 5970 rows 105 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | pregrt_ff_hold | 1.4 | repair_Violations best 16237 last 16282 rows 78 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | pregrt_ff_hold | 1.4 | repair_TNS best 202591 last 202591 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | pregrt_ff_hold | 1.4 | repair_Violations best 1920 last 1920 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 1.4 | last meaningful line 0.1 h ago (201/203 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (3776/3777 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | tt_setup_repair | 1.4 | last meaningful line 0.0 h ago (325/325 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (3706/3706 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6030/6030 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 1.4 | last meaningful line 0.1 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | postcts_gate_TT | 8.0 | last meaningful line 0.1 h ago (1863/1863 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 8.0 | last meaningful line 2.3 h ago (221/1119 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_1_grt | 8.0 | last meaningful line 0.2 h ago (213/929 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_1_grt | 8.0 | last meaningful line 0.7 h ago (213/980 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 8.0 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 8.0 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 5_1_grt | 1.8 | last meaningful line 0.2 h ago (282/649 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 8.0 | repair_TNS best 308.468 last 308.468 rows 5 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 8.0 | repair_TNS best 19.506 last 19.506 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 8.0 | last meaningful line 1.8 h ago (220/959 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 8.0 | last meaningful line 2.5 h ago (226/1208 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_1_grt | 8.0 | last meaningful line 0.2 h ago (219/936 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_1_grt | 8.0 | last meaningful line 0.1 h ago (1233/1239 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | postcts_gate_FF | 8.0 | last meaningful line 0.1 h ago (1503/1503 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-3539997-3077 | 3539997 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | otc-3717177-15267 | 3717177 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | otc-3805345-19722 | 3805345 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | otc-651200-7971 | 651200 | s81.t.col_h9_r2__t1__clce45cab5__pv7a260fc0 | 0.5 | last meaningful line 0.2 h ago (4/4 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-809242-17895 | 809242 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-850004-7309 | 850004 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-1937834 | bk_sel__t2 | 3_3_place_gp | 0.6 | overflow best 0.2169 last 0.24 rows 15 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2435818 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7327 last 0.7327 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2067739 | col_h10_r0_p4__t1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (173/173 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2370233 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.4 | overflow best 0.402 last 0.402 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2521358 | col_h10_r0_p4__t1 | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2701296 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7377 last 0.7768 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2702252 | col_h9_r0_p3__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-2530162 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6923 last 0.6923 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-2542398 | col_h9_r0_p4__t1 | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-145913 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 1.9 | repair_Remaining best 276178 last 276178 rows 95 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-1741867 | dsdv_slice_lepe_mu_LP__t2 | 3_4_place_resized | 0.7 | repair_Remaining best 28475 last 28475 rows 181 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-iqf__t1-1849629 | iqf__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-2813014 | ot_s81sl_kv_leaf__t1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (723/723 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t2-2226719 | ot_s81sl_leaf__t2 | 3_3_place_gp | 0.5 | last meaningful line 0.1 h ago (572/572 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-2257710 | ot_s81sl_leaf__t33 | 3_3_place_gp | 0.5 | overflow best 0.3749 last 0.3835 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-2261606 | ot_s81sl_leaf__t55 | 3_3_place_gp | 0.5 | last meaningful line 0.2 h ago (240/240 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4397/4397 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t62-2347072 | ot_s81sl_leaf__t62 | 3_3_place_gp | 0.4 | overflow best 0.55 last 0.55 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 3_5_place_dp | 1.4 | last meaningful line 0.2 h ago (39/39 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 2_4_floorplan_pdn | 1.4 | last meaningful line 0.8 h ago (130/130 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 1.1 | last meaningful line 0.3 h ago (9007/9007 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | postcts_gate_TT | 8.0 | last meaningful line 0.2 h ago (785/785 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | postcts_gate_TT | 8.0 | last meaningful line 0.1 h ago (375/375 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 8.0 | drt_violations best 91576 last 91576 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-2143713 | tt_ctlm | 3_5_place_dp | 0.5 | last meaningful line -0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | fsk-rr-kv3_pv_v5n-2429273 | fsk-rr-kv3_pv_v5n | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2025592-2928 | 2025592 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-2039494-11393 | 2039494 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_2_route | 2.9 | drt_violations best 213 last 213 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-fin-2785704 | fin | 6_report | 0.3 | last meaningful line 0.2 h ago (340/340 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_1633932_ff_73415 | so_1633932_ff_73415 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc7 | so_1633932_tt_73415 | so_1633932_tt_73415 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3891436 | col_h10_r1__t1 | 3_1_place_gp_skip_io | 0.4 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-3919822 | col_h10_r2__t1 | 3_2_place_iop | 0.4 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (210/212 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_1_grt | 2.0 | last meaningful line 0.5 h ago (204/221 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 7.2 | drt_violations best 100260 last 100260 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3617465 | col_h9_r1__t1 | 3_2_place_iop | 0.5 | last meaningful line 0.1 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_1_floorplan | 1.0 | last meaningful line 0.5 h ago (1424/1424 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 3.3 | repair_TNS best 236465 last 236465 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t4-3684447 | ot_s81sl_kv_leaf__t4 | 1_2_yosys | 0.5 | last meaningful line 0.1 h ago (855/855 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3703022 | ot_s81sl_leaf__t14 | 3_1_place_gp_skip_io | 0.5 | last meaningful line -0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-3703972 | ot_s81sl_leaf__t44 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8989 last 0.8989 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t58-3789284 | ot_s81sl_leaf__t58 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (584/584 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-3908746 | ot_s81sl_leaf__t75 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3421882 | slice_station__t6 | 3_2_place_iop | 0.6 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | eco-abs-3115347 | eco-abs | generate_abstract | 0.7 | last meaningful line 0.5 h ago (656/656 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | nowave-lec-sml_h259 | nowave-lec-sml_h259 | gold.ys | 1.2 | last meaningful line 1.0 h ago (29124/29124 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | otc-3158239-32486 | 3158239 | qwen_compute.t.slw_sc_v1__cl64543eaf__cl4590432d | 0.7 | last meaningful line 0.2 h ago (4/4 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | otc-3689957-27112 | 3689957 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco-i1-3698803 | eco-i1 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (228/1310 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-dsdv-slice-lepw-mu-LP--t2-grt-2171707 | dsdv-slice-lepw-mu-LP--t2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 6.1 | last meaningful line 0.7 h ago (284/285 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 3.9 | last meaningful line 0.2 h ago (262/262 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 60299.1 last 60299.1 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 7.9 | last meaningful line 0.3 h ago (267/268 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3967683 | kv3_pc_v3 | 3_3_place_gp | 1.4 | overflow best 0.7977 last 0.8038 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v3-3969057 | kv3_pc_v3 | 3_3_place_gp | 1.4 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 3_5_place_dp | 1.4 | last meaningful line 0.5 h ago (38/38 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | postcts_gate_TT | 7.9 | last meaningful line 0.1 h ago (855/855 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | postcts_gate_FF | 7.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_1_grt | 8.5 | last meaningful line 0.1 h ago (1243/1249 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | postcts_gate_TT | 8.3 | last meaningful line 0.1 h ago (1104/1104 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | postcts_gate_TT | 7.9 | last meaningful line 0.1 h ago (415/415 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 6_report | 8.6 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 7.9 | drt_violations best 135 last 162 rows 19 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 3.8 | drt_violations best 83927 last 83927 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4120075 | eco-i1t | 5_2_route | 4.6 | drt_violations best 3383 last 3383 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | prd-eco2-i2t-3578697 | eco2-i2t | 5_2_route | 1.7 | drt_violations best 33399 last 33399 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 3_3_place_gp | 1.5 | overflow best 0.1992 last 0.1992 rows 41 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3818192 | col_h10_r0_p1__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3477317 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.2 | repair_Viol best 6050 last 6050 rows 1373 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3660762 | col_h10_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3559 last 3559 rows 609 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (203/206 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (203/206 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 28579.6 last 28579.6 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3453/3453 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | tt_setup_repair | 1.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 6.6 | drt_violations best 86218 last 86218 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-3489028 | col_h9_r1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (198/199 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | sdc_lint | 1.5 | last meaningful line 1.5 h ago (1/1 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | sdc_lint | 1.5 | last meaningful line 1.5 h ago (1/1 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | sdc_lint | 1.5 | last meaningful line 1.5 h ago (1/1 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 3_1_place_gp_skip_io | 1.5 | overflow best 0.2231 last 0.2231 rows 42 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.5 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_LP__t2-1853771 | dsdv_slice_lepe_mu_LP__t2 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (235/235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 143320 last 143320 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (61/61 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-eng__t1-3282689 | eng__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9473 last 0.9773 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_5_place_dp | 1.4 | last meaningful line 0.8 h ago (41/41 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 7.3 | drt_violations best 34685 last 34685 rows 2 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 3_3_place_gp | 1.5 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (3155/3155 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | tt_setup_repair | 1.4 | repair_Viol best 46 last 46 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t31-1082760 | ot_s81sl_leaf__t31 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | tt_setup_repair | 1.4 | repair_Violations best 103 last 133 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t46-3487755 | ot_s81sl_leaf__t46 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t71-3526655 | ot_s81sl_leaf__t71 | 3_1_place_gp_skip_io | 0.1 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (1139/1139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 3_3_place_gp | 1.4 | overflow best 0.8814 last 0.8814 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | tt_setup_measure | 1.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 7.3 | repair_TNS best 35.001 last 35.001 rows 3 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 8.6 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | fsk-rr-kv3_pv_v3-2941838 | fsk-rr-kv3_pv_v3 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2047425-5864 | 2047425 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-3371548-26394 | 3371548 | qwen_compute.t.slw_fw_v2__cl8f84514c | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3428097-1823 | 3428097 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3451428-28163 | 3451428 | qwen_compute.t.slw_fw_v2__cl8f84514c | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3828953-15065 | 3828953 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 4.4 | drt_violations best 58 last 58 rows 12 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-529166 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.2607 last 0.2607 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-541108 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.346 last 0.346 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-385585 | col_h10_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 857801 last 857801 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-676769 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3401 last 0.3401 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-664794 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3393 last 0.3393 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 22541.8 last 22541.8 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1655136 | col_h10_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-558541 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6799 last 0.6799 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-581574 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7452 last 0.7452 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-685457 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9004 last 0.9004 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-595613 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4692 last 0.4692 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-coll_ftm-2637008 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (226/227 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_kv512_C__t1-524813 | dsdv_slice_kv512_C__t1 | 2_1_floorplan | 0.4 | repair_Viol best 8953 last 8953 rows 134 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 6.8 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 2_4_floorplan_pdn | 2.1 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-gunit__t1-533357 | gunit__t1 | 3_3_place_gp | 0.4 | overflow best 0.4092 last 0.4092 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-hd_lep0N_w-880189 | hd_lep0N_w | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3155/3155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-303527 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 59 last 59 rows 3 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-921223 | hd_turn_a | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-304550 | kv3_io_ft | 5_1_grt | 0.5 | repair_Remaining best 171 last 171 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t1-3886007 | ot_s81sl_kv_leaf__t1 | 3_3_place_gp | 0.9 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.2 | repair_TNS best 306043 last 306043 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1642535 | ot_s81sl_leaf__t28 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (579/579 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-544494 | ot_s81sl_leaf__t43 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t52-643025 | ot_s81sl_leaf__t52 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t60-1673352 | ot_s81sl_leaf__t60 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t7-637595 | ot_s81sl_leaf__t7 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t8-508307 | ot_s81sl_leaf__t8 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.211 last 0.211 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-1723438 | ot_s81sl_leaf__t9 | 2_2_floorplan_macro | 0.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-seqhost__t1-430619 | seqhost__t1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3114107 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-247573 | slice_station__t51 | 3_3_place_gp | 0.5 | overflow best 0.2421 last 0.2547 rows 6 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i1-3128620 | eco_20261122_041142_2199995-i1 | 5_2_route | 1.0 | drt_violations best 25 last 25 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i1t-261967 | eco_20261122_054330_1688646-i1t | 5_2_route | 0.5 | last meaningful line 0.1 h ago (225/226 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-4134222-4145 | 4134222 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 47.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 7.8 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 51.5 | last meaningful line 1.9 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 8.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_1_grt | 2.2 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 17.9 | drt_violations best 49344 last 49344 rows 15 | before-window best 53583, window best 49344 | PROGRESS: drt_violations improved 7.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 3.9 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | tt_setup_repair | 3.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 17.4 | drt_violations best 597 last 1395 rows 30 | before-window best 1045, window best 597 | PROGRESS: drt_violations improved 42.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 17.2 | drt_violations best 45146 last 45146 rows 14 | before-window best 50163, window best 45146 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 6.8 | drt_violations best 9668 last 9668 rows 9 | before-window best 85188, window best 9668 | PROGRESS: drt_violations improved 88.7 % in window |  |
| intel1 | ap-ageom-kw-col-h10-r1--t1--cld01bb4ae-grt-3608606 | col-h10-r1--t1--cld01bb4ae-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 42 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | tt_setup_repair | 1.5 | repair_Violations best 0 last 0 rows 9 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | 4_1_cts | 1.0 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_1_grt | 8.2 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 8.9 | drt_violations best 11187 last 11187 rows 10 | before-window best 152197, window best 11187 | PROGRESS: drt_violations improved 92.6 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 12.3 | drt_violations best 27 last 27 rows 47 | before-window best 170434, window best 27 | PROGRESS: drt_violations improved 100.0 % in window |  |
