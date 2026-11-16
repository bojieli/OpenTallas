# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 14:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 9, 'NO-DATA': 1, 'EXCLUDED': 10, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | bksel-o-lec-fx6 | bksel-o-lec-fx6 | 5_1_grt | 0.8 | repair_Violations best 50 last 50 rows 61 | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | fdqs4q9m_comb-kit | fdqs4q9m_comb-kit | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | klegacy-bksel_vC9fx6-2821105 | bksel_vC9fx6 | 5_1_grt | 0.8 | repair_Violations best 50 last 50 rows 61 | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | ot-group44-w0-route3 | ot-group44-w0-route3 | layout_dump | 1.3 | last meaningful line 0.8 h ago (16/16 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | ot-headseg44-kv1-mm | ot-headseg44-kv1-mm | layout_dump_5_1_grt | 1.5 | last meaningful line 1.0 h ago (5/5 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-hd_spn_end-1852481 | hd_spn_end | 5_2_route | 2.9 | drt_violations best 14809 last 14809 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 43.9 | repair_TNS best 351205 last 351205 rows 5 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 43.9 | repair_TNS best 429563 last 429563 rows 10 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-serdes__t12-3799958 | serdes__t12 | 1_2_yosys | 0.3 | last meaningful line 0.2 h ago (240/240 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 43.9 | repair_TNS best 28.792 last 28.792 rows 6 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 12.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 12.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 2.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 12.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 35.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 36.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 4_1_cts | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 3_5_place_dp | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbx_q10__cl89936551-2625714 | cbx_q10 | 5_1_grt | 1.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 11.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 36.1 | last meaningful line 0.9 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_host_e-2937286 | hd_host_e | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 66 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 20.5 | drt_violations best 2187 last 2635 rows 24 | before-window best 2247, window best 2187 | PROGRESS: drt_violations improved 2.7 % in window |  |
