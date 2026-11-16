# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 05:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 12, 'EXCLUDED': 25, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | klegacy-bksel_vC9fx3-38817 | bksel_vC9fx3 | 5_1_grt | 5.6 | repair_TNS best 4550.2 last 4550.2 rows 403 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | klegacy-bksel_vC9fx5-2107662 | bksel_vC9fx5 | 5_1_grt | 3.4 | repair_TNS best 47274.7 last 47274.7 rows 97 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | prd-eco_he4-i1-4039408 | eco_he4-i1 | 5_2_route | 0.7 | drt_violations best 29 last 29 rows 35 | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-43024 | kv3_hub_C | 3_1_place_gp_skip_io | 3.8 | overflow best 0.9347 last 0.9398 rows 17 | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dhr1-unit-u026_b-drt | dhr1-unit-u026_b-drt | drt | 2.0 | last meaningful line 0.1 h ago (428/428 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dhr1-unit-u029_b-drt | dhr1-unit-u029_b-drt | drt | 1.8 | last meaningful line 0.0 h ago (469/469 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dhr1-unit-u308_b-drt | dhr1-unit-u308_b-drt | drt | 1.2 | last meaningful line 0.3 h ago (216/216 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 35.4 | repair_TNS best 394945 last 394945 rows 11 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 35.4 | repair_TNS best 479291 last 479291 rows 13 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 35.4 | repair_TNS best 41916.8 last 41916.8 rows 11 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_1_grt | 35.4 | repair_TNS best 444.601 last 444.601 rows 9 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 12.0 | drt_violations best 4062 last 4062 rows 10 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-2227852 | cbn_q00 | 5_1_grt | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | pregrt_ff_hold | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-2229609 | cbn_q01 | 5_1_grt | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 27.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-native59-2234969 | native59 | postcts_gate_TT | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 27.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-4063502 | cbn_q00 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl89936551-4064823 | cbx_q10 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-100441 | cbx_q10 | 5_1_grt | 9.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 31.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-hd_ctl-1496685 | hd_ctl | pregrt_ff_hold | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_serdes-1782468 | hd_serdes | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hub_Ei-458436 | kv3_hub_Ei | 4_1_cts | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | tt_setup_repair | 1.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl254f2e73-1821658 | kv3_pc | pregrt_ff_hold | 3.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | pregrt_ff_hold | 2.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t42-1625780 | ot_s81sl_leaf__t42 | 5_2_route | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-1664471 | cbf_q00 | 5_1_grt | 16.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-1791823 | cbf_q00 | 5_1_grt | 16.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q00__cl622f65d2-1550826 | cbn_q00 | 5_1_grt | 16.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_154955_2417288-i1-176162 | eco_20261115_154955_2417288-i1 | 5_2_route | 5.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_212433_1495639-i1-2098019 | eco_20261115_212433_1495639-i1 | 5_2_route | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_222122_1478023-i1-3147364 | eco_20261115_222122_1478023-i1 | 5_2_route | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_1_grt | 2.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 27.3 | last meaningful line 1.2 h ago (1548/1548 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_serdes-1086898-lec | hd_serdes | lec | 14.1 | LEC last write 0.4 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-hd_serdes-2330830 | hd_serdes | lec | 10.9 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
