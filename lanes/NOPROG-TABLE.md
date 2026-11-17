# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 23:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-DATA': 1, 'YOUNG': 10, 'EXCLUDED': 13, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | otc-1916521-17252 | 1916521 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc2 | otc-640031-13674 | 640031 | orfs_synth | 2.6 | last meaningful line 2.5 h ago (603/603 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-3538325 | kv3_hub_C | 3_3_place_gp | 7.1 | overflow best 0.0994 last 0.0994 rows 48 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t62-920776 | ot_s81sl_leaf__t62 | 5_1_grt | 4.7 | last meaningful line 2.5 h ago (205/234 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t72-932176 | ot_s81sl_leaf__t72 | 5_1_grt | 4.7 | last meaningful line 0.8 h ago (207/214 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3456629 | sle_fe_v1 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 52.9 | repair_TNS best 306193 last 306193 rows 6 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 52.9 | repair_TNS best 381840 last 381840 rows 2 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t28-2091344 | ot_s81sl_leaf__t28 | 5_1_grt | 4.8 | last meaningful line 0.8 h ago (204/212 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t34-2093853 | ot_s81sl_leaf__t34 | 5_1_grt | 4.8 | last meaningful line 3.0 h ago (199/232 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-hd_serdes-787792 | hd_serdes | 3_1_place_gp_skip_io | 0.5 | overflow best 0.1784 last 0.1784 rows 45 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 21.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 11.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 45.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1588687 | cbx_q10 | 5_1_grt | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 20.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-521400 | phy__t1 | 5_1_grt | 10.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-2717826 | sle_fe_v1 | 5_1_grt | 1.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3267375 | sle_fe_v1 | pregrt_ff_hold | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 5_1_grt | 10.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 5_1_grt | 9.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slice_station__t42__clcf44e680-3277913 | slice_station__t42 | 5_2_route | 3.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1t-2308651 | eco_20261116_023111_238129-i1t | 5_2_route | 20.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v1n-3540261 | kv3_pv_v1n | 5_1_grt | 2.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 45.1 | last meaningful line 0.1 h ago (1608/1608 lines) | PROGRESS: log still growing |  |
| epyc7 | fxsta_3910197 | fxsta_3910197 | 4_1_cts | 0.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | ffs5-t47_ov25td30-634720 | ffs5-t47_ov25td30 | 4_1_cts | 0.7 | repair_Violations best 0 last 0 rows 19 | PROGRESS: repair_Violations reached 0 |  |
