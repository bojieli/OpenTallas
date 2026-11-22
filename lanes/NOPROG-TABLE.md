# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 05:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 19, 'YOUNG': 162, 'NO-DATA': 14, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 14.0 | last meaningful line 12.3 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 12.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1523684 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | hold_gate | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 6.2 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 43.7 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 58.1 | grt rounds 6 overflow 5:9444 -> 10:5570 -> 15:3582 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 5_1_grt | 6.8 | grt rounds 1 overflow 5:26779 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 2.0 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 37.2 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 42.2 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 31.6 | grt rounds 4 overflow 5:55819 -> 10:49018 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 31.6 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 41.3 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42880 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 31.1 | grt rounds 4 overflow 5:108343 -> 10:69762 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 14.9 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 32.4 | grt rounds 5 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 -> 25:22767 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3564680 | kv3_hroot | 5_1_grt | 3.8 | grt rounds 2 overflow 5:4295 -> 10:1894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 45.3 | grt rounds 5 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 56.0 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 38.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8231 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-3176591 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6927 last 0.6927 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-3225820 | cbf_q00 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6766/6766 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3628903 | coll_core | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | 5_2_route | 4.3 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 4.8 | drt_violations best 28 last 30 rows 51 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 6.6 | drt_violations best 5657 last 5657 rows 12 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2317/2317 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8905 last 0.8941 rows 15 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | pregrt_ff_hold | 2.1 | repair_TNS best 40222.5 last 40222.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_1_grt | 6.4 | last meaningful line 0.7 h ago (226/1063 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 6.7 | drt_violations best 48857 last 48857 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | postcts_gate_TT | 6.5 | last meaningful line 0.0 h ago (849/849 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | postcts_gate_TT | 6.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc10 | otc-616218-14777 | 616218 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 5.2 | drt_violations best 7783 last 7783 rows 7 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc10 | so_3540804_ff_51511 | so_3540804_ff_51511 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | so_3540804_tt_51511 | so_3540804_tt_51511 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | 3_4_place_resized | 0.2 | repair_Remaining best 17933 last 17933 rows 45 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | pregrt_ff_hold | 0.2 | repair_TNS best 36377.1 last 36377.1 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2767328 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-2764618 | gunit__t1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9072 last 0.9072 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9439 last 0.9439 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (54/54 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2525/2526 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2563/2563 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.2304 last 0.2304 rows 38 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 3_3_place_gp | 0.2 | overflow best 0.6625 last 0.6625 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 4_1_cts | 0.2 | last meaningful line -0.0 h ago (2641/2641 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.4691 last 0.4691 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2919/2919 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2520/2520 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2432/2433 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8463 last 0.8463 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2889025 | ot_s81sl_leaf__t57 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8073 last 0.8073 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9274 last 0.9359 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8658 last 0.8838 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_1_grt | 6.8 | last meaningful line 0.1 h ago (1316/1331 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_1_grt | 6.8 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 6.8 | last meaningful line 0.1 h ago (261/261 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4050/4050 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 6.7 | repair_TNS best 2677.74 last 2677.74 rows 9 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 6.7 | repair_TNS best 1472.42 last 1472.42 rows 7 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 6.7 | repair_Remaining best 86020 last 86020 rows 368 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | postcts_gate_TT | 6.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | tt_setup_measure_grt | 6.7 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3083720-2048 | 3083720 | s81.c.ot_hdc_v41x_attn_tr_x_xoff0__h8_1119 | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3165948-16799 | 3165948 | s81.c.ot_hdc_v41x_attn_tr_x_xoff0__h8_1119 | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_3107688_ff_85593 | so_3107688_ff_85593 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3107688_tt_85593 | so_3107688_tt_85593 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-cbf-q00-s2-grt-698882 | cbf-q00-s2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-ctl--cla4f6f12f-grt-725005 | sle-ctl--cla4f6f12f-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-145913 | dsdv_slice_kv512_C__t1 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 1_synth | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | generate_abstract | 15.5 | last meaningful line 0.2 h ago (606/606 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_1_grt | 6.8 | last meaningful line 0.0 h ago (1097/1103 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_1_grt | 6.8 | last meaningful line 0.5 h ago (214/994 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 6.7 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-3828137-8889 | 3828137 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-839361-474 | 839361 | ot_bind_native_095307ffbea013551f0b4c42 | 0.0 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-96114-15417 | 96114 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_105456_3667962-i1-2785704 | eco_20261122_105456_3667962-i1 | 5_2_route | 2.0 | drt_violations best 47 last 47 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (265/265 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-kv3-pc-v3-dump-2053867 | kv3-pc-v3-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-pc-v3-grt-2053867 | kv3-pc-v3-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | clkgrtff-base-1763391 | clkgrtff-base | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_2_route | 8.6 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 50692.5 last 50692.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 90469.7 last 90469.7 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 26480.1 last 26480.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_2_route | 16.7 | drt_violations best 92608 last 92608 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (6675/6675 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3890798 | kv3_hub_Eo | 3_4_place_resized | 1.9 | last meaningful line 0.2 h ago (377/377 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (6648/6648 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3879851 | kv3_hub_Wo | 3_4_place_resized | 1.9 | last meaningful line 0.2 h ago (396/396 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-2157331 | count-p1_tc | prd_count_p1_tc | 0.3 | last meaningful line 0.1 h ago (48/48 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco-i1t-3166843 | eco-i1t | 5_2_route | 2.4 | drt_violations best 6 last 6 rows 57 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-hd-lep0N-w-grt-4015874 | hd-lep0N-w-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 4.8 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_1_grt | 2.6 | last meaningful line 1.0 h ago (233/1363 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3235/3235 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 6.6 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3967683 | kv3_pc_v3 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (533/533 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3969057 | kv3_pc_v3 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (533/533 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | tt_setup_repair_grt | 6.0 | repair_Viol best 2207 last 2207 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2286/2286 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (584/584 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_1_grt | 6.6 | last meaningful line 3.2 h ago (221/1225 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_1_grt | 6.7 | last meaningful line 0.4 h ago (213/919 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_1_grt | 7.1 | last meaningful line 0.3 h ago (1208/1255 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_1_grt | 6.7 | last meaningful line 1.2 h ago (214/1034 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_1_grt | 6.7 | last meaningful line 1.0 h ago (213/1028 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 5_2_route | 7.3 | drt_violations best 74054 last 74054 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 6.6 | drt_violations best 2824 last 2824 rows 3 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 2.6 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4120075 | eco-i1t | 5_2_route | 3.3 | drt_violations best 3383 last 3383 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | prd-eco2-i2t-3578697 | eco2-i2t | 5_2_route | 0.4 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 5.5 | drt_violations best 10290 last 10290 rows 7 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 2_1_floorplan | 0.2 | repair_Viol best 5514 last 5514 rows 1138 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 59490.1 last 59490.1 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 52805.8 last 52805.8 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.274 last 0.274 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3523/3523 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (314/314 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8688 last 0.8688 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9212 last 0.9212 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 5.4 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | tt_setup_repair | 0.2 | repair_Viol best 2197 last 2197 rows 84 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.2911 last 0.2911 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (402/402 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2814/2814 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7935 last 0.8696 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 6.0 | drt_violations best 87099 last 87099 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-1537459 | kv3_hub_Ei | 3_5_place_dp | 3.2 | last meaningful line 0.3 h ago (114/114 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (553/553 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t31-1082760 | ot_s81sl_leaf__t31 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8133 last 0.8382 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (1167/1167 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (328/328 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 6.1 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 7.3 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-775009-2896 | 775009 | qwen_compute.t.slw_fe_v2__cle312294d | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-782529-11013 | 782529 | qwen_compute.t.slw_fe_v2__cle312294d | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 3.2 | drt_violations best 554 last 554 rows 9 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 45008.8 last 45008.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.5 | repair_TNS best 23523 last 23523 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 0.8 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_host_n-1689611 | hd_host_n | 5_2_route | 0.6 | last meaningful line 0.0 h ago (229/230 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N-2232792 | hd_lep0N | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8119 last 0.8119 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-595098 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i1t-1449367 | eco_20261122_041142_2199995-i1t | 5_2_route | 0.8 | drt_violations best 4412 last 4412 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | so_2564683_ff_84493 | so_2564683_ff_84493 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_2564683_tt_84493 | so_2564683_tt_84493 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | otc-3743440-17166 | 3743440 | asbuilt.yosys | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-4127327-11870 | 4127327 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 45.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 6.5 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 8.4 | last meaningful line 0.0 h ago (1160774/1160774 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 50.2 | last meaningful line 0.6 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 6.8 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 6.4 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 16.6 | drt_violations best 51519 last 51519 rows 14 | before-window best 55390, window best 51519 | PROGRESS: drt_violations improved 7.0 % in window |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 16.1 | drt_violations best 597 last 1701 rows 28 | before-window best 1246, window best 597 | PROGRESS: drt_violations improved 52.1 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 15.9 | drt_violations best 45146 last 45146 rows 14 | before-window best 53153, window best 45146 | PROGRESS: drt_violations improved 15.1 % in window |  |
| epyc9 | ap-ageom-kw-col-h10-r1--t1--cld01bb4ae-grt-4098383 | col-h10-r1--t1--cld01bb4ae-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 29 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 4_2_tapbal_grt | 0.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_1_grt | 7.2 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_1_grt | 7.0 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 7.7 | drt_violations best 12000 last 12000 rows 9 | before-window best 152197, window best 12000 | PROGRESS: drt_violations improved 92.1 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 11.1 | drt_violations best 40 last 40 rows 16 | before-window best 170434, window best 40 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
