# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-17 01:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 11, 'NO-DATA': 2, 'EXCLUDED': 17, 'PROGRESS': 1}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-serdes__t13-121443 | serdes__t13 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.2139 last 0.2139 rows 43 | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | fdqrs4q9n_nb-kit | fdqrs4q9n_nb-kit | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-hd_serdes-940414 | hd_serdes | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (190/216 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kit_hd_ctl-4092960 | kit_hd_ctl | postcts_gate_TT | 2.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-3538325 | kv3_hub_C | 3_4_place_resized | 9.6 | last meaningful line 0.5 h ago (948/948 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | htl_insert_1779032 | htl_insert_1779032 | - | 0.3 |  | NO-DATA: no log found |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 55.4 | repair_TNS best 295130 last 295130 rows 7 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 55.4 | repair_TNS best 369774 last 369774 rows 3 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t34-2093853 | ot_s81sl_leaf__t34 | 5_1_grt | 7.3 | grt_overflow best 3516 last 3516 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-2917623 | slw_fw_v1 | 3_3_place_gp | 0.7 | overflow best 0.0993 last 0.0993 rows 41 | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2917208 | slw_hc1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-3010164 | slw_hc2 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_serdes-787792 | hd_serdes | tt_setup_repair_grt | 2.7 | last meaningful line 0.0 h ago (751/751 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 23.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 13.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 47.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1588687 | cbx_q10 | 5_1_grt | 6.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-glue-1675098 | glue | 4_1_cts | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 22.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-2717826 | sle_fe_v1 | 5_2_route | 4.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3267375 | sle_fe_v1 | 5_2_route | 3.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-4120208 | sle_fe_v1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v3-1168996 | sle_fe_v3 | 5_2_route | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1175569 | sle_hc2 | pregrt_ff_hold | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_fw_v1__cl51d45468-1411029 | slw_fw_v1 | tt_setup_repair | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-1181211 | slw_hc0 | pregrt_ff_hold | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 5_1_grt | 13.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 5_1_grt | 12.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1gt-1973717 | eco_20261116_023111_238129-i1gt | 5_1_grt | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v1n-3540261 | kv3_pv_v1n | 5_1_grt | 4.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 47.3 | last meaningful line 0.4 h ago (1612/1612 lines) | PROGRESS: log still growing |  |
