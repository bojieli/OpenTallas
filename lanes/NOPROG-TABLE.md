# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 15:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 2, 'GRT-LABEL': 44, 'NO-DATA': 10, 'YOUNG': 123, 'KEEP': 2, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 17.1 | drt_violations best 4374 last 6676 rows 22 | before-window best 4374, window best 6676 | NO-PROGRESS: drt_violations best 6676 vs 4374 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-HROOT-R1 decides |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 24.5 | last meaningful line 21.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 21.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 10.7 | grt rounds 1 overflow 5:2 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -443.22 ps (< -300, gate TT >= -42); job age 10 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 16.0 | last meaningful line 8.2 h ago (233/1712 lines) | NO-PROGRESS: no new non-iteration log line for 8.2 h | REPORT-ONLY: lane-own kit (FAM-S81-LEPE-4 decides; |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 6.9 | last meaningful line 0.0 h ago (1451/1451 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -811.77 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 14.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 54.2 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49076 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:29001 -> 10:26780 -> 15:24876 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 68.6 | grt rounds 6 overflow 5:9414 -> 10:5163 -> 15:3613 -> 20:3104 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-3487466-21488 | 3487466 | 5_1_grt | 1.6 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:59446 -> 10:64367 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-3648688 | ot_s81sl_leaf__t34 | 5_1_grt | 0.8 | grt rounds 4 overflow 5:48483 -> 10:32112 -> 15:29676 -> 20:28101 | GRT-LABEL: DESIGN-FAIL: overflow 32112 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:7392 -> 10:5019 -> 15:3621 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 10.7 | grt rounds 4 overflow 5:5714 -> 10:3404 -> 15:2651 -> 20:2469 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:32368 -> 10:23713 -> 15:20435 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:24072 -> 10:16574 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:32852 -> 10:27052 -> 15:20655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:56686 -> 10:35827 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 0.2 | grt rounds 3 overflow 5:37003 -> 10:36397 -> 15:29681 | GRT-LABEL: DESIGN-FAIL: overflow 36397 at round 10 > 1000 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.8 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 47.7 | grt rounds 3 overflow 5:65447 -> 10:66805 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 52.7 | grt rounds 3 overflow 5:61609 -> 10:62172 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 42.1 | grt rounds 4 overflow 5:58312 -> 10:48607 -> 15:39545 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 42.1 | grt rounds 3 overflow 5:60910 -> 10:48673 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 51.8 | grt rounds 4 overflow 5:77624 -> 10:49634 -> 15:42859 -> 20:43935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 41.6 | grt rounds 4 overflow 5:114153 -> 10:70115 -> 15:50222 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 16.4 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 5_1_grt | 10.4 | grt rounds 2 overflow 5:40547 -> 10:32257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-994857 | slw_st_a_v2 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:21080 -> 10:15696 | GRT-LABEL: DESIGN-FAIL: overflow 15696 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:2457 -> 10:480 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:35677 -> 10:16162 -> 15:8042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 10.7 | grt rounds 4 overflow 5:33424 -> 10:30944 -> 15:23760 -> 20:20154 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 10.6 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 11.9 | grt rounds 3 overflow 5:63320 -> 10:33517 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 10.7 | grt rounds 4 overflow 5:33084 -> 10:3323 -> 15:1561 -> 20:909 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 10.7 | grt rounds 4 overflow 5:33301 -> 10:3290 -> 15:1523 -> 20:1038 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 10.7 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:55088 -> 10:51245 -> 15:48252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 10.7 | grt rounds 3 overflow 5:22842 -> 10:2857 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:83696 -> 10:70 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 4.7 | grt rounds 3 overflow 5:7803 -> 10:738 -> 15:476 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:21814 -> 10:20459 | GRT-LABEL: DESIGN-FAIL: overflow 20459 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t50-617275 | ot_s81sl_leaf__t50 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:26237 -> 10:3589 | GRT-LABEL: DESIGN-FAIL: overflow 3589 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
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
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-679902 | col_h10_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.2547 last 0.2547 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-679412 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.5645 last 0.5645 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-3109130 | dsdv_slice_c1x_C__t1 | 3_5_place_dp | 2.9 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-3659100 | dsdv_slice_c1x_C__t10 | selrange | 0.8 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-683007 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t23-694414 | ot_s81sl_leaf__t23 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-687429 | ot_s81sl_leaf__t54 | 3_3_place_gp | 0.2 | overflow best 0.5991 last 0.6197 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | pregrt_ff_hold | 0.8 | repair_TNS best 754066 last 754066 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-686262 | ot_s81sl_leaf__t7 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t71-691089 | ot_s81sl_leaf__t71 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t73-3636691 | ot_s81sl_leaf__t73 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-seqhost__t1-686556 | seqhost__t1 | 2_1_floorplan | 0.2 | repair_Viol best 2319 last 2319 rows 1280 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | generate_abstract | 17.3 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 17.3 | drt_violations best 23813 last 23813 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | generate_abstract | 17.3 | last meaningful line 0.1 h ago (1023/1023 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 17.2 | drt_violations best 11311 last 11311 rows 3 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | generate_abstract | 17.2 | last meaningful line 0.3 h ago (555/555 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-691946 | slw_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.2053 last 0.2053 rows 38 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | otc-1094939-10134 | 1094939 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2738927-2977 | 2738927 | signoff | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 2.8 | drt_violations best 7433 last 7433 rows 3 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_140001_4005935-i1-2236985 | eco_20261122_140001_4005935-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_retry_1795389734917048336-i1t-961404 | eco_retry_1795389734917048336-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_80751_ff_18750 | so_80751_ff_18750 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | so_80751_tt_18750 | so_80751_tt_18750 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t39-grt-1096648 | ot-s81sl-leaf--t39-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 | col_h9_r0_p6__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 29643.1 last 29643.1 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-1077307 | col_h9_r2__t1 | 5_1_grt | 2.2 | repair_Remaining best 15624 last 15624 rows 100 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 111710 last 111710 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t10-853751 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 2.3 | overflow best 0.7253 last 0.7259 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t9-4106886 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_C__t1-4102769 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (2829/2829 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t29-3865255 | ot_s81sl_leaf__t29 | pregrt_ff_hold | 0.8 | repair_TNS best 5435.06 last 5435.06 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t46-3967105 | ot_s81sl_leaf__t46 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4501/4501 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t55-3844958 | ot_s81sl_leaf__t55 | pregrt_ff_hold | 0.8 | repair_TNS best 74500.7 last 74500.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t61-3925881 | ot_s81sl_leaf__t61 | tt_setup_repair | 0.8 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 10.6 | last meaningful line 0.0 h ago (270/270 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t26-1831819 | slice_station__t26 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (6059/6059 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | otc-1004368-22302 | 1004368 | signoff | 2.2 | last meaningful line 2.1 h ago (3/3 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | otc-339337-27149 | 339337 | signoff | 2.5 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_215654_330309-i1t-2527780 | eco_20261122_215654_330309-i1t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i1t-2658286 | eco_20261122_220050_168828-i1t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_2_route | 7.9 | last meaningful line 0.1 h ago (290/291 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_2_route | 7.3 | drt_violations best 63616 last 63616 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t4-3857153 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 8.0 | last meaningful line 4.3 h ago (210/219 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_4_place_resized | 10.2 | last meaningful line 1.0 h ago (449/449 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 6_report | 13.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 12.6 | last meaningful line 0.3 h ago (1234/1240 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t21-3954640 | ot_s81sl_leaf__t21 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3845641 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.3068 last 0.3356 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t21-3827757 | slice_station__t21 | 3_2_place_iop | 0.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t29__cl2e5c855a-3939444 | slice_station__t29 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2276/2276 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 8.2 | drt_violations best 31724 last 31724 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-3952570 | slice_station__t40 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2854/2855 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco-i2r-1852378 | eco-i2r | 5_2_route | 2.4 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | postcts_gate_TT | 10.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t3-2895025 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 2.4 | overflow best 0.6498 last 0.6498 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-566156 | dsdv_slice_iq_C__t1 | 3_4_place_resized | 1.6 | repair_Remaining best 367849 last 367849 rows 47 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_io_cor_v1-565709 | kv3_io_cor_v1 | postcts_gate_TT | 1.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t58-670966 | ot_s81sl_leaf__t58 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (190/203 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | pregrt_ff_hold | 1.6 | repair_Violations best 619 last 619 rows 59 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | generate_abstract | 17.1 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (4015/4015 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t8-568577 | slice_station__t8 | tt_setup_repair_grt | 1.6 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1206087-22764 | 1206087 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | otc-2867161-32206 | 2867161 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-643573-21558 | 643573 | signoff | 1.5 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 3.3 | drt_violations best 15272 last 15272 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1-1472150 | eco_20261122_174935_2347281-i1 | 5_2_route | 1.1 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1-577405 | eco_20261122_180231_342380-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1t-231218 | eco_20261122_214447_3988541-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_223653_314236-i1-2039775 | eco_20261122_223653_314236-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-fin-1586484 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
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
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 54510.5 last 54510.5 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_2_route | 10.4 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 11.1 | last meaningful line 0.2 h ago (290/291 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_2_route | 8.6 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-587373 | coll_ftm | 5_2_route | 2.6 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 6.9 | last meaningful line 1.3 h ago (208/212 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 4.9 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.6 | last meaningful line 0.5 h ago (198/208 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 4.7 | repair_TNS best 10405.5 last 10405.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 10.5 | last meaningful line 3.8 h ago (241/341 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (209/215 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 2.6 | last meaningful line 0.5 h ago (202/208 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 5_1_grt | 4.8 | last meaningful line 2.0 h ago (208/216 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 8.2 | drt_violations best 48586 last 48586 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_1067443_ff_69298 | so_1067443_ff_69298 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_1067443_tt_69298 | so_1067443_tt_69298 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h9_r2__t1__cl774acf45__pvea45273b-3781481 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 |  | KEEP: col_h9_r2__t1__cl774acf45__pvea45273b	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | prd-eco_20261120_150342_478824-i1-1690412 | eco_20261120_150342_478824-i1 | 5_2_route | 1.0 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 9.2 | last meaningful line 0.0 h ago (986/986 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 60.7 | last meaningful line 2.4 h ago (1564/1564 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 17.2 | drt_violations best 825 last 825 rows 4 | before-window best 136145, window best 825 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 7.6 | last meaningful line 4.3 h ago (562/562 lines) | PROGRESS: log still growing |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 7.6 | last meaningful line 4.3 h ago (562/562 lines) | PROGRESS: log still growing |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 7.6 | last meaningful line 4.3 h ago (562/562 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 16.3 | drt_violations best 19658 last 19658 rows 3 | before-window best 161798, window best 19658 | PROGRESS: drt_violations improved 87.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 11.3 | drt_violations best 18867 last 18867 rows 8 | before-window best 128949, window best 18867 | PROGRESS: drt_violations improved 85.4 % in window |  |
| epyc8 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-3921644 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-682008 | col_h9_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-567543 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t42__cl4bd1432c-568478 | slice_station__t42 | 5_1_grt | 1.6 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_1_grt | 1.6 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 16.5 | drt_violations best 2973 last 18181 rows 18 | before-window best 5167, window best 2973 | PROGRESS: drt_violations improved 42.5 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 18.2 | drt_violations best 1719 last 1719 rows 16 | before-window best 5193, window best 1719 | PROGRESS: drt_violations improved 66.9 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 12.8 | repair_TNS best 2836.89 last 2836.89 rows 3 | before-window best 3315.09, window best 2836.89 | PROGRESS: repair_TNS improved 14.4 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
