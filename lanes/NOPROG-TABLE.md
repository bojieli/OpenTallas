# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-15 11:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'CANCEL-NOW': 1, 'YOUNG': 28, 'NO-DATA': 2, 'KEEP': 3, 'EXCLUDED': 73, 'PROGRESS': 12}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t3-1267116 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 8.6 | last meaningful line 6.0 h ago (300/300 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t4-1151180 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 8.7 | last meaningful line 6.0 h ago (300/300 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORTED (cancel next pass) |
| intel1 | dpkit-serdes__t4-2999799-lec | serdes__t4 | lec | 24.3 | LEC last write 0.9 h ago | CANCEL-NOW: LEC >24h, advisory | REPORTED (cancel next pass) |
| epyc2 | darabs1-r_base32 | darabs1-r_base32 | drt | 0.3 | last meaningful line 0.0 h ago (265/265 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | darabs1-r_c16t8 | darabs1-r_c16t8 | drt | 0.3 | last meaningful line 0.0 h ago (314/314 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | darabs1-r_fine | darabs1-r_fine | drt | 0.7 | last meaningful line 0.0 h ago (307/307 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-189478 | cbn_q11 | 5_1_grt | 10.6 | last meaningful line 3.8 h ago (305/345 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-600318 | col_h9_r0_p1__t1 | 5_1_grt | 15.5 | repair_TNS best 920474 last 920474 rows 7 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-318081 | col_h9_r0_p2__t1 | 5_1_grt | 21.0 | repair_TNS best 1.1061e+06 last 1.1061e+06 rows 5 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-1458540 | kv3_hgi_v2 | 5_1_grt | 8.5 | last meaningful line 0.0 h ago (1091/1091 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-699312 | kv3_hgi_v2 | 5_2_route | 12.1 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-706931 | kv3_hgi_v2 | 5_1_grt | 12.0 | repair_TNS best 259713 last 259713 rows 8 | YOUNG: series started inside the last 6 h |  |
| epyc2 | kvcore-q1_-1077405 | kvcore-q1_ | 5_3_fillcell | 0.7 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kvcore-q2_-1081059 | kvcore-q2_ | 5_2_route | 0.7 | drt_violations best 18 last 18 rows 4 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01-2355986 | cbf_q01 | 3_3_place_gp | 0.6 | overflow best 0.442 last 0.442 rows 21 | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv8241ebb8-579347 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.1 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvea45abf3-593045 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.1 | last meaningful line -0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1n-4072175 | kv3_pv_v1n | 2_1_floorplan | 0.3 | last meaningful line 0.2 h ago (83/83 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1n-4072175-lec | kv3_pv_v1n | lec | 0.2 | LEC last write 0.1 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t14-2488980 | ot_s81sl_leaf__t14 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4074/4074 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t21-4174146 | ot_s81sl_leaf__t21 | 5_1_grt | 3.5 | repair_Remaining best 64656 last 64656 rows 62 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-hd_host_w-873076-lec | hd_host_w | lec | 3.5 | LEC last write 0.0 h ago | YOUNG: evidence 3.5 h < 6 h |  |
| intel1 | dpkit-hd_host_w-873333-lec | hd_host_w | lec | 3.5 | LEC last write 0.0 h ago | YOUNG: evidence 3.5 h < 6 h |  |
| intel1 | dpkit-kit-2544581 | kit | 5_1_grt | 16.9 | repair_TNS best 496537 last 496537 rows 4 | YOUNG: series started inside the last 7.5 h |  |
| intel1 | dpkit-kit-3952785 | kit | 5_1_grt | 12.6 | repair_TNS best 615161 last 615161 rows 4 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kv3_pc_v1__cl23f6a148-4009507 | kv3_pc_v1 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t1-3205384 | ot_s81sl_kv_leaf__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (106/106 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 16.9 | repair_TNS best 161180 last 161180 rows 1 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_1_grt | 16.9 | repair_TNS best 70359.7 last 70359.7 rows 21 | YOUNG: series started inside the last 6 h |  |
| intel1 | flamboyant_maxwell | flamboyant_maxwell | - | 12.1 |  | NO-DATA: no log found |  |
| intel1 | kvcore-q0_-2526366 | kvcore-q0_ | lec | 2.5 | LEC last write 0.1 h ago | YOUNG: evidence 2.5 h < 6 h |  |
| intel1 | kvcore-q0_-2696401 | kvcore-q0_ | lec | 2.4 | LEC last write 0.1 h ago | YOUNG: evidence 2.4 h < 6 h |  |
| intel1 | optimistic_franklin | optimistic_franklin | - | 12.2 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-3966284 | col_h10_r1__t1 | 5_1_grt | 12.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-2061436 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 8.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hg_v1p2-1725066 | kv3_hg_v1p2 | 5_1_grt | 14.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v1__cl141fc26e-1200306 | kv3_hgi_v1 | 5_1_grt | 8.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-4076024 | kv3_hgi_v2 | 5_1_grt | 9.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v3-1206504 | kv3_hgi_v3 | 5_1_grt | 8.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hub_Eo-1630185 | kv3_hub_Eo | 5_1_grt | 14.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv-1581125 | kv3_pv | 5_1_grt | 14.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | pregrt_ff_hold | 8.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-2902549 | kv3_pv_v8 | 5_1_grt | 16.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | pregrt_ff_hold | 9.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q11__cl49ae4555-2688009 | cbn_q11 | 5_1_grt | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 12.8 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-2836986 | col_h9_r0_p6__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv082a7609-2909432 | col_h9_r0_p6__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv6398a5b7-2859683 | col_h9_r0_p6__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv7808008f-2851059 | col_h9_r0_p6__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv9da72aa7-2894787 | col_h9_r0_p6__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvb38a9d6c-2854597 | col_h9_r0_p6__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvbdbd69f2-3186520 | col_h9_r0_p6__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvea45abf3-3166870 | col_h9_r0_p6__t1 | 5_1_grt | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2446603 | col_h9_r2__t1 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3197073 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-682201 | col_h9_r2__t1 | 5_1_grt | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv1aac64f0-681410 | col_h9_r2__t1 | 5_1_grt | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv22267ca0-3759134 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-231764 | col_h9_r2__t1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv2f87774f-3761876 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | KEEP: col_h9_r2__t1__clce45cab5__pv2f87774f	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-3771777 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv37074264-226688 | col_h9_r2__t1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-3235695 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-3245969 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3236269 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-3263179 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-221373 | col_h9_r2__t1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-3240906 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3259321 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-900692 | col_h9_r2__t1 | 5_1_grt | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-3254820 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-3771624 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-3807745 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-3827300 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb11188eb-3787429 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-3880087 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-3830064 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvf57acd2b-3883707 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-1733650 | dsdv_slice_c1x_C__t1 | pregrt_ff_hold | 4.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t3-3385105 | dsdv_slice_c1x_C__t3 | pregrt_ff_hold | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1703897 | dsdv_slice_c1x_C__t4 | pregrt_ff_hold | 4.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t5-1711603 | dsdv_slice_c1x_C__t5 | pregrt_ff_hold | 4.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_ctl-2770424 | hd_ctl | pregrt_ff_hold | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_spn_end-2767194 | hd_spn_end | postcts_gate_TT | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_io_cor-2777284 | kv3_io_cor | pregrt_ff_hold | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_io_cor_v1-2734966 | kv3_io_cor_v1 | pregrt_ff_hold | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-2717932 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t30-908103 | ot_s81sl_leaf__t30 | 5_1_grt | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t42-335381 | ot_s81sl_leaf__t42 | pregrt_ff_hold | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-267889 | phy__t1 | 4_1_cts | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-serdes__t12-369872 | serdes__t12 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2796113 | slw_hc0 | 4_1_cts | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t9-383004 | dsdv_slice_c1x_C__t9 | pregrt_ff_hold | 3.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3745700 | dsdv_slice_lepw_mu_C__t1 | selrange | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-3745069 | dsdv_slice_lepw_mus_C__t1 | selrange | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_host_w-382422 | hd_host_w | pregrt_ff_hold | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_st_n4-4083845 | hd_st_n4 | 5_2_route | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_tile-3494733 | hd_tile | 5_2_route | 1.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2421779 | sle_fe_v1 | 5_2_route | 10.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-3637423 | sle_hc0 | pregrt_ff_hold | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc2__clcc5e3e61-3637692 | sle_hc2 | pregrt_ff_hold | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cle683a076-3728476 | slw_hc1 | 4_1_cts | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-3724816 | slw_stm_v1 | 4_1_cts | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2055284 | slw_stm_v2 | 5_2_route | 10.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v3-3732754 | slw_stm_v3 | 5_1_grt | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-2143272 | slw_su_l0 | 3_4_place_resized | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-3182142 | slw_su_l1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_074057_3757778-i1-1329241 | eco_20261115_074057_3757778-i1 | 5_2_route | 3.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 8.8 | last meaningful line 0.2 h ago (1377/1377 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-unit-u198_a-drt | dhr1-unit-u198_a-drt | drt | 7.1 | last meaningful line 0.2 h ago (822/822 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-unit-u201_a-drt | dhr1-unit-u201_a-drt | drt | 7.1 | last meaningful line 0.1 h ago (878/878 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-unit-u261_a-drt | dhr1-unit-u261_a-drt | drt | 7.1 | last meaningful line 0.1 h ago (814/814 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-600402 | col_h9_r0_p1__t1 | 5_1_grt | 15.5 | last meaningful line 0.0 h ago (1339/1339 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_pc__cl254f2e73-3316517-lec | kv3_pc | lec | 12.8 | LEC last write 0.1 h ago | PROGRESS: LEC still writing |  |
| epyc2 | kvcore-q3_-1083749 | kvcore-q3_ | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 116 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | m7hgg-749463 | m7hgg | 5_1_grt | 12.7 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | prd-eco_gunit_m1-i1-1173086 | eco_gunit_m1-i1 | 5_1_grt | 0.8 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | prd-eco_gunit_m2-i1-1173088 | eco_gunit_m2-i1 | 5_1_grt | 0.8 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 16.9 | last meaningful line 0.1 h ago (879/879 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 16.9 | last meaningful line 0.1 h ago (1037/1037 lines) | PROGRESS: log still growing |  |
