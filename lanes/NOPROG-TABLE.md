# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 12:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 2, 'CANCEL-NOW': 2, 'GRT-LABEL': 51, 'NO-DATA': 14, 'YOUNG': 108, 'KEEP': 2, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 21.5 | last meaningful line 19.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 19.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 46.3 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -3266.53 ps (< -300, gate TT >= -42); job age 4 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | dpkit-ot_s81sl_kv_leaf__t4-3639183 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -438.97 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2116565 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.6 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2332029 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.5 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 11.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 13.7 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:22539 -> 10:21664 -> 15:15764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 51.2 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:38895 -> 10:29678 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 7.6 | grt rounds 3 overflow 5:59362 -> 10:66966 -> 15:56502 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 65.6 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3613 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 9.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 10.0 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:40789 -> 10:31945 -> 15:27448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:19437 -> 10:19849 -> 15:17415 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 7.7 | grt rounds 4 overflow 5:2659 -> 10:1890 -> 15:1296 -> 20:1316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:69154 -> 10:65194 -> 15:61747 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:65491 -> 10:65132 -> 15:51654 | GRT-LABEL: DESIGN-FAIL: overflow 65132 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:59610 -> 10:63465 -> 15:54882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:7441 -> 10:5183 -> 15:3941 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:5714 -> 10:3404 -> 15:2649 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:31459 -> 10:23432 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:40043 -> 10:36201 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:24286 -> 10:18853 -> 15:14888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:32869 -> 10:26686 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:10045 -> 10:3860 -> 15:2868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:61754 -> 10:36825 -> 15:33761 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:37003 -> 10:36397 -> 15:29681 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:35763 -> 10:34510 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 44.7 | grt rounds 3 overflow 5:64017 -> 10:65234 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 49.7 | grt rounds 3 overflow 5:60065 -> 10:63105 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 39.1 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 39.1 | grt rounds 3 overflow 5:60910 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 48.8 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42859 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 38.6 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 13.4 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:29534 -> 10:27331 -> 15:30143 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 4.4 | grt rounds 2 overflow 5:63568 -> 10:297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:91555 -> 10:41 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:3567 -> 10:316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 7.9 | grt rounds 8 overflow 15:172 -> 20:100 -> 25:77 -> 30:31 -> 35:4 -> 40:9 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 40: 4 -> 9 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:36431 -> 10:17425 -> 15:8830 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:33424 -> 10:30944 -> 15:23958 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 7.6 | grt rounds 6 overflow 5:2796 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: overflow 1268 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 8.9 | grt rounds 3 overflow 5:61421 -> 10:36554 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:33084 -> 10:3500 -> 15:1699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:33301 -> 10:3457 -> 15:1742 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 7.7 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 7.7 | grt rounds 2 overflow 5:2533 -> 10:1498 | GRT-LABEL: DESIGN-FAIL: overflow 1498 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 7.7 | grt rounds 2 overflow 5:56176 -> 10:51245 | GRT-LABEL: DESIGN-FAIL: overflow 51245 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:43340 -> 10:3595 -> 15:2137 | GRT-LABEL: DESIGN-FAIL: overflow 3595 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:97661 -> 10:93648 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:37205 -> 10:24866 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 5_1_grt | 1.7 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-col-h9-r0-p2--t1--cl9f71e63d--pv11b73b67-grt-103549 | col-h9-r0-p2--t1--cl9f71e63d--pv11b73b67-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | postcts_gate_TT | 8.7 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 5.0 | drt_violations best 53797 last 53797 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 5.0 | repair_Remaining best 58823 last 58823 rows 256 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-3711034 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4694 last 0.4694 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 4.9 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_2_route | 5.6 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 6.0 | last meaningful line 0.3 h ago (196/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 6.2 | last meaningful line 0.0 h ago (581/581 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | postcts_gate_TT | 9.6 | last meaningful line 0.0 h ago (1968/1968 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 13.9 | drt_violations best 10742 last 10742 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 14.0 | drt_violations best 111085 last 111085 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | otc-51041-24654 | 51041 | postcts_gate_TT | 0.0 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_2_route | 2.0 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i2t-3252184 | eco_20261122_144137_2274607-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (229/1797 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_2_route | 3.6 | drt_violations best 5337 last 5337 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | so_3068052_ff_82504 | so_3068052_ff_82504 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc10 | so_3068052_tt_82504 | so_3068052_tt_82504 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | generate_abstract | 7.7 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_2_route | 7.7 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t5-3584924 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (128/128 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t16-3331703 | serdes__t16 | 3_4_place_resized | 1.6 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 14.3 | drt_violations best 132730 last 132730 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 14.3 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 14.3 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 14.3 | drt_violations best 108992 last 108992 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 14.2 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 14.2 | drt_violations best 114889 last 114889 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 14.2 | drt_violations best 136145 last 136145 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 14.2 | drt_violations best 100356 last 100356 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 14.2 | drt_violations best 12572 last 12572 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 14.2 | drt_violations best 4954 last 4954 rows 3 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | otc-2412624-22295 | 2412624 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-2669299-29018 | 2669299 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1-4075679 | eco_20261122_051545_3846533-i1 | 5_2_route | 2.9 | drt_violations best 21611 last 21611 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_2_route | 5.6 | drt_violations best 55788 last 55788 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3061412 | col_h9_r0_p4__t1 | 2_1_floorplan | 0.0 | repair_Viol best 5231 last 5231 rows 624 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-1845665 | dsdv_slice_kv512_C__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8859 last 0.8859 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 5_2_route | 5.5 | drt_violations best 27295 last 27295 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | generate_abstract | 14.3 | last meaningful line 0.1 h ago (184/184 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | eco-abs-2874138 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (606/606 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_qbank_S__fix | 4.6 | last meaningful line 1.3 h ago (562/562 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_qbank_S__fix | 4.6 | last meaningful line 1.3 h ago (562/562 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_qbank_S__fix | 4.6 | last meaningful line 1.3 h ago (562/562 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | so_2547513_ff_34712 | so_2547513_ff_34712 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_2547513_tt_34712 | so_2547513_tt_34712 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p5--t1--pv35382794-grt-4087114 | col-h9-r0-p5--t1--pv35382794-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 4.9 | last meaningful line 1.3 h ago (211/231 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 13.3 | last meaningful line 0.5 h ago (295/296 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 8.3 | drt_violations best 128949 last 128949 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-3684875 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 5.0 | last meaningful line 1.3 h ago (210/214 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_3_place_gp | 7.2 | overflow best 0.0998 last 0.0998 rows 44 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 10.2 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 5_1_grt | 9.6 | repair_Remaining best 242460 last 242460 rows 240 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 5.0 | last meaningful line 0.3 h ago (206/215 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | 5_1_grt | 4.1 | last meaningful line 0.7 h ago (207/213 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | 5_1_grt | 4.4 | last meaningful line 1.3 h ago (208/217 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_2_route | 5.2 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | eco-abs-3630970 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (656/656 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r2--t1--clc9ad8f7e--pv81a5dbf4-grt-1297463 | col-h9-r2--t1--clc9ad8f7e--pv81a5dbf4-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv14626557-grt-1421373 | col-h9-r2--t1--clce45cab5--pv14626557-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t27-grt-1416392 | ot-s81sl-leaf--t27-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t34-grt-1461166 | ot-s81sl-leaf--t34-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t4-dump-1461834 | ot-s81sl-leaf--t4-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t4-grt-1461834 | ot-s81sl-leaf--t4-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-625156 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-175162 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t13-425517 | serdes__t13 | 2_4_floorplan_pdn | 2.6 | last meaningful line 2.0 h ago (130/130 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 14.1 | drt_violations best 140478 last 140478 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 14.2 | drt_violations best 15264 last 15264 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_2_route | 14.7 | drt_violations best 93581 last 93581 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 14.6 | drt_violations best 1 last 1 rows 49 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 14.2 | drt_violations best 7985 last 7985 rows 3 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 5.4 | drt_violations best 97752 last 97752 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_2_route | 2.6 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1t-805483 | eco_20261122_180231_342380-i1t | 5_2_route | 2.4 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r0-p5--t1--pvbca8d846-grt-627697 | col-h9-r0-p5--t1--pvbca8d846-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv7c30fd4e-grt-769771 | col-h9-r2--t1--clce45cab5--pv7c30fd4e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_1_grt | 7.7 | last meaningful line 0.5 h ago (212/217 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_2_route | 5.3 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_2_route | 7.7 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | tt_setup_repair_grt | 6.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 8.0 | last meaningful line 1.8 h ago (210/225 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 7.7 | last meaningful line 1.0 h ago (212/219 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-458411 | col_h9_r0_p4__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 7.7 | drt_violations best 67967 last 67967 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 7.7 | drt_violations best 63708 last 63708 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 4_1_cts | 7.7 | last meaningful line 0.0 h ago (2843/2843 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 4.4 | overflow best 0.6683 last 0.6683 rows 23 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 7.7 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 6.2 | last meaningful line 1.3 h ago (7671/7671 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-1738735 | serdes__t14 | 3_3_place_gp | 1.4 | overflow best 0.8523 last 0.8523 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_2_route | 13.6 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 14.5 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | otc-2017350-30882 | 2017350 | gen_lint_yosys | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 2.7 | last meaningful line 2.6 h ago (3/3 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 4.0 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 7.4 | last meaningful line 0.0 h ago (427/433 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 8.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 5.2 | last meaningful line 0.5 h ago (212/218 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 5.2 | repair_TNS best 1285.83 last 1285.83 rows 11 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 4_1_cts | 3.9 | last meaningful line 0.0 h ago (3060/3060 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.5 h ago (125/125 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 4_1_cts | 3.9 | last meaningful line 0.0 h ago (6278/6278 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | 3_4_place_resized | 3.9 | last meaningful line 0.0 h ago (395/395 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2258805 | hd_turn_a | 5_2_route | 0.5 | last meaningful line 0.0 h ago (222/223 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2278295 | kv3_io_ft | 5_1_grt | 0.5 | repair_Remaining best 171 last 171 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 3_3_place_gp | 1.7 | overflow best 0.0989 last 0.0989 rows 244 | YOUNG: stage 1.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.8 | repair_TNS best 12068.2 last 12068.2 rows 2 | YOUNG: evidence 4.7 h < 6 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.5 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (183/183 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (4502/4502 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (4826/4827 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (4615/4615 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_2_route | 5.2 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (4526/4526 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | strip-n-stride2-3535051 | strip-n-stride2 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__cl774acf45__pvea45273b-2951772 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 |  | KEEP: col_h9_r2__t1__cl774acf45__pvea45273b	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 53.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 14.1 | drt_violations best 4374 last 10441 rows 19 | before-window best 4754, window best 4374 | PROGRESS: drt_violations improved 8.0 % in window |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t42-3564737 | ot_s81sl_leaf__t42 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 17 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 14.0 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 57.7 | last meaningful line 2.1 h ago (1562/1562 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 7.7 | drt_violations best 0 last 0 rows 13 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 5.4 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2637151 | col_h9_r2__t1 | 3_5_place_dp | 0.2 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_1_grt | 7.6 | repair_TNS best 0 last 0 rows 27 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | pregrt_ff_hold | 7.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 8.2 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 13.4 | drt_violations best 2539 last 6430 rows 18 | before-window best 100260, window best 2539 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 9.6 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 23.4 | drt_violations best 43966 last 43966 rows 15 | before-window best 45146, window best 43966 | PROGRESS: drt_violations improved 2.6 % in window |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 14.2 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 13.5 | drt_violations best 3281 last 3281 rows 16 | before-window best 28005, window best 3281 | PROGRESS: drt_violations improved 88.3 % in window |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 15.2 | drt_violations best 2439 last 2439 rows 14 | before-window best 11187, window best 2439 | PROGRESS: drt_violations improved 78.2 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 10.7 | drt_violations best 1 last 30 rows 42 | before-window best 58, window best 1 | PROGRESS: drt_violations improved 98.3 % in window |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_1_grt | 5.6 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 13.0 | last meaningful line 5.2 h ago (233/1712 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2931852 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t30__cl1653104c-3832946 | slice_station__t30 | 5_2_route | 1.7 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
