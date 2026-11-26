# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 22:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'GRT-LABEL': 4, 'YOUNG': 88, 'NO-DATA': 32, 'EXCLUDED': 3, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 8.5 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 13.2 | grt rounds 8 overflow 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 | UNSIGNABLE: GRT overflow flat: overflow 1923 at iteration 35 -> 2127 at iteration 40: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 33.6 | drt_violations best 1 last 1 rows 47 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 11.1 | grt rounds 6 overflow 5:128855 -> 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 17.5 | grt rounds 9 overflow 20:1472 -> 25:1063 -> 30:774 -> 35:659 -> 40:652 -> 45:573 | GRT-LABEL: DESIGN-FAIL: overflow 2158 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 17.5 | grt rounds 10 overflow 25:1212 -> 30:970 -> 35:768 -> 40:889 -> 45:735 -> 50:680 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 17.6 | grt rounds 10 overflow 25:1148 -> 30:913 -> 35:770 -> 40:787 -> 45:655 -> 50:627 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3854423 | dsdv_slice_c1x_C__t8 | 3_3_place_gp | 1.7 | overflow best 0.574 last 0.7425 rows 50 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-2261865 | serdes__t4 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.4651 last 0.4651 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | 5_2_route | 3.0 | drt_violations best 34322 last 34322 rows 2 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 3.2 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-retained-relays | lecaf-hdm-p1-retained-relays | - | 0.8 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-16147f31a235 | lecq9-16147f31a235 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 3.8 | last meaningful line 1.8 h ago (33/34 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1022010 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3842 last 3842 rows 381 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-3148189 | col_h10_r0_p4__t1 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r1__t1__cld01bb4ae-213926 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.525 last 0.525 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-806649 | col_h10_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p1__t1__pv697f40c9-283764 | col_h9_r0_p1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvabc9823e-801902 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 1005 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 13.3 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-438706 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (201/201 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pva7e46565-417895 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__cl774acf45__pve3ab90e7-94728 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | repair_Remaining best 64333 last 64333 rows 16 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-dsdv_slice_iq_C__t1-3149121 | dsdv_slice_iq_C__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8889 last 0.8889 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t34-200887 | ot_s81sl_leaf__t34 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3822 last 0.3822 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 6_report | 10.4 | last meaningful line 0.2 h ago (65/65 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-446396-15597 | 446396 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (136279/136279 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | otc-541512-30698 | 541512 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (4122/4122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-4027604 | kv3_pc_v1 | 3_5_place_dp | 1.8 | last meaningful line 0.5 h ago (32/32 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 5_2_route | 4.7 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | tt_setup_repair_grt | 2.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (1988/2005 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | tt_setup_measure_grt | 4.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1-2828164 | eco_20261125_200405_3323313-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_211504_2977850-i1t-1003964 | eco_20261125_211504_2977850-i1t | 5_2_route | 1.2 | drt_violations best 67916 last 67916 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-bk_sel__t2-181339 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.311 last 0.311 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1017259 | dsdv_slice_c1x_C__t4 | 3_1_place_gp_skip_io | 1.5 | overflow best 0.2563 last 0.2563 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3327555 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.0 | last meaningful line 0.5 h ago (36/36 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_spn-976147 | hd_spn | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_2_route | 12.0 | drt_violations best 115795 last 115795 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 0.6 | last meaningful line 0.2 h ago (448/448 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | lecq9-09fe297654d7 | lecq9-09fe297654d7 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-59017ec270a7 | lecq9-59017ec270a7 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-hd-ctl-sequencer-1125 | lecq9-hd-ctl-sequencer | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-1572699-31485 | 1572699 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 5.1 |  | NO-DATA: no log found |  |
| epyc7 | so_3304067_ff_19534 | so_3304067_ff_19534 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc7 | so_3304067_tt_19534 | so_3304067_tt_19534 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.3 h ago (137/137 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-4113643 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-gunit__t1-342903 | gunit__t1 | 3_5_place_dp | 1.1 | last meaningful line 0.5 h ago (39/39 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-112132 | hd_lep0N | port_bind | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_2_tapbal_grt | 2.4 | last meaningful line 0.8 h ago (48/50 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-hd_spn_wshim_rx-4060638 | hd_spn_wshim_rx | 3_3_place_gp | 0.1 | overflow best 0.482 last 0.4888 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v2n-2852342 | kv3_pv_v2n | 3_3_place_gp | 0.4 | overflow best 0.467 last 0.467 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v3e-3103773 | kv3_pv_v3e | 3_1_place_gp_skip_io | 0.4 | overflow best 0.5385 last 0.5385 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v5ne-2852315 | kv3_pv_v5ne | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2900728 | kv3_pv_v6 | 3_3_place_gp | 0.4 | overflow best 0.6291 last 0.6291 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v7e-2857250 | kv3_pv_v7e | 3_1_place_gp_skip_io | 0.4 | overflow best 0.2486 last 0.2486 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-377632 | ot_s81sl_leaf__t14 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 12.1 | drt_violations best 2465 last 2465 rows 12 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | lecaf-hc0-6e8 | lecaf-hc0-6e8 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-b821dc8b6fe0 | lecq9-b821dc8b6fe0 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-1530472-10583 | 1530472 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1589750-5019 | 1589750 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 5.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-4174262-4961 | 4174262 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-877014-30307 | 877014 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-941401-14145 | 941401 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3-312208 | eco_20261125_104318_3955073-i3 | 5_2_route | 2.1 | drt_violations best 20 last 20 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | prd-fin-928710 | fin | 6_report | 0.3 | last meaningful line 0.3 h ago (67/67 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pvf9c773d5-grt-2323657 | col-h9-r2--t1--clce45cab5--pvf9c773d5-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3231/3231 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 4_2_tapbal_grt | 1.1 | last meaningful line 0.5 h ago (60/73 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 10.6 | drt_violations best 89851 last 89851 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 14.8 | drt_violations best 545016 last 545016 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 11.2 | last meaningful line 0.5 h ago (290/291 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pvea45abf3-1692761 | col_h9_r0_p6__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.7 | last meaningful line 0.0 h ago (61/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.3 h ago (61/70 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.3 h ago (61/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.1 h ago (61/68 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 124624 last 124624 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 11.6 | last meaningful line 1.3 h ago (284/1290 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 13.3 | last meaningful line 3.0 h ago (277/1287 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t5-138115 | ot_s81sl_leaf__t5 | 3_3_place_gp | 0.4 | overflow best 0.3856 last 0.3856 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (6380/6380 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3812/3812 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t23-1100978 | slice_station__t23 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | postcts_gate_FF | 1.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (3921/3921 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (320/950 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 12.0 | drt_violations best 10102 last 10102 rows 4 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-1625008 | kv3_pc_v1 | 3_3_place_gp | 1.2 | overflow best 0.2039 last 0.2039 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v6-285159 | kv3_pv_v6 | 3_5_place_dp | 1.7 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 6_report | 12.6 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 2.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 2.2 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 2.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 2.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 1.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 3.7 | last meaningful line 0.2 h ago (31/32 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3878162-6060 | 3878162 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_1_grt | 0.1 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_729430_ff_11472 | so_729430_ff_11472 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_729430_tt_11472 | so_729430_tt_11472 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-626876 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (236/237 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-coll_n-1319177 | coll_n | 5_2_route | 1.2 | drt_violations best 13929 last 13929 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (3261/3261 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-hd_host_e-3016190 | hd_host_e | tt_setup_repair_grt | 0.7 | repair_Remaining best 36823 last 36823 rows 52 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-hd_host_w-3039917 | hd_host_w | pregrt_ff_hold | 0.7 | repair_TNS best 43383.5 last 43383.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (6226/6226 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-hd_spn_wshim_rx-3049643 | hd_spn_wshim_rx | 5_2_route | 0.7 | last meaningful line 0.1 h ago (222/223 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1558093 | kv3_io_ft | abstract_exact | 2.5 | last meaningful line 1.0 h ago (4/4 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3690925 | kv3_pc_v1 | 3_5_place_dp | 1.9 | last meaningful line 0.3 h ago (32/32 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2056022 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2986 last 2986 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | otc-4164407-11341 | 4164407 | gold_b.ys | 0.3 | last meaningful line 0.2 h ago (96320/96320 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_877650_ff_91965 | so_877650_ff_91965 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_877650_tt_91965 | so_877650_tt_91965 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 16.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 16.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 16.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 35.7 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 13.3 | drt_violations best 417 last 417 rows 23 | before-window best 255884, window best 417 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-3792988 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-3993278 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-4056788 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-serdes__t4-3760103 | serdes__t4 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 21.0 | drt_violations best 3665 last 3665 rows 17 | before-window best 11101, window best 3665 | PROGRESS: drt_violations improved 67.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 21.0 | drt_violations best 14890 last 14890 rows 13 | before-window best 25919, window best 14890 | PROGRESS: drt_violations improved 42.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 21.4 | drt_violations best 448 last 448 rows 30 | before-window best 4340, window best 448 | PROGRESS: drt_violations improved 89.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 14.2 | drt_violations best 11088 last 44179 rows 18 | before-window best 23868, window best 11088 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 38.4 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best 13 | PROGRESS: drt_violations: active iteration at 12 < best completed total 13 (in-iteration D |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 11.1 | drt_violations best 1011 last 1011 rows 9 | before-window best 174634, window best 1011 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 13.2 | drt_violations best 13 last 14 rows 43 | before-window best 174806, window best 13 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 14.8 | drt_violations best 6 last 8 rows 52 | before-window best 176025, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 1.4 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 20.9 | drt_violations best 9211 last 9211 rows 7 | before-window best 470122, window best 9211 | PROGRESS: drt_violations improved 98.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 11.7 | drt_violations best 380531 last 380531 rows 1 | before-window best 380531, window best 380531 | PROGRESS: drt_violations: active iteration at 221415 < best completed total 380531 (in-ite |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 11.9 | drt_violations best 5571 last 5571 rows 6 | before-window best 171015, window best 5571 | PROGRESS: drt_violations improved 96.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 12.7 | drt_violations best 7575 last 7575 rows 7 | before-window best 176573, window best 7575 | PROGRESS: drt_violations improved 95.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 14.7 | drt_violations best 1524 last 1524 rows 15 | before-window best 178781, window best 1524 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 11.2 | drt_violations best 368 last 372 rows 29 | before-window best 151829, window best 368 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 25.6 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 13.2 | drt_violations best 6126 last 6126 rows 8 | before-window best 178567, window best 6126 | PROGRESS: drt_violations improved 96.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 11.2 | drt_violations best 2136 last 2136 rows 10 | before-window best 162182, window best 2136 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 14.0 | drt_violations best 372 last 372 rows 31 | before-window best 159056, window best 372 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 13.3 | drt_violations best 450 last 466 rows 26 | before-window best 157970, window best 450 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 17.6 | repair_TNS best 179.502 last 179.502 rows 14 | before-window best 451.346, window best 179.502 | PROGRESS: repair_TNS improved 60.2 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 17.5 | drt_violations best 367 last 370 rows 42 | before-window best 35793, window best 367 | PROGRESS: drt_violations improved 99.0 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 12.0 | drt_violations best 2446 last 2446 rows 5 | before-window best 211273, window best 2446 | PROGRESS: drt_violations improved 98.8 % in window |  |
