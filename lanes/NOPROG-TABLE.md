# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 09:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-DATA': 2, 'YOUNG': 16, 'EXCLUDED': 12, 'KEEP': 1, 'PROGRESS': 4}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | fdqs4q9c-kit | fdqs4q9c-kit | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | klegacy-bksel_vC9fx6-1407582 | bksel_vC9fx6 | 5_1_grt | 0.4 | repair_Violations best 50 last 50 rows 61 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-43024 | kv3_hub_C | 3_3_place_gp | 7.0 | overflow best 0.0993 last 0.0993 rows 47 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t15__cla2127225-3502145 | serdes__t15 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | fdkv-kit-b7g | fdkv-kit-b7g | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-he0-3818485 | he0 | lec | 0.5 | LEC last write 0.5 h ago | YOUNG: evidence 0.5 h < 6 h |  |
| epyc7 | klegacy-hw0-3818132 | hw0 | lec | 0.5 | LEC last write 0.5 h ago | YOUNG: evidence 0.5 h < 6 h |  |
| intel1 | dhr1-unit-u020_b-drt | dhr1-unit-u020_b-drt | drt | 0.1 | last meaningful line 0.0 h ago (216/216 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dhr1-unit-u240_b-drt | dhr1-unit-u240_b-drt | drt | 0.2 | last meaningful line 0.0 h ago (270/270 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dhr1-unit-u261_b-drt | dhr1-unit-u261_b-drt | drt | 0.2 | last meaningful line 0.0 h ago (205/205 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dhr1-unit-u262_b-drt | dhr1-unit-u262_b-drt | drt | 0.1 | last meaningful line 0.0 h ago (205/205 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dhr1-unit-u263_b-drt | dhr1-unit-u263_b-drt | drt | 0.1 | last meaningful line 0.1 h ago (199/199 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dhr1-unit-u265_b-drt | dhr1-unit-u265_b-drt | drt | 0.2 | last meaningful line 0.0 h ago (274/274 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dhr1-unit-u268_b-drt | dhr1-unit-u268_b-drt | drt | 0.2 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 38.9 | repair_TNS best 377216 last 377216 rows 4 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 38.9 | repair_TNS best 459729 last 459729 rows 6 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 38.9 | repair_TNS best 16327.4 last 16327.4 rows 6 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 15.5 | drt_violations best 2187 last 9338 rows 18 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 6.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 6.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 6.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 30.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 31.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-4063502 | cbn_q00 | 5_1_grt | 10.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 34.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hub_Ei-458436 | kv3_hub_Ei | 5_1_grt | 4.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | pregrt_ff_hold | 5.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl254f2e73-1821658 | kv3_pc | 5_1_grt | 6.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 6.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-1791823 | cbf_q00 | 5_1_grt | 19.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 6.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 30.8 | last meaningful line 1.1 h ago (1552/1552 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_serdes-1086898-lec | hd_serdes | lec | 17.6 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-hd_serdes-2330830 | hd_serdes | lec | 14.2 | LEC last write 0.7 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-serdes__t13-3502111 | serdes__t13 | 4_1_cts | 0.9 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
