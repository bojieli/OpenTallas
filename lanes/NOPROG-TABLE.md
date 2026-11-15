# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-15 04:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 1, 'YOUNG': 74, 'NO-DATA': 5, 'KEEP': 6, 'EXCLUDED': 76, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-serdes__t3-1111613 | serdes__t3 | 5_1_grt | 13.7 | repair_Remaining best 167661 last 167661 rows 311 | before-window best 167661, window best - | NO-PROGRESS: no new repair_Remaining row in 6 h | REPORTED (cancel next pass) |
| intel1 | happy_hodgkin | happy_hodgkin | lec | 35.7 | LEC last write 1.7 h ago | CANCEL-NOW: LEC >24h, advisory | REPORT-ONLY: no ot-heavy scope |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 1.8 | last meaningful line 0.4 h ago (1365/1365 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dhr1-drt7-small96-p16g | dhr1-drt7-small96-p16g | drt_TT | 0.6 | last meaningful line 0.3 h ago (1383/1383 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dhr1-unit-u198_a-drt | dhr1-unit-u198_a-drt | drt | 0.1 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dhr1-unit-u198_b-prep | dhr1-unit-u198_b-prep | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dhr1-unit-u201_a-drt | dhr1-unit-u201_a-drt | drt | 0.1 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dhr1-unit-u201_b-prep | dhr1-unit-u201_b-prep | prep | 0.1 | last meaningful line 0.1 h ago (6/6 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dhr1-unit-u261_a-drt | dhr1-unit-u261_a-drt | drt | 0.1 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dhr1-unit-u261_b-prep | dhr1-unit-u261_b-prep | prep | 0.1 | last meaningful line 0.1 h ago (6/6 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01-2429332 | cbf_q01 | 3_3_place_gp | 0.7 | overflow best 0.6549 last 0.6549 rows 5 | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-186036 | cbn_q00 | pregrt_ff_hold | 3.6 | repair_TNS best 397074 last 397074 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-189478 | cbn_q11 | pregrt_ff_hold | 3.6 | repair_TNS best 1.34695e+06 last 1.34695e+06 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-600402 | col_h9_r0_p1__t1 | 5_1_grt | 8.5 | repair_Remaining best 130368 last 130368 rows 75 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-316849 | col_h9_r0_p2__t1 | 5_1_grt | 14.0 | repair_TNS best 1.03536e+06 last 1.03536e+06 rows 2 | YOUNG: series started inside the last 6 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2094304 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg-1462659 | kv3_hg | 3_3_place_gp | 1.5 | overflow best 0.0998 last 0.0998 rows 44 | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg-1462659-lec | kv3_hg | lec | 1.3 | LEC last write 0.0 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc2 | dpkit-kv3_hg-711961 | kv3_hg | lec | 5.0 | LEC last write 0.1 h ago | YOUNG: evidence 5.0 h < 6 h |  |
| epyc2 | dpkit-kv3_hg-711961-lec | kv3_hg | lec | 4.9 | LEC last write 0.1 h ago | YOUNG: evidence 4.9 h < 6 h |  |
| epyc2 | dpkit-kv3_hg-718010 | kv3_hg | lec | 5.0 | LEC last write 0.1 h ago | YOUNG: evidence 5.0 h < 6 h |  |
| epyc2 | dpkit-kv3_hg-718010-lec | kv3_hg | lec | 4.9 | LEC last write 0.1 h ago | YOUNG: evidence 4.9 h < 6 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-1458540 | kv3_hgi_v2 | pregrt_ff_hold | 1.5 | repair_TNS best 1.89004e+06 last 1.89004e+06 rows 1 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-699312 | kv3_hgi_v2 | 5_1_grt | 5.1 | repair_Remaining best 152933 last 152933 rows 67 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-706931 | kv3_hgi_v2 | 5_1_grt | 5.0 | repair_Remaining best 152949 last 152949 rows 67 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Eo-1875680 | kv3_hub_Eo | 3_1_place_gp_skip_io | 1.2 | overflow best 0.6399 last 0.6399 rows 29 | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-2055645 | kv3_hub_Wo | 3_3_place_gp | 1.0 | overflow best 0.211 last 0.211 rows 32 | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc__cl254f2e73-3316517-lec | kv3_pc | lec | 5.8 | LEC last write 0.1 h ago | YOUNG: evidence 5.8 h < 6 h |  |
| epyc2 | dpkit-kv3_pc__cl5a95b461-1137592-lec | kv3_pc | lec | 4.8 | LEC last write 0.2 h ago | YOUNG: evidence 4.8 h < 6 h |  |
| epyc2 | dpkit-slw_hc1__cl3449ea95-3794593-lec | slw_hc1 | lec | 5.4 | LEC last write 0.1 h ago | YOUNG: evidence 5.4 h < 6 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b-3856794-lec | slw_hc3 | lec | 5.4 | LEC last write 0.1 h ago | YOUNG: evidence 5.4 h < 6 h |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1719686 | slw_st_b_v1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t3-1267116 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t4-1151180 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 1.7 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dproto-head-mp5-otclk | dproto-head-mp5-otclk | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | fkvovf-sta2-3388410 | fkvovf-sta2 | pregrt_ff_hold | 0.0 | repair_TNS best 1.89004e+06 last 1.89004e+06 rows 1 | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2787375 | col_h9_r2__t1 | 5_1_grt | 29.8 | repair_TNS best 612620 last 612620 rows 18 | YOUNG: series started inside the last 6 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv22267ca0-2662496 | col_h9_r2__t1 | 5_1_grt | 30.0 | repair_TNS best 571105 last 571105 rows 9 | YOUNG: series started inside the last 6 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-1138516 | col_h9_r2__t1 | 5_2_route | 27.0 | drt_violations best 289 last 289 rows 10 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb11188eb-2664314 | col_h9_r2__t1 | 5_1_grt | 30.0 | repair_TNS best 577951 last 577951 rows 3 | YOUNG: series started inside the last 6 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvf57acd2b-3762255 | col_h9_r2__t1 | 5_2_route | 26.7 | drt_violations best 276 last 276 rows 21 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-1525696 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-1935886 | dsdv_slice_c1x_C__t1 | 2_1_floorplan | 2.9 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t3-2766175 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.7 h ago (149/149 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1916635 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t5-1163667 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2802431 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.7 h ago (152/152 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t26-2560093 | ot_s81sl_leaf__t26 | 5_1_grt | 12.5 | repair_TNS best 81186.9 last 81186.9 rows 33 | YOUNG: series started inside the last 6 h |  |
| epyc7 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-438306 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 2.4 | last meaningful line 0.2 h ago (300/300 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-95257 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 3.0 | last meaningful line 0.3 h ago (302/302 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | frc-s81-B6gsh-otclk | frc-s81-B6gsh-otclk | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | m7hgg-749463 | m7hgg | 5_1_grt | 5.5 | last meaningful line 5.0 h ago (212/254 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t10-1740744 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 3.5 | last meaningful line 1.5 h ago (153/153 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t9-2828858 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 2.9 | last meaningful line 0.7 h ago (148/148 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-1976130 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 3.4 | last meaningful line 1.2 h ago (153/153 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-3391750 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 2.6 | last meaningful line 0.5 h ago (152/152 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-hd_ctl-1931080-lec | hd_ctl | lec | 3.3 | LEC last write 0.0 h ago | YOUNG: evidence 3.3 h < 6 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 9.9 | repair_Remaining best 29893 last 29893 rows 134 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2540814 | kit | 5_1_grt | 9.9 | repair_TNS best 429140 last 429140 rows 36 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2541488 | kit | 5_1_grt | 9.9 | repair_TNS best 599775 last 599775 rows 1 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-3952785 | kit | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (846/846 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-2552608 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 3.1 | last meaningful line 0.0 h ago (171/171 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-2538819 | serdes__t14 | 5_2_route | 9.9 | last meaningful line 0.2 h ago (267/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__clcc5e3e61-169369-lec | sle_hc2 | lec | 3.9 | LEC last write 0.2 h ago | YOUNG: evidence 3.9 h < 6 h |  |
| intel1 | dpkit-sle_st_b_v2__clfde1249e-2052014-lec | sle_st_b_v2 | lec | 3.0 | LEC last write 0.1 h ago | YOUNG: evidence 3.0 h < 6 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | 5_1_grt | 9.9 | repair_TNS best 228496 last 228496 rows 4 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | 5_1_grt | 9.9 | repair_TNS best 123483 last 123483 rows 1 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cle683a076-133180-lec | slw_hc1 | lec | 3.9 | LEC last write 0.3 h ago | YOUNG: evidence 3.9 h < 6 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t3-2798011 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 2.9 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-2672411 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 3.0 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | flamboyant_maxwell | flamboyant_maxwell | - | 5.1 |  | NO-DATA: no log found |  |
| intel1 | optimistic_franklin | optimistic_franklin | - | 5.2 |  | NO-DATA: no log found |  |
| intel2 | dpkit-hd_mesh-2429139-lec | hd_mesh | lec | 5.8 | LEC last write 0.5 h ago | YOUNG: evidence 5.8 h < 6 h |  |
| intel2 | dpkit-kv3_pv_v4n-1133856 | kv3_pv_v4n | 3_5_place_dp | 6.6 | last meaningful line 0.5 h ago (114/114 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-3734467 | sle_fw_v1 | 5_1_grt | 7.9 | last meaningful line 0.0 h ago (1177/1177 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-3735985 | sle_fw_v1 | 5_1_grt | 7.9 | last meaningful line 0.0 h ago (1222/1222 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-3019172-lec | sle_hc0 | lec | 5.3 | LEC last write 0.3 h ago | YOUNG: evidence 5.3 h < 6 h |  |
| intel2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152-2933994-lec | sle_hc2 | lec | 5.3 | LEC last write 0.2 h ago | YOUNG: evidence 5.3 h < 6 h |  |
| intel2 | dpkit-slw_hc0__cl1bc59e1c-2964785-lec | slw_hc0 | lec | 5.3 | LEC last write 0.3 h ago | YOUNG: evidence 5.3 h < 6 h |  |
| intel2 | dpkit-slw_hc2__cla3497502__cl16607c7a-3006742-lec | slw_hc2 | lec | 5.3 | LEC last write 0.3 h ago | YOUNG: evidence 5.3 h < 6 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-2839123 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 5.7 | last meaningful line 2.0 h ago (302/302 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-3966284 | col_h10_r1__t1 | 5_1_grt | 5.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-4032125 | col_h9_r0_p3__t1 | 5_1_grt | 5.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-2061436 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hg_v1p2-1725066 | kv3_hg_v1p2 | pregrt_ff_hold | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v1__cl141fc26e-1200306 | kv3_hgi_v1 | 5_1_grt | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-4011686 | kv3_hgi_v2 | 5_1_grt | 5.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-4076024 | kv3_hgi_v2 | 5_1_grt | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v3-1206504 | kv3_hgi_v3 | pregrt_ff_hold | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hub_Eo-1630185 | kv3_hub_Eo | pregrt_ff_hold | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_io_cor-321776 | kv3_io_cor | 5_2_route | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv-1581125 | kv3_pv | pregrt_ff_hold | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-1381363 | kv3_pv_v8 | 4_1_cts | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-2902549 | kv3_pv_v8 | pregrt_ff_hold | 9.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2497812 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 6.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t11-4027960 | ot_s81sl_leaf__t11 | 5_1_grt | 5.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-phy__t1-746475 | phy__t1 | pregrt_ff_hold | 2.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-serdes__t14-1427227 | serdes__t14 | postcts_gate_TT | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1397514 | sle_stm_v2 | 4_1_cts | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-731444 | slw_stm_v1 | 4_1_cts | 2.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-cbn_q11__cl49ae4555-2688009 | cbn_q11 | 5_1_grt | 2.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4147164 | col_h10_r1__t1 | 5_1_grt | 5.5 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2246910 | col_h9_r1__t1 | 5_1_grt | 30.6 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t24__cl2456157b-3963505 | ot_s81sl_leaf__t24 | 5_1_grt | 9.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t42-1046186 | ot_s81sl_leaf__t42 | 5_1_grt | 5.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2448993 | ot_s81sl_leaf__t44 | 5_1_grt | 8.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slice_station__t24__cleece78ec-2368652 | slice_station__t24 | pregrt_ff_hold | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slice_station__t42__cl4bd1432c-2406029 | slice_station__t42 | 5_1_grt | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-681814 | slice_station__t6 | 5_2_route | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | hbmcore-faceA_-2975207 | faceA_ | lec | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | hbmcore-faceB_-2975667 | faceB_ | lec | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | prd-count-p1_tc-3743207 | count-p1_tc | prd_count_p1_tc | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-3752134 | col_h10_r1__t1 | pregrt_ff_hold | 5.7 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3471904 | col_h10_r1__t1 | 5_1_grt | 9.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1731869 | col_h9_r0_p5__t1 | 5_1_grt | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-3752408 | col_h9_r1__t1 | pregrt_ff_hold | 5.7 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-coll_ftc-2208645 | coll_ftc | 5_2_route | 3.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_ctl-3630743 | hd_ctl | 5_1_grt | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-hd_spn_end-3730029 | hd_spn_end | 5_2_route | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t1-1637174 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-ot_s81sl_leaf__t36-1770007 | ot_s81sl_leaf__t36 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-ot_s81sl_leaf__t4-1696625 | ot_s81sl_leaf__t4 | 5_1_grt | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-ot_s81sl_leaf__t41-1777114 | ot_s81sl_leaf__t41 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-ot_s81sl_leaf__t59-1531980 | ot_s81sl_leaf__t59 | 5_1_grt | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-ot_s81sl_leaf__t67-1672333 | ot_s81sl_leaf__t67 | 5_1_grt | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-serdes__t1__clfe1f0815-4089644 | serdes__t1 | 5_1_grt | 9.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-serdes__t3-2758499 | serdes__t3 | 5_1_grt | 3.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1394431 | sle_fe_v1 | 5_2_route | 7.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2421779 | sle_fe_v1 | 5_1_grt | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36-1520610 | sle_hc1 | 5_1_grt | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_st_b_v2__clfde1249e-802879 | sle_st_b_v2 | 4_1_cts | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slice_station__t25-4178214 | slice_station__t25 | 5_2_route | 5.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3757943 | slice_station__t40 | 5_2_route | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1471491 | slw_fe_v1 | 5_2_route | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cle683a076-1707681 | slw_hc1 | 5_1_grt | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-1679747 | slw_hc2 | postcts_gate_FF | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2055284 | slw_stm_v2 | 5_1_grt | 3.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | hbmcore-kit_-2287051 | kit_ | 5_2_route | 3.2 |  | KEEP: /claude/type-hdcore-elemab/	TYPE-HDCORE-ELEMAB	HEAD cores built with the HBM kit |  |
| intel2 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2338487 | col_h10_r2__t1 | 5_1_grt | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3851006 | col_h9_r0_p4__t1 | 5_1_grt | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pv35382794-368710 | col_h9_r0_p5__t1 | 5_1_grt | 7.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4063614 | col_h9_r0_p5__t1 | 5_1_grt | 7.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pvde240d6d-298115 | col_h9_r0_p6__t1 | 5_1_grt | 7.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-dsdv_slice_lepw_mus_LP__t2-4021371 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-3915887 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-3981257 | ot_s81sl_leaf__t10 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t14-47752 | ot_s81sl_leaf__t14 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-3980398 | ot_s81sl_leaf__t2 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t39-3998300 | ot_s81sl_leaf__t39 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t46-3943921 | ot_s81sl_leaf__t46 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t5-3892518 | ot_s81sl_leaf__t5 | 5_1_grt | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t51-3806592 | ot_s81sl_leaf__t51 | 5_1_grt | 7.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t52-3789221 | ot_s81sl_leaf__t52 | 5_1_grt | 7.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3811971 | ot_s81sl_leaf__t53 | 5_1_grt | 7.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-4151302 | ot_s81sl_leaf__t58 | 5_1_grt | 7.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t6-3816875 | ot_s81sl_leaf__t6 | 5_2_route | 7.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t61-3994171 | ot_s81sl_leaf__t61 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t74-4008110 | ot_s81sl_leaf__t74 | 5_1_grt | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3723276 | sle_hc2 | 5_2_route | 7.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152-4003630 | sle_hc2 | 5_2_route | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-slice_station__t27-3831616 | slice_station__t27 | 5_2_route | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-slice_station__t27-3986615 | slice_station__t27 | 5_2_route | 7.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-slice_station__t6__cl54a9ceeb-2342536 | slice_station__t6 | 5_2_route | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-600318 | col_h9_r0_p1__t1 | 5_1_grt | 8.5 | last meaningful line 0.0 h ago (1300/1300 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-318081 | col_h9_r0_p2__t1 | 5_1_grt | 14.0 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-kv3_hg_v1p5-2393816-lec | kv3_hg_v1p5 | lec | 6.4 | LEC last write 0.1 h ago | PROGRESS: LEC still writing |  |
| epyc2 | dpkit-kv3_hg_v1p6-2384061-lec | kv3_hg_v1p6 | lec | 6.4 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
| epyc2 | dpkit-kv3_pc__cl5a95b461-3396823-lec | kv3_pc | lec | 16.1 | LEC last write 0.0 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2258510 | col_h9_r2__t1 | 5_1_grt | 30.6 | last meaningful line 0.0 h ago (2449/2449 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-2662258 | col_h9_r2__t1 | 5_1_grt | 30.0 | last meaningful line 0.0 h ago (2801/2801 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t53__cl958451dd-1341790 | ot_s81sl_leaf__t53 | 5_1_grt | 9.7 | last meaningful line 3.0 h ago (363/364 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-serdes__t13-3244412-lec | serdes__t13 | lec | 9.8 | LEC last write 2.0 h ago | PROGRESS: LEC still writing |  |
| epyc7 | klegacy-dsdv_gunit_l1f_bf_gf5g3f-2323851 | dsdv_gunit_l1f_bf_gf5g3f | 5_2_route | 5.6 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-kit-2542756 | kit | 5_1_grt | 9.9 | last meaningful line 0.0 h ago (1780/1780 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kit-2544581 | kit | 5_1_grt | 9.9 | last meaningful line 0.0 h ago (1780/1780 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 9.9 | last meaningful line 0.1 h ago (869/869 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-serdes__t4-2999799-lec | serdes__t4 | lec | 17.3 | LEC last write 0.3 h ago | PROGRESS: LEC still writing |  |
| intel2 | dpkit-cbn_q11__cl5cc92dfe-3737497 | cbn_q11 | 5_1_grt | 7.9 | repair_Violations best 0 last 0 rows 19 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p3-1105936-lec | kv3_hg_v1p3 | lec | 6.4 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
| intel2 | dpkit-kv3_hg_v1p4-1062077-lec | kv3_hg_v1p4 | lec | 6.4 | LEC last write 0.0 h ago | PROGRESS: LEC still writing |  |
| intel2 | dpkit-kv3_sys_c-495233-lec | kv3_sys_c | lec | 7.0 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
