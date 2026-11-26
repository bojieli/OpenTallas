# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 22:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'GRT-STUCK': 1, 'NO-PROGRESS': 1, 'GRT-LABEL': 2, 'NO-DATA': 27, 'YOUNG': 94, 'EXCLUDED': 3, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 8.7 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 13.5 | grt rounds 8 overflow 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (30:1933 -> 35:1923 -> 40:2127; best 1923 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 33.9 | drt_violations best 1 last 1 rows 47 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 11.3 | grt rounds 6 overflow 5:128855 -> 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 17.8 | grt rounds 9 overflow 20:1472 -> 25:1063 -> 30:774 -> 35:659 -> 40:652 -> 45:573 | GRT-LABEL: DESIGN-FAIL: overflow 2158 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | selrange | 0.6 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3854423 | dsdv_slice_c1x_C__t8 | 3_5_place_dp | 2.0 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_serdes-6683 | hd_serdes | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-2261865 | serdes__t4 | 3_3_place_gp | 0.8 | overflow best 0.3507 last 0.3507 rows 108 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | 5_2_route | 3.2 | drt_violations best 621 last 621 rows 6 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 3.4 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-retained-relays | lecaf-hdm-p1-retained-relays | - | 1.1 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 0.9 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 4.0 | last meaningful line 2.0 h ago (33/34 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | otc-3652144-28954 | 3652144 | flow | 0.2 | last meaningful line 0.0 h ago (3876/3876 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1022010 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (239/239 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2088775 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3842 last 3842 rows 516 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-2194532 | col_h10_r1__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3559 last 3559 rows 280 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p1__t1__pv697f40c9-283764 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.5 | overflow best 0.4743 last 0.4743 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvabc9823e-801902 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.4 | overflow best 0.4855 last 0.4855 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 13.5 | last meaningful line 0.0 h ago (279/280 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1621795 | col_h9_r0_p5__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pv8d617470-1438191 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.2 | overflow best 0.4655 last 0.4655 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv461b5256-2093340 | col_h9_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3589 last 3589 rows 688 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-dsdv_slice_iq_C__t1-3149121 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1450190 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t11-1486156 | ot_s81sl_leaf__t11 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.3652 last 0.3652 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t34-200887 | ot_s81sl_leaf__t34 | 3_3_place_gp | 0.5 | overflow best 0.2898 last 0.2898 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-native59-478901 | native59 | generate_abstract | 10.6 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-446396-15597 | 446396 | asbuilt.yosys | 0.4 | last meaningful line 0.0 h ago (229029/229029 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | otc-541512-30698 | 541512 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (136725/136725 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-4027604 | kv3_pc_v1 | 3_5_place_dp | 2.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 5_2_route | 4.9 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | postcts_gate_TT | 3.1 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | postcts_gate_TT | 3.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | postcts_gate_TT | 4.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-1003964 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1-2828164 | eco_20261125_200405_3323313-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (302/406 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-181339 | bk_sel__t2 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1017259 | dsdv_slice_c1x_C__t4 | 3_3_place_gp | 1.8 | overflow best 0.7024 last 0.8622 rows 42 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3327555 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.3 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-gunit__t1-1078622 | gunit__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.1948 last 0.1948 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_spn-976147 | hd_spn | 3_3_place_gp | 0.3 | overflow best 0.0992 last 0.0992 rows 46 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slice_station__t51-1607646 | slice_station__t51 | lec | 0.0 | LEC last write 0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_2_route | 12.2 | drt_violations best 115795 last 115795 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 0.8 | last meaningful line 0.2 h ago (700/700 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | lecq9-hd-ctl-seq-guarded-discovery-1125 | lecq9-hd-ctl-seq-guarded-discovery | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 5.3 |  | NO-DATA: no log found |  |
| epyc7 | so_3304067_ff_19534 | so_3304067_ff_19534 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | 1_2_yosys | 1.7 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-4113643 | dsdv_slice_c1x_C__t6 | selrange | 1.5 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | 1_2_yosys | 1.6 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-gunit__t1-342903 | gunit__t1 | 3_5_place_dp | 1.4 | last meaningful line 0.8 h ago (39/39 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-112132 | hd_lep0N | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2402 last 0.2402 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_2_tapbal_grt | 2.6 | last meaningful line 1.0 h ago (48/51 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2n-2852342 | kv3_pv_v2n | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (305/305 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3e-3103773 | kv3_pv_v3e | 3_3_place_gp | 0.6 | overflow best 0.2063 last 0.2063 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v5ne-2852315 | kv3_pv_v5ne | 3_3_place_gp | 0.7 | overflow best 0.0987 last 0.0987 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2900728 | kv3_pv_v6 | 3_3_place_gp | 0.7 | overflow best 0.0964 last 0.0964 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v7e-2857250 | kv3_pv_v7e | 3_3_place_gp | 0.7 | overflow best 0.2005 last 0.2005 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-seqhost__t1-556663 | seqhost__t1 | 2_1_floorplan | 0.2 | repair_Viol best 2319 last 2319 rows 918 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 12.4 | drt_violations best 2465 last 2465 rows 12 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t24__cl66b71008-769228 | slice_station__t24 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | lecaf-hc0-6e8 | lecaf-hc0-6e8 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 1.5 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-b821dc8b6fe0 | lecq9-b821dc8b6fe0 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1323388-4039 | 1323388 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1530472-10583 | 1530472 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1589750-5019 | 1589750 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 6.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-4174262-4961 | 4174262 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-877014-30307 | 877014 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-941401-14145 | 941401 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3-312208 | eco_20261125_104318_3955073-i3 | 5_2_route | 2.3 | drt_violations best 20 last 20 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1-671626 | eco_20261126_033711_2888564-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (171/171 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t5-grt-3260219 | ot-s81sl-leaf--t5-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3546/3546 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.8 h ago (60/78 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 10.9 | drt_violations best 89851 last 89851 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 13231.2 last 13231.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 15.0 | drt_violations best 545016 last 545016 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 11.4 | last meaningful line 0.5 h ago (292/293 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pvea45abf3-1692761 | col_h9_r0_p6__t1 | 3_4_place_resized | 0.4 | repair_Remaining best 66329 last 66329 rows 37 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.0 | last meaningful line 0.3 h ago (61/70 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.1 | last meaningful line 0.5 h ago (61/74 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.0 h ago (61/67 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.1 | last meaningful line 0.5 h ago (61/73 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.1 | last meaningful line 0.3 h ago (61/73 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 124234 last 124234 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 124624 last 124624 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 11.9 | last meaningful line 1.5 h ago (284/1290 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 13.5 | last meaningful line 3.3 h ago (277/1287 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | pregrt_ff_hold | 1.0 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3892/3892 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t23-1100978 | slice_station__t23 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (463/477 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (234/234 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (3968/3968 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_1_grt | 0.6 | last meaningful line 0.4 h ago (320/1434 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-1625008 | kv3_pc_v1 | 3_4_place_resized | 1.5 | last meaningful line 0.1 h ago (360/360 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | generate_abstract | 12.9 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 2.6 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 2.4 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 1.6 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 4.0 | last meaningful line 0.3 h ago (33/34 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-3878162-6060 | 3878162 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | so_729430_ff_11472 | so_729430_ff_11472 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_729430_tt_11472 | so_729430_tt_11472 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ft__cla4a25d77-1695839 | coll_ft | 3_2_place_iop | 0.1 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-626876 | coll_ftm | 5_2_route | 1.7 | drt_violations best 9847 last 9847 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-coll_n-1319177 | coll_n | 5_2_route | 1.5 | drt_violations best 1907 last 1907 rows 2 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | tt_setup_repair_grt | 1.5 | repair_Violations best 1.58124e+06 last 1.58124e+06 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_host_w-3039917 | hd_host_w | pregrt_ff_hold | 0.9 | repair_TNS best 31478 last 31478 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (6633/6633 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-hd_spn_wshim_rx-3049643 | hd_spn_wshim_rx | 5_2_route | 0.9 | drt_violations best 5603 last 5603 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-hd_st_n3_turn-1188158 | hd_st_n3_turn | 3_3_place_gp | 0.2 | overflow best 0.1263 last 0.1263 rows 48 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3690925 | kv3_pc_v1 | 3_5_place_dp | 2.2 | last meaningful line 0.5 h ago (32/32 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v2-1217990 | kv3_pv_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.1 h ago (238/238 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v4-1263946 | kv3_pv_v4 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v6n-1232246 | kv3_pv_v6n | 2_1_floorplan | 0.1 | last meaningful line 0.1 h ago (240/240 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2056022 | slice_station__t12 | generate_abstract | 1.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-4164407-11341 | 4164407 | gold_b.ys | 0.6 | last meaningful line 0.3 h ago (96320/96320 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 17.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 17.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 17.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 35.9 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h10_r1__t1__cld01bb4ae-213926 | col_h10_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 35 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 13.5 | drt_violations best 414 last 439 rows 26 | before-window best 255884, window best 414 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-438706 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pva7e46565-417895 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-serdes__t4-3760103 | serdes__t4 | 4_1_cts | 0.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 21.2 | drt_violations best 3665 last 21095 rows 18 | before-window best 11101, window best 3665 | PROGRESS: drt_violations improved 67.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 21.2 | drt_violations best 14890 last 14890 rows 13 | before-window best 24157, window best 14890 | PROGRESS: drt_violations improved 38.4 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 21.6 | drt_violations best 448 last 448 rows 30 | before-window best 3419, window best 448 | PROGRESS: drt_violations improved 86.9 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 14.4 | drt_violations best 11088 last 44179 rows 18 | before-window best 23868, window best 11088 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 38.6 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best 13 | PROGRESS: drt_violations: active iteration at 12 < best completed total 13 (in-iteration D |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 11.4 | drt_violations best 432 last 432 rows 11 | before-window best 174634, window best 432 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 13.4 | drt_violations best 13 last 14 rows 46 | before-window best 174806, window best 13 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 15.0 | drt_violations best 6 last 8 rows 52 | before-window best 176025, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 1.3 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 21.2 | drt_violations best 8616 last 8616 rows 8 | before-window best 470122, window best 8616 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 12.0 | drt_violations best 380531 last 380531 rows 1 | before-window best 380531, window best 380531 | PROGRESS: drt_violations: active iteration at 160800 < best completed total 380531 (in-ite |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 12.2 | drt_violations best 4482 last 4482 rows 8 | before-window best 171015, window best 4482 | PROGRESS: drt_violations improved 97.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 13.0 | drt_violations best 7354 last 7354 rows 8 | before-window best 176573, window best 7354 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 15.0 | drt_violations best 1524 last 1524 rows 15 | before-window best 178781, window best 1524 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 11.4 | drt_violations best 368 last 369 rows 32 | before-window best 151829, window best 368 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 25.9 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 13.5 | drt_violations best 5613 last 5613 rows 9 | before-window best 178567, window best 5613 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 11.5 | drt_violations best 1795 last 1795 rows 11 | before-window best 162182, window best 1795 | PROGRESS: drt_violations improved 98.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 14.3 | drt_violations best 368 last 370 rows 36 | before-window best 159056, window best 368 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 13.5 | drt_violations best 422 last 422 rows 29 | before-window best 157970, window best 422 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 17.9 | repair_TNS best 71.433 last 71.433 rows 2 | before-window best 80.626, window best 71.433 | PROGRESS: repair_TNS improved 11.4 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 8022 last 8022 rows 5 | before-window best 167111, window best 8022 | PROGRESS: drt_violations improved 95.2 % in window |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 12.2 | drt_violations best 1106 last 1106 rows 8 | before-window best 211273, window best 1106 | PROGRESS: drt_violations improved 99.5 % in window |  |
