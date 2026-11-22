# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 15:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 1, 'GRT-LABEL': 39, 'NO-DATA': 8, 'YOUNG': 131, 'KEEP': 2, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 17.1 | drt_violations best 4374 last 6676 rows 22 | before-window best 4374, window best 6676 | NO-PROGRESS: drt_violations best 6676 vs 4374 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-HROOT-R1 decides |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 24.7 | last meaningful line 21.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 21.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 10.7 | grt rounds 1 overflow 5:2 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -443.22 ps (< -300, gate TT >= -42); job age 10 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 16.3 | last meaningful line 8.5 h ago (233/1712 lines) | NO-PROGRESS: no new non-iteration log line for 8.5 h | REPORT-ONLY: lane-own kit (FAM-S81-LEPE-4 decides; |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 14.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 54.2 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:29001 -> 10:26780 -> 15:24876 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 68.6 | grt rounds 6 overflow 5:9414 -> 10:5163 -> 15:3613 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-3487466-21488 | 3487466 | 5_1_grt | 1.6 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:59557 -> 10:64367 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 1.1 | grt rounds 4 overflow 5:48483 -> 10:32112 -> 15:29676 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: overflow 32112 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:7392 -> 10:5019 -> 15:3621 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 10.9 | grt rounds 4 overflow 5:5427 -> 10:3404 -> 15:2651 -> 20:2469 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:32368 -> 10:23713 -> 15:20435 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:24072 -> 10:16574 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:32852 -> 10:26729 -> 15:20655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 0.5 | grt rounds 3 overflow 5:37003 -> 10:36397 -> 15:29681 | GRT-LABEL: DESIGN-FAIL: overflow 36397 at round 10 > 1000 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 48.0 | grt rounds 3 overflow 5:65447 -> 10:66805 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 52.9 | grt rounds 3 overflow 5:61609 -> 10:62172 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 42.3 | grt rounds 4 overflow 5:58312 -> 10:48607 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 42.3 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 52.1 | grt rounds 4 overflow 5:77624 -> 10:49634 -> 15:42859 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 41.8 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 16.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 10.6 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-994857 | slw_st_a_v2 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:21080 -> 10:15696 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 8.3 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 10.9 | grt rounds 4 overflow 5:42588 -> 10:30944 -> 15:23760 -> 20:20154 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 10.9 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 11.9 | grt rounds 3 overflow 5:63320 -> 10:33517 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 10.7 | grt rounds 4 overflow 5:33084 -> 10:3323 -> 15:1561 -> 20:909 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 10.7 | grt rounds 4 overflow 5:33301 -> 10:3290 -> 15:1523 -> 20:1038 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 10.7 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:55088 -> 10:51245 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:22842 -> 10:2857 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:83696 -> 10:70 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 5.0 | grt rounds 3 overflow 5:7803 -> 10:769 -> 15:476 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:21814 -> 10:20459 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 8.4 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-sle-st-a-v1--cl989804f6--cl18eece69-grt-2315927 | sle-st-a-v1--cl989804f6--cl18eece69-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 8.0 | drt_violations best 1385 last 1390 rows 36 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 8.0 | repair_Viol best 1776 last 1776 rows 76 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 7.9 | drt_violations best 363722 last 363722 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-307240 | dsdv_slice_c1x_C__t10 | 3_5_place_dp | 2.9 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t32-2228301 | ot_s81sl_leaf__t32 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (93/93 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t35-2225961 | ot_s81sl_leaf__t35 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9886 last 0.9886 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_2_route | 12.6 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | generate_abstract | 17.0 | last meaningful line 0.4 h ago (665/665 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-210420-13766 | 210420 | signoff | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | otc-2195601-28775 | 2195601 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-2226456-6040 | 2226456 | qwen_compute.t.sle_stm_v1__cl27746664 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 5.0 | drt_violations best 1958 last 1958 rows 6 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1-693810 | eco_20261122_165114_3352738-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1t-873116 | eco_20261122_223531_3628570-i1t | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (233/1358 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-fin-3565304 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | so_2258756_ff_91458 | so_2258756_ff_91458 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | so_2258756_tt_91458 | so_2258756_tt_91458 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-679902 | col_h10_r1__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3248/3249 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-1360538 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.3449 last 0.3465 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-679412 | col_h9_r0_p2__t1 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (193/193 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-3659100 | dsdv_slice_c1x_C__t10 | selrange | 1.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-683007 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t23-694414 | ot_s81sl_leaf__t23 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3901/3901 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-687429 | ot_s81sl_leaf__t54 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-686262 | ot_s81sl_leaf__t7 | 3_3_place_gp | 0.5 | overflow best 0.5721 last 0.5748 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t71-691089 | ot_s81sl_leaf__t71 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t73-3636691 | ot_s81sl_leaf__t73 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (3877/3878 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-seqhost__t1-686556 | seqhost__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5685 last 0.5685 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | generate_abstract | 17.5 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 17.5 | drt_violations best 23813 last 23813 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 17.5 | drt_violations best 422 last 422 rows 4 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | generate_abstract | 17.5 | last meaningful line 0.2 h ago (557/557 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 6_report | 17.5 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-691946 | slw_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (8730/8730 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-1094939-10134 | 1094939 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-1481339-18431 | 1481339 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-2738927-2977 | 2738927 | signoff | 1.5 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 3.1 | drt_violations best 4880 last 4880 rows 4 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_140001_4005935-i1-2236985 | eco_20261122_140001_4005935-i1 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_153005_3681923-i1t-1213027 | eco_20261122_153005_3681923-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_retry_1795389734917048336-i1t-961404 | eco_retry_1795389734917048336-i1t | 5_2_route | 0.4 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1299458_ff_7769 | so_1299458_ff_7769 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_1299458_tt_7769 | so_1299458_tt_7769 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 | col_h9_r0_p6__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_1_grt | 2.4 | repair_TNS best 401.919 last 401.919 rows 3 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 111710 last 111710 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 2.5 | overflow best 0.3739 last 0.3739 rows 34 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t9-4106886 | dsdv_slice_c1x_C__t9 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_C__t1-4102769 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 1.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t29-3865255 | ot_s81sl_leaf__t29 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3967105 | ot_s81sl_leaf__t46 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4681/4681 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3844958 | ot_s81sl_leaf__t55 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 10.9 | last meaningful line 0.2 h ago (278/278 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (3729/3729 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (247/248 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (6086/6086 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-1004368-22302 | 1004368 | signoff | 2.5 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 2.7 | last meaningful line 2.6 h ago (3/3 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1t-2527780 | eco_20261122_215654_330309-i1t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1t-2658286 | eco_20261122_220050_168828-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-497679 | col_h9_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 201 last 231 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-3921644 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 67889.7 last 67889.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_2_route | 7.5 | drt_violations best 11670 last 11670 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t4-3857153 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 8.3 | last meaningful line 4.5 h ago (210/219 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-492515 | kv3_hroot | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (952/952 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_4_place_resized | 10.5 | last meaningful line 1.3 h ago (449/449 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 6_report | 13.4 | last meaningful line 0.2 h ago (1072/1072 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (6859/6859 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | tt_setup_repair_grt | 12.8 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-491783 | kv3_io_cor_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6n-496119 | kv3_pv_v6n | port_bind | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t21-3954640 | ot_s81sl_leaf__t21 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3087/3087 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3845641 | sle_st_a_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5892/5892 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t21-3827757 | slice_station__t21 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (1334/1334 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t29__cl2e5c855a-3939444 | slice_station__t29 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3952570 | slice_station__t40 | pregrt_ff_hold | 0.4 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-489473-4122 | 489473 | qwen_compute.t.slw_st_b_v2__pvc2ec5bfb | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-492156-28314 | 492156 | qwen_compute.t.slw_st_b_v2__pvc2ec5bfb | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-602558-26362 | 602558 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco-i2r-1852378 | eco-i2r | 5_2_route | 2.6 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 11.1 | last meaningful line 0.1 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-682008 | col_h9_r1__t1 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | 3_4_place_resized | 2.6 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-566156 | dsdv_slice_iq_C__t1 | 3_5_place_dp | 1.8 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | postcts_gate_FF | 1.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-670966 | ot_s81sl_leaf__t58 | 5_1_grt | 1.8 | last meaningful line 0.3 h ago (204/207 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | generate_abstract | 17.4 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | tt_setup_repair_grt | 1.8 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | pregrt_ff_hold | 1.8 | repair_TNS best 181264 last 181264 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | postcts_gate_FF | 1.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | eco-abs-4044321 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (498/498 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 1.5 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | otc-2867161-32206 | 2867161 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 3.5 | drt_violations best 4135 last 4135 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1-1472150 | eco_20261122_174935_2347281-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1-577405 | eco_20261122_180231_342380-i1 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_2_route | 2.0 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_223653_314236-i1-2039775 | eco_20261122_223653_314236-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv3a0a8b60-grt-2741625 | col-h9-r1--t1--cl49d7a23e--pv3a0a8b60-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 10.7 | last meaningful line 0.3 h ago (150/150 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_2_route | 8.3 | drt_violations best 48217 last 48217 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_2_route | 9.3 | drt_violations best 55826 last 55826 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 11.0 | repair_Remaining best 86495 last 86495 rows 217 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 10.7 | last meaningful line 0.2 h ago (272/272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1675980 | col_h9_r0_p4__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 94532.8 last 94532.8 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 10.7 | drt_violations best 1385 last 1388 rows 20 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | tt_setup_repair | 0.7 | repair_Viol best 49 last 49 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-1671863 | col_h9_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 95341.9 last 95341.9 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 9.0 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_1_grt | 9.2 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 10.7 | last meaningful line 1.0 h ago (208/221 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t28-2748044 | ot_s81sl_leaf__t28 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (579/579 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 16.6 | drt_violations best 88173 last 88173 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 17.5 | drt_violations best 9842 last 9842 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 7.0 | drt_violations best 33922 last 33922 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 10.6 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 11.4 | last meaningful line 0.5 h ago (290/291 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 8.9 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_2_route | 2.8 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 7.1 | last meaningful line 1.5 h ago (208/213 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 5.1 | last meaningful line 1.0 h ago (36/36 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 5.0 | repair_TNS best 10405.5 last 10405.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 10.7 | repair_TNS best 11884.8 last 11884.8 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 3.0 | repair_Remaining best 252404 last 252404 rows 52 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 2.8 | last meaningful line 0.8 h ago (202/210 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 5.0 | last meaningful line 2.3 h ago (208/217 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 8.5 | drt_violations best 48586 last 48586 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | otc-1349921-30783 | 1349921 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__cl774acf45__pvea45273b-3781481 | col_h9_r2__t1 | pregrt_ff_hold | 1.1 |  | KEEP: col_h9_r2__t1__cl774acf45__pvea45273b	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | prd-eco_20261120_150342_478824-i1-1690412 | eco_20261120_150342_478824-i1 | 5_2_route | 1.3 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 9.2 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 61.0 | last meaningful line 0.2 h ago (1566/1566 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t61-3925881 | ot_s81sl_leaf__t61 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 7.9 | last meaningful line 4.5 h ago (562/562 lines) | PROGRESS: log still growing |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 7.9 | last meaningful line 4.5 h ago (562/562 lines) | PROGRESS: log still growing |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 7.8 | last meaningful line 4.5 h ago (562/562 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 7.6 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 8.1 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 16.5 | drt_violations best 37 last 37 rows 13 | before-window best 161798, window best 37 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 11.5 | drt_violations best 18867 last 18867 rows 8 | before-window best 128949, window best 18867 | PROGRESS: drt_violations improved 85.4 % in window |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 8.4 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_1_grt | 1.8 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 16.5 | drt_violations best 2973 last 18181 rows 18 | before-window best 5167, window best 2973 | PROGRESS: drt_violations improved 42.5 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 18.2 | drt_violations best 1719 last 1719 rows 16 | before-window best 5193, window best 1719 | PROGRESS: drt_violations improved 66.9 % in window |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 13.0 | repair_TNS best 2117.14 last 2117.14 rows 6 | before-window best 3315.09, window best 2117.14 | PROGRESS: repair_TNS improved 36.1 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_1_grt | 5.1 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
