# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 06:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-LABEL': 1, 'YOUNG': 100, 'NO-DATA': 6, 'PROGRESS': 29}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 12.6 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 12.3 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 12.5 | grt rounds 1 overflow 5:13977 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_ft__cl78c7b300-1240042 | coll_ft | postcts_gate_FF | 1.2 | last meaningful line 0.0 h ago (426/426 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-1296583 | coll_ft | 5_1_grt | 1.2 | last meaningful line 0.1 h ago (550/582 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-2761182 | hd_spn | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (94/94 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-2760809 | hd_st_n4 | 2_2_floorplan_macro | 0.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2032997 | sle_hc0 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5717/5717 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1908980 | sle_hc2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5305/5305 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-2356638 | sle_st_b_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5559/5559 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-2226501 | slw_fw_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4822/4822 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2106973 | slw_hc1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5770/5770 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5413/5413 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4890/4890 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2142862 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4960/4960 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-2814991-6373 | 2814991 | neg_retime_0645 | 0.0 | last meaningful line -0.0 h ago (14510/14510 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-2815218-27789 | 2815218 | neg_retime_0645 | 0.0 | last meaningful line -0.0 h ago (14093/14094 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_st_n4-4161241 | hd_st_n4 | 5_2_route | 1.9 | drt_violations best 20361 last 20361 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 2.1 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 5.8 | last meaningful line 0.2 h ago (294/1298 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 2.0 | repair_TNS best 6562.24 last 6562.24 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | tt_setup_repair | 2.0 | last meaningful line 0.0 h ago (427/427 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 2.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 2.0 | repair_TNS best 6194.91 last 6194.91 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 1.9 | repair_TNS best 22328.5 last 22328.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | tt_setup_repair_grt | 1.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 1.9 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (1736/1773 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (237/1929 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 2.5 | last meaningful line 0.1 h ago (246/247 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 7.1 | last meaningful line 0.5 h ago (261/262 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_1_grt | 3.3 | last meaningful line 0.5 h ago (1291/1941 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (274/277 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-2492812 | sle_st_a_v1 | 5_1_grt | 1.6 | repair_Remaining best 19607 last 19607 rows 129 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (276/278 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-2355490 | sle_st_a_v2 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (1943/1947 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2354216 | sle_st_a_v2 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (1943/1991 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2374002 | sle_st_a_v2 | 5_1_grt | 1.7 | last meaningful line 0.1 h ago (1941/1958 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (5763/5763 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 7.2 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (254/254 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | 5_1_grt | 7.5 | last meaningful line 0.1 h ago (1144/1150 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | tt_setup_repair | 1.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | 4_1_cts | 1.7 | last meaningful line 0.2 h ago (5732/5732 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 7.3 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (1905/1916 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clb036e152-2495581 | slw_st_a_v1 | 5_1_grt | 1.6 | repair_Remaining best 101182 last 101182 rows 49 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | 5_1_grt | 1.6 | repair_Remaining best 148462 last 148462 rows 6 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2581554 | slw_st_a_v1 | 5_1_grt | 1.6 | repair_Remaining best 15634 last 15634 rows 137 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-2648278 | slw_st_a_v2 | 5_1_grt | 1.6 | last meaningful line 0.2 h ago (1297/1975 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 7.5 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (4950/4950 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2-4134013 | eco_20261123_171023_3055226-i2 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | so_746327_ff_19388 | so_746327_ff_19388 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_746327_tt_19388 | so_746327_tt_19388 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 12.2 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01-2426583 | cbf_q01 | 3_3_place_gp | 1.0 | overflow best 0.1995 last 0.1995 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-cbf_q11-2485724 | cbf_q11 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (101/101 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-coll_ft__cl78c7b300-2577534 | coll_ft | 5_2_route | 0.9 | last meaningful line 0.0 h ago (240/241 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-1232121 | sle_fe_v1 | 3_3_place_gp | 1.2 | overflow best 0.0992 last 0.0992 rows 42 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1324390 | sle_hc1 | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1418859 | sle_hc1 | 3_3_place_gp | 1.2 | overflow best 0.2992 last 0.3607 rows 167 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1976922 | sle_st_b_v1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (465/465 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2040264 | sle_st_b_v2 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (449/449 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-2055893 | sle_st_b_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-2048146 | sle_stm_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1137615 | slw_fe_v1 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-1999325 | slw_hc1 | 3_3_place_gp | 1.0 | overflow best 0.3013 last 0.5422 rows 170 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2563364 | slw_sc_v1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-2629778 | slw_sc_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-330317 | slw_st_a_v2 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (2115/2121 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-2582857 | slw_st_b_v1 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (453/453 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 5.9 | drt_violations best 11 last 136 rows 40 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | eco-abs-1130144 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.2 h ago (691/691 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937-lec | qfd_qc_su_lane_w_l0_wfb17da | lec | 0.7 | LEC last write -0.0 h ago | YOUNG: evidence 0.7 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688-lec | qfd_qc_su_lane_w_l1_w460927 | lec | 0.8 | LEC last write -0.0 h ago | YOUNG: evidence 0.8 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329-lec | qfd_qc_su_lane_w_l4_w285325 | lec | 0.8 | LEC last write -0.0 h ago | YOUNG: evidence 0.8 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935-lec | qfd_qc_su_lane_w_l5_wf949e1 | lec | 0.8 | LEC last write -0.0 h ago | YOUNG: evidence 0.8 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896-lec | qfd_qc_su_lane_w_l6_wb51d05 | lec | 0.7 | LEC last write -0.0 h ago | YOUNG: evidence 0.7 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251-lec | qfd_qc_su_lane_w_l7_wd4f14d | lec | 0.7 | LEC last write -0.0 h ago | YOUNG: evidence 0.7 h < 6 h |  |
| epyc9 | otc-1202915-11343 | 1202915 | asbuilt.yosys | 0.5 | last meaningful line 0.1 h ago (241095/241095 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-1365020-9952 | 1365020 | asbuilt.yosys | 0.4 | last meaningful line -0.0 h ago (135962/135962 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1871258-8946 | 1871258 | asbuilt.yosys | 0.1 | last meaningful line -0.0 h ago (135241/135241 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold.ys | 0.1 | last meaningful line 0.0 h ago (122054/122054 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2040165-28348 | 2040165 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-2040757-2457 | 2040757 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-2527977 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3-368978 | eco_20261123_190031_3093983-i3 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (5754/5754 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 2.0 | last meaningful line 0.4 h ago (5938/5938 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (5832/5832 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (5052/5052 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (5589/5589 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | hold_gate | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 1.9 | last meaningful line 0.3 h ago (5853/5853 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (5280/5280 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5747/5747 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5064/5064 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5488/5488 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (4950/4950 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (4990/4990 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | eco-abs-3571988 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 6.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 1.6 | last meaningful line 1.3 h ago (208/209 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1873477 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-1857635 | sle_ctl | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 5.9 | drt_violations best 58 last 151 rows 18 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 33.8 | drt_violations best 779 last 1386 rows 38 | before-window best 954, window best 779 | PROGRESS: drt_violations improved 18.3 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 29.1 | drt_violations best 17065 last 17065 rows 13 | before-window best 30930, window best 17065 | PROGRESS: drt_violations improved 44.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 22.4 | drt_violations best 27940 last 27940 rows 12 | before-window best 42803, window best 27940 | PROGRESS: drt_violations improved 34.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | pregrt_ff_hold | 3.1 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | pregrt_ff_hold | 3.5 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 36.4 | drt_violations best 48746 last 160916 rows 18 | before-window best 48746, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 4_1_cts | 0.8 | repair_TNS best 0 last 0 rows 66 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 4_1_cts | 0.8 | repair_TNS best 0 last 0 rows 23 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 4_1_cts | 0.8 | repair_TNS best 0 last 0 rows 82 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 4_1_cts | 0.8 | repair_TNS best 0 last 0 rows 79 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 4_1_cts | 0.8 | repair_TNS best 0 last 0 rows 84 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 4_1_cts | 0.7 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_1_grt | 0.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 36.6 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 14.7 | last meaningful line 3.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 18.4 | last meaningful line 3.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
