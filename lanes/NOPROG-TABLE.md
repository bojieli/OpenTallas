# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 19:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 1, 'GRT-LABEL': 34, 'YOUNG': 183, 'NO-DATA': 16, 'PROGRESS': 44}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 12.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 12.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 28.7 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | tt_setup_repair_grt | 12.4 | repair_Violations best 0 last 0 rows 41 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -611.19 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-3113889 | col_h9_r0_p5__t1 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:58130 -> 10:3288 | GRT-LABEL: DESIGN-FAIL: overflow 3288 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1512680 | ot_s81sl_leaf__t27 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:28580 -> 10:8107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 58.4 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50054 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1501489 | sle_st_a_v1 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:1078 -> 10:533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_a_v2__pv4242de79-43496 | sle_st_a_v2 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:18195 -> 10:8116 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 72.8 | grt rounds 6 overflow 5:8939 -> 10:5163 -> 15:3337 -> 20:2951 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2032513 | ot_s81sl_leaf__t30 | 5_1_grt | 3.8 | grt rounds 4 overflow 5:32003 -> 10:27757 -> 15:23027 -> 20:21475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 5.1 | grt rounds 4 overflow 5:33787 -> 10:32188 -> 15:29669 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 14.9 | grt rounds 4 overflow 5:7049 -> 10:4695 -> 15:3416 -> 20:3335 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 14.9 | grt rounds 3 overflow 5:24185 -> 10:16633 -> 15:14263 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 4.5 | grt rounds 3 overflow 5:36651 -> 10:36233 -> 15:30181 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:40889 -> 10:35808 -> 15:29110 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 13.0 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 52.0 | grt rounds 3 overflow 5:76937 -> 10:70297 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 56.9 | grt rounds 3 overflow 5:61116 -> 10:63134 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 46.3 | grt rounds 4 overflow 5:58312 -> 10:48779 -> 15:39348 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 46.3 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 56.1 | grt rounds 4 overflow 5:77624 -> 10:49527 -> 15:42727 -> 20:44053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 45.8 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 20.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t42-283577 | ot_s81sl_leaf__t42 | 5_1_grt | 1.6 | grt rounds 2 overflow 5:44899 -> 10:41746 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 14.9 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 5_1_grt | 5.8 | grt rounds 3 overflow 5:36002 -> 10:35295 -> 15:33217 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 15.0 | grt rounds 5 overflow 5:47409 -> 10:2770 -> 15:1232 -> 20:855 -> 25:396 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 15.0 | grt rounds 6 overflow 5:47882 -> 10:2931 -> 15:1264 -> 20:1038 -> 25:413 -> 30:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-645502 | col_h9_r2__t1 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:3231 -> 10:234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 13.3 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 15.0 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 14.9 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 14.9 | grt rounds 3 overflow 5:36618 -> 10:2722 -> 15:2123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t68-641169 | ot_s81sl_leaf__t68 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:38992 -> 10:8140 | GRT-LABEL: DESIGN-FAIL: overflow 8140 at round 10 > 1000 |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_1_grt | 7.0 | grt rounds 2 overflow 5:60853 -> 10:337 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 11.1 | grt rounds 2 overflow 5:88896 -> 10:83085 | GRT-LABEL: DESIGN-FAIL: overflow 83085 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 6.8 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-2991761 | bk_sel__t2 | pregrt_ff_hold | 3.9 | repair_TNS best 33255 last 33255 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2844492 | col_h10_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 151547 last 151547 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-2806984 | col_h10_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 96461.4 last 96461.4 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-44672 | col_h9_r0_p5__t1 | 5_1_grt | 3.0 | last meaningful line 0.1 h ago (209/212 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t3-886705 | dsdv_slice_c1x_C__t3 | 3_1_place_gp_skip_io | 2.4 | overflow best 0.4671 last 0.4671 rows 35 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-880876 | dsdv_slice_c1x_C__t7 | 3_1_place_gp_skip_io | 2.4 | overflow best 0.8284 last 0.8423 rows 15 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_kv512_C__t1-3997844 | dsdv_slice_kv512_C__t1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.9635 last 0.9635 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-2617721 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 75437.1 last 75437.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-iqf__t1-13421 | iqf__t1 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (250/251 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-1070279 | kv3_sys_c | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (1145/1145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-native59-2568165 | native59 | 3_3_place_gp | 1.6 | overflow best 0.1698 last 0.1698 rows 226 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t15-1140501 | ot_s81sl_leaf__t15 | 5_1_grt | 2.2 | last meaningful line 0.8 h ago (200/209 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | 5_1_grt | 2.3 | last meaningful line 0.5 h ago (200/208 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-1070507 | ot_s81sl_leaf__t28 | tt_setup_repair | 2.3 | repair_Viol best 3 last 3 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-3765593 | ot_s81sl_leaf__t29 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t33-29735 | ot_s81sl_leaf__t33 | 5_1_grt | 3.0 | last meaningful line 1.3 h ago (205/214 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t35-2862501 | ot_s81sl_leaf__t35 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (199/202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t38-2879349 | ot_s81sl_leaf__t38 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t4-1513632 | ot_s81sl_leaf__t4 | 5_1_grt | 2.1 | last meaningful line 0.8 h ago (203/211 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t51-69679 | ot_s81sl_leaf__t51 | 3_3_place_gp | 0.6 | overflow best 0.2252 last 0.274 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-1482469 | ot_s81sl_leaf__t67 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (5337/5337 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-3226431 | ot_s81sl_leaf__t67 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5291/5291 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t71-78115 | ot_s81sl_leaf__t71 | 3_4_place_resized | 0.6 | last meaningful line -0.0 h ago (227/227 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-seqhost__t1-284630 | seqhost__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.927 last 0.927 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-2766932 | sle_fw_v1 | 3_4_place_resized | 1.5 | last meaningful line 0.1 h ago (408/408 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3138515 | sle_hc1 | 3_3_place_gp | 1.3 | overflow best 0.2976 last 0.3124 rows 182 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_1_grt | 3.8 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t25-3118247 | slice_station__t25 | 5_2_route | 3.8 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__cl95cd1d0c-3981528 | slw_fe_v1 | 3_3_place_gp | 0.7 | overflow best 0.2865 last 0.2865 rows 26 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3982998 | slw_fe_v1 | 3_3_place_gp | 0.7 | overflow best 0.2387 last 0.2458 rows 31 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | otc-2598673-6856 | 2598673 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc10 | otc-2600316-20386 | 2600316 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc10 | so_4113514_ff_98490 | so_4113514_ff_98490 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc10 | so_4113514_tt_98490 | so_4113514_tt_98490 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3444/3445 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3579/3579 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-2024740 | col_h10_r0_p1__t1 | 5_1_grt | 3.8 | last meaningful line 0.5 h ago (209/215 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-2046903 | col_h9_r0_p5__t1 | 5_1_grt | 3.8 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 63390.8 last 63390.8 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2510614 | col_h9_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 84209.8 last 84209.8 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-1865895 | dsdv_slice_c1x_C__t1 | selrange | 1.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 4_1_cts | 3.8 | last meaningful line 0.0 h ago (2738/2738 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 4_1_cts | 3.8 | last meaningful line 0.1 h ago (3183/3183 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-1830876 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.5 h ago (126/126 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-1932490 | dsdv_slice_c1x_C__t5 | selrange | 1.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1830466 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.5 h ago (128/128 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1835310 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | selrange | 1.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-3244008 | gunit__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.3 h ago (39/39 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3327/3327 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-3748922 | kv3_io_cor_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3654/3654 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t13-3064395 | ot_s81sl_leaf__t13 | 3_3_place_gp | 0.9 | overflow best 0.5876 last 0.5876 rows 3 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t17-1828917 | ot_s81sl_leaf__t17 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (4114/4114 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t23-4154466 | ot_s81sl_leaf__t23 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.681 last 0.681 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (2473/2473 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (202/207 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-1897215 | ot_s81sl_leaf__t34 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-1816190 | ot_s81sl_leaf__t41 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3199/3199 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t47-1932405 | ot_s81sl_leaf__t47 | pregrt_ff_hold | 1.5 | repair_TNS best 115788 last 115788 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-1861843 | ot_s81sl_leaf__t5 | 5_1_grt | 1.5 | last meaningful line 0.1 h ago (201/204 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t61-3939526 | ot_s81sl_leaf__t61 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t62-1866677 | ot_s81sl_leaf__t62 | pregrt_ff_hold | 1.5 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t4-1837565 | serdes__t4 | 3_3_place_gp | 1.5 | overflow best 0.6047 last 0.6047 rows 33 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-217266 | sle_ctl | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t17-1827654 | slice_station__t17 | 5_2_route | 1.5 | drt_violations best 2552 last 2552 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-2336581 | slice_station__t29 | postcts_gate_FF | 1.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-2458281 | slw_fe_v1 | 3_5_place_dp | 1.3 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (5428/5428 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5206/5206 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-1777311 | slw_hc1 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 3.8 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2569/2569 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | pregrt_ff_hold | 0.8 | repair_Violations best 8747 last 8747 rows 20 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | otc-1094939-10134 | 1094939 | signoff | 4.3 | last meaningful line 4.3 h ago (3/3 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | otc-1481339-18431 | 1481339 | signoff | 4.1 | last meaningful line 4.0 h ago (3/3 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | otc-8794-30617 | 8794 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1t-3385034 | eco_20261122_164248_3895049-i1t | 5_2_route | 3.0 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1t-3466592 | eco_20261122_164521_3948325-i1t | 5_2_route | 3.0 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_180145_3931237-i1-1443078 | eco_20261122_180145_3931237-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1t-1909174 | eco_20261122_181101_3945375-i1t | 5_2_route | 1.5 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_306350_ff_95502 | so_306350_ff_95502 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1027/1027 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_306350_tt_95502 | so_306350_tt_95502 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1027/1027 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_2_route | 6.4 | drt_violations best 1392 last 1392 rows 6 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | tt_setup_measure_grt | 5.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-8352 | dsdv_slice_lepe_nh_mus_C__t1 | 2_1_floorplan | 2.3 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 5.0 | last meaningful line 0.3 h ago (208/217 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t21-1786623 | ot_s81sl_leaf__t21 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | pregrt_ff_hold | 2.3 | repair_TNS best 11432.9 last 11432.9 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 1.6 | repair_TNS best 452309 last 452309 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3434359 | ot_s81sl_leaf__t46 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4738 last 0.4738 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t50-1499047 | ot_s81sl_leaf__t50 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (207/213 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 14.9 | drt_violations best 107202 last 107202 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-1949749 | sle_fw_v1 | 3_4_place_resized | 1.3 | last meaningful line 0.2 h ago (405/405 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_1_grt | 5.5 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | postcts_gate_TT | 1.5 | last meaningful line -0.0 h ago (35966/35966 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-1764151 | sle_hc1 | 3_3_place_gp | 1.4 | overflow best 0.2634 last 0.2634 rows 199 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_1_grt | 6.5 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1983201 | sle_st_a_v2 | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (271/1279 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_2_route | 6.5 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t18-1919126 | slice_station__t18 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (555/555 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t45-1870760 | slice_station__t45 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (117/117 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-1772119 | slice_station__t6 | tt_setup_repair_grt | 1.4 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1946912 | slw_fe_v1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_1_grt | 6.4 | repair_Remaining best 222869 last 222869 rows 229 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1955539 | slw_fw_v1 | 3_3_place_gp | 1.3 | overflow best 0.0988 last 0.0988 rows 41 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_1_grt | 5.0 | repair_Remaining best 302718 last 302718 rows 128 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_1_grt | 1.4 | last meaningful line 0.2 h ago (260/1267 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1-251441 | eco_20261122_215654_330309-i1 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1-3987348 | eco_20261122_220050_168828-i1 | 5_2_route | 2.5 | drt_violations best 4470 last 4470 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t54--cl501e5681-grt-687635 | ot-s81sl-leaf--t54--cl501e5681-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 11.6 | drt_violations best 110424 last 110424 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4104970 | col_h10_r2__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 53396.9 last 53396.9 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 93931.6 last 93931.6 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 12.1 | drt_violations best 180834 last 180834 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 1.6 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 3.0 | last meaningful line 0.3 h ago (257/258 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_5_place_dp | 14.5 | last meaningful line 2.5 h ago (131/131 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-2778952 | kv3_io_cor_v1 | 5_2_route | 3.0 | last meaningful line 0.3 h ago (250/251 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6n-4024718 | kv3_pv_v6n | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8868 last 0.8868 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | postcts_gate_TT | 12.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3458913 | ot_s81sl_leaf__t14 | 3_3_place_gp | 0.9 | last meaningful line 0.3 h ago (88/88 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t36-2215632 | ot_s81sl_leaf__t36 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t52-2261818 | ot_s81sl_leaf__t52 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t58-3445802 | ot_s81sl_leaf__t58 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (4307/4307 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t65-2863435 | ot_s81sl_leaf__t65 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (207/213 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3952570 | slice_station__t40 | 5_2_route | 4.4 | drt_violations best 17220 last 17220 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-159237-lec | kvcore-qkd_ectlk_q0__216x172.8_ | lec | 0.4 | LEC last write 0.0 h ago | YOUNG: evidence 0.4 h < 6 h |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-3106818-lec | kvcore-qkd_ectlk_q0__216x172.8_ | lec | 1.0 | LEC last write 0.1 h ago | YOUNG: evidence 1.0 h < 6 h |  |
| epyc8 | kvcore-qkd_ectlk_q2__243.648x172.8_-157778 | kvcore-qkd_ectlk_q2__243.648x172.8_ | 5_1_grt | 0.4 | repair_Remaining best 14307 last 14307 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | so_792511_ff_82051 | so_792511_ff_82051 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_792511_tt_82051 | so_792511_tt_82051 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-237532 | col_h10_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 62823.2 last 62823.2 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 15.1 | drt_violations best 178849 last 178849 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-238701 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 109251 last 109251 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-275844 | col_h9_r2__t1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t6-401942 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-405849 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (3657/3657 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-288662 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.6 | overflow best 0.7064 last 0.9394 rows 24 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-426957 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-eng__t1-443909 | eng__t1 | 5_1_grt | 1.5 | last meaningful line 0.5 h ago (196/202 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-236913 | hd_host_n | 5_2_route | 1.6 | drt_violations best 412 last 412 rows 3 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-852757 | ot_s81sl_kv_leaf__t5 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-457556 | ot_s81sl_leaf__t22 | pregrt_ff_hold | 1.5 | repair_TNS best 7998.22 last 7998.22 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-426492 | ot_s81sl_leaf__t39 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (182/182 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-306943 | ot_s81sl_leaf__t44 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-236943 | ot_s81sl_leaf__t59 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t69-442023 | ot_s81sl_leaf__t69 | 5_1_grt | 1.5 | last meaningful line 0.5 h ago (200/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t3-403584 | serdes__t3 | 3_3_place_gp | 1.5 | overflow best 0.8318 last 0.8318 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t22-239981 | slice_station__t22 | 5_1_grt | 1.6 | last meaningful line 0.2 h ago (203/440 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_2_route | 5.8 | drt_violations best 31237 last 31237 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clb036e152-429176 | slw_st_a_v1 | 5_1_grt | 1.5 | repair_Remaining best 103772 last 103772 rows 51 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | otc-2086126-20683 | 2086126 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-3560213-28657 | 3560213 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-682537-13250 | 682537 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1t-3504713 | eco-i1t | 5_2_route | 2.1 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco-i3-2776988 | eco-i3 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i2t-3854167 | eco_20261122_180231_342380-i2t | 5_2_route | 1.9 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1-1254579 | eco_20261122_214447_3988541-i1 | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (239/724 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 15.0 | drt_violations best 195281 last 195281 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3359910 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 121922 last 121922 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3365642 | col_h10_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 108409 last 108409 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 15.0 | drt_violations best 210671 last 210671 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3518851 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 58591.8 last 58591.8 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3535177 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 74162.8 last 74162.8 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3531236 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 170706 last 170706 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-3367117 | col_h9_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 38088.9 last 38088.9 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3522410 | col_h9_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 44884.8 last 44884.8 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_1_grt | 4.9 | last meaningful line 0.2 h ago (1318/1379 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-3365034 | dsdv_slice_c1x_C__t3 | sdc_lint | 1.6 | last meaningful line 1.6 h ago (1/1 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | 4_1_cts | 4.9 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | postcts_gate_TT | 13.5 | last meaningful line 0.2 h ago (23/23 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 15.0 | last meaningful line 0.8 h ago (209/218 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-3536309 | ot_s81sl_leaf__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 65423.2 last 65423.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t32-3518438 | ot_s81sl_leaf__t32 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3557/3557 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3-3373654 | ot_s81sl_leaf__t40 | 5_1_grt | 1.6 | last meaningful line 0.3 h ago (199/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | pregrt_ff_hold | 1.5 | repair_TNS best 9230.96 last 9230.96 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t70-643388 | ot_s81sl_leaf__t70 | 5_1_grt | 3.1 | last meaningful line 1.0 h ago (203/212 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 4_1_cts | 1.5 | last meaningful line -0.0 h ago (3577/3577 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4780/4781 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_1_grt | 1.6 | last meaningful line 0.2 h ago (260/1268 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | otc-105520-18563 | 105520 | signoff | 1.0 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-2998450-18208 | 2998450 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-count-p1_bc-4088168 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_2_route | 5.1 | drt_violations best 2542 last 2542 rows 8 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1t-1135156 | eco_20261122_165619_1517073-i1t | 5_2_route | 2.8 | drt_violations best 36312 last 36312 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1154585 | coll_ftm | 5_2_route | 1.9 | drt_violations best 10185 last 10185 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 11.1 | last meaningful line 0.5 h ago (211/214 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-4129782 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (210/211 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 7.0 | repair_TNS best 204204 last 204204 rows 5 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | postcts_gate_TT | 9.0 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_2_route | 9.1 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-21704 | slice_station__t24 | 3_3_place_gp | 0.2 | overflow best 0.6961 last 0.6966 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 9.1 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | so_3998319_ff_77491 | so_3998319_ff_77491 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | so_3998319_tt_77491 | so_3998319_tt_77491 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 12.2 | drt_violations best 14388 last 14388 rows 8 | before-window best 363722, window best 14388 | PROGRESS: drt_violations improved 96.0 % in window |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-1472079 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_sys_c-1472961 | kv3_sys_c | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 13.5 | last meaningful line 0.1 h ago (1177/1177 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 9.3 | drt_violations best 11 last 11 rows 49 | before-window best 66325, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1-42727 | eco_20261122_223531_3628570-i1 | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 65.0 | last meaningful line 0.2 h ago (1608/1608 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2022266 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-1903434 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-2035057 | tt_ctlm | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 7.1 | drt_violations best 1 last 2 rows 42 | before-window best 84758, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1t-3508652 | eco_20261122_190506_3875261-i1t | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-hd_ctl-1922947 | hd_ctl | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-1928775 | slice_station__t40 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 15.5 | drt_violations best 15336 last 15336 rows 12 | before-window best 40838, window best 15336 | PROGRESS: drt_violations improved 62.4 % in window |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-2830715 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-glue-555250 | glue | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_1_grt | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-159237 | kvcore-qkd_ectlk_q0__216x172.8_ | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 108 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | kvcore-qkd_ectlk_q1__243.648x172.8_-158121 | kvcore-qkd_ectlk_q1__243.648x172.8_ | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | kvcore-qkd_ectlk_q3__216x172.8_-160081 | kvcore-qkd_ectlk_q3__216x172.8_ | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 150 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 7.5 | drt_violations best 53 last 53 rows 15 | before-window best 15272, window best 53 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3367083 | col_h10_r2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3522831 | col_h10_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 15.2 | repair_TNS best 1962.78 last 1962.78 rows 9 | before-window best 5394.07, window best 1962.78 | PROGRESS: repair_TNS improved 63.6 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-3533701 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 20.8 | drt_violations best 2973 last 5326 rows 21 | before-window best 2973, window best 5326 | PROGRESS: drt_violations: falling inside the active iteration (5326 -> 4749) |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | tt_setup_repair | 3.1 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slice_station__t28-3353995 | slice_station__t28 | 5_1_grt | 1.6 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 22.4 | drt_violations best 1159 last 1159 rows 21 | before-window best 1939, window best 1159 | PROGRESS: drt_violations improved 40.2 % in window |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 15.4 | drt_violations best 156124 last 156124 rows 1 | before-window best 156124, window best 156124 | PROGRESS: drt_violations: active iteration at 44028 < best completed total 156124 (in-iter |  |
| intel2 | dpkit-kv3_io_ft-4133103 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 9.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 14.7 | repair_TNS best 107.627 last 107.627 rows 9 | before-window best 1024.79, window best 107.627 | PROGRESS: repair_TNS improved 89.5 % in window |  |
| intel2 | dpkit-slice_station__t12-4171719 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
