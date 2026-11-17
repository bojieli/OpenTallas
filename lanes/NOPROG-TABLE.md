# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-17 03:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 9, 'EXCLUDED': 36, 'PROGRESS': 2}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-serdes__t13-1235488 | serdes__t13 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2904 last 0.2904 rows 42 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t13-1235700 | serdes__t13 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2638 last 0.2638 rows 43 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-744407 | svc_lo_dsdv_svc_rs__t7 | 2_1_floorplan | 0.9 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_1406914_ff_11843 | so_1406914_ff_11843 | sta | 0.0 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1406914_tt_11843 | so_1406914_tt_11843 | sta | 0.0 | last meaningful line 0.0 h ago (387/387 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kit_hd_ctl-2177420 | kit_hd_ctl | 5_2_route | 1.3 | drt_violations best 50080 last 50080 rows 1 | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hub_C-3538325 | kv3_hub_C | 3_4_place_resized | 11.1 | last meaningful line 2.0 h ago (948/948 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 57.2 | repair_TNS best 287330 last 287330 rows 5 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 57.2 | repair_TNS best 360848 last 360848 rows 1 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 24.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 15.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 49.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1588687 | cbx_q10 | 5_1_grt | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-glue-1675098 | glue | 5_1_grt | 2.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 24.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-2717826 | sle_fe_v1 | 5_2_route | 5.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3267375 | sle_fe_v1 | 5_2_route | 4.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-4120208 | sle_fe_v1 | 5_2_route | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1175569 | sle_hc2 | postcts_gate_TT | 2.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f-2212034 | sle_st_a_v2 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_fw_v1__cl51d45468-1411029 | slw_fw_v1 | 5_1_grt | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-1181211 | slw_hc0 | postcts_gate_TT | 2.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | prd-eco_20261117_103636_1168872-i1t-2805374 | eco_20261117_103636_1168872-i1t | 5_2_route | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 5_1_grt | 15.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 5_1_grt | 14.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-633264 | sle_hc2 | 3_5_place_dp | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v1__pv0e7b1dcc-830807 | sle_st_b_v1 | 3_3_place_gp | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-830740 | sle_st_b_v2 | 3_3_place_gp | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-831716 | sle_st_b_v2 | 3_3_place_gp | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v2__clfde1249e-576583 | sle_st_b_v2 | 3_3_place_gp | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_stm_v3-418792 | sle_stm_v3 | 4_1_cts | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_su_l1__clc6d66f5b-312121 | sle_su_l1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fw_v2__cl8537f156-747897 | slw_fw_v2 | 3_3_place_gp | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-748157 | slw_fw_v2 | 3_3_place_gp | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-639745 | slw_hc1 | 3_4_place_resized | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-641692 | slw_hc2 | 3_5_place_dp | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-576361 | slw_sc_v1 | 3_4_place_resized | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_st_a_v2__cl9f076a5c-381769 | slw_st_a_v2 | 5_1_grt | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-644320 | slw_stm_v1 | 3_3_place_gp | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-576862 | slw_stm_v2 | 3_3_place_gp | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-577119 | slw_stm_v2 | 3_3_place_gp | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-311708 | slw_su_l1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-tt_ctlm-424280 | tt_ctlm | 4_1_cts | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1gt-1973717 | eco_20261116_023111_238129-i1gt | 5_2_route | 3.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v1n-3540261 | kv3_pv_v1n | 5_1_grt | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 48.8 | last meaningful line 0.1 h ago (1616/1616 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-serdes__t13-638264 | serdes__t13 | 4_1_cts | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
