# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 14:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'YOUNG': 9, 'NO-DATA': 5, 'EXCLUDED': 13, 'KEEP': 1, 'PROGRESS': 4}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 21.0 | drt_violations best 2187 last 2415 rows 25 | before-window best 2187, window best 2415 | NO-PROGRESS: drt_violations best 2415 vs 2187 before window: < 2 % in 6 h | REPORT-ONLY: no ot-heavy scope |
| epyc2 | bksel-o-lec-fx6 | bksel-o-lec-fx6 | 5_1_grt | 1.1 | repair_Violations best 50 last 50 rows 61 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | fdqs4q9m_comb-kit | fdqs4q9m_comb-kit | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | fdqs4q9m_comb_t-kit | fdqs4q9m_comb_t-kit | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | klegacy-bksel_vC9fx6-2821105 | bksel_vC9fx6 | 5_1_grt | 1.1 | repair_Violations best 50 last 50 rows 61 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | ot-group44-w0-route3 | ot-group44-w0-route3 | layout_dump | 1.5 | last meaningful line 1.0 h ago (16/16 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | ot-headseg44-kv1-mm | ot-headseg44-kv1-mm | layout_dump_5_1_grt | 1.7 | last meaningful line 1.3 h ago (5/5 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1570258 | col_h10_r2__t1 | 5_1_grt | 0.8 | repair_Remaining best 16340 last 16340 rows 97 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | fdkv-kit-e4 | fdkv-kit-e4 | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 44.4 | repair_TNS best 348121 last 348121 rows 7 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 44.4 | repair_TNS best 426983 last 426983 rows 1 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-serdes__t12-3799958 | serdes__t12 | 3_3_place_gp | 0.8 | overflow best 0.7303 last 0.7303 rows 29 | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | postcts_gate_TT | 44.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | so_50761_ff_3625 | so_50761_ff_3625 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | so_50761_tt_3625 | so_50761_tt_3625 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 12.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 12.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 2.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 12.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 36.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 36.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 40.0 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | 5_1_grt | 10.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 11.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-521400 | phy__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | pregrt_ff_hold | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 4_1_cts | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbx_q10__cl89936551-2625714 | cbx_q10 | 5_1_grt | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 11.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 36.3 | last meaningful line 1.1 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_host_e-2937286 | hd_host_e | 5_1_grt | 0.9 | repair_TNS best 0 last 0 rows 58 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1598588 | col_h10_r0_p1__t1 | tt_setup_repair | 0.8 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1570448 | col_h9_r2__t1 | 5_1_grt | 0.8 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
