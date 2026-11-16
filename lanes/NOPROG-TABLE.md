# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 14:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 13, 'EXCLUDED': 13, 'KEEP': 1, 'PROGRESS': 2}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | bksel-o-lec-fx6 | bksel-o-lec-fx6 | 5_1_grt | 0.6 | repair_Violations best 50 last 50 rows 61 | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_e-2937286 | hd_host_e | 5_1_grt | 0.4 | repair_TNS best 15.167 last 15.167 rows 4 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | klegacy-bksel_vC9fx6-2821105 | bksel_vC9fx6 | 5_1_grt | 0.6 | repair_Violations best 50 last 50 rows 61 | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | ot-group44-w0-route3 | ot-group44-w0-route3 | layout_dump | 1.0 | last meaningful line 0.5 h ago (16/16 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | ot-headseg44-kv1-mm | ot-headseg44-kv1-mm | layout_dump_5_1_grt | 1.2 | last meaningful line 0.8 h ago (5/5 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1598588 | col_h10_r0_p1__t1 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1570258 | col_h10_r2__t1 | 3_3_place_gp | 0.1 | overflow best 0.5524 last 0.5532 rows 18 | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1570448 | col_h9_r2__t1 | 3_3_place_gp | 0.1 | overflow best 0.6406 last 0.6463 rows 24 | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-hd_spn_end-1852481 | hd_spn_end | 5_2_route | 2.9 | drt_violations best 14809 last 14809 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 43.9 | repair_TNS best 351205 last 351205 rows 5 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 43.9 | repair_TNS best 429563 last 429563 rows 10 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-serdes__t12-3799958 | serdes__t12 | 1_2_yosys | 0.3 | last meaningful line 0.2 h ago (240/240 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 43.9 | repair_TNS best 28.792 last 28.792 rows 6 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 11.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 11.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 11.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 35.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 36.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 39.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | 5_1_grt | 9.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 10.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-521400 | phy__t1 | 5_1_grt | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 4_1_cts | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 3_5_place_dp | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbx_q10__cl89936551-2625714 | cbx_q10 | 5_1_grt | 1.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 11.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 35.8 | last meaningful line 0.6 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 20.5 | drt_violations best 2187 last 2635 rows 24 | before-window best 2247, window best 2187 | PROGRESS: drt_violations improved 2.7 % in window |  |
