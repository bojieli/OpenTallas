# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-14 20:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 1, 'YOUNG': 109, 'NO-DATA': 2, 'KEEP': 2, 'EXCLUDED': 32, 'PROGRESS': 43}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-kv3_hub_C-2125571 | kv3_hub_C | lec | 8.1 | LEC last write 6.2 h ago | NO-PROGRESS: no new LEC file/log write for 6.2 h | REPORTED (cancel next pass) |
| intel1 | happy_hodgkin | happy_hodgkin | lec | 27.7 | LEC last write 0.3 h ago | CANCEL-NOW: LEC >24h, advisory | REPORT-ONLY: no ot-heavy scope |
| epyc2 | dpkit-cbn_q00__cld7bf7197-225963 | cbn_q00 | 3_3_place_gp | 1.0 | overflow best 0.3759 last 0.3759 rows 28 | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cld7bf7197-227128 | cbn_q00 | 3_3_place_gp | 1.0 | overflow best 0.4471 last 0.4471 rows 21 | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-600318 | col_h9_r0_p1__t1 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (203/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-600402 | col_h9_r0_p1__t1 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (202/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-316849 | col_h9_r0_p2__t1 | 5_1_grt | 6.2 | repair_Remaining best 171747 last 171747 rows 30 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-318081 | col_h9_r0_p2__t1 | 5_1_grt | 6.2 | last meaningful line 2.2 h ago (205/217 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2870809 | col_h9_r1__t1 | 5_1_grt | 9.6 | repair_Remaining best 53549 last 53549 rows 74 | YOUNG: series started inside the last 7.5 h |  |
| epyc2 | dpkit-hd_ctl_n-752590 | hd_ctl_n | 5_2_route | 0.7 | last meaningful line 0.0 h ago (243/243 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kit-382138 | kit | 5_2_route | 3.9 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-kit-382419 | kit | 5_2_route | 3.9 | last meaningful line 0.2 h ago (250/251 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kit-805367 | kit | 5_1_grt | 8.4 | grt_overflow best 96 last 96 rows 1 | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-3379184 | kv3_hg_v1p5 | 3_4_place_resized | 4.5 | last meaningful line 0.0 h ago (434/434 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v3-315863 | kv3_hg_v3 | 5_1_grt | 6.3 | last meaningful line 2.2 h ago (216/244 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-2721746 | kv3_hgi_v4 | pregrt_ff_hold | 2.4 | repair_TNS best 174328 last 174328 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1183053 | kv3_hroot | 5_1_grt | 5.8 | repair_TNS best 240.61 last 240.61 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-2295925 | kv3_hub_Ei | lec | 2.6 | LEC last write 0.1 h ago | YOUNG: evidence 2.6 h < 6 h |  |
| epyc2 | dpkit-kv3_io_ft_v1-2648778 | kv3_io_ft_v1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (221/222 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc__cl5a95b461-2069926 | kv3_pc | lec | 2.7 | LEC last write 0.2 h ago | YOUNG: evidence 2.7 h < 6 h |  |
| epyc2 | dpkit-kv3_pc__cl5a95b461-2695086 | kv3_pc | pregrt_ff_hold | 2.4 | repair_TNS best 1.81453e+06 last 1.81453e+06 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc_v1__cl7f648944-2777314 | kv3_pc_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 3.00835e+06 last 3.00835e+06 rows 1 | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv-1242006 | kv3_pv | pregrt_ff_hold | 5.8 | repair_TNS best 3.93976e+06 last 3.93976e+06 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v12-2819817 | kv3_pv_v12 | 3_3_place_gp | 2.4 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v1n-3461146 | kv3_pv_v1n | 3_3_place_gp | 4.4 | overflow best 0.3051 last 0.5874 rows 182 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v2n-1222059 | kv3_pv_v2n | 3_3_place_gp | 1.8 | last meaningful line 0.1 h ago (26/26 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v2n-1222059-lec | kv3_pv_v2n | lec | 1.0 | LEC last write 0.1 h ago | YOUNG: evidence 1.0 h < 6 h |  |
| epyc2 | dpkit-kv3_pv_v3-1219367 | kv3_pv_v3 | 3_3_place_gp | 1.8 | last meaningful line 0.1 h ago (26/26 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3-1219367-lec | kv3_pv_v3 | lec | 1.0 | LEC last write 0.1 h ago | YOUNG: evidence 1.0 h < 6 h |  |
| epyc2 | dpkit-kv3_pv_v4n-1624690 | kv3_pv_v4n | 3_3_place_gp | 10.2 | overflow best 0.2987 last 0.6623 rows 480 | YOUNG: series started inside the last 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5-2800367 | kv3_pv_v5 | 3_3_place_gp | 2.4 | last meaningful line 0.3 h ago (26/26 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5n-1638573 | kv3_pv_v5n | 3_3_place_gp | 10.2 | overflow best 0.0986 last 0.0986 rows 341 | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t4-3958471 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 11.1 | repair_Remaining best 112319 last 112319 rows 238 | YOUNG: series started inside the last 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t28-904300 | ot_s81sl_leaf__t28 | 5_1_grt | 6.0 | last meaningful line 2.1 h ago (208/216 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t3-1111613 | serdes__t3 | 5_1_grt | 5.9 | last meaningful line 0.3 h ago (202/210 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-883108 | slw_fw_v1 | 5_2_route | 6.0 | last meaningful line 0.5 h ago (386/387 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | kqc-hd_cland_w1107_ew_34b9e_synth0-3659836 | hd_cland_w1107_ew_34b9e_synth0 | 5_1_grt | 1.4 | repair_TNS best 86353.5 last 86353.5 rows 14 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | kqc-kv_cland_w1057_ew_94a44_synth0-3656421 | kv_cland_w1057_ew_94a44_synth0 | sta_FF | 1.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kqc-qfd_dv_s5_ctl_repair4_leaf_synth0-2392711 | qfd_dv_s5_ctl_repair4_leaf_synth0 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-3972895 | col_h9_r0_p2__t1 | 5_1_grt | 16.3 | repair_Remaining best 93763 last 93763 rows 62 | YOUNG: series started inside the last 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-3985947 | col_h9_r0_p2__t1 | 5_1_grt | 16.3 | repair_Remaining best 93763 last 93763 rows 62 | YOUNG: series started inside the last 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-189394 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 1.11536e+06 last 1.11536e+06 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-1862437 | col_h9_r1__t1 | 5_1_grt | 8.4 | repair_Remaining best 68549 last 68549 rows 59 | YOUNG: series started inside the last 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_iq_C__t1-2659022 | dsdv_slice_iq_C__t1 | 3_4_place_resized | 1.7 | repair_Remaining best 82102 last 82102 rows 472 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mus_C__t1-1157631 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 2.4 | last meaningful line 0.8 h ago (152/152 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-181260 | hd_ctl | 5_1_grt | 1.7 | repair_TNS best 124508 last 124508 rows 17 | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t16-2525530 | ot_s81sl_leaf__t16 | 5_1_grt | 4.5 | repair_Remaining best 120970 last 120970 rows 48 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t26-2560093 | ot_s81sl_leaf__t26 | 5_1_grt | 4.5 | repair_Remaining best 65756 last 65756 rows 75 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t5-3531899 | ot_s81sl_leaf__t5 | 5_2_route | 8.4 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t53__cl958451dd-1341790 | ot_s81sl_leaf__t53 | 5_1_grt | 1.7 | last meaningful line 0.5 h ago (199/210 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t74-3544392 | ot_s81sl_leaf__t74 | 5_1_grt | 8.4 | repair_Remaining best 53465 last 53465 rows 115 | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-3244412-lec | serdes__t13 | lec | 1.8 | LEC last write 0.6 h ago | YOUNG: evidence 1.8 h < 6 h |  |
| epyc7 | dpkit-slice_station__t29__clc7772371-2860765 | slice_station__t29 | 5_3_fillcell | 4.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | cranky_gauss | cranky_gauss | t | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1331488 | col_h9_r0_p4__t1 | 5_1_grt | 10.0 | last meaningful line 1.8 h ago (203/215 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3564124 | col_h9_r0_p4__t1 | 5_1_grt | 9.3 | last meaningful line 1.8 h ago (203/214 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-coll_n-3794077 | coll_n | lec | 1.1 | LEC last write 0.0 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| intel1 | dpkit-hd_serdes-2543723-lec | hd_serdes | lec | 1.1 | LEC last write 0.9 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kit-2540814 | kit | 5_1_grt | 1.9 | last meaningful line 1.5 h ago (194/218 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kit-2541488 | kit | 5_1_grt | 1.9 | last meaningful line 1.4 h ago (194/218 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kit-2542756 | kit | 5_1_grt | 1.9 | last meaningful line 1.5 h ago (389/442 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kit-2544581 | kit | 5_1_grt | 1.9 | last meaningful line 1.5 h ago (389/442 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor-3864025 | kv3_io_cor | 3_4_place_resized | 1.1 | last meaningful line 0.1 h ago (176/176 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t1-3076967 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 9.4 | repair_TNS best 391110 last 391110 rows 18 | YOUNG: series started inside the last 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-3321561 | ot_s81sl_kv_leaf__t3 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (3753/3753 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t13-2548513 | ot_s81sl_leaf__t13 | 5_1_grt | 1.9 | last meaningful line 1.2 h ago (202/209 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t36-3737354 | ot_s81sl_leaf__t36 | 5_1_grt | 9.2 | repair_TNS best 278319 last 278319 rows 23 | YOUNG: series started inside the last 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t55-3308167 | ot_s81sl_leaf__t55 | pregrt_ff_hold | 1.3 | repair_TNS best 167931 last 167931 rows 1 | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t69-3864542 | ot_s81sl_leaf__t69 | lec | 1.1 | LEC last write -0.0 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t7-1102435 | ot_s81sl_leaf__t7 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-phy__t1-3692498 | phy__t1 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-2538819 | serdes__t14 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (882/882 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-serdes__t15__cla2127225-1054791 | serdes__t15 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t4-2999799 | serdes__t4 | 5_2_route | 9.4 | last meaningful line 1.7 h ago (282/283 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1821434 | sle_fe_v1 | 5_2_route | 15.2 | last meaningful line 1.1 h ago (369/370 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36-3314588 | sle_hc1 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (4664/4664 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36-931656 | sle_hc1 | 5_1_grt | 10.2 | last meaningful line 2.5 h ago (213/291 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508-3321214 | sle_hc1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (5238/5238 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl7479a5ec-3051295 | sle_sc_v1 | pregrt_ff_hold | 1.1 | repair_TNS best 697401 last 697401 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t49-3789740 | slice_station__t49 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (183/183 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1399390 | slw_fe_v1 | 5_2_route | 14.0 | last meaningful line 1.1 h ago (368/369 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2596195 | slw_fe_v1 | pregrt_ff_hold | 1.9 | repair_TNS best 648104 last 648104 rows 1 | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-2553657 | slw_fe_v2 | pregrt_ff_hold | 1.9 | repair_TNS best 518993 last 518993 rows 1 | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cl16607c7a-2595529 | slw_hc2 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (4335/4335 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-3812391 | slw_hc2 | lec | 1.1 | LEC last write 0.5 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-3617193 | slw_stm_v1 | 5_1_grt | 12.9 | repair_TNS best 265983 last 265983 rows 32 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | fh-A-3702488 | fh-A | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (210/215 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | fh-C-3703120 | fh-C | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (194/199 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | kqc-kv_cland_w1045_ns_ddbeb_synth0-3641029 | kv_cland_w1045_ns_ddbeb_synth0 | 5_1_grt | 1.1 | repair_TNS best 95168.7 last 95168.7 rows 243 | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | kqc-kv_cland_w1119_ew_86ca8_synth0-3620753 | kv_cland_w1119_ew_86ca8_synth0 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (221/222 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | kqc-kv_cland_w1560_ew_0433f_synth0-3635791 | kv_cland_w1560_ew_0433f_synth0 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (655/655 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | kqc-kv_cland_w781_ns_8522d_synth0-3804705 | kv_cland_w781_ns_8522d_synth0 | 5_2_route | 1.1 | drt_violations best 427 last 427 rows 2 | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | kqc-kv_cland_w781_ns_9f2d9_synth0-3799117 | kv_cland_w781_ns_9f2d9_synth0 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | kqc-s81_cland_w1105_ew_a49fe_synth0-3622667 | s81_cland_w1105_ew_a49fe_synth0 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (219/220 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | kqc-s81_cland_w2939_ew_6bc7f_synth0-3625815 | s81_cland_w2939_ew_6bc7f_synth0 | 5_1_grt | 1.1 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | kqc-s81_cland_w596_ns_75b27_synth0-3637390 | s81_cland_w596_ns_75b27_synth0 | generate_abstract | 1.1 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | kqc-s81_cland_w669_ns_acc1f_synth0-3639946 | s81_cland_w669_ns_acc1f_synth0 | 6_report | 1.1 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | kqc-sta_region_nb0_h17_n6_s7_synth0-3276556 | sta_region_nb0_h17_n6_s7_synth0 | 1_2_yosys | 1.3 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | kqc-sta_region_nb0_h17_n6_s7_synth0_ns-1017828 | sta_region_nb0_h17_n6_s7_synth0_ns | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (2483/2483 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | kqc-sta_region_nb0_h18_n6_s7_synth0-3276151 | sta_region_nb0_h18_n6_s7_synth0 | 1_2_yosys | 1.3 | last meaningful line 0.0 h ago (283/283 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | kqc-sta_region_nb0_h18_n6_s7_synth0_ns-1004706 | sta_region_nb0_h18_n6_s7_synth0_ns | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (3219/3219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-945759-24937 | 945759 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (2/2 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco99_tile_c-i1t-3830097 | eco99_tile_c-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (123/123 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_1159094_ff_69052 | so_1159094_ff_69052 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | dpkit-cbn_q11__cl5cc92dfe-3737497 | cbn_q11 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (567/567 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t8-3702409 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-hd_host_e-3738967 | hd_host_e | lec | 0.2 | LEC last write 0.0 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-3732611 | sle_fw_v1 | lec | 0.2 | LEC last write 0.1 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-3734467 | sle_fw_v1 | lec | 0.2 | LEC last write 0.1 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-3735985 | sle_fw_v1 | lec | 0.2 | LEC last write 0.1 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| intel2 | dpkit-slw_su_l0__cl1a1c1f8f-3637797 | slw_su_l0 | lec | 0.2 | LEC last write 0.2 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-219998 | col_h9_r1__t1 | 5_1_grt | 1.0 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dpkit-kv3_hgi_v1__cl141fc26e-1063511 | kv3_hgi_v1 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-1063926 | kv3_hgi_v2 | pregrt_ff_hold | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_pv_v8-2902549 | kv3_pv_v8 | 4_1_cts | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-serdes__t14-1427227 | serdes__t14 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | prd-eco-i1t-3762971 | eco-i1t | 5_2_route | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | prd-eco-i1t-3849274 | eco-i1t | 5_2_route | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3715983 | col_h9_r0_p5__t1 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2246910 | col_h9_r1__t1 | 5_1_grt | 22.6 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t24__cl2456157b-3963505 | ot_s81sl_leaf__t24 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t24__cl81374cd8-3950109 | ot_s81sl_leaf__t24 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t38-2246047 | ot_s81sl_leaf__t38 | pregrt_ff_hold | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3-2308751 | ot_s81sl_leaf__t40 | 5_1_grt | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2448993 | ot_s81sl_leaf__t44 | pregrt_ff_hold | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t50-92132 | ot_s81sl_leaf__t50 | 5_1_grt | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slice_station__t6__cl0755c26e-3706771 | slice_station__t6 | 5_1_grt | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | prd-eco-i1t-916503 | eco-i1t | 5_2_route | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3471904 | col_h10_r1__t1 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-serdes__t1__clfe1f0815-4089644 | serdes__t1 | 4_1_cts | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-collft_cl78c7b300_a5-i1t-37055 | collft_cl78c7b300_a5-i1t | 5_2_route | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-hdtile_a6-i1-33143 | hdtile_a6-i1 | 5_2_route | 0.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3851006 | col_h9_r0_p4__t1 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3770092 | col_h9_r0_p4__t1 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-hd_st_n4-3701861 | hd_st_n4 | pregrt_ff_hold | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-3915887 | ot_s81sl_kv_leaf__t5 | synth_odb_v | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t5-3892518 | ot_s81sl_leaf__t5 | 4_1_cts | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t51-3806592 | ot_s81sl_leaf__t51 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t52-3789221 | ot_s81sl_leaf__t52 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3811971 | ot_s81sl_leaf__t53 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t6-3816875 | ot_s81sl_leaf__t6 | 2_1_floorplan | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t71-3743115 | ot_s81sl_leaf__t71 | 4_1_cts | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3723276 | sle_hc2 | 4_1_cts | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-slice_station__t27-3831616 | slice_station__t27 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-slice_station__t37-3875412 | slice_station__t37 | 4_1_cts | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-kv3_hg_v3-2651474 | kv3_hg_v3 | 5_1_grt | 11.8 | last meaningful line 4.1 h ago (214/275 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v5-2635186 | kv3_hgi_v5 | 5_1_grt | 11.8 | last meaningful line 4.1 h ago (202/279 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_pc__cl5a95b461-2262077-lec | kv3_pc | lec | 9.6 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
| epyc2 | dpkit-kv3_pc__cl5a95b461-3396823-lec | kv3_pc | lec | 8.4 | LEC last write 0.1 h ago | PROGRESS: LEC still writing |  |
| epyc2 | dpkit-kv3_pc_v1__cl7f648944-597431-lec | kv3_pc_v1 | lec | 6.0 | LEC last write 0.3 h ago | PROGRESS: LEC still writing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-766084 | ot_s81sl_leaf__t72 | 5_1_grt | 12.8 | last meaningful line 2.4 h ago (208/222 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-285849 | col_h9_r0_p3__t1 | 5_1_grt | 16.2 | last meaningful line 5.5 h ago (201/277 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-874434 | col_h9_r0_p4__t1 | 5_1_grt | 12.1 | last meaningful line 4.9 h ago (203/298 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-282880 | col_h9_r0_p4__t1 | 5_1_grt | 16.2 | repair_Violations best 0 last 0.4 rows 21 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-293959 | col_h9_r0_p4__t1 | 5_1_grt | 16.2 | repair_Violations best 0 last 0.4 rows 20 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-285055 | col_h9_r0_p5__t1 | 5_1_grt | 16.2 | last meaningful line 6.1 h ago (201/294 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv8995e794-1821376 | col_h9_r0_p5__t1 | 5_1_grt | 8.4 | last meaningful line 2.8 h ago (203/246 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-1100761 | col_h9_r1__t1 | 5_1_grt | 23.6 | repair_Remaining best 50028 last 50028 rows 50 | before-window best 86028, window best 50028 | PROGRESS: repair_Remaining improved 41.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-1019926 | col_h9_r1__t1 | 5_1_grt | 11.4 | repair_Violations best 0 last 0 rows 17 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-2405947 | col_h9_r1__t1 | 5_1_grt | 22.4 | repair_Remaining best 48218 last 48218 rows 52 | before-window best 78218, window best 48218 | PROGRESS: repair_Remaining improved 38.4 % in window |  |
| epyc7 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2258510 | col_h9_r2__t1 | 5_1_grt | 22.6 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2787375 | col_h9_r2__t1 | 5_1_grt | 21.8 | last meaningful line 0.0 h ago (1543/1543 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-2662258 | col_h9_r2__t1 | 5_1_grt | 22.0 | last meaningful line 0.0 h ago (1466/1466 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv22267ca0-2662496 | col_h9_r2__t1 | 5_1_grt | 22.0 | last meaningful line 0.0 h ago (1715/1715 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-1138516 | col_h9_r2__t1 | 5_1_grt | 19.0 | last meaningful line 0.0 h ago (2772/2772 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb11188eb-2664314 | col_h9_r2__t1 | 5_1_grt | 22.0 | last meaningful line 0.0 h ago (1759/1759 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-1155968 | col_h9_r2__t1 | 5_1_grt | 19.0 | last meaningful line 0.0 h ago (2620/2620 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvf57acd2b-3762255 | col_h9_r2__t1 | 5_1_grt | 18.7 | last meaningful line 0.0 h ago (2824/2824 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvfb42a1ad-2196309 | col_h9_r2__t1 | 5_1_grt | 18.4 | last meaningful line 0.0 h ago (2372/2372 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_serdes-3685768 | hd_serdes | lec | 18.7 | LEC last write 0.0 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-hd_serdes-3686232 | hd_serdes | lec | 18.7 | LEC last write 0.6 h ago | PROGRESS: LEC still writing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t14-2874796 | ot_s81sl_leaf__t14 | 5_1_grt | 8.4 | last meaningful line 3.0 h ago (202/267 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t51-3454868 | ot_s81sl_leaf__t51 | 5_1_grt | 8.4 | last meaningful line 2.7 h ago (202/250 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3621808 | ot_s81sl_leaf__t53 | 5_1_grt | 8.4 | last meaningful line 1.8 h ago (363/364 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3603160 | ot_s81sl_leaf__t53 | 5_1_grt | 8.4 | last meaningful line 2.0 h ago (204/214 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t58-4071735 | ot_s81sl_leaf__t58 | 5_1_grt | 12.2 | last meaningful line 3.8 h ago (202/256 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t62-1351543 | ot_s81sl_leaf__t62 | 5_1_grt | 15.2 | last meaningful line 4.3 h ago (206/271 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-3635517 | col_h9_r0_p5__t1 | 5_1_grt | 9.3 | last meaningful line 2.7 h ago (204/245 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kit-3502667 | kit | 5_1_grt | 9.3 | last meaningful line 1.8 h ago (170/170 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kit-3505406 | kit | 5_1_grt | 9.3 | last meaningful line 1.8 h ago (171/171 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3866094 | ot_s81sl_leaf__t25 | 5_1_grt | 1.1 | repair_Violations best 0 last 0 rows 16 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-ot_s81sl_leaf__t4-3047292 | ot_s81sl_leaf__t4 | 5_1_grt | 9.4 | last meaningful line 0.0 h ago (1018/1018 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t41-988700 | ot_s81sl_leaf__t41 | 5_1_grt | 10.2 | last meaningful line 3.4 h ago (201/273 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t59-477388 | ot_s81sl_leaf__t59 | 5_1_grt | 12.5 | last meaningful line 4.3 h ago (203/275 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t67-3166818 | ot_s81sl_leaf__t67 | 5_1_grt | 9.4 | last meaningful line 2.2 h ago (207/236 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-serdes__t4-2999799-lec | serdes__t4 | lec | 9.3 | LEC last write 1.2 h ago | PROGRESS: LEC still writing |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cle683a076-279489 | slw_hc1 | 5_1_grt | 15.5 | last meaningful line 4.3 h ago (211/309 lines) | PROGRESS: log still growing |  |
| intel1 | kqc-s81_cland_w2134_ns_8c69f_synth0-3798185 | s81_cland_w2134_ns_8c69f_synth0 | 5_1_grt | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
