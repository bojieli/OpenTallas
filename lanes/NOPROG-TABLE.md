# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 13:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-DATA': 3, 'YOUNG': 7, 'EXCLUDED': 13, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | ot-group44-w0-route3 | ot-group44-w0-route3 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | ot-headseg44-kv1-mm | ot-headseg44-kv1-mm | layout_dump_5_1_grt | 0.5 | last meaningful line 0.1 h ago (5/5 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t1__clb45db5be-184846 | serdes__t1 | tt_setup_measure | 1.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-993068-3042 | 993068 | tt_setup_measure | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_973589_ff_26079 | so_973589_ff_26079 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_973589_tt_26079 | so_973589_tt_26079 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-hd_spn_end-1852481 | hd_spn_end | 5_2_route | 1.9 | last meaningful line 0.1 h ago (252/253 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 42.9 | repair_TNS best 356943 last 356943 rows 2 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 42.9 | repair_TNS best 435878 last 435878 rows 5 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 42.9 | repair_TNS best 751.934 last 751.934 rows 19 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 11.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 11.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | pregrt_ff_hold | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 11.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 34.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 35.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 38.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | 5_1_grt | 9.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-521400 | phy__t1 | 5_1_grt | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 3_3_place_gp | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbx_q10__cl89936551-2625714 | cbx_q10 | pregrt_ff_hold | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v1__cl23f6a148-3497409 | kv3_pc_v1 | 4_1_cts | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 10.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 35.1 | last meaningful line 1.6 h ago (1556/1556 lines) | PROGRESS: log still growing |  |
| epyc2 | klegacy-bksel_vC9fx6-1407582 | bksel_vC9fx6 | 5_1_grt | 4.6 | repair_TNS best 0 last 0 rows 409 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 19.5 | drt_violations best 2187 last 2642 rows 23 | before-window best 2527, window best 2187 | PROGRESS: drt_violations improved 13.5 % in window |  |
