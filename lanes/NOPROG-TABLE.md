# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 05:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-STUCK': 2, 'CANCEL-NOW': 3, 'GRT-LABEL': 15, 'NO-DATA': 10, 'YOUNG': 177, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 14.5 | last meaningful line 12.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 12.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 32.9 | grt rounds 6 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 -> 25:22767 -> 30:12274 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:10120 -> 25:22767 -> 30:12274; best 1 | REPORTED (cancel next pass) |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 45.8 | grt rounds 6 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 -> 30:9582 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:7397 -> 25:22417 -> 30:9582; best 958 | REPORT-ONLY: lane-own kit (fable-fix-s81-leaf-2140 |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-3063508 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | postcts_gate_FF | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3072708 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3072708-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 6.7 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 44.2 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 58.6 | grt rounds 6 overflow 5:9167 -> 10:5570 -> 15:3582 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 2.5 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 37.7 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 42.7 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 32.1 | grt rounds 4 overflow 5:55819 -> 10:49018 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 32.1 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 41.8 | grt rounds 4 overflow 5:82513 -> 10:50077 -> 15:42880 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 31.6 | grt rounds 4 overflow 5:108343 -> 10:69762 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 6.4 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 15.4 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 56.5 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 39.3 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8231 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-bk-sel--t2-grt-300210 | bk-sel--t2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-3225820 | cbf_q00 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (6807/6807 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r1__t1__clf32cde8d__pvd9381c1d-3860918 | col_h9_r1__t1 | 3_5_place_dp | 0.3 | repair_Violations best 213968 last 213968 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-coll_core-3628903 | coll_core | 3_3_place_gp | 0.5 | overflow best 0.4215 last 0.4215 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-3788069 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_3_place_gp | 0.4 | overflow best 0.2932 last 0.2932 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | 5_2_route | 4.8 | drt_violations best 57053 last 57053 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 5.3 | drt_violations best 28 last 30 rows 51 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 7.1 | drt_violations best 5300 last 5300 rows 13 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3442077 | ot_s81sl_leaf__t25 | pregrt_ff_hold | 0.7 | repair_Violations best 3203 last 3236 rows 86 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t58-3457908 | ot_s81sl_leaf__t58 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t7-3495266 | ot_s81sl_leaf__t7 | tt_setup_repair | 0.6 | repair_Violations best 89 last 137 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_1_grt | 6.9 | last meaningful line 0.0 h ago (1166/1172 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 7.2 | drt_violations best 48857 last 48857 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 7.0 | last meaningful line 2.7 h ago (220/1545 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | postcts_gate_TT | 7.0 | last meaningful line -0.0 h ago (37377/37377 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | postcts_gate_TT | 6.9 | last meaningful line 0.0 h ago (1088/1088 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-13726-22506 | 13726 | s81_head.t.ot_s81hd_ctl_nstrip | 0.2 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-309422-1691 | 309422 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-330998-24919 | 330998 | s81_head.t.ot_s81hd_ctl_nstrip | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3847572-23521 | 3847572 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-49680-17069 | 49680 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-49835-23343 | 49835 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-616218-14777 | 616218 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 5.7 | drt_violations best 6972 last 6972 rows 9 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-2610090 | col_h10_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 21103.8 last 21103.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2633203 | col_h9_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 20474 last 20474 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2682799 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2667127 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2671221 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-2695780 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-2702758 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2738443 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2741085 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2767328 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3440653 | dsdv_slice_lepw_mus_LP__t2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7317 last 0.7324 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-gunit__t1-2764618 | gunit__t1 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (197/203 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-2754359 | iqf__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-2784457 | ot_s81sl_kv_leaf__t3 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3086/3086 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-2789488 | ot_s81sl_leaf__t1 | 3_3_place_gp | 0.7 | last meaningful line 0.3 h ago (114/114 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t10-2768081 | ot_s81sl_leaf__t10 | 3_3_place_gp | 0.7 | overflow best 0.6781 last 0.6781 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t12-2799940 | ot_s81sl_leaf__t12 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4572/4573 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t14-2796357 | ot_s81sl_leaf__t14 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4356/4356 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-2801937 | ot_s81sl_leaf__t15 | pregrt_ff_hold | 0.7 | repair_TNS best 45578.2 last 45578.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t16-2785627 | ot_s81sl_leaf__t16 | 3_3_place_gp | 0.7 | overflow best 0.4217 last 0.4217 rows 33 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t21-2807445 | ot_s81sl_leaf__t21 | pregrt_ff_hold | 0.7 | repair_TNS best 62100.2 last 62100.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t22-2818785 | ot_s81sl_leaf__t22 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4201/4201 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t24__cl2456157b-2800341 | ot_s81sl_leaf__t24 | 3_5_place_dp | 0.7 | last meaningful line 0.1 h ago (38/38 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-2826195 | ot_s81sl_leaf__t26 | pregrt_ff_hold | 0.7 | repair_TNS best 11977.8 last 11977.8 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2811685 | ot_s81sl_leaf__t30 | 4_1_cts | 0.7 | repair_Violations best 8 last 24 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-2844097 | ot_s81sl_leaf__t34 | tt_setup_repair | 0.7 | last meaningful line -0.0 h ago (294/294 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | pregrt_ff_hold | 0.7 | last meaningful line -0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-2864631 | ot_s81sl_leaf__t36 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3741/3741 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t38-2847712 | ot_s81sl_leaf__t38 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-2883041 | ot_s81sl_leaf__t4 | tt_setup_repair | 0.7 | repair_Violations best 59 last 325 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-2875591 | ot_s81sl_leaf__t44 | tt_setup_repair | 0.7 | repair_Violations best 1660 last 3491 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4463/4463 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t5-2905422 | ot_s81sl_leaf__t5 | pregrt_ff_hold | 0.7 | repair_TNS best 200047 last 200047 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t50-2871099 | ot_s81sl_leaf__t50 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-2889160 | ot_s81sl_leaf__t54 | pregrt_ff_hold | 0.7 | repair_Violations best 4400 last 4426 rows 43 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-2885728 | ot_s81sl_leaf__t57 | 3_3_place_gp | 0.7 | overflow best 0.1983 last 0.1983 rows 46 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-2912844 | ot_s81sl_leaf__t60 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4051/4051 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-2924212 | ot_s81sl_leaf__t65 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4521/4521 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-2906128 | ot_s81sl_leaf__t67 | 3_3_place_gp | 0.7 | overflow best 0.4881 last 0.4881 rows 21 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t70-2915763 | ot_s81sl_leaf__t70 | 3_3_place_gp | 0.7 | overflow best 0.488 last 0.488 rows 32 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t72-2931601 | ot_s81sl_leaf__t72 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5608/5608 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t74-2930328 | ot_s81sl_leaf__t74 | tt_setup_repair | 0.7 | repair_Remaining best 81809 last 81809 rows 86 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | postcts_gate_TT | 7.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 5_1_grt | 7.3 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 5_1_grt | 7.3 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_2_route | 7.3 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 5_2_route | 7.2 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | pregrt_ff_hold | 1.1 | repair_TNS best 60587.8 last 60587.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 7.2 | repair_TNS best 1595.85 last 1595.85 rows 5 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 7.2 | repair_TNS best 680.582 last 680.582 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 7.2 | repair_TNS best 73259.3 last 73259.3 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 5_1_grt | 7.2 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | postcts_gate_TT | 7.2 | last meaningful line 0.0 h ago (1518/1518 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-3539997-3077 | 3539997 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-3547227-32188 | 3547227 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-3717177-15267 | 3717177 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-3805345-19722 | 3805345 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_051545_3846533-i1t-3825271 | eco_20261122_051545_3846533-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-145913 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.1 | overflow best 0.6845 last 0.6904 rows 15 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t56-655531 | ot_s81sl_leaf__t56 | 3_3_place_gp | 0.7 | overflow best 0.3074 last 0.3074 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t8-694119 | ot_s81sl_leaf__t8 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (234/234 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-986726 | sle_ctl | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | postcts_gate_FF | 7.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_1_grt | 7.3 | last meaningful line 0.1 h ago (1097/1114 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 5_1_grt | 1.4 | repair_Remaining best 75844 last 75844 rows 50 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 7.2 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_105456_3667962-i1-2785704 | eco_20261122_105456_3667962-i1 | 5_2_route | 2.5 | drt_violations best 47 last 47 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | so_1633932_ff_73415 | so_1633932_ff_73415 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_1633932_tt_73415 | so_1633932_tt_73415 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_2_route | 9.1 | drt_violations best 116357 last 116357 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 50692.5 last 50692.5 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 90469.7 last 90469.7 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 6.4 | drt_violations best 100260 last 100260 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_2_route | 17.2 | drt_violations best 92608 last 92608 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1938614 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2578730 | kv3_hub_C | 2_1_floorplan | 0.2 | repair_Viol best 1797 last 1797 rows 72 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 5_1_grt | 3.2 | last meaningful line 0.4 h ago (232/933 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (6684/6684 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3890798 | kv3_hub_Eo | 3_5_place_dp | 2.4 | last meaningful line 0.3 h ago (116/116 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (6806/6806 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3879851 | kv3_hub_Wo | 3_5_place_dp | 2.4 | last meaningful line 0.3 h ago (117/117 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | nowave-lec-sml_h259 | nowave-lec-sml_h259 | gold.ys | 0.5 | last meaningful line 0.2 h ago (29124/29124 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-2764380-29913 | 2764380 | qwen_kvsys.t.kv_cland_w145_ew_7d736 | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-3107623-11623 | 3107623 | 6_report | 0.0 | last meaningful line 0.0 h ago (711/711 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-fin-3166843 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1065/1065 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 5.3 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | tt_setup_measure_grt | 3.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 60299.1 last 60299.1 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_LP__t2-186108 | dsdv_slice_lepw_mu_LP__t2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6952 last 0.7309 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-glue-344102 | glue | 5_2_route | 7.1 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3967683 | kv3_pc_v3 | 2_3_floorplan_tapcell | 0.7 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3969057 | kv3_pc_v3 | 2_2_floorplan_macro | 0.7 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t59-3957582 | ot_s81sl_leaf__t59 | 3_3_place_gp | 0.7 | overflow best 0.2016 last 0.2016 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4247/4247 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_1_grt | 7.1 | last meaningful line 0.3 h ago (1272/1302 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_1_grt | 7.2 | last meaningful line 0.1 h ago (1038/1038 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | postcts_gate_TT | 7.6 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | tt_setup_repair_grt | 7.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_1_grt | 7.2 | last meaningful line 0.1 h ago (1113/1130 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 5_2_route | 7.8 | drt_violations best 6844 last 6844 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 7.1 | drt_violations best 249 last 249 rows 11 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 3.1 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4120075 | eco-i1t | 5_2_route | 3.8 | drt_violations best 3383 last 3383 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | prd-eco2-i2t-3578697 | eco2-i2t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 6.0 | drt_violations best 10021 last 10021 rows 8 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.1984 last 0.1984 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-2015717 | col_h10_r1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-919784 | col_h10_r2__t1 | tt_setup_repair | 0.7 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-2058116 | col_h10_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 144401 last 144401 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-933599 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.7 | overflow best 0.1998 last 0.1998 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.7 | overflow best 0.2392 last 0.2392 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 5.9 | drt_violations best 86218 last 86218 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-946485 | col_h9_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 32584.1 last 32584.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t1-968155 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1066404 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-1041357 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-987195 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t8-997295 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-1012827 | dsdv_slice_iq_C__t1 | 2_1_floorplan | 0.7 | repair_Viol best 8980 last 8980 rows 1131 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_kv512_C__t1-1012934 | dsdv_slice_kv512_C__t1 | 2_1_floorplan | 0.7 | last meaningful line 0.0 h ago (1370/1370 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_LP__t2-1853771 | dsdv_slice_lepe_mu_LP__t2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1079555 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-1057149 | dsdv_slice_lepe_nh_mus_LP__t1 | hold_gate | 0.7 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 3_3_place_gp | 0.7 | overflow best 0.7305 last 0.7344 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-gunit__t1-1020217 | gunit__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.1 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 6.5 | drt_violations best 87099 last 87099 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-1537459 | kv3_hub_Ei | 3_5_place_dp | 3.7 | last meaningful line 0.8 h ago (114/114 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 2_1_floorplan | 0.7 | repair_Viol best 1304 last 1304 rows 637 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (2965/2965 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-1096621 | ot_s81sl_leaf__t2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4286/4286 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t31-1082760 | ot_s81sl_leaf__t31 | 3_3_place_gp | 0.7 | last meaningful line 0.3 h ago (82/82 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4226/4226 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (1189/1195 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-seqhost__t1-1139133 | seqhost__t1 | 2_1_floorplan | 0.7 | repair_Viol best 2403 last 2403 rows 1020 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-serdes__t12-1669942 | serdes__t12 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (12360/12360 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 5_1_grt | 6.6 | last meaningful line 0.0 h ago (199/200 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_1_grt | 7.5 | last meaningful line 1.0 h ago (218/1079 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | otc-1783005-9556 | 1783005 | qwen_compute.t.slw_sc_v3 | 0.3 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1917694-8119 | 1917694 | qwen_compute.t.slw_sc_v3 | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-2047425-5864 | 2047425 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 3.7 | drt_violations best 58 last 58 rows 12 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3016152 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2743 last 0.2743 rows 33 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 45008.8 last 45008.8 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-coll_ftm-2637008 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.0 | repair_TNS best 23523 last 23523 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.5 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-hd_host_n-1689611 | hd_host_n | 5_2_route | 1.1 | drt_violations best 3 last 3 rows 29 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-hd_lep0N-2232792 | hd_lep0N | 3_3_place_gp | 0.7 | last meaningful line 0.2 h ago (192/192 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N_w-3792090 | hd_lep0N_w | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3070868 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3085154 | hd_turn_a | postcts_gate_FF | 0.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t1-3886007 | ot_s81sl_kv_leaf__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (407/407 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2644024 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (2757/2757 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i1-3128620 | eco_20261122_041142_2199995-i1 | 5_2_route | 0.2 | last meaningful line 0.0 h ago (212/212 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_3994488_ff_3035 | so_3994488_ff_3035 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3994488_tt_3035 | so_3994488_tt_3035 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | otc-1036906-7647 | 1036906 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | otc-967133-15498 | 967133 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 46.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 8.9 | last meaningful line 0.0 h ago (1161073/1161073 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 50.7 | last meaningful line 1.1 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2653133 | col_h9_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2665763 | col_h9_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 7.3 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 7.2 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_1_grt | 7.2 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 17.1 | drt_violations best 49344 last 49344 rows 15 | before-window best 53583, window best 49344 | PROGRESS: drt_violations improved 7.9 % in window |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 16.6 | drt_violations best 597 last 1488 rows 29 | before-window best 1162, window best 597 | PROGRESS: drt_violations improved 48.6 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 16.4 | drt_violations best 45146 last 45146 rows 14 | before-window best 53153, window best 45146 | PROGRESS: drt_violations improved 15.1 % in window |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3955196 | ot_s81sl_leaf__t40 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_1_grt | 7.7 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-948983 | col_h9_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t14-1454507 | serdes__t14 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 8.2 | drt_violations best 12000 last 12000 rows 9 | before-window best 152197, window best 12000 | PROGRESS: drt_violations improved 92.1 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 11.6 | drt_violations best 29 last 29 rows 32 | before-window best 170434, window best 29 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2763617 | col_h10_r1__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t12-3114107 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
