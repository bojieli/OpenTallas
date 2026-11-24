# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 11:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 1, 'GRT-LABEL': 6, 'YOUNG': 176, 'NO-DATA': 20, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 4.3 | repair_TNS best 758714 last 758714 rows 1 | before-window best 758714, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-HG-CAP decides; neve |
| epyc8 | dpkit-sle_sc_v3-4127450 | sle_sc_v3 | tt_setup_repair_grt | 3.1 | repair_Viol best 50 last 50 rows 21 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -385.58 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 19.2 | last meaningful line 8.4 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 8.4 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 22.9 | last meaningful line 8.4 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 8.4 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc10 | dpkit-kv3_hgi_v4-677838 | kv3_hgi_v4 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:27808 -> 10:18867 | GRT-LABEL: DESIGN-FAIL: overflow 18867 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi_v5-772924 | kv3_hgi_v5 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:20779 -> 10:6892 | GRT-LABEL: DESIGN-FAIL: overflow 6892 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv-1051314 | kv3_pv | 5_1_grt | 2.4 | grt rounds 2 overflow 5:55206 -> 10:46293 | GRT-LABEL: DESIGN-FAIL: overflow 46293 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v2e-252410 | kv3_pv_v2e | 5_1_grt | 3.0 | grt rounds 2 overflow 5:54763 -> 10:39326 | GRT-LABEL: DESIGN-FAIL: overflow 39326 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v2ne-269596 | kv3_pv_v2ne | 5_1_grt | 4.6 | grt rounds 2 overflow 5:64721 -> 10:51671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 5_1_grt | 4.2 | grt rounds 2 overflow 5:88213 -> 10:73755 | GRT-LABEL: DESIGN-FAIL: overflow 73755 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 2.3 | last meaningful line 1.0 h ago (48/51 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | pregrt_ff_hold | 2.6 | repair_TNS best 468304 last 468304 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-87252 | kv3_hgi_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1301/1301 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-180086 | kv3_hgi_v2 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 149411 last 149411 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | pregrt_ff_hold | 2.3 | repair_TNS best 61304.5 last 61304.5 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | pregrt_ff_hold | 2.4 | repair_TNS best 34496.4 last 34496.4 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | pregrt_ff_hold | 2.7 | repair_TNS best 67002.5 last 67002.5 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (154/154 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | pregrt_ff_hold | 2.9 | repair_TNS best 845383 last 845383 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | pregrt_ff_hold | 2.7 | repair_TNS best 32592.1 last 32592.1 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | pregrt_ff_hold | 2.5 | repair_TNS best 26222.1 last 26222.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v6e-760052 | kv3_pv_v6e | 5_1_grt | 2.6 | last meaningful line 0.8 h ago (268/1276 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | pregrt_ff_hold | 2.4 | repair_TNS best 30680.7 last 30680.7 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v6ne-1050153 | kv3_pv_v6ne | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (272/1278 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7-1199684 | kv3_pv_v7 | pregrt_ff_hold | 2.2 | repair_TNS best 133545 last 133545 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 4_1_cts | 2.3 | last meaningful line 0.1 h ago (11168/11168 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (6724/6724 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3227025 | sle_hc0 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3963118 | sle_st_b_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3605780 | sle_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.2164 last 0.2164 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-3336251 | sle_st_b_v2 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | pregrt_ff_hold | 1.0 | repair_TNS best 11326 last 11326 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5023/5023 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5105/5105 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (8255/8255 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-3446125 | slw_hc1 | 3_3_place_gp | 0.6 | overflow best 0.2998 last 0.5836 rows 114 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | postcts_gate_TT | 5.1 | last meaningful line 0.1 h ago (353/353 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-3359908 | slw_st_b_v1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4448/4448 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3605853-9611 | 3605853 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R1_coll_a | relec-r2-R1_coll_a | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R2_coll_eco | relec-r2-R2_coll_eco | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R3_coll_hint | relec-r2-R3_coll_hint | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 0.2 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 5.4 | last meaningful line 1.8 h ago (48/60 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v7-1276815 | kv3_hgi_v7 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (6527/6527 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-614287 | kv3_hub_Eo | 3_3_place_gp | 1.3 | overflow best 0.0997 last 0.0997 rows 44 | YOUNG: stage 0.4 h < 1 h |  |
| epyc11 | dpkit-kv3_io_cor-3977350 | kv3_io_cor | 5_2_route | 4.9 | drt_violations best 22975 last 22975 rows 3 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v3e-3783354 | kv3_pv_v3e | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (12278/12278 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | tt_setup_repair | 2.1 | repair_Viol best 9289 last 9289 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 4_1_cts | 1.7 | last meaningful line 0.2 h ago (5915/5915 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | 4_1_cts | 1.7 | last meaningful line 0.2 h ago (5204/5204 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (5698/5698 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5666/5666 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (5693/5693 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1187645 | slw_fw_v1 | generate_abstract | 13.9 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (4914/4914 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5018/5018 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | pregrt_ff_hold | 2.1 | repair_TNS best 80990.7 last 80990.7 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5506/5506 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5044/5044 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | lecautofill-hd_mesh | lecautofill-hd_mesh | - | 15.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1t-3435586 | eco_20261124_154417_1016084-i1t | 5_2_route | 2.4 | drt_violations best 8982 last 8982 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1t-2053304 | eco_20261124_190641_1260390-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_2110869_ff_24850 | so_2110869_ff_24850 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc11 | so_2110869_tt_24850 | so_2110869_tt_24850 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-3557026 | cbn_q00 | pregrt_ff_hold | 1.0 | repair_TNS best 57595.9 last 57595.9 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc2 | dpkit-coll_ftm-1783743 | coll_ftm | 5_2_route | 2.2 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5865/5865 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 5_1_grt | 4.5 | last meaningful line 1.5 h ago (300/1309 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | pregrt_ff_hold | 4.3 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc2 | dpkit-kv3_sys_SD_v1-3451438 | kv3_sys_SD_v1 | 5_2_route | 1.1 | drt_violations best 19273 last 19273 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | 4_1_cts | 2.2 | last meaningful line 0.3 h ago (5795/5795 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-4026959 | sle_hc2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (4803/4803 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (5083/5083 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 6.5 | last meaningful line 0.5 h ago (263/264 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 5.5 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | postcts_gate_TT | 2.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | postcts_gate_TT | 2.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4782/4782 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 6.4 | drt_violations best 70 last 70 rows 10 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3602061 | sle_su_l1 | pregrt_ff_hold | 1.0 | repair_TNS best 63501.9 last 63501.9 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5782/5782 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (4766/4766 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (4195/4195 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | postcts_gate_FF | 2.4 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | postcts_gate_TT | 2.4 | last meaningful line 0.0 h ago (894/894 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (6346/6346 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | otc-657670-8568 | 657670 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3-451477 | eco_20261123_103136_2028090-i3 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | tt_setup_repair_grt | 2.1 | repair_Viol best 3 last 3 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (6779/6779 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 11.6 | drt_violations best 490378 last 490378 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | postcts_gate_FF | 6.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | pregrt_ff_hold | 1.8 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.3 h < 2.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (5735/5735 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 6_report | 11.7 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 7.6 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (5571/5571 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (5616/5616 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5729/5729 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (5186/5186 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | postcts_gate_TT | 6.2 | last meaningful line 0.0 h ago (2182/2182 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 7.9 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | tt_setup_measure | 2.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | generate_abstract | 12.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_1_grt | 6.3 | last meaningful line 0.1 h ago (1017/1023 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 8.0 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | pregrt_ff_hold | 1.9 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_1_grt | 1.2 | last meaningful line 0.6 h ago (234/1374 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1t-3184147 | eco_20261124_175441_992552-i1t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | so_562417_ff_94801 | so_562417_ff_94801 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_562417_tt_94801 | so_562417_tt_94801 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_957275_ff_86359 | so_957275_ff_86359 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_957275_tt_86359 | so_957275_tt_86359 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-coll_ftc-3942021 | coll_ftc | tt_setup_repair_grt | 3.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | 5_2_route | 3.2 | drt_violations best 65079 last 65079 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 3.1 | last meaningful line 0.2 h ago (6183/6183 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v3-3927550 | sle_fe_v3 | generate_abstract | 3.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (5600/5600 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 4_1_cts | 3.1 | last meaningful line 0.3 h ago (5756/5756 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (5772/5772 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 3.1 | last meaningful line 0.2 h ago (5841/5841 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | pregrt_ff_hold | 3.2 | repair_TNS best 6462.44 last 6462.44 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | tt_setup_measure | 3.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 3.1 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 16907.3 last 16907.3 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 3.1 | last meaningful line 0.1 h ago (254/254 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 4_1_cts | 3.1 | last meaningful line 0.0 h ago (5737/5737 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (5713/5713 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (5792/5792 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 3.1 | last meaningful line 0.2 h ago (5354/5354 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | postcts_gate_TT | 6.4 | last meaningful line 0.0 h ago (723/723 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | pregrt_ff_hold | 3.2 | repair_TNS best 4756.98 last 4756.98 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | pregrt_ff_hold | 3.2 | repair_TNS best 200695 last 200695 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | pregrt_ff_hold | 3.1 | repair_TNS best 337726 last 337726 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | postcts_gate_TT | 3.1 | last meaningful line 0.1 h ago (523/523 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 3.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 5_2_route | 3.2 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 3.1 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (262/471 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_hub_Wo-2104173 | kv3_hub_Wo | 3_3_place_gp | 1.8 | overflow best 0.0994 last 0.0994 rows 46 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5507/5507 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (4944/4944 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4462/4462 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 4.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-29732-24624 | 29732 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-29851-10135 | 29851 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-30219-7096 | 30219 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_2_route | 3.2 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 5.0 | drt_violations best 40 last 40 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-4114232 | cbf_q00 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (6687/6687 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-4036084 | cbn_q11 | pregrt_ff_hold | 1.3 | repair_TNS best 110036 last 110036 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (7360/7360 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cla4a25d77-56057 | coll_ft | 5_2_route | 1.1 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ucie-4183666 | coll_ucie | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (3239/3239 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-521791 | kv3_hgi_v4 | 3_3_place_gp | 0.8 | overflow best 0.2498 last 0.2827 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 3.9 | last meaningful line 0.2 h ago (12718/12718 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 5_1_grt | 4.3 | last meaningful line 0.3 h ago (155/155 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | pregrt_ff_hold | 3.3 | repair_TNS best 169718 last 169718 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 5_1_grt | 4.2 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4460/4460 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5818/5818 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5261/5261 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5941/5941 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-1449506 | sle_st_b_v1 | 1_2_yosys | 0.2 | last meaningful line -0.0 h ago (2233/2233 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4453/4453 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 4.5 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_1_grt | 6.4 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (4492/4492 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5770/5770 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | 4_1_cts | 2.0 | last meaningful line 0.3 h ago (4988/4988 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-1726642 | slw_sc_v1 | rtl_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (5371/5371 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_1_grt | 6.4 | last meaningful line 0.0 h ago (1020/1020 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | pregrt_ff_hold | 2.1 | repair_TNS best 22724.7 last 22724.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 0.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 0.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1713817-29286 | 1713817 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 4.2 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 2.1 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2763021 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-524420 | kv3_hub_C | 2_1_floorplan | 1.7 | last meaningful line 1.3 h ago (1424/1424 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-487140 | kv3_hub_Wi | 3_1_place_gp_skip_io | 1.7 | overflow best 0.9343 last 0.9343 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2016810 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-2106104 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.8534 last 0.8534 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-578782 | sle_ctl | 3_4_place_resized | 1.6 | last meaningful line 0.1 h ago (437/437 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-1286736 | sle_fw_v1 | 3_5_place_dp | 1.2 | last meaningful line 0.2 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5724/5724 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2045071 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (221/222 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5235/5235 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (4918/4918 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-slw_hc2__cl6bcaba89-2372247 | slw_hc2 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2371984 | slw_hc3 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 14.2 | drt_violations best 22940 last 22940 rows 10 | before-window best 186583, window best 22940 | PROGRESS: drt_violations improved 87.7 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 6.6 | drt_violations best 2057 last 2057 rows 12 | before-window best 112571, window best 2057 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_1_grt | 2.1 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 33.6 | drt_violations best 13426 last 13426 rows 15 | before-window best 19595, window best 13426 | PROGRESS: drt_violations improved 31.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 26.9 | drt_violations best 15355 last 15355 rows 14 | before-window best 32431, window best 15355 | PROGRESS: drt_violations improved 52.7 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 11.8 | drt_violations best 141373 last 141373 rows 2 | before-window best 407677, window best 141373 | PROGRESS: drt_violations improved 65.3 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_1_grt | 3.1 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | 5_1_grt | 3.1 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_1_grt | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 200 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 194 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 229 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 237 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 213 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 5.2 | repair_TNS best 0 last 0 rows 198 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 6.1 | last meaningful line 5.8 h ago (208/209 lines) | PROGRESS: log still growing |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 10.4 | drt_violations best 2 last 2 rows 52 | before-window best 424, window best 2 | PROGRESS: drt_violations improved 99.5 % in window |  |
