# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-15 10:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'CANCEL-NOW': 1, 'NO-PROGRESS': 1, 'YOUNG': 32, 'NO-DATA': 2, 'KEEP': 3, 'EXCLUDED': 41, 'PROGRESS': 12}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-serdes__t4-2999799-lec | serdes__t4 | lec | 24.1 | LEC last write 0.7 h ago | CANCEL-NOW: LEC >24h, advisory | REPORTED (cancel next pass) |
| intel2 | dpkit-cbn_q11__cl5cc92dfe-3737497 | cbn_q11 | 5_1_grt | 14.7 | repair_Violations best 0 last 0 rows 19 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | CANCELLED |
| epyc2 | darabs1-r_base32 | darabs1-r_base32 | drt | 0.1 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | darabs1-r_c16s | darabs1-r_c16s | drt | 0.1 | last meaningful line 0.0 h ago (211/211 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | darabs1-r_c16t8 | darabs1-r_c16t8 | drt | 0.1 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | darabs1-r_fine | darabs1-r_fine | drt | 0.5 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-189478 | cbn_q11 | 5_1_grt | 10.4 | last meaningful line 3.5 h ago (305/344 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-600318 | col_h9_r0_p1__t1 | 5_1_grt | 15.3 | repair_TNS best 922172 last 922172 rows 6 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-318081 | col_h9_r0_p2__t1 | 5_1_grt | 20.8 | repair_TNS best 1.10805e+06 last 1.10805e+06 rows 4 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-1458540 | kv3_hgi_v2 | 5_1_grt | 8.2 | last meaningful line 0.0 h ago (1077/1077 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-699312 | kv3_hgi_v2 | 5_2_route | 11.8 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-706931 | kv3_hgi_v2 | 5_1_grt | 11.8 | repair_TNS best 261301 last 261301 rows 7 | YOUNG: series started inside the last 6 h |  |
| epyc2 | kvcore-q2_-1081059 | kvcore-q2_ | 5_1_grt | 0.4 | repair_TNS best 71.781 last 71.781 rows 126 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | kvcore-q3_-1083749 | kvcore-q3_ | 5_1_grt | 0.4 | repair_TNS best 285.565 last 285.565 rows 4 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01-2355986 | cbf_q01 | 2_1_floorplan | 0.1 | last meaningful line -0.0 h ago (806/806 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_io_ft_v1-1861741 | kv3_io_ft_v1 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3016461 | kv3_pv_v4n | 3_5_place_dp | 3.8 | last meaningful line 0.3 h ago (113/113 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-2844960 | kv3_pv_v5n | 3_5_place_dp | 3.8 | last meaningful line 0.2 h ago (111/111 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t14-2488980 | ot_s81sl_leaf__t14 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t21-4174146 | ot_s81sl_leaf__t21 | 5_1_grt | 3.0 | repair_Remaining best 88656 last 88656 rows 38 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l0__cl086d85ba-2098983 | sle_su_l0 | 3_4_place_resized | 0.2 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1858067 | sle_su_l1 | 3_3_place_gp | 0.2 | overflow best 0.2008 last 0.2008 rows 42 | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-1794894 | sle_su_l1 | 3_3_place_gp | 0.2 | overflow best 0.0984 last 0.0984 rows 53 | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_gunit_m1-i1-1173086 | eco_gunit_m1-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_gunit_m2-i1-1173088 | eco_gunit_m2-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (315/315 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-hd_host_w-873076-lec | hd_host_w | lec | 3.3 | LEC last write 0.1 h ago | YOUNG: evidence 3.3 h < 6 h |  |
| intel1 | dpkit-hd_host_w-873333-lec | hd_host_w | lec | 3.3 | LEC last write 0.0 h ago | YOUNG: evidence 3.3 h < 6 h |  |
| intel1 | dpkit-kit-2544581 | kit | 5_1_grt | 16.7 | repair_TNS best 497754 last 497754 rows 3 | YOUNG: series started inside the last 7.5 h |  |
| intel1 | dpkit-kit-3952785 | kit | 5_1_grt | 12.3 | repair_TNS best 618369 last 618369 rows 2 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kv3_pc_v1__cl23f6a148-4009507 | kv3_pc_v1 | 3_3_place_gp | 1.2 | overflow best 0.2105 last 0.2105 rows 40 | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 16.6 | repair_TNS best 163339 last 163339 rows 8 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_1_grt | 16.7 | repair_TNS best 72253.1 last 72253.1 rows 15 | YOUNG: series started inside the last 6 h |  |
| intel1 | flamboyant_maxwell | flamboyant_maxwell | - | 11.9 |  | NO-DATA: no log found |  |
| intel1 | kvcore-q0_-2526366 | kvcore-q0_ | lec | 2.2 | LEC last write 0.1 h ago | YOUNG: evidence 2.2 h < 6 h |  |
| intel1 | kvcore-q0_-2696401 | kvcore-q0_ | lec | 2.1 | LEC last write 0.0 h ago | YOUNG: evidence 2.1 h < 6 h |  |
| intel1 | optimistic_franklin | optimistic_franklin | - | 12.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-3966284 | col_h10_r1__t1 | 5_1_grt | 12.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-2061436 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hg_v1p2-1725066 | kv3_hg_v1p2 | 5_1_grt | 14.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v1__cl141fc26e-1200306 | kv3_hgi_v1 | 5_1_grt | 8.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-4076024 | kv3_hgi_v2 | 5_1_grt | 9.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v3-1206504 | kv3_hgi_v3 | 5_1_grt | 8.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hub_Eo-1630185 | kv3_hub_Eo | 5_1_grt | 14.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv-1581125 | kv3_pv | 5_1_grt | 14.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | pregrt_ff_hold | 8.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-2902549 | kv3_pv_v8 | 5_1_grt | 16.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | pregrt_ff_hold | 8.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q11__cl49ae4555-2688009 | cbn_q11 | 5_1_grt | 9.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 12.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2246910 | col_h9_r1__t1 | 5_1_grt | 37.3 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2446603 | col_h9_r2__t1 | 5_1_grt | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-682201 | col_h9_r2__t1 | 5_1_grt | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv1aac64f0-681410 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-231764 | col_h9_r2__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv37074264-226688 | col_h9_r2__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-221373 | col_h9_r2__t1 | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-900692 | col_h9_r2__t1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-1733650 | dsdv_slice_c1x_C__t1 | pregrt_ff_hold | 3.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t3-3385105 | dsdv_slice_c1x_C__t3 | pregrt_ff_hold | 4.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1703897 | dsdv_slice_c1x_C__t4 | pregrt_ff_hold | 3.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t5-1711603 | dsdv_slice_c1x_C__t5 | pregrt_ff_hold | 3.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_io_cor_v1-2734966 | kv3_io_cor_v1 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-2717932 | kv3_pc_v1 | 1_synth | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t30-908103 | ot_s81sl_leaf__t30 | 5_1_grt | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t9-383004 | dsdv_slice_c1x_C__t9 | hold_gate | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-3745700 | dsdv_slice_lepw_mu_C__t1 | selrange | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-3745069 | dsdv_slice_lepw_mus_C__t1 | selrange | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_host_w-382422 | hd_host_w | pregrt_ff_hold | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_st_n4-4083845 | hd_st_n4 | 5_2_route | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_tile-3494733 | hd_tile | 5_2_route | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2421779 | sle_fe_v1 | 5_2_route | 9.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-3637423 | sle_hc0 | 4_1_cts | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc2__clcc5e3e61-3637692 | sle_hc2 | 4_1_cts | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cle683a076-3728476 | slw_hc1 | 4_1_cts | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-3724816 | slw_stm_v1 | 4_1_cts | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2055284 | slw_stm_v2 | 5_2_route | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v3-3732754 | slw_stm_v3 | pregrt_ff_hold | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-2143272 | slw_su_l0 | 1_2_yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-3182142 | slw_su_l1 | 5_1_grt | 1.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_074057_3757778-i1-1329241 | eco_20261115_074057_3757778-i1 | 5_2_route | 3.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 8.6 | last meaningful line 0.9 h ago (1375/1375 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-unit-u198_a-drt | dhr1-unit-u198_a-drt | drt | 6.8 | last meaningful line 0.2 h ago (818/818 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-unit-u201_a-drt | dhr1-unit-u201_a-drt | drt | 6.8 | last meaningful line 0.2 h ago (829/829 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-unit-u261_a-drt | dhr1-unit-u261_a-drt | drt | 6.8 | last meaningful line 0.1 h ago (808/808 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-600402 | col_h9_r0_p1__t1 | 5_1_grt | 15.3 | last meaningful line 0.1 h ago (1331/1331 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_pc__cl254f2e73-3316517-lec | kv3_pc | lec | 12.5 | LEC last write 0.1 h ago | PROGRESS: LEC still writing |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t3-1267116 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 8.4 | last meaningful line 5.8 h ago (300/300 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t4-1151180 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 8.5 | last meaningful line 5.8 h ago (300/300 lines) | PROGRESS: log still growing |  |
| epyc2 | kvcore-q1_-1077405 | kvcore-q1_ | 5_1_grt | 0.4 | repair_Violations best 0 last 0 rows 59 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | m7hgg-749463 | m7hgg | 5_1_grt | 12.2 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 16.7 | last meaningful line 0.1 h ago (872/872 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 16.7 | last meaningful line 0.1 h ago (1032/1032 lines) | PROGRESS: log still growing |  |
