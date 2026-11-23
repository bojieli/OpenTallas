# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 02:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 1, 'GRT-LABEL': 12, 'YOUNG': 150, 'NO-DATA': 45, 'EXCLUDED': 1, 'PROGRESS': 42}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 35.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 21.6 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -695.09 ps (< -300, gate TT >= -42); job age 21 | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 18.9 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 5_1_grt | 18.9 | grt rounds 2 overflow 5:13717 -> 10:12993 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t11-3893305 | ot_s81sl_leaf__t11 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-3837047 | ot_s81sl_leaf__t41 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:37090 -> 10:30355 | GRT-LABEL: DESIGN-FAIL: overflow 30355 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 9.1 | grt rounds 2 overflow 5:1586 -> 10:260 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t32-1902400 | ot_s81sl_leaf__t32 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:22624 -> 10:6545 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-1869131 | ot_s81sl_leaf__t61 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:48090 -> 10:40576 | GRT-LABEL: DESIGN-FAIL: overflow 40576 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 21.7 | grt rounds 6 overflow 5:805 -> 10:203 -> 15:132 -> 20:64 -> 25:77 -> 30:61 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 21.7 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 8.3 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 17.9 | grt rounds 3 overflow 5:88896 -> 10:83085 -> 15:86608 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-2787287 | bk_sel__t2 | 2_3_floorplan_tapcell | 0.3 | last meaningful line -0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbx_q10__cl89936551_h-2845733 | cbx_q10 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2403270 | col_h10_r0_p1__t1 | 3_2_place_iop | 0.5 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | 4_2_tapbal_grt | 1.4 | last meaningful line 1.0 h ago (46/108 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | 4_2_tapbal_grt | 1.4 | last meaningful line 1.0 h ago (46/135 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3814785 | hd_st_n4 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (248/249 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3877061 | hd_st_n4 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 5_1_grt | 1.5 | last meaningful line 0.2 h ago (1667/1692 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-3882608 | kv3_pv_v3 | 3_5_place_dp | 2.1 | last meaningful line 0.2 h ago (55/55 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3e-3821788 | kv3_pv_v3e | 3_5_place_dp | 2.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 2_4_floorplan_pdn | 20.2 | last meaningful line 0.5 h ago (19/19 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_2_route | 10.6 | drt_violations best 186084 last 186084 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | eco-abs-1364309 | eco-abs | generate_abstract | 1.2 | last meaningful line 0.6 h ago (1030/1030 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | eco-abs-1958616 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.5 h ago (621/621 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | flowops-sdt2g-kG-2992633 | flowops-sdt2g-kG | repro_grt | 0.2 | last meaningful line 0.0 h ago (519/519 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3034915-23491 | 3034915 | qwen_compute.t.sle_stm_v2__cl55be2264 | 0.1 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-3082835-5546 | 3082835 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 5.6 | drt_violations best 39405 last 39405 rows 2 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i1t-3218186 | eco_20261123_075519_12410-i1t | 5_2_route | 2.5 | drt_violations best 1077 last 1077 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-gunit--t1-grt-3342517 | gunit--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 8.3 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 38299.4 last 38299.4 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | tt_setup_repair | 1.5 | repair_Viol best 89 last 89 rows 94 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2056070 | col_h10_r1__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 108409 last 108409 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cld01bb4ae-1062709 | col_h10_r1__t1 | 5_1_grt | 4.1 | last meaningful line 1.3 h ago (265/1275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1483343 | col_h9_r0_p4__t1 | 5_1_grt | 3.9 | last meaningful line 0.3 h ago (215/219 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 5_2_route | 8.0 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 10.5 | last meaningful line 4.8 h ago (208/214 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 10.5 | last meaningful line 4.5 h ago (211/220 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 7.6 | last meaningful line 2.5 h ago (207/213 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 7.2 | repair_TNS best 975.165 last 975.165 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | pregrt_ff_hold | 7.1 | repair_TNS best 68.992 last 68.992 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | pregrt_ff_hold | 1.2 | repair_TNS best 98684.5 last 98684.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-724077 | kv3_hgi_v4 | 5_1_grt | 4.3 | last meaningful line 0.1 h ago (155/155 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 3.9 | drt_violations best 87459 last 87459 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 2.5 | last meaningful line 0.3 h ago (246/247 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_3_place_gp | 3.9 | overflow best 0.0996 last 0.0996 rows 41 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_3_place_gp | 4.4 | overflow best 0.0996 last 0.0996 rows 42 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-3941275 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 8852.42 last 8852.42 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 8.3 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-1023895 | ot_s81sl_leaf__t30 | 5_1_grt | 1.7 | last meaningful line 0.5 h ago (198/205 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-1430945 | ot_s81sl_leaf__t36 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-3842605 | ot_s81sl_leaf__t7 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (204/207 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 4_1_cts | 4.2 | last meaningful line 0.2 h ago (9109/9109 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 10.6 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | postcts_gate_TT | 10.5 | last meaningful line -0.0 h ago (24492/24492 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | postcts_gate_TT | 10.5 | last meaningful line -0.0 h ago (24853/24853 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (276/276 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 7.1 | drt_violations best 167955 last 167955 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 7.5 | drt_violations best 75867 last 75867 rows 3 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 3.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2436152-11731 | 2436152 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-2438095-32195 | 2438095 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-3189586-5240 | 3189586 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-3333217-11213 | 3333217 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-3513276-2117 | 3513276 | qwen_compute.t.sle_hc1__cl22c1ff36__pve230954c | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 3.3 | last meaningful line 0.2 h ago (268/268 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_2_route | 3.5 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (237/1290 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (143/143 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | uncdie-phs-serdes__t16-3514880 | uncdie-phs-serdes__t16 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-hd-lep0N-w-grt-4109985 | hd-lep0N-w-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t45-grt-4091276 | ot-s81sl-leaf--t45-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-3499572 | col_h10_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 855413 last 855457 rows 38 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.0 h ago (63/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-836163 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 131142 last 131142 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t9-4069286 | dsdv_slice_c1x_C__t9 | 3_1_place_gp_skip_io | 3.2 | overflow best 0.2318 last 0.2318 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3154/3154 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | 4_1_cts | 3.6 | last meaningful line 0.2 h ago (6388/6388 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3029504 | hd_lep0N | 3_3_place_gp | 0.9 | last meaningful line 0.1 h ago (196/196 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | 4_2_tapbal_grt | 0.7 | last meaningful line 0.3 h ago (46/58 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-1251911 | hd_st_n4 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (241/242 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-2829569 | hd_st_n4 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (555/586 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-1064320 | kv3_pv_v1 | 3_3_place_gp | 2.2 | overflow best 0.2014 last 0.2014 rows 32 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 3_3_place_gp | 2.6 | overflow best 0.1817 last 0.1817 rows 36 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-4105867 | ot_s81sl_leaf__t22 | 5_1_grt | 3.2 | last meaningful line 1.0 h ago (204/212 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 12.3 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_2_route | 13.2 | drt_violations best 144858 last 144858 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 6_report | 13.3 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 13.2 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 11.8 | drt_violations best 72487 last 72487 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 8.2 | drt_violations best 108964 last 108964 rows 3 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | otc-2287405-27505 | 2287405 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-254531-30458 | 254531 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc7 | otc-3357716-20952 | 3357716 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-3815737-1746 | 3815737 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2-3585488 | eco_20261122_215654_330309-i2 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (230/957 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i2-2223567 | eco_20261122_220050_168828-i2 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 2.4 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | relec1122-trx-mainlec | relec1122-trx-mainlec | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | unch-eq-4113996 | unch-eq | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-hg-v1p2-grt-343778 | kv3-hg-v1p2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-pc-v1--cl7f648944-grt-139906 | kv3-pc-v1--cl7f648944-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-pc-v1--cl7f648944-grt-309819 | kv3-pc-v1--cl7f648944-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1919292 | col_h9_r0_p2__t1 | 5_1_grt | 2.8 | last meaningful line 0.3 h ago (271/1278 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 8.4 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | postcts_gate_TT | 8.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2205610 | dsdv_slice_c1x_C__t1 | 1_2_yosys | 2.7 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | 1_2_yosys | 2.9 | last meaningful line 0.0 h ago (226/226 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | 5_2_route | 10.8 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | tt_setup_repair | 1.7 | repair_Violations best 22 last 195 rows 49 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3763428 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.68 last 0.714 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v8-3855514 | kv3_hgi_v8 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 5.7 | last meaningful line 0.2 h ago (12235/12235 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 10.8 | drt_violations best 91531 last 91531 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-2296613 | kv3_hub_Eo | 3_5_place_dp | 2.7 | last meaningful line 0.1 h ago (116/116 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-2343024 | kv3_hub_Wo | 3_4_place_resized | 2.7 | last meaningful line 0.3 h ago (393/393 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | 5_2_route | 5.1 | drt_violations best 53187 last 53187 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_4_place_resized | 5.2 | last meaningful line 0.8 h ago (644/644 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-2320204 | ot_s81sl_leaf__t14 | 5_1_grt | 2.7 | last meaningful line 0.5 h ago (264/1271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t23-1888361 | ot_s81sl_leaf__t23 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (214/223 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | 5_1_grt | 3.2 | repair_Remaining best 456 last 456 rows 438 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (192/195 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | fablerc-2704743 | fablerc | tt_setup_repair | 0.8 | repair_Violations best 22 last 195 rows 49 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | otc-1910005-4834 | 1910005 | - | 4.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2514615-8132 | 2514615 | lec | 2.6 | LEC last write 2.6 h ago | YOUNG: evidence 2.6 h < 6 h |  |
| epyc8 | otc-3641731-29356 | 3641731 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t2-grt-4136800 | ot-s81sl-leaf--t2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 6.4 | last meaningful line 0.2 h ago (267/376 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | 5_2_route | 8.3 | drt_violations best 1418 last 1418 rows 8 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | pregrt_ff_hold | 8.3 | repair_Violations best 146 last 238 rows 134 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v3-2875910 | kv3_hgi_v3 | 5_1_grt | 3.5 | last meaningful line 0.5 h ago (290/1299 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 3.6 | repair_TNS best 236158 last 236158 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 2.4 | repair_TNS best 309828 last 309828 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_pv-146967 | kv3_pv | 3_5_place_dp | 2.5 | last meaningful line 0.2 h ago (54/54 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 3_4_place_resized | 3.6 | last meaningful line 0.3 h ago (747/747 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 3_3_place_gp | 3.5 | overflow best 0.0997 last 0.0997 rows 42 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_1_place_gp_skip_io | 2.4 | overflow best 0.199 last 0.199 rows 35 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | 4_1_cts | 3.8 | last meaningful line 0.0 h ago (8035/8035 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.3 | repair_Remaining best 354110 last 354110 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t15-153595 | ot_s81sl_leaf__t15 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (201/207 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-450077 | ot_s81sl_leaf__t17 | 5_1_grt | 2.3 | last meaningful line 0.5 h ago (210/217 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t33-1533302 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 1.6 | repair_TNS best 8710.16 last 8710.16 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-204188 | ot_s81sl_leaf__t46 | 5_1_grt | 2.5 | last meaningful line 1.5 h ago (215/224 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | 5_2_route | 3.6 | drt_violations best 14680 last 14680 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | lrc-qgrt-3979888 | lrc-qgrt | qgrt | 2.7 | last meaningful line 2.5 h ago (44/57 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | otc-1108174-15457 | 1108174 | - | 4.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1631796-31019 | 1631796 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1661483-30301 | 1661483 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1916796-12156 | 1916796 | - | 4.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2062537-15369 | 2062537 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-2908313-11466 | 2908313 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-2908826-5237 | 2908826 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-2909264-658 | 2909264 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-3706696-10109 | 3706696 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3850737-30319 | 3850737 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-3879808-1968 | 3879808 | gate.ys | 0.2 | last meaningful line 0.1 h ago (22052/22052 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-4008685-19280 | 4008685 | s81_head.t.ot_s81hd_ctl | 0.1 | last meaningful line 0.0 h ago (2/2 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-664483-8927 | 664483 | - | 4.9 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_2_route | 2.3 | last meaningful line 0.4 h ago (286/287 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3t-3335435 | eco_20261122_180231_342380-i3t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (239/535 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-residual-i4r-2209462 | residual-i4r | 5_2_route | 1.3 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | pvr7-pv8-fstart-4087939 | pvr7-pv8-fstart | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | pvr7-pv8-hifo-3975570 | pvr7-pv8-hifo | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-slw_hc3_clccfc_mainlec | relec1122-ml-slw_hc3_clccfc_mainlec | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t15-grt-2611945 | ot-s81sl-leaf--t15-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-ot-s81sl-leaf--t68-grt-2587408 | ot-s81sl-leaf--t68-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 22.0 | last meaningful line 0.5 h ago (292/293 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | tt_setup_repair_grt | 8.3 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 5.9 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 6.7 | last meaningful line 4.5 h ago (48/56 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl141fc26e-1859451 | kv3_hgi_v1 | 3_3_place_gp | 0.7 | overflow best 0.1953 last 0.1953 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 20.2 | last meaningful line 0.5 h ago (289/290 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_3_place_gp | 5.3 | overflow best 0.0999 last 0.0999 rows 43 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1209290 | ot_s81sl_kv_leaf__t3 | 3_3_place_gp | 1.2 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t14-656158 | ot_s81sl_leaf__t14 | 3_3_place_gp | 1.5 | overflow best 0.5987 last 0.8801 rows 12 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (259/260 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_1_grt | 6.6 | last meaningful line 0.0 h ago (167/167 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 8.4 | drt_violations best 344103 last 344103 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | otc-2356193-21680 | 2356193 | qwen_compute.t.sle_st_b_v2__cl14c98df5__pv41c959f3 | 0.3 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-2573378-14964 | 2573378 | qwen_compute.t.sle_st_b_v2__cl14c98df5__pv41c959f3 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-589898-30912 | 589898 | - | 4.5 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 4.5 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 4.3 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 5.7 | last meaningful line 0.2 h ago (291/292 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 3.9 | drt_violations best 7877 last 7877 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1-380897 | eco_20261122_165619_1517073-i1 | 5_2_route | 4.7 | drt_violations best 2914 last 2914 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 13.7 | drt_violations best 17077 last 17077 rows 2 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 186769 last 186769 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-coll_ftm-1679354 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (217/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_1_floorplan | 0.9 | last meaningful line 0.5 h ago (1424/1424 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v5-3790571 | kv3_pv_v5 | 3_4_place_resized | 4.5 | last meaningful line 0.5 h ago (679/679 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 4_1_cts | 2.7 | last meaningful line 0.5 h ago (9157/9157 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 15.7 | drt_violations best 327883 last 327883 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1301330 | slice_station__t12 | generate_abstract | 1.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2076253-7937 | 2076253 | asbuilt.yosys | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 18.9 | drt_violations best 1646 last 1646 rows 35 | before-window best 8998, window best 1646 | PROGRESS: drt_violations improved 81.7 % in window |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | 4_2_tapbal_grt | 1.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | 4_2_tapbal_grt | 1.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 71.7 | last meaningful line 0.6 h ago (1616/1616 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 8.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | pregrt_ff_hold | 8.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | pregrt_ff_hold | 8.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 10.5 | drt_violations best 13880 last 13880 rows 6 | before-window best 154966, window best 13880 | PROGRESS: drt_violations improved 91.0 % in window |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | generate_abstract | 8.2 | last meaningful line 0.2 h ago (182/182 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 18.4 | drt_violations best 1 last 1 rows 51 | before-window best 19862, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 18.9 | drt_violations best 57 last 57 rows 23 | before-window best 180834, window best 57 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 22.3 | drt_violations best 12904 last 12904 rows 15 | before-window best 14242, window best 12904 | PROGRESS: drt_violations improved 9.4 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 8.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 9.8 | drt_violations best 15880 last 15880 rows 14 | before-window best 132034, window best 15880 | PROGRESS: drt_violations improved 88.0 % in window |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2109433 | col_h10_r0_p4__t1 | 5_1_grt | 4.0 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 5_1_grt | 6.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 14.3 | drt_violations best 20 last 71 rows 30 | before-window best 53, window best 20 | PROGRESS: drt_violations improved 62.3 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 21.7 | drt_violations best 33673 last 33673 rows 2 | before-window best 195281, window best 33673 | PROGRESS: drt_violations improved 82.8 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 21.7 | drt_violations best 60023 last 60023 rows 3 | before-window best 210671, window best 60023 | PROGRESS: drt_violations improved 71.5 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_2_route | 11.7 | drt_violations best 1392 last 1392 rows 7 | before-window best 52013, window best 1392 | PROGRESS: drt_violations improved 97.3 % in window |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 29.2 | drt_violations best 1027 last 2630 rows 26 | before-window best 1159, window best 1027 | PROGRESS: drt_violations improved 11.4 % in window |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 15.8 | drt_violations best 4 last 4 rows 21 | before-window best 305042, window best 4 | PROGRESS: drt_violations improved 100.0 % in window |  |
