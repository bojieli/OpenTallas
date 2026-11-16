# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 08:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 11, 'EXCLUDED': 13, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-hd_host_e-2852431 | hd_host_e | 5_2_route | 1.3 | drt_violations best 2503 last 2503 rows 3 | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-43024 | kv3_hub_C | 3_3_place_gp | 6.5 | overflow best 0.0993 last 0.0993 rows 47 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-3502111 | serdes__t13 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t15__cla2127225-3502145 | serdes__t15 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.5379 last 0.5379 rows 38 | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 38.4 | repair_TNS best 378871 last 378871 rows 3 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 38.4 | repair_TNS best 463062 last 463062 rows 4 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 38.4 | repair_TNS best 19237.5 last 19237.5 rows 12 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_2_route | 38.4 | last meaningful line 0.1 h ago (354/355 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 15.0 | drt_violations best 2187 last 2187 rows 17 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | so_728136_ff_16423 | so_728136_ff_16423 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (619/619 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_728136_tt_16423 | so_728136_tt_16423 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (619/619 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 6.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-2229609 | cbn_q01 | 5_1_grt | 6.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 6.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 6.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 30.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 30.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-4063502 | cbn_q00 | 5_1_grt | 10.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 34.0 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hub_Ei-458436 | kv3_hub_Ei | 5_1_grt | 4.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | pregrt_ff_hold | 4.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl254f2e73-1821658 | kv3_pc | 5_1_grt | 5.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 5.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-1791823 | cbf_q00 | 5_1_grt | 19.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 5.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 30.3 | last meaningful line 0.6 h ago (1552/1552 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_serdes-1086898-lec | hd_serdes | lec | 17.1 | LEC last write 1.8 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-hd_serdes-2330830 | hd_serdes | lec | 13.7 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
