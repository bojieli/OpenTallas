# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 11:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 2, 'CANCEL-NOW': 2, 'GRT-LABEL': 56, 'NO-DATA': 7, 'YOUNG': 158, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 12.7 | last meaningful line 6.5 h ago (220/1112 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORTED (cancel next pass) |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 20.0 | last meaningful line 18.3 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 18.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | tt_setup_repair | 6.2 | repair_Violations best 864 last 864 rows 71 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -648.07 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | hold_gate | 6.2 | last meaningful line 0.0 h ago (961/961 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -934.23 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2897404 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.4 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2919224 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.4 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 7.2 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 10.4 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 12.2 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:23152 -> 10:21940 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 49.7 | grt rounds 4 overflow 5:108780 -> 10:62187 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:33908 -> 10:27872 -> 15:25694 | GRT-LABEL: DESIGN-FAIL: overflow 27872 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 6.1 | grt rounds 3 overflow 5:60876 -> 10:66966 -> 15:72547 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 64.1 | grt rounds 6 overflow 5:9213 -> 10:5561 -> 15:3613 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 7.9 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:40844 -> 10:31798 -> 15:27448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:19413 -> 10:19610 -> 15:17415 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:9096 -> 10:2439 -> 15:1748 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:2659 -> 10:1890 -> 15:1296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:69154 -> 10:65194 -> 15:61747 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:65491 -> 10:65132 | GRT-LABEL: DESIGN-FAIL: overflow 65132 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:66235 -> 10:63465 | GRT-LABEL: DESIGN-FAIL: overflow 63465 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:29527 -> 10:22456 -> 15:17060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:32004 -> 10:27400 -> 15:23081 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:33831 -> 10:32112 -> 15:29676 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:7687 -> 10:5183 -> 15:4269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:5714 -> 10:3390 -> 15:2649 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:31459 -> 10:24947 -> 15:20235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:39998 -> 10:37170 -> 15:32159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:28701 -> 10:18853 | GRT-LABEL: DESIGN-FAIL: overflow 18853 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:32655 -> 10:26686 -> 15:20666 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:10375 -> 10:3860 -> 15:3468 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:61754 -> 10:36825 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:23007 -> 10:3527 -> 15:1004 | GRT-LABEL: DESIGN-FAIL: overflow 3527 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:37003 -> 10:36397 -> 15:29898 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:35319 -> 10:34931 -> 15:33075 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 43.2 | grt rounds 3 overflow 5:64017 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 48.2 | grt rounds 3 overflow 5:60065 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 37.6 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 37.6 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:58891 -> 10:32145 | GRT-LABEL: DESIGN-FAIL: overflow 32145 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 47.3 | grt rounds 4 overflow 5:78032 -> 10:49634 -> 15:42813 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 37.1 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:58733 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 11.9 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:34248 -> 10:27118 -> 15:30446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:2375 -> 10:1559 | GRT-LABEL: DESIGN-FAIL: overflow 1559 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:9870 -> 10:488 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:36431 -> 10:17425 -> 15:9316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:33647 -> 10:30839 -> 15:23958 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 6.1 | grt rounds 5 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 7.4 | grt rounds 3 overflow 5:62744 -> 10:36554 -> 15:27257 | GRT-LABEL: DESIGN-FAIL: overflow 36554 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:7404 -> 10:123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:8404 -> 10:286 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:46985 -> 10:4215 -> 15:1699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:47106 -> 10:4266 -> 15:1742 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 6.2 | grt rounds 1 overflow 5:2 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 44.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:56176 -> 10:51245 | GRT-LABEL: DESIGN-FAIL: overflow 51245 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:43340 -> 10:3595 | GRT-LABEL: DESIGN-FAIL: overflow 3595 at round 10 > 1000 |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 6.6 | grt rounds 4 overflow 5:8485 -> 10:200 -> 15:22 -> 20:7 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:29741 -> 10:22067 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t44--clf4ea6d4b-grt-380971 | ot-s81sl-leaf--t44--clf4ea6d4b-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t71-grt-420181 | ot-s81sl-leaf--t71-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_2_route | 3.5 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | postcts_gate_FF | 4.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 3.9 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | 3_4_place_resized | 3.9 | last meaningful line 0.0 h ago (403/403 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | 3_5_place_dp | 3.9 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_io_cor_v1-66793 | kv3_io_cor_v1 | 3_1_place_gp_skip_io | 0.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 3.4 | repair_TNS best 207473 last 207473 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 3.4 | repair_TNS best 207751 last 207751 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 4.7 | last meaningful line 0.0 h ago (352/352 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1466438 | sle_hc1 | 3_3_place_gp | 1.3 | overflow best 0.1 last 0.1 rows 232 | YOUNG: stage 1.0 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 12.4 | drt_violations best 92764 last 92764 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t22-4102201 | slice_station__t22 | 3_3_place_gp | 0.3 | overflow best 0.4049 last 0.4049 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_2_route | 12.5 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 12.5 | drt_violations best 119597 last 119597 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc10 | otc-264663-3675 | 264663 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-2891866-5466 | 2891866 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | otc-635730-8421 | 635730 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2-3553043 | eco_20261121_154936_3396612-i2 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (254/426 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1-3804162 | eco_20261122_144137_2274607-i1 | 5_2_route | 1.8 | drt_violations best 4435 last 4435 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc10 | prd-eco_20261122_165114_3352738-i1t-2889585 | eco_20261122_165114_3352738-i1t | 5_2_route | 2.1 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl87f3ff59-3243829 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 6.2 | drt_violations best 60898 last 60898 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 6.2 | drt_violations best 63830 last 63830 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | tt_setup_repair_grt | 6.2 | repair_Viol best 2272 last 2272 rows 60 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-3239393 | ot_s81sl_leaf__t16 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8675 last 0.8675 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3237407 | ot_s81sl_leaf__t26 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.7946 last 0.7994 rows 15 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-serdes__t16-3331703 | serdes__t16 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (319/319 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 12.8 | drt_violations best 132730 last 132730 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_2_route | 12.8 | last meaningful line 0.2 h ago (268/268 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_2_route | 12.8 | last meaningful line 0.0 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_2_route | 12.8 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 6_report | 12.8 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 6_report | 12.7 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_2_route | 12.7 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 12.7 | last meaningful line 0.4 h ago (284/285 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 12.7 | last meaningful line 0.3 h ago (284/285 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_2_route | 12.7 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 12.7 | drt_violations best 95974 last 95974 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 12.7 | drt_violations best 70104 last 70104 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_2_route | 8.0 | drt_violations best 89 last 89 rows 4 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | otc-2588823-17558 | 2588823 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1-4075679 | eco_20261122_051545_3846533-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (134/134 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t10-grt-3743093 | ot-s81sl-leaf--t10-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3366797 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4185 last 0.4185 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_2_route | 4.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (203/209 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 5_2_route | 4.0 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t59-2530517 | ot_s81sl_leaf__t59 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t1__clb45db5be-2593606 | serdes__t1 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t1__clfe1f0815-1376853 | serdes__t1 | 3_3_place_gp | 1.2 | overflow best 0.8323 last 0.8323 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 12.8 | drt_violations best 12789 last 12789 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 12.8 | drt_violations best 99129 last 99129 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | dsfd_node_NNfu__fix | 3.1 | last meaningful line 0.2 h ago (562/562 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | dsfd_node_NNfu__fix | 3.1 | last meaningful line 0.2 h ago (562/562 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | otc-2062410-18700 | 2062410 | dsfd_node_NNfu__fix | 3.1 | last meaningful line 0.2 h ago (562/562 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | dsfd_node_NNfu__fix | 3.1 | last meaningful line 0.2 h ago (562/562 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | otc-3682094-2549 | 3682094 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 4.3 | drt_violations best 47 last 47 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_183009_2671271-i1t-3023419 | eco_20261122_183009_2671271-i1t | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1870118 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.7 | overflow best 0.4146 last 0.4146 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_1_grt | 2.9 | last meaningful line 0.3 h ago (211/216 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | 5_1_grt | 3.4 | last meaningful line 0.5 h ago (210/216 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (161/161 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_2_route | 11.8 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 6.8 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (202/208 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-3684875 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 3_3_place_gp | 5.7 | overflow best 0.5519 last 0.5519 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_2_route | 8.7 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 5_1_grt | 8.1 | repair_Remaining best 296884 last 296884 rows 157 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-3463794 | ot_s81sl_leaf__t14 | 3_3_place_gp | 1.5 | last meaningful line 0.1 h ago (91/91 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | pregrt_ff_hold | 2.6 | repair_Violations best 185 last 233 rows 103 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t57-629868 | ot_s81sl_leaf__t57 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (204/208 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t60-538445 | ot_s81sl_leaf__t60 | 5_1_grt | 2.7 | last meaningful line 0.8 h ago (204/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-320857 | ot_s81sl_leaf__t7 | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t72-157835 | ot_s81sl_leaf__t72 | 3_3_place_gp | 1.2 | overflow best 0.2928 last 0.2928 rows 42 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | 5_1_grt | 2.9 | last meaningful line 0.2 h ago (157/157 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t9-595588 | ot_s81sl_leaf__t9 | 5_1_grt | 2.6 | last meaningful line 0.5 h ago (207/212 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-seqhost__t1-4071746 | seqhost__t1 | 3_3_place_gp | 1.3 | overflow best 0.667 last 0.667 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-serdes__t3-22213 | serdes__t3 | 3_1_place_gp_skip_io | 1.3 | overflow best 0.4549 last 0.4549 rows 38 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-816007 | sle_stm_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | 5_1_grt | 3.7 | last meaningful line 1.5 h ago (215/616 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t51-3956484 | slice_station__t51 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_2_route | 3.5 | drt_violations best 215 last 215 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t17-grt-2371693 | ot-s81sl-leaf--t17-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 8.6 | drt_violations best 1386 last 1389 rows 29 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 6.4 | last meaningful line 2.8 h ago (211/247 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | 3_4_place_resized | 3.8 | last meaningful line 0.0 h ago (408/408 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-eng__t1-2465015 | eng__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2081675 | ot_s81sl_leaf__t32 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3387 last 0.3387 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-1855793 | ot_s81sl_leaf__t54 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t13-425517 | serdes__t13 | 2_4_floorplan_pdn | 1.1 | last meaningful line 0.5 h ago (130/130 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 12.6 | drt_violations best 140478 last 140478 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 12.7 | drt_violations best 107296 last 107296 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_2_route | 13.2 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 13.1 | drt_violations best 98877 last 98877 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 12.7 | drt_violations best 96831 last 96831 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 12.7 | drt_violations best 99319 last 99319 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | otc-758725-2436 | 758725 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-763364-1025 | 763364 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 3.9 | last meaningful line 0.4 h ago (294/295 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_174935_2347281-i1t-460298 | eco_20261122_174935_2347281-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (271/271 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i1t-805483 | eco_20261122_180231_342380-i1t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h10-r0-p1--t1--cl911743eb-grt-1245702 | col-h10-r0-p1--t1--cl911743eb-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t53--cl958451dd-grt-1217111 | ot-s81sl-leaf--t53--cl958451dd-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-720288 | col_h10_r1__t1 | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | 5_1_grt | 4.2 | last meaningful line 0.1 h ago (203/205 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (259/259 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 6.5 | last meaningful line 0.3 h ago (210/213 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-998561 | col_h9_r0_p5__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 3_5_place_dp | 6.2 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 3_5_place_dp | 6.2 | last meaningful line 0.1 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 4_1_cts | 6.2 | last meaningful line 0.1 h ago (3699/3699 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.9 | last meaningful line 1.2 h ago (143/143 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 4.7 | last meaningful line 0.3 h ago (7504/7504 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-2473787 | ot_s81sl_leaf__t2 | 3_5_place_dp | 1.3 | last meaningful line 0.1 h ago (121/121 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | tt_setup_repair_grt | 5.9 | repair_Viol best 2963 last 2963 rows 11 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-serdes__t2-2411650 | serdes__t2 | 3_3_place_gp | 1.3 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | postcts_gate_FF | 12.1 | last meaningful line 0.1 h ago (935/935 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_2_route | 13.0 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-1539886-21873 | 1539886 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2835423-3110 | 2835423 | signoff | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1-4088168 | eco_20261121_175441_3776558-i1 | 5_2_route | 2.5 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 5.9 | last meaningful line 0.3 h ago (205/212 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | 5_1_grt | 3.7 | last meaningful line 0.5 h ago (210/216 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | 5_1_grt | 3.7 | last meaningful line 0.3 h ago (203/210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | 5_1_grt | 3.7 | repair_TNS best 8596.42 last 8596.42 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | 5_1_grt | 4.1 | repair_Remaining best 14785 last 14785 rows 103 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-coll_ftm-3606558 | coll_ftm | 5_2_route | 2.2 | last meaningful line 0.2 h ago (241/242 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | selrange | 2.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | 3_3_place_gp | 4.2 | overflow best 0.6543 last 0.6543 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-2890860 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 11.5 | last meaningful line 3.7 h ago (233/1712 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 2.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | selrange | 2.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-hd_turn_a-2918538 | hd_turn_a | 5_2_route | 0.4 | drt_violations best 3137 last 3137 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2925591 | hd_turn_a | 5_2_route | 0.4 | last meaningful line 0.0 h ago (210/211 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-native59-3804419 | native59 | 2_1_floorplan | 0.2 | repair_Viol best 18801 last 18801 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t3-2931852 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 0.4 | repair_TNS best 449417 last 449417 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t4-3639183 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 2.2 | repair_TNS best 266780 last 266780 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 8.3 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.0 | repair_Remaining best 163583 last 163583 rows 192 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t36-3841308 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 0.2 | repair_TNS best 481561 last 481561 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | 5_1_grt | 3.7 | last meaningful line 1.0 h ago (205/211 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t47-3810313 | ot_s81sl_leaf__t47 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.6532 last 0.6532 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | 5_1_grt | 3.7 | last meaningful line 1.0 h ago (209/218 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | 5_1_grt | 3.7 | last meaningful line 1.3 h ago (206/214 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t67-3712715 | ot_s81sl_leaf__t67 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3858063 | sle_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6045/6045 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3651324 | slice_station__t12 | 5_1_grt | 0.3 | repair_Remaining best 8223 last 8223 rows 6 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3809395 | slice_station__t24 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.3173 last 0.3173 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-slice_station__t30__cl1653104c-3832946 | slice_station__t30 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | 5_1_grt | 3.7 | last meaningful line 1.2 h ago (208/693 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 3_3_place_gp | 0.3 | overflow best 0.383 last 0.383 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | otc-2746791-17160 | 2746791 | asbuilt.yosys | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 51.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | 5_1_grt | 3.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | tt_setup_repair_grt | 3.4 | repair_Violations best 0 last 0 rows 16 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 12.6 | drt_violations best 4374 last 10441 rows 19 | before-window best 5657, window best 4374 | PROGRESS: drt_violations improved 22.7 % in window |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 8.1 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 12.4 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 56.2 | last meaningful line 0.6 h ago (1562/1562 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 5_1_grt | 4.2 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | 5_1_grt | 3.9 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | 5_1_grt | 3.9 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | 5_1_grt | 3.7 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | pregrt_ff_hold | 6.1 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 22.6 | drt_violations best 48926 last 48926 rows 16 | before-window best 51519, window best 48926 | PROGRESS: drt_violations improved 5.0 % in window |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 7.1 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 11.9 | drt_violations best 3038 last 3038 rows 16 | before-window best 100260, window best 3038 | PROGRESS: drt_violations improved 97.0 % in window |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 8.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 21.9 | drt_violations best 43966 last 43966 rows 15 | before-window best 45146, window best 43966 | PROGRESS: drt_violations improved 2.6 % in window |  |
| epyc9 | prd-eco-i2-1586484 | eco-i2 | 5_1_grt | 0.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 11.5 | drt_violations best 647 last 647 rows 15 | before-window best 10290, window best 647 | PROGRESS: drt_violations improved 93.7 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-41241 | col_h9_r1__t1 | 3_5_place_dp | 0.6 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-coll_core-180674 | coll_core | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 12.0 | drt_violations best 4012 last 4012 rows 14 | before-window best 87099, window best 4012 | PROGRESS: drt_violations improved 95.4 % in window |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 13.7 | drt_violations best 3242 last 3242 rows 13 | before-window best 12000, window best 3242 | PROGRESS: drt_violations improved 73.0 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 9.2 | drt_violations best 1 last 30 rows 42 | before-window best 554, window best 1 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
