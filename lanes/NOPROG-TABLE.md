# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 13:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 3, 'GRT-LABEL': 47, 'NO-DATA': 20, 'YOUNG': 109, 'KEEP': 1, 'PROGRESS': 19}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | tt_setup_repair_grt | 6.6 | repair_Viol best 5594 last 5594 rows 5 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -349.91 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 22.7 | last meaningful line 21.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 21.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 24.7 | drt_violations best 43315 last 43315 rows 16 | before-window best 43966, window best 43315 | NO-PROGRESS: drt_violations best 43315 vs 43966 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 14.3 | last meaningful line 6.5 h ago (233/1712 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (FAM-S81-LEPE-4 decides; |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2931852 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -429.51 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 13.2 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 15.0 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 7.3 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:22539 -> 10:21664 -> 15:15614 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 52.4 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:29001 -> 10:29678 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:59362 -> 10:66624 -> 15:45360 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 66.8 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3613 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 10.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 9.0 | grt rounds 3 overflow 5:40789 -> 10:31945 -> 15:26894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:19437 -> 10:19849 -> 15:17373 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 8.9 | grt rounds 5 overflow 5:2659 -> 10:1890 -> 15:1296 -> 20:1316 -> 25:676 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:59446 -> 10:65132 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:59610 -> 10:62798 -> 15:54882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:7392 -> 10:4871 -> 15:3941 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:5714 -> 10:3404 -> 15:2651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:32368 -> 10:23713 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:40043 -> 10:36246 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:24286 -> 10:18739 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:32869 -> 10:27052 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:10045 -> 10:3730 -> 15:2731 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:56686 -> 10:36825 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 46.0 | grt rounds 3 overflow 5:65447 -> 10:65234 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 50.9 | grt rounds 3 overflow 5:61609 -> 10:63105 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 40.3 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 40.3 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 50.1 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42859 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 39.8 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 14.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:29534 -> 10:27331 -> 15:29724 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 5.6 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 6.1 | grt rounds 3 overflow 5:91555 -> 10:41 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 9.1 | grt rounds 8 overflow 15:172 -> 20:100 -> 25:77 -> 30:31 -> 35:4 -> 40:9 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 4 -> 9 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:35677 -> 10:16162 -> 15:8830 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:33424 -> 10:30944 -> 15:23760 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 8.9 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:762 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:61421 -> 10:33517 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 8.7 | grt rounds 3 overflow 5:33084 -> 10:3323 -> 15:1561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 8.7 | grt rounds 3 overflow 5:33301 -> 10:3290 -> 15:1742 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 8.7 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 8.7 | grt rounds 4 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 8.7 | grt rounds 2 overflow 5:56176 -> 10:51245 | GRT-LABEL: DESIGN-FAIL: overflow 51245 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 8.7 | grt rounds 3 overflow 5:34972 -> 10:3595 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 6.4 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 6.5 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-col-h9-r0-p5--t1--pv5c8f2166-grt-2881164 | col-h9-r0-p5--t1--pv5c8f2166-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 6.3 | drt_violations best 1385 last 1385 rows 16 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 6.2 | repair_Viol best 1776 last 1776 rows 16 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_2_route | 6.9 | drt_violations best 10136 last 10136 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-307240 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | postcts_gate_FF | 10.8 | last meaningful line 0.2 h ago (1959/1959 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 15.3 | drt_violations best 16793 last 16793 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | generate_abstract | 15.2 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | kqc-sle_cland_w517_n_s10_1_freg_synth0-2833118 | sle_cland_w517_n_s10_1_freg_synth0 | sta_FF | 0.2 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | kqc-sle_cland_w517_n_s10_2_freg_synth0-3168862 | sle_cland_w517_n_s10_2_freg_synth0 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (218/218 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-574718-9437 | 574718 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-3252184 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (318/318 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 3.3 | drt_violations best 66325 last 66325 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | so_3123525_ff_86469 | so_3123525_ff_86469 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | so_3123525_tt_86469 | so_3123525_tt_86469 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-3109130 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.2 h ago (126/126 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3584924 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 2.7 | overflow best 0.6576 last 0.6576 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 15.5 | drt_violations best 136712 last 136712 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 15.5 | drt_violations best 113702 last 113702 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 15.5 | drt_violations best 8778 last 8778 rows 3 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 15.5 | drt_violations best 109923 last 109923 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 15.5 | drt_violations best 16838 last 16838 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 15.5 | drt_violations best 136145 last 136145 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 15.5 | drt_violations best 13466 last 13466 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_125009_2644377-i1t-3775722 | eco_20261122_125009_2644377-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-fin-4075679 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (462/462 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1255285_ff_47352 | so_1255285_ff_47352 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_1255285_tt_47352 | so_1255285_tt_47352 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_631118_ff_14588 | so_631118_ff_14588 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_631118_tt_14588 | so_631118_tt_14588 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pvc11684b5-grt-1825377 | col-h9-r0-p3--t1--cl8ce97bcb--pvc11684b5-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_3_fillcell | 6.8 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 67179.5 last 67179.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-1845665 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 1.8 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | generate_abstract | 6.7 | last meaningful line 0.0 h ago (371/371 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_1_grt | 8.9 | last meaningful line 0.1 h ago (1306/1330 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 8.6 | last meaningful line 0.5 h ago (225/234 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5756/5756 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9369 last 0.9369 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4269/4269 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-1004368-22302 | 1004368 | signoff | 0.5 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | otc-1305471-15069 | 1305471 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-1940430-23511 | 1940430 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 5.9 | last meaningful line 2.5 h ago (562/562 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 5.9 | last meaningful line 2.5 h ago (562/562 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 5.8 | last meaningful line 2.5 h ago (562/562 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | so_1412167_ff_60050 | so_1412167_ff_60050 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (612/612 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_1412167_tt_60050 | so_1412167_tt_60050 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (612/612 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_2_route | 6.5 | drt_violations best 55845 last 55845 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 6.1 | repair_Remaining best 196446 last 196446 rows 118 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 14.5 | drt_violations best 161798 last 161798 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 9.5 | drt_violations best 40838 last 40838 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_2_route | 5.5 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-3684875 | dsdv_slice_c1x_C__t6 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.7995 last 0.7995 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 6.3 | last meaningful line 2.5 h ago (210/217 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_3_place_gp | 8.5 | overflow best 0.0998 last 0.0998 rows 44 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 11.4 | drt_violations best 69171 last 69171 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 10.8 | repair_Viol best 40 last 40 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 10.8 | repair_TNS best 172.94 last 172.94 rows 10 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3-2853962 | ot_s81sl_leaf__t40 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 6.4 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | prd-eco-i2r-1852378 | eco-i2r | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (237/1328 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t44--clf4ea6d4b-grt-127000 | ot-s81sl-leaf--t44--clf4ea6d4b-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-serdes--t13-grt-4149013 | serdes--t13-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-175162 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.7 h ago (127/127 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 15.4 | drt_violations best 129 last 129 rows 9 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 6_report | 16.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-3698275-17901 | 3698275 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 6.7 | drt_violations best 17985 last 17985 rows 2 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_2_route | 3.3 | drt_violations best 83470 last 83470 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_2_route | 3.8 | drt_violations best 56590 last 56590 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | prd-fin-805483 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (1071/1071 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_2949217_ff_47972 | so_2949217_ff_47972 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc9 | so_2949217_tt_47972 | so_2949217_tt_47972 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc9 | so_3595715_ff_3427 | so_3595715_ff_3427 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | so_3595715_tt_3427 | so_3595715_tt_3427 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | so_4128351_ff_76511 | so_4128351_ff_76511 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_4128351_tt_76511 | so_4128351_tt_76511 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-kw-dsdv-slice-lepw-mu-C--t1-dump-3090475 | dsdv-slice-lepw-mu-C--t1-dump | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-dsdv-slice-lepw-mu-C--t1-grt-3090475 | dsdv-slice-lepw-mu-C--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_2_route | 8.7 | drt_violations best 87699 last 87699 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_2_route | 7.2 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 9.0 | last meaningful line 2.8 h ago (210/232 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pve3ab90e7-2871487 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 8.7 | drt_violations best 67967 last 67967 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 8.7 | drt_violations best 11497 last 11497 rows 2 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 8.7 | last meaningful line 0.8 h ago (195/210 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 8.7 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t60-1586390 | ot_s81sl_leaf__t60 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 14.6 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 15.5 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 3.7 | last meaningful line 3.6 h ago (3/3 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | otc-3034506-22939 | 3034506 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 5.0 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (2998/2998 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 8.6 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 9.4 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 6.5 | repair_Remaining best 31953 last 31953 rows 202 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | tt_setup_repair_grt | 6.5 | last meaningful line -0.0 h ago (930/930 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | tt_setup_repair_grt | 6.9 | repair_Viol best 2251 last 2251 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_1_grt | 0.8 | repair_Remaining best 817 last 817 rows 49 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 5.1 | last meaningful line 0.3 h ago (157/157 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_1_place_gp_skip_io | 3.1 | overflow best 0.7963 last 0.7963 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.9 | repair_Violations best 1360 last 1360 rows 31 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | tt_setup_repair | 5.1 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 5.1 | last meaningful line 0.1 h ago (2825/2825 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2278295 | kv3_io_ft | 5_2_route | 1.8 | drt_violations best 5487 last 5487 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 4_1_cts | 3.0 | last meaningful line 0.3 h ago (4953/4953 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 11.0 | repair_TNS best 7851.33 last 7851.33 rows 5 | YOUNG: evidence 6.0 h < 6 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 8.7 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 3.0 | last meaningful line 1.1 h ago (204/216 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-617275 | ot_s81sl_leaf__t50 | pregrt_ff_hold | 0.8 | repair_TNS best 6033.65 last 6033.65 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (208/210 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 4_1_cts | 3.0 | last meaningful line 0.2 h ago (4944/4944 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 5_2_route | 3.0 | drt_violations best 8654 last 8654 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 6.5 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | tt_setup_repair | 3.1 | repair_Remaining best 128476 last 128476 rows 222 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | serene_bartik | serene_bartik | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 54.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 15.3 | drt_violations best 4374 last 7940 rows 20 | before-window best 4691, window best 4374 | PROGRESS: drt_violations improved 6.8 % in window |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 6.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 7.5 | last meaningful line 0.0 h ago (801/801 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_2_route | 4.8 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 59.0 | last meaningful line 0.6 h ago (1564/1564 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 15.5 | drt_violations best 22829 last 22829 rows 2 | before-window best 132730, window best 22829 | PROGRESS: drt_violations improved 82.8 % in window |  |
| epyc7 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-1848639 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-994857 | slw_st_a_v2 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 14.7 | drt_violations best 2539 last 2962 rows 20 | before-window best 5325, window best 2539 | PROGRESS: drt_violations improved 52.3 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_1_grt | 8.7 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 8.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 14.5 | drt_violations best 2973 last 18181 rows 18 | before-window best 9518, window best 2973 | PROGRESS: drt_violations improved 68.8 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | pregrt_ff_hold | 7.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 16.2 | drt_violations best 1939 last 1939 rows 15 | before-window best 7622, window best 1939 | PROGRESS: drt_violations improved 74.6 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 11.7 | drt_violations best 1 last 30 rows 42 | before-window best 29, window best 1 | PROGRESS: drt_violations improved 96.6 % in window |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
