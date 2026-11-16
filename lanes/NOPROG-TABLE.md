# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 12:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-DATA': 5, 'YOUNG': 13, 'EXCLUDED': 12, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | otc-2177723-5236 | 2177723 | hold_margin_value | 1.9 |  | NO-DATA: empty log |  |
| epyc2 | so_4005311_ff_56792 | so_4005311_ff_56792 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_4005311_tt_56792 | so_4005311_tt_56792 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-serdes__t14-2642599 | serdes__t14 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (200/205 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t15__cla2127225-3502145 | serdes__t15 | 5_1_grt | 3.9 | repair_TNS best 772.332 last 772.332 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t1__clb45db5be-184846 | serdes__t1 | 3_1_place_gp_skip_io | 0.0 | overflow best 0.8887 last 0.8887 rows 7 | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | klegacy-he1p-3678750 | he1p | 5_1_grt | 0.7 | repair_TNS best 383.537 last 383.537 rows 1 | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | ap-ageom-kw-cbn-q00--cl622f65d2-grt-2476732 | cbn-q00--cl622f65d2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-cbx-q10--cl89936551-grt-2475094 | cbx-q10--cl89936551-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-2045361 | cbn_q01 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-hd_spn_end-1852481 | hd_spn_end | postcts_gate_FF | 0.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-hd_st_n3_turn-1852246 | hd_st_n3_turn | 5_2_route | 0.9 | last meaningful line 0.1 h ago (235/236 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 41.9 | repair_TNS best 361816 last 361816 rows 6 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 41.9 | repair_TNS best 442148 last 442148 rows 9 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-serdes__t14-2190921 | serdes__t14 | 3_3_place_gp | 0.4 | overflow best 0.8236 last 0.8236 rows 23 | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-2329471 | serdes__t14 | pregrt_ff_hold | 1.7 | repair_TNS best 500681 last 500681 rows 1 | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 41.9 | repair_TNS best 2819.71 last 2819.71 rows 11 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-2108752 | slw_fw_v2 | 3_3_place_gp | 0.5 | overflow best 0.2038 last 0.2038 rows 36 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 9.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 9.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 4_1_cts | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 9.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 33.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 34.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-4063502 | cbn_q00 | 5_1_grt | 13.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 37.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | 5_1_grt | 8.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 9.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-4139066 | phy__t1 | 5_1_grt | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v1__cl23f6a148-3497409 | kv3_pc_v1 | 3_5_place_dp | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 9.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 33.8 | last meaningful line 0.4 h ago (1556/1556 lines) | PROGRESS: log still growing |  |
| epyc2 | klegacy-bksel_vC9fx6-1407582 | bksel_vC9fx6 | 5_1_grt | 3.4 | repair_TNS best 0 last 0 rows 220 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 18.5 | drt_violations best 2187 last 2777 rows 22 | before-window best 3067, window best 2187 | PROGRESS: drt_violations improved 28.7 % in window |  |
