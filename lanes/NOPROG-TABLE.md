# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-16 23:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 13, 'NO-DATA': 2, 'EXCLUDED': 14, 'PROGRESS': 1}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | ifn0r-drt_data_unwire1116-route-2613669 | ifn0r-drt_data_unwire1116-route | 5_2_route | 0.2 | drt_violations best 1834 last 1834 rows 2 | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-1916521-17252 | 1916521 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc2 | otc-640031-13674 | 640031 | orfs_synth | 2.9 | last meaningful line 2.8 h ago (603/603 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-kit_hd_ctl-4092960 | kit_hd_ctl | 3_3_place_gp | 0.2 | overflow best 0.2997 last 0.3519 rows 81 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-3538325 | kv3_hub_C | 3_3_place_gp | 7.6 | overflow best 0.0994 last 0.0994 rows 48 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t62-920776 | ot_s81sl_leaf__t62 | 5_1_grt | 5.2 | last meaningful line 3.0 h ago (205/240 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t72-932176 | ot_s81sl_leaf__t72 | 5_1_grt | 5.2 | last meaningful line 1.3 h ago (207/216 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | head-actualclock-FF-16755 | head-actualclock-FF | run | 0.0 | last meaningful line 0.0 h ago (566/567 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | head-actualclock-TT-16697 | head-actualclock-TT | run | 0.0 | last meaningful line 0.0 h ago (555/556 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | kvr2e9-kit | kvr2e9-kit | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 53.4 | repair_TNS best 303886 last 303886 rows 8 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 53.4 | repair_TNS best 379203 last 379203 rows 4 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t28-2091344 | ot_s81sl_leaf__t28 | 5_1_grt | 5.3 | last meaningful line 1.3 h ago (204/214 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t34-2093853 | ot_s81sl_leaf__t34 | 5_1_grt | 5.3 | last meaningful line 3.5 h ago (199/234 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-hd_serdes-787792 | hd_serdes | 3_3_place_gp | 0.7 | overflow best 0.2045 last 0.2045 rows 44 | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 21.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 11.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 45.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1588687 | cbx_q10 | 5_1_grt | 4.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 20.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-phy__t1-521400 | phy__t1 | 5_1_grt | 11.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-2717826 | sle_fe_v1 | 5_1_grt | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3267375 | sle_fe_v1 | pregrt_ff_hold | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-4120208 | sle_fe_v1 | 4_1_cts | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 5_1_grt | 11.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 5_1_grt | 10.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slice_station__t42__clcf44e680-3277913 | slice_station__t42 | 5_2_route | 3.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-count-p1_tc-2308651 | count-p1_tc | prd_count_p1_tc | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v1n-3540261 | kv3_pv_v1n | 5_1_grt | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 45.3 | last meaningful line 0.4 h ago (1608/1608 lines) | PROGRESS: log still growing |  |
