# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-17 08:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'YOUNG': 9, 'NO-DATA': 3, 'EXCLUDED': 39, 'PROGRESS': 2}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 0.2 | last meaningful line 0.1 h ago (1363/1363 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t13-153484 | serdes__t13 | 5_1_grt | 1.3 | repair_Remaining best 59654 last 59654 rows 331 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t13-476605 | serdes__t13 | pregrt_ff_hold | 1.0 | repair_TNS best 20857.7 last 20857.7 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t13-502221 | serdes__t13 | pregrt_ff_hold | 0.9 | repair_TNS best 24745.6 last 24745.6 rows 1 | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | otc-811279-5016 | 811279 | lec | 0.6 | LEC last write 0.6 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc7 | dpkit-kv3_hub_C-3538325 | kv3_hub_C | 3_5_place_dp | 16.1 | last meaningful line 3.5 h ago (115/115 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | otc-1791435-18327 | 1791435 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | r4sd9f-eco2 | r4sd9f-eco2 | 5_2_route_ecodrt2 | 0.3 | drt_violations best 1158 last 1158 rows 1 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_1663399_ff_28126 | so_1663399_ff_28126 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_1663399_tt_28126 | so_1663399_tt_28126 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 61.9 | repair_TNS best 269768 last 269768 rows 4 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 61.9 | repair_TNS best 340836 last 340836 rows 2 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2230510 | cbn_q11 | 5_1_grt | 29.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3740733 | cbn_q11 | 5_1_grt | 20.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | 5_1_grt | 54.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1588687 | cbx_q10 | 5_1_grt | 12.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2280690 | kv3_pc | 5_1_grt | 29.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-998608 | sle_su_l1 | 5_2_route | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1001022 | slw_fe_v1 | pregrt_ff_hold | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_fe_v2__cle312294d-1004221 | slw_fe_v2 | pregrt_ff_hold | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_fw_v1__cl51d45468-1411029 | slw_fw_v1 | 6_report | 7.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_hc3__clccfc3e6b-1007715 | slw_hc3 | 5_1_grt | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4-1003908 | slw_hc3 | pregrt_ff_hold | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | prd-eco_20261117_151445_1175384-i1-1522554 | eco_20261117_151445_1175384-i1 | 5_2_route | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | prd-eco_20261117_152310_1674454-i1t-1600407 | eco_20261117_152310_1674454-i1t | 5_2_route | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | prd-eco_20261117_155129_4119974-i1t-1852904 | eco_20261117_155129_4119974-i1t | 5_1_grt | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2756335 | cbf_q00 | 5_1_grt | 19.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-3365622 | cbn_q11 | 5_1_grt | 18.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-3493656 | sle_fe_v1 | pregrt_ff_hold | 2.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-633264 | sle_hc2 | postcts_gate_FF | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3272845 | sle_sc_v1 | 5_1_grt | 2.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v1__pv0e7b1dcc-830807 | sle_st_b_v1 | tt_setup_measure_grt | 5.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-830740 | sle_st_b_v2 | postcts_gate_TT | 5.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-831716 | sle_st_b_v2 | postcts_gate_TT | 5.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_su_l1__clc6d66f5b-312121 | sle_su_l1 | 5_2_route | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3342924 | slw_fe_v1 | 5_1_grt | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fw_v2__cl8537f156-747897 | slw_fw_v2 | postcts_gate_TT | 5.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-748157 | slw_fw_v2 | 5_1_grt | 5.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-639745 | slw_hc1 | postcts_gate_TT | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-641692 | slw_hc2 | postcts_gate_FF | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-576361 | slw_sc_v1 | 5_2_route | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_st_a_v2__cl9f076a5c-381769 | slw_st_a_v2 | 5_1_grt | 5.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_st_a_v2__clf4365a62-2140557 | slw_st_a_v2 | 5_1_grt | 4.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-644320 | slw_stm_v1 | postcts_gate_TT | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-576862 | slw_stm_v2 | 5_1_grt | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-577119 | slw_stm_v2 | postcts_gate_TT | 5.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-2395140 | slw_su_l1 | 5_1_grt | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-311708 | slw_su_l1 | 5_1_grt | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-2367146 | slw_su_l1 | 5_1_grt | 3.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco_20261116_023111_238129-i1g-692412 | eco_20261116_023111_238129-i1g | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v1n-3540261 | kv3_pv_v1n | 5_1_grt | 10.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | klegacy-dsdv_bksel_c_rfdq-1132557 | dsdv_bksel_c_rfdq | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | klegacy-dsdv_bksel_c_rfdq-1132557-lec | dsdv_bksel_c_rfdq | 3_5_place_dp | 0.2 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
