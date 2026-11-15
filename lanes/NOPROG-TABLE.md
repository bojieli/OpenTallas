# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-15 13:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 14, 'NO-DATA': 3, 'KEEP': 3, 'EXCLUDED': 81, 'PROGRESS': 5}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | darabs1-r_c16r | darabs1-r_c16r | drt | 0.1 | last meaningful line 0.0 h ago (209/209 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-189478 | cbn_q11 | 5_1_grt | 12.6 | last meaningful line 5.8 h ago (305/368 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-318081 | col_h9_r0_p2__t1 | 5_1_grt | 23.0 | repair_TNS best 1.08809e+06 last 1.08809e+06 rows 19 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-706931 | kv3_hgi_v2 | 5_1_grt | 14.0 | repair_TNS best 248785 last 248785 rows 15 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dproto-head-native1-otclk | dproto-head-native1-otclk | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-ot_s81sl_leaf__t14-2488980 | ot_s81sl_leaf__t14 | 5_1_grt | 2.3 | repair_Remaining best 5719 last 5719 rows 215 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_gunit_m1-i1-1173086 | eco_gunit_m1-i1 | 5_2_route | 2.6 | drt_violations best 1964 last 1964 rows 1 | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_gunit_m2-i1-1173088 | eco_gunit_m2-i1 | 5_2_route | 2.6 | drt_violations best 1886 last 1886 rows 1 | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-hd_spn_end-1411688 | hd_spn_end | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 18.9 | repair_TNS best 494274 last 494274 rows 8 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2544581 | kit | 5_1_grt | 18.9 | repair_TNS best 487546 last 487546 rows 11 | YOUNG: series started inside the last 7.5 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 18.9 | repair_TNS best 565400 last 565400 rows 6 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t1-862362 | ot_s81sl_kv_leaf__t1 | 3_3_place_gp | 1.0 | overflow best 0.2024 last 0.2024 rows 40 | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 18.9 | repair_TNS best 145570 last 145570 rows 7 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_1_grt | 18.9 | repair_TNS best 56941.2 last 56941.2 rows 7 | YOUNG: series started inside the last 6 h |  |
| intel1 | flamboyant_maxwell | flamboyant_maxwell | - | 14.1 |  | NO-DATA: no log found |  |
| intel1 | optimistic_franklin | optimistic_franklin | - | 14.2 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-3966284 | col_h10_r1__t1 | 5_1_grt | 14.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-kv3_hg_v1p2-1725066 | kv3_hg_v1p2 | 5_1_grt | 16.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v1__cl141fc26e-1200306 | kv3_hgi_v1 | 5_1_grt | 10.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-4076024 | kv3_hgi_v2 | 5_1_grt | 11.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v3-1206504 | kv3_hgi_v3 | 5_1_grt | 10.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hub_Eo-1630185 | kv3_hub_Eo | postcts_gate_TT | 16.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv-1581125 | kv3_pv | 5_1_grt | 16.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 10.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-2902549 | kv3_pv_v8 | 5_1_grt | 18.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | pregrt_ff_hold | 11.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q11__cl49ae4555-2688009 | cbn_q11 | 5_1_grt | 11.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 14.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv0012ba28-2836986 | col_h9_r0_p6__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv082a7609-2909432 | col_h9_r0_p6__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv7808008f-2851059 | col_h9_r0_p6__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv8241ebb8-1667688 | col_h9_r0_p6__t1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv87853a7e-2071430 | col_h9_r0_p6__t1 | 5_1_grt | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv8d617470-1909055 | col_h9_r0_p6__t1 | 5_1_grt | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv9da72aa7-2894787 | col_h9_r0_p6__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvb38a9d6c-2854597 | col_h9_r0_p6__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvbdbd69f2-3186520 | col_h9_r0_p6__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvde240d6d-2072366 | col_h9_r0_p6__t1 | 5_1_grt | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pvea45abf3-1669153 | col_h9_r0_p6__t1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2446603 | col_h9_r2__t1 | 5_1_grt | 3.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3197073 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-682201 | col_h9_r2__t1 | 5_1_grt | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv1aac64f0-1909299 | col_h9_r2__t1 | 5_1_grt | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv1aac64f0-681410 | col_h9_r2__t1 | 5_1_grt | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv22267ca0-3759134 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-231764 | col_h9_r2__t1 | 5_1_grt | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv2f87774f-3761876 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | KEEP: col_h9_r2__t1__clce45cab5__pv2f87774f	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-3771777 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv37074264-226688 | col_h9_r2__t1 | 5_1_grt | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-3235695 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-3245969 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3236269 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-3263179 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-221373 | col_h9_r2__t1 | 5_1_grt | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-3240906 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3259321 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-900692 | col_h9_r2__t1 | 5_1_grt | 2.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-3254820 | col_h9_r2__t1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-3771624 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-3807745 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-3827300 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb11188eb-3787429 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-3880087 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-3830064 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvf57acd2b-3883707 | col_h9_r2__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-1733650 | dsdv_slice_c1x_C__t1 | pregrt_ff_hold | 6.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t3-3385105 | dsdv_slice_c1x_C__t3 | pregrt_ff_hold | 6.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1703897 | dsdv_slice_c1x_C__t4 | pregrt_ff_hold | 6.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t5-1711603 | dsdv_slice_c1x_C__t5 | pregrt_ff_hold | 6.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_ctl-2770424 | hd_ctl | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_io_cor-2777284 | kv3_io_cor | 5_2_route | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t30-908103 | ot_s81sl_leaf__t30 | 5_1_grt | 2.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t42-335381 | ot_s81sl_leaf__t42 | 5_1_grt | 1.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-267889 | phy__t1 | pregrt_ff_hold | 1.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-1664471 | cbf_q00 | 2_1_floorplan | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q11-1664853 | cbf_q11 | 2_1_floorplan | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q00__cl622f65d2-1550826 | cbn_q00 | 2_1_floorplan | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q00__cld7bf7197-1551130 | cbn_q00 | 2_1_floorplan | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-coll_ftc-1200513 | coll_ftc | 3_3_place_gp | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t9-383004 | dsdv_slice_c1x_C__t9 | pregrt_ff_hold | 5.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3745700 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-3745069 | dsdv_slice_lepw_mus_C__t1 | 4_1_cts | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_host_w-1551309 | hd_host_w | pregrt_ff_hold | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_spn-1496036 | hd_spn | 3_3_place_gp | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_st_n4-4083845 | hd_st_n4 | generate_abstract | 3.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor_v1-1478407 | kv3_io_cor_v1 | 4_1_cts | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v1__cl7f648944-1484009 | kv3_pc_v1 | 2_1_floorplan | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2421779 | sle_fe_v1 | 5_2_route | 12.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-235658 | sle_hc0 | pregrt_ff_hold | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-3637423 | sle_hc0 | postcts_gate_TT | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc2__clcc5e3e61-3637692 | sle_hc2 | postcts_gate_TT | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_sc_v2-453941 | sle_sc_v2 | 4_1_cts | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cle683a076-3728476 | slw_hc1 | 5_1_grt | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-239915 | slw_hc2 | 4_1_cts | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-3724816 | slw_stm_v1 | 5_1_grt | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v3-3732754 | slw_stm_v3 | postcts_gate_TT | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-2143272 | slw_su_l0 | 5_2_route | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_113347_3494677-i1t-508460 | eco_20261115_113347_3494677-i1t | 5_2_route | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv6398a5b7-3778848 | col_h9_r0_p6__t1 | 5_1_grt | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pvea45abf3-3776313 | col_h9_r0_p6__t1 | 5_1_grt | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 10.8 | last meaningful line 0.2 h ago (1381/1381 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-600402 | col_h9_r0_p1__t1 | 5_1_grt | 17.5 | last meaningful line 0.0 h ago (1420/1420 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-1458540 | kv3_hgi_v2 | 5_1_grt | 10.5 | last meaningful line 0.0 h ago (1335/1335 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t21-4174146 | ot_s81sl_leaf__t21 | 5_1_grt | 5.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | m7hgg-749463 | m7hgg | 5_1_grt | 14.5 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
