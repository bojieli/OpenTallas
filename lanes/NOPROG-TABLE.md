# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-15 20:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 15, 'EXCLUDED': 27, 'KEEP': 1, 'PROGRESS': 5}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-761742 | cbn_q11 | 5_1_grt | 5.2 | last meaningful line 2.5 h ago (197/251 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-hd_ctl-3948516 | hd_ctl | 3_3_place_gp | 0.1 | overflow best 0.6738 last 0.679 rows 13 | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_w-3967352 | hd_host_w | 3_4_place_resized | 0.1 | repair_Remaining best 127230 last 127230 rows 11 | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_lep0N-4129279 | hd_lep0N | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_serdes-1086898-lec | hd_serdes | lec | 4.6 | LEC last write 0.3 h ago | YOUNG: evidence 4.6 h < 6 h |  |
| epyc2 | dpkit-hd_spn_end-3995696 | hd_spn_end | 3_3_place_gp | 0.1 | overflow best 0.1858 last 0.1878 rows 11 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-3932580 | cbn_q00 | 3_3_place_gp | 0.3 | overflow best 0.6117 last 0.6117 rows 1 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2330830 | hd_serdes | lec | 1.4 | LEC last write 0.1 h ago | YOUNG: evidence 1.4 h < 6 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t21-4174146 | ot_s81sl_leaf__t21 | 5_1_grt | 12.5 | repair_TNS best 1218.08 last 1218.08 rows 22 | YOUNG: series started inside the last 6 h |  |
| epyc7 | prd-eco_gf1115c-i1-4012204 | eco_gf1115c-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (314/314 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dhr1-unit-u002_b-drt | dhr1-unit-u002_b-drt | drt | 4.2 | last meaningful line 0.0 h ago (568/568 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dhr1-unit-u063_b-prep | dhr1-unit-u063_b-prep | prep | 0.1 | last meaningful line 0.1 h ago (6/6 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-hd_host_w-2947281 | hd_host_w | 5_2_route | 5.7 | drt_violations best 32343 last 32343 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 26.1 | repair_TNS best 109946 last 109946 rows 7 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_1_grt | 26.2 | repair_TNS best 20163.8 last 20163.8 rows 4 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 17.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-2902549 | kv3_pv_v8 | 5_1_grt | 25.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 18.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-3125842 | cbn_q00 | pregrt_ff_hold | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-1327447 | cbn_q00 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 21.8 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv1aac64f0-1909299 | col_h9_r2__t1 | 5_1_grt | 8.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvf57acd2b-3883707 | col_h9_r2__t1 | 5_2_route | 9.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_host_n-4074350 | hd_host_n | 5_2_route | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_st_k5-4119116 | hd_st_k5 | 5_1_grt | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_st_n3_transit-4076831 | hd_st_n3_transit | 5_2_route | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-267889 | phy__t1 | pregrt_ff_hold | 9.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v3-2658471 | sle_fe_v3 | 5_2_route | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-tt_ctlm-3292477 | tt_ctlm | 5_1_grt | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-1664471 | cbf_q00 | 5_1_grt | 7.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-1791823 | cbf_q00 | 5_1_grt | 7.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q11-1664853 | cbf_q11 | 5_1_grt | 7.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q00__cl622f65d2-1550826 | cbn_q00 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q00__cld7bf7197-1551130 | cbn_q00 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_spn-1496036 | hd_spn | 5_2_route | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor_v1-1478407 | kv3_io_cor_v1 | 5_2_route | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-235658 | sle_hc0 | 5_2_route | 9.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_sc_v2-453941 | sle_sc_v2 | 5_2_route | 8.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cle683a076-3728476 | slw_hc1 | 5_1_grt | 10.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-239915 | slw_hc2 | 5_2_route | 9.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-3724816 | slw_stm_v1 | 5_2_route | 10.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_154955_2417288-i1t-4050928 | eco_20261115_154955_2417288-i1t | 5_2_route | 4.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-serdes__t12-4151483 | serdes__t12 | 5_1_grt | 7.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 17.8 | last meaningful line 0.4 h ago (1440/1440 lines) | PROGRESS: log still growing |  |
| epyc7 | prd-eco_gf1115b-i1-3420069 | eco_gf1115b-i1 | 5_1_grt | 0.7 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 26.2 | repair_TNS best 447870 last 447870 rows 34 | before-window best 484079, window best 447870 | PROGRESS: repair_TNS improved 7.5 % in window |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 26.2 | repair_TNS best 525141 last 525141 rows 42 | before-window best 556258, window best 525141 | PROGRESS: repair_TNS improved 5.6 % in window |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_1_grt | 2.7 | repair_Violations best 0 last 0 rows 32 | PROGRESS: repair_Violations reached 0 |  |
