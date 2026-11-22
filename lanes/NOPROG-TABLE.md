# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 08:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 2, 'CANCEL-NOW': 2, 'GRT-LABEL': 42, 'NO-DATA': 13, 'YOUNG': 199, 'EXCLUDED': 4, 'KEEP': 1, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 17.7 | last meaningful line 16.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 16.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 59.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2322.47 ps (< -300, gate TT >= -42); job age 5 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | tt_setup_repair | 3.7 | repair_Violations best 0 last 0 rows 2 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -878.16 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2642185 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 3_5_place_dp | 0.1 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2586170 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 1_2_yosys | 0.1 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:5540 -> 10:4894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 5_1_grt | 8.2 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 10.0 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:22677 -> 10:22390 -> 15:16425 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 47.4 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:50092 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:61583 -> 10:70130 | GRT-LABEL: DESIGN-FAIL: overflow 70130 at round 10 > 1000 |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 61.8 | grt rounds 6 overflow 5:9213 -> 10:5212 -> 15:3426 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-1420229-24210 | 1420229 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-616218-14777 | 616218 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:13586 -> 10:2066 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | 5_1_grt | 4.0 | grt rounds 6 overflow 5:5968 -> 10:452 -> 15:57 -> 20:13 -> 25:5 -> 30:1 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 5_1_grt | 4.0 | grt rounds 2 overflow 5:51765 -> 10:37996 | GRT-LABEL: DESIGN-FAIL: overflow 37996 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:21001 -> 10:20178 | GRT-LABEL: DESIGN-FAIL: overflow 20178 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:9096 -> 10:2889 -> 15:1834 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:3611 -> 10:2062 | GRT-LABEL: DESIGN-FAIL: overflow 2062 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:66243 -> 10:59241 -> 15:60682 | GRT-LABEL: DESIGN-FAIL: overflow 59241 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:29978 -> 10:24305 -> 15:17060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:32004 -> 10:27892 -> 15:23179 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:50237 -> 10:35490 -> 15:30362 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:7927 -> 10:6080 -> 15:4269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:7755 -> 10:3584 | GRT-LABEL: DESIGN-FAIL: overflow 3584 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:36793 -> 10:24947 | GRT-LABEL: DESIGN-FAIL: overflow 24947 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:43402 -> 10:37170 | GRT-LABEL: DESIGN-FAIL: overflow 37170 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:36220 -> 10:27751 | GRT-LABEL: DESIGN-FAIL: overflow 27751 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:14948 -> 10:4450 -> 15:3468 | GRT-LABEL: DESIGN-FAIL: overflow 4450 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:61754 -> 10:36825 | GRT-LABEL: DESIGN-FAIL: overflow 36825 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:38276 -> 10:36558 -> 15:29898 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:49663 -> 10:35602 | GRT-LABEL: DESIGN-FAIL: overflow 35602 at round 10 > 1000 |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 41.0 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 45.9 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 35.3 | grt rounds 4 overflow 5:55819 -> 10:48607 -> 15:39545 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 35.3 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39533 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 45.1 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42813 -> 20:43925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 34.8 | grt rounds 4 overflow 5:108343 -> 10:70617 -> 15:50597 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 9.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:83933 -> 10:43 -> 15:18 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:36049 -> 10:19657 -> 15:9316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:35993 -> 10:32273 | GRT-LABEL: DESIGN-FAIL: overflow 32273 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:1893 -> 10:1155 -> 15:762 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:63744 -> 10:38442 | GRT-LABEL: DESIGN-FAIL: overflow 38442 at round 10 > 1000 |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | 5_1_grt | 4.9 | grt rounds 2 overflow 5:62744 -> 10:36554 | GRT-LABEL: DESIGN-FAIL: overflow 36554 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 42.3 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t47-grt-2323183 | ot-s81sl-leaf--t47-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-4139317 | col_h10_r2__t1 | 5_1_grt | 1.3 | repair_Remaining best 18838 last 18838 rows 90 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-23882 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 60498 last 60498 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_1_grt | 1.2 | last meaningful line 0.2 h ago (265/1270 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r2__t1__cl87f3ff59-3083567 | col_h9_r2__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_C__t1-3550591 | dsdv_slice_lepe_mu_C__t1 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3520921 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-3435353 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.7 | last meaningful line 0.5 h ago (131/131 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (3697/3697 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (3779/3779 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-1491393 | kv3_sys_c | 3_3_place_gp | 0.5 | overflow best 0.6624 last 0.6624 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.5 | last meaningful line 0.0 h ago (290/290 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 5_1_grt | 3.9 | last meaningful line 0.8 h ago (204/211 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-1760524 | sle_fw_v2 | 3_3_place_gp | 0.4 | overflow best 0.3911 last 0.3968 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve289215f-1673529 | sle_hc1 | 3_3_place_gp | 0.4 | overflow best 0.6461 last 0.6461 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1996870 | sle_st_a_v2 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_2_route | 10.1 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl55be2264-1917377 | sle_stm_v2 | 3_3_place_gp | 0.3 | overflow best 0.1291 last 0.1291 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1757602 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.524 last 0.524 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | postcts_gate_FF | 10.3 | last meaningful line 0.2 h ago (1628/1628 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2005514 | slw_fw_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9988 last 0.9988 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_2_route | 10.2 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_2_route | 10.2 | drt_violations best 88765 last 88765 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | so_1970332_ff_15535 | so_1970332_ff_15535 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc10 | so_1970332_tt_15535 | so_1970332_tt_15535 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | ap-ageom-kw-sle-fw-v1--clf58b4dfb-grt-2041401 | sle-fw-v1--clf58b4dfb-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 5_1_grt | 3.9 | last meaningful line 1.3 h ago (202/210 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 5_1_grt | 3.9 | last meaningful line 0.1 h ago (201/204 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 5_1_grt | 3.9 | last meaningful line 1.3 h ago (204/219 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 3.9 | last meaningful line 1.3 h ago (207/216 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 5_1_grt | 3.9 | last meaningful line 0.5 h ago (204/210 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 5_1_grt | 3.9 | last meaningful line 0.8 h ago (202/210 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 5_1_grt | 3.9 | last meaningful line 0.5 h ago (209/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | postcts_gate_TT | 10.5 | last meaningful line 0.1 h ago (1869/1869 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | postcts_gate_TT | 10.5 | last meaningful line 0.1 h ago (836/836 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | postcts_gate_FF | 10.5 | last meaningful line 0.0 h ago (825/825 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 10.5 | drt_violations best 78672 last 78672 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 10.5 | drt_violations best 77889 last 77889 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (895/895 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | postcts_gate_TT | 10.5 | last meaningful line 0.1 h ago (1840/1840 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_2_route | 10.5 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 10.5 | repair_TNS best 45225.6 last 45225.6 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_2_route | 10.5 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | postcts_gate_FF | 10.5 | last meaningful line 0.0 h ago (394/394 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_2_route | 10.5 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_2_route | 10.5 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_2_route | 3.5 | drt_violations best 4195 last 4195 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h9-r2--t1--clc9ad8f7e--pvcf44b14c-grt-3419127 | col-h9-r2--t1--clc9ad8f7e--pvcf44b14c-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv7a260fc0-grt-3356398 | col-h9-r2--t1--clce45cab5--pv7a260fc0-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-30918 | col_h10_r0_p4__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-452106 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 56787.8 last 56787.8 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-456345 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 55220.5 last 55220.5 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-170392 | col_h10_r2__t1 | 5_1_grt | 1.8 | grt_overflow best 297 last 297 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1106130 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 61395.6 last 61395.6 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-801709 | col_h9_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 84209.8 last 84209.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-coll_core-1737007 | coll_core | 3_3_place_gp | 1.0 | overflow best 0.1224 last 0.1224 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.0 | repair_TNS best 228722 last 228722 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-native59-1738201 | native59 | 3_3_place_gp | 1.0 | overflow best 0.3146 last 0.3146 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t33-1238552 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 1.2 | repair_TNS best 116279 last 116279 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 5_1_grt | 3.9 | last meaningful line 0.5 h ago (208/216 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 4_1_cts | 3.9 | last meaningful line 0.1 h ago (7028/7028 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 4_1_cts | 3.9 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 3.6 | last meaningful line 0.1 h ago (9089/9089 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl69f5e854-2551268 | sle_fw_v2 | 3_3_place_gp | 0.6 | overflow best 0.3917 last 0.3992 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_2_route | 10.5 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1631153 | sle_hc1 | 3_3_place_gp | 1.1 | overflow best 0.2982 last 0.4127 rows 108 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3286829 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.54 last 0.54 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_2_route | 4.7 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-1706410 | slw_fw_v3 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (354/354 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 6_report | 10.5 | last meaningful line 0.2 h ago (1073/1073 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-3093007 | slw_st_a_v2 | 3_3_place_gp | 0.3 | overflow best 0.417 last 0.417 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | otc-1986186-11442 | 1986186 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 0.9 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2015840-20581 | 2015840 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 0.9 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2052962-2847 | 2052962 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 0.9 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2062410-18700 | 2062410 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 0.8 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2088375-5834 | 2088375 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 0.8 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2871649-16919 | 2871649 | ot_hdc_v41x_attn_tr_x_xoff0__fix | 0.4 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_142924_3969577-i1-4027915 | eco_20261122_142924_3969577-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (261/261 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-fin-3246240 | fin | 6_report | 0.6 | last meaningful line 0.2 h ago (736/736 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-col-h10-r1--t1--cl95b37463--pv0713a75a-grt-1328502 | col-h10-r1--t1--cl95b37463--pv0713a75a-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h10-r2--t1--cl1f5d6c2a--pv418d3dc0-grt-1223187 | col-h10-r2--t1--cl1f5d6c2a--pv418d3dc0-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv06a1adf6-grt-1344801 | col-h9-r2--t1--clce45cab5--pv06a1adf6-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 55553.4 last 55553.4 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2547565 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 151547 last 151547 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2363969 | col_h10_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 102659 last 102659 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl8b686b3e-2479015 | col_h10_r2__t1 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3108937 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 93931.6 last 93931.6 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 5_1_grt | 4.4 | last meaningful line 1.8 h ago (209/236 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 96178 last 96178 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 9.7 | drt_violations best 3629 last 3629 rows 12 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-272822 | col_h9_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 67926.7 last 67926.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-2773276 | dsdv_slice_kv512_C__t1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3437/3437 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | 3_4_place_resized | 3.8 | last meaningful line 0.0 h ago (414/414 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_4_floorplan_pdn | 3.5 | last meaningful line 0.2 h ago (175/175 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-2790301 | ot_s81sl_kv_leaf__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 210434 last 210434 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-636353 | ot_s81sl_leaf__t28 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t57-629868 | ot_s81sl_leaf__t57 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3596/3596 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t60-538445 | ot_s81sl_leaf__t60 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3951/3951 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t73-3375193 | ot_s81sl_leaf__t73 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t75-4095800 | ot_s81sl_leaf__t75 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5397/5398 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t9-595588 | ot_s81sl_leaf__t9 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4078/4079 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-2581726 | slice_station__t37 | pregrt_ff_hold | 1.4 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2657484-2996 | 2657484 | gen_lint_yosys | 1.4 | last meaningful line 0.2 h ago (7/7 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco-i2-2877912 | eco-i2 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (262/262 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-kv-leaf--t3-grt-2489197 | ot-s81sl-kv-leaf--t3-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 8.6 | drt_violations best 10018 last 10018 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_2_route | 6.4 | drt_violations best 60755 last 60755 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_1_grt | 4.1 | last meaningful line 0.5 h ago (211/220 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-31383 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-87338 | hd_ctl | 5_2_route | 1.5 | drt_violations best 50275 last 50275 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | tt_setup_repair_grt | 4.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_2_route | 10.4 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_2_route | 10.4 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | postcts_gate_FF | 11.0 | last meaningful line 0.0 h ago (1022/1022 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_2_route | 10.8 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_2_route | 10.4 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_2_route | 10.4 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | eco-abs-2213072 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.2 h ago (509/509 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-4183895-10969 | 4183895 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-3675346 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (353/353 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4032381 | eco-i1t | 5_2_route | 1.7 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv09b9967e-grt-3873521 | col-h9-r2--t1--clce45cab5--pv09b9967e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-slice-station--t52-grt-3883299 | slice-station--t52-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.7 | repair_TNS best 67815.3 last 67815.3 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-673167 | col_h10_r1__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 69202.3 last 69202.3 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1518600 | col_h10_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 48166.6 last 48166.6 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | 5_1_grt | 3.7 | last meaningful line 1.3 h ago (201/228 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3831187 | col_h10_r2__t1 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1497604 | col_h9_r0_p3__t1 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (206/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1398169 | col_h9_r0_p5__t1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (98/98 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (547/576 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (7165/7165 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | 1_2_yosys | 3.7 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | 4_1_cts | 3.7 | last meaningful line 0.1 h ago (41/41 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | 4_1_cts | 3.7 | last meaningful line 0.2 h ago (40/40 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | 1_2_yosys | 3.7 | last meaningful line 0.0 h ago (229/229 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | 1_2_yosys | 3.7 | last meaningful line 0.0 h ago (288/288 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 3_5_place_dp | 3.7 | last meaningful line 0.2 h ago (37/37 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-158068 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 2.0 | overflow best 0.6369 last 0.6369 rows 24 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 3.7 | last meaningful line 0.1 h ago (87/87 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 3.7 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3222027 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-eng__t1-1558999 | eng__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (191/192 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 4_1_cts | 3.7 | last meaningful line -0.0 h ago (1606/1606 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 9.5 | drt_violations best 7967 last 7967 rows 9 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (7410/7411 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 4_1_cts | 3.7 | last meaningful line 0.0 h ago (3230/3230 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (207/209 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t24__cl2456157b-1317854 | ot_s81sl_leaf__t24 | 3_5_place_dp | 1.4 | last meaningful line 0.3 h ago (39/39 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (205/208 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t51-2973305 | ot_s81sl_leaf__t51 | 3_3_place_gp | 0.5 | last meaningful line 0.1 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | 5_1_grt | 3.3 | last meaningful line 0.2 h ago (1293/1893 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 5_1_grt | 3.4 | last meaningful line 0.2 h ago (235/809 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-3149151 | sle_ctl | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6932 last 0.6932 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3682021 | sle_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.1 h ago (397/397 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 9.6 | last meaningful line 0.2 h ago (1236/1289 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-2719308 | sle_su_c | 3_1_place_gp_skip_io | 0.7 | overflow best 0.2161 last 0.2161 rows 38 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2461538 | slw_hc0 | 3_3_place_gp | 0.8 | overflow best 0.2071 last 0.2071 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 10.8 | drt_violations best 3110 last 3110 rows 3 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | postcts_gate_TT | 10.5 | last meaningful line 0.2 h ago (574/574 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-2993623 | tt_ctlm | 3_3_place_gp | 0.5 | overflow best 0.206 last 0.206 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-2656503-353 | 2656503 | ot_s81sl_xrt1__fix | 0.7 | last meaningful line 0.0 h ago (1221/1221 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-3700530-25757 | 3700530 | j6ctl_rom_elem_q_hw__fix | 0.1 | last meaningful line 0.0 h ago (496/496 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 5_1_grt | 3.6 | last meaningful line 1.0 h ago (203/218 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_1_grt | 4.4 | last meaningful line 0.2 h ago (254/297 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4019157 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 49104 last 49104 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4037811 | col_h9_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 63390.8 last 63390.8 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-2701642 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3089137 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 111710 last 111710 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c3x_C__t1-2922221 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_kv512_C__t1-524813 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.9 | last meaningful line 0.1 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3157882 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.9 | repair_TNS best 102526 last 102526 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 9.3 | last meaningful line 1.5 h ago (233/1622 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepw_mu_C__t1-2639659 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-glue-813028 | glue | 3_4_place_resized | 1.0 | last meaningful line 0.1 h ago (276/276 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-gunit__t1-533357 | gunit__t1 | 3_5_place_dp | 2.9 | last meaningful line 2.3 h ago (40/40 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2735473 | hd_turn_a | 3_3_place_gp | 0.1 | overflow best 0.1081 last 0.1081 rows 43 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2744267 | hd_turn_a | 3_3_place_gp | 0.1 | overflow best 0.4096 last 0.4387 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2585034 | kv3_io_ft | 3_3_place_gp | 0.1 | overflow best 0.1137 last 0.1153 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v3-1286721 | kv3_pc_v3 | 3_3_place_gp | 0.8 | overflow best 0.2624 last 0.2624 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.0 | repair_Remaining best 354583 last 354583 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-77059 | ot_s81sl_kv_leaf__t5 | 3_4_place_resized | 1.4 | repair_Remaining best 66679 last 66679 rows 199 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t16-961104 | ot_s81sl_leaf__t16 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t23-1069009 | ot_s81sl_leaf__t23 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t43-4042269 | ot_s81sl_leaf__t43 | tt_setup_repair | 1.5 | repair_Violations best 791 last 791 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t55-4191294 | ot_s81sl_leaf__t55 | pregrt_ff_hold | 1.4 | repair_TNS best 4883.12 last 4883.12 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t56-4102003 | ot_s81sl_leaf__t56 | tt_setup_repair | 1.5 | repair_Viol best 27 last 27 rows 17 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-4105280 | ot_s81sl_leaf__t66 | pregrt_ff_hold | 1.5 | repair_TNS best 76138.4 last 76138.4 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-2733013 | sle_fw_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-691417 | sle_hc0 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-1751047 | sle_stm_v2 | 3_3_place_gp | 0.6 | overflow best 0.0988 last 0.0988 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slice_station__t51-4067255 | slice_station__t51 | pregrt_ff_hold | 1.5 | repair_TNS best 181264 last 181264 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_fe_v2__clf110fab2-850187 | slw_fe_v2 | 3_4_place_resized | 1.0 | repair_Remaining best 310000 last 310000 rows 33 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-2734287 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (342/342 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_stm_v2__cl9beb65e6-770558 | slw_stm_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | fable-lep0n-sta-2575625 | fable-lep0n-sta | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | heuristic_proskuriakova | heuristic_proskuriakova | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-1734334-4594 | 1734334 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261122_054330_1688646-i1-206630 | eco_20261122_054330_1688646-i1 | 5_2_route | 1.3 | drt_violations best 3 last 3 rows 11 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | otc-1323501-20824 | 1323501 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-1355044-5800 | 1355044 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-743095-21290 | 743095 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-1701663-21848 | 1701663 | asbuilt.yosys | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 49.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3069799 | col_h10_r1__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-2171053 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 8.5 | drt_violations best 28 last 30 rows 55 | before-window best 55, window best 28 | PROGRESS: drt_violations improved 49.1 % in window |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 10.3 | drt_violations best 4374 last 20511 rows 18 | before-window best 86318, window best 4374 | PROGRESS: drt_violations improved 94.9 % in window |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 5_1_grt | 5.8 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 8.9 | drt_violations best 16 last 26 rows 21 | before-window best 144464, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc10 | prd-eco_20261122_144137_2274607-i1t-2778713 | eco_20261122_144137_2274607-i1t | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 54.0 | last meaningful line 1.6 h ago (1560/1560 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-825932 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-iqf__t1-331472 | iqf__t1 | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 20.4 | drt_violations best 49344 last 49344 rows 15 | before-window best 52295, window best 49344 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc7 | dpkit-tt_ctlm-617323 | tt_ctlm | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | tt_setup_repair_grt | 9.5 | repair_Violations best 0 last 0 rows 31 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | tt_setup_repair_grt | 4.5 | repair_Violations best 0 last 0 rows 18 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | tt_setup_repair_grt | 6.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 19.9 | drt_violations best 597 last 2670 rows 35 | before-window best 939, window best 597 | PROGRESS: drt_violations improved 36.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 19.7 | drt_violations best 43966 last 43966 rows 15 | before-window best 46518, window best 43966 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 10.4 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 10.4 | drt_violations best 72 last 72 rows 54 | before-window best 39741, window best 72 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 9.3 | drt_violations best 7192 last 7192 rows 12 | before-window best 20291, window best 7192 | PROGRESS: drt_violations improved 64.6 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | 5_1_grt | 3.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 11.2 | drt_violations best 7622 last 7622 rows 11 | before-window best 18627, window best 7622 | PROGRESS: drt_violations improved 59.1 % in window |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 6.7 | drt_violations best 1 last 6 rows 28 | before-window best 20664, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4040448 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-4048612 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t12-2632859 | slice_station__t12 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
