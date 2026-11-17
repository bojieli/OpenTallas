# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 18:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-DATA': 5, 'YOUNG': 15, 'EXCLUDED': 9, 'PROGRESS': 1}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | ck_kv_cland_w1057_ew_94a44_ff_3328180 | ck_kv_cland_w1057_ew_94a44_ff_3328180 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ck_kv_cland_w1057_ew_94a44_tt_3328179 | ck_kv_cland_w1057_ew_94a44_tt_3328179 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-serdes__t13-2519686 | serdes__t13 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (199/205 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | fdqrs4q9m_r-kit | fdqrs4q9m_r-kit | - | 0.6 |  | NO-DATA: no log found |  |
| epyc2 | ifn0r-he_splitbal1-route-3065549 | ifn0r-he_splitbal1-route | 5_2_route | 0.3 | drt_violations best 29723 last 29723 rows 1 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | ifn0r-hw_splitbal1-route-3102327 | ifn0r-hw_splitbal1-route | 5_2_route | 0.3 | drt_violations best 29881 last 29881 rows 1 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | klegacy-bksel_vC9fx6-2821105 | bksel_vC9fx6 | 5_2_route | 5.3 | drt_violations best 4776 last 4776 rows 2 | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-2940617-29073 | 2940617 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1598588 | col_h10_r0_p1__t1 | 5_1_grt | 4.8 | last meaningful line 3.2 h ago (210/223 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-441191 | hd_serdes | tt_setup_measure_grt | 1.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-3538325 | kv3_hub_C | 2_1_floorplan | 2.6 | last meaningful line 2.0 h ago (1399/1399 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t62-920776 | ot_s81sl_leaf__t62 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.1386 last 0.1386 rows 46 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t72-932176 | ot_s81sl_leaf__t72 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7693 last 0.7693 rows 25 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t75-927566 | ot_s81sl_leaf__t75 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.1681 last 0.1752 rows 40 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | fdkv-kit-e6a | fdkv-kit-e6a | - | 0.3 |  | NO-DATA: no log found |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 48.4 | repair_TNS best 327268 last 327268 rows 8 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 48.4 | repair_TNS best 404503 last 404503 rows 10 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t28-2091344 | ot_s81sl_leaf__t28 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t34-2093853 | ot_s81sl_leaf__t34 | 3_3_place_gp | 0.3 | overflow best 0.7149 last 0.7278 rows 18 | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-2098305 | ot_s81sl_leaf__t47 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 16.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 7.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 5_1_grt | 40.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 40.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 15.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-521400 | phy__t1 | 5_1_grt | 6.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 5_1_grt | 6.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 5_1_grt | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 15.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 40.6 | last meaningful line 0.1 h ago (1564/1564 lines) | PROGRESS: log still growing |  |
