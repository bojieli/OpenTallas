# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 06:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 12, 'EXCLUDED': 23, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | klegacy-bksel_vC9fx3-38817 | bksel_vC9fx3 | 5_1_grt | 6.1 | repair_TNS best 4550.2 last 4550.2 rows 479 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | klegacy-bksel_vC9fx5-2107662 | bksel_vC9fx5 | 5_1_grt | 3.9 | repair_TNS best 32516 last 32516 rows 132 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-43024 | kv3_hub_C | 3_1_place_gp_skip_io | 4.0 | overflow best 0.2962 last 0.2962 rows 42 | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dhr1-unit-u197_b-drt | dhr1-unit-u197_b-drt | drt | 0.2 | last meaningful line 0.0 h ago (215/215 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dhr1-unit-u300_b-drt | dhr1-unit-u300_b-drt | drt | 0.3 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dhr1-unit-u308_b-drt | dhr1-unit-u308_b-drt | drt | 1.7 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dhr1-unit-u310_b-drt | dhr1-unit-u310_b-drt | drt | 0.0 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 35.9 | repair_TNS best 393482 last 393482 rows 2 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 35.9 | repair_TNS best 477374 last 477374 rows 3 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 35.9 | repair_TNS best 37434.7 last 37434.7 rows 5 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_1_grt | 35.9 | repair_TNS best 176.805 last 176.805 rows 1 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-4090240 | slw_su_l1 | 5_2_route | 12.5 | drt_violations best 3067 last 3067 rows 12 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-2227852 | cbn_q00 | 5_1_grt | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2229149 | cbn_q01 | 5_1_grt | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-2229609 | cbn_q01 | 5_1_grt | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2231252 | cbx_q10 | 5_1_grt | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 27.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 28.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-4063502 | cbn_q00 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl89936551-4064823 | cbx_q10 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-100441 | cbx_q10 | 5_1_grt | 9.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 31.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-hd_ctl-1496685 | hd_ctl | pregrt_ff_hold | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-hd_serdes-1782468 | hd_serdes | 5_1_grt | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hub_Ei-458436 | kv3_hub_Ei | tt_setup_repair | 1.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hub_Eo-203594 | kv3_hub_Eo | pregrt_ff_hold | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl254f2e73-1821658 | kv3_pc | pregrt_ff_hold | 3.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | pregrt_ff_hold | 3.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-1664471 | cbf_q00 | 5_1_grt | 17.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-1791823 | cbf_q00 | 5_1_grt | 16.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q00__cl622f65d2-1550826 | cbn_q00 | 5_1_grt | 17.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | eco-abs-2400284 | eco-abs | generate_abstract | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_154955_2417288-i1-176162 | eco_20261115_154955_2417288-i1 | 5_2_route | 6.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261115_222122_1478023-i1-3147364 | eco_20261115_222122_1478023-i1 | 5_2_route | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_1_grt | 3.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 27.8 | last meaningful line 0.2 h ago (1550/1550 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_serdes-1086898-lec | hd_serdes | lec | 14.6 | LEC last write 0.4 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-hd_serdes-2330830 | hd_serdes | lec | 11.2 | LEC last write 0.4 h ago | PROGRESS: LEC still writing |  |
