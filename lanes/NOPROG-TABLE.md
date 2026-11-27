# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 22:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'NO-DATA': 2, 'YOUNG': 6, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 27.5 | last meaningful line 20.3 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 20.3 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 23.0 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best 33 | NO-PROGRESS: drt_violations best 33 vs 7 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 57.4 | drt_violations best 1 last 1 rows 51 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 27.5 | last meaningful line 20.2 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 20.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | hdmesh-lec-D_relay_norename | hdmesh-lec-D_relay_norename | - | 7.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-3622744-22114 | 3622744 | qwen_compute.t.qfd_qc_su_lane_w_l1_m44s1 | 0.4 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-3849430-31409 | 3849430 | qwen_compute.t.qfd_qc_su_lane_w_l1_m44s1 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i3t-605705 | eco_20261126_045746_1995760-i3t | 5_2_route | 2.0 | drt_violations best 223 last 223 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-2272451-22380 | 2272451 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-fin-2883915 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-1491488 | coll_ftc | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-hd_spn_wshim_tx-184806 | hd_spn_wshim_tx | abstract_exact | 1.0 | last meaningful line 0.3 h ago (4/4 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-803149-20499 | 803149 | qwen_compute.t.slw_su_l0__cl76fb247e | 0.1 |  | KEEP: qwen_compute.t.slw_su_l0__cl76fb247e	FLOW-OPS-R2	same job (type ident) |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 7.6 | drt_violations best 2996 last 2996 rows 14 | before-window best 468535, window best 2996 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 62.1 | drt_violations best 9 last 9 rows 60 | before-window best 9, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 14.1 | drt_violations best 137 last 137 rows 20 | before-window best 225882, window best 137 | PROGRESS: drt_violations improved 99.9 % in window |  |
