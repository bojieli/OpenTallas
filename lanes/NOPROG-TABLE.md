# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 00:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'CANCEL-NOW': 3, 'YOUNG': 5, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 29.5 | last meaningful line 20.7 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 20.7 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc10 | otc-85983-18648 | 85983 | hbm.t.q_spb1 | 0.3 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 25.0 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best 33 | NO-PROGRESS: drt_violations best 33 vs 7 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| epyc8 | otc-3007156-16293 | 3007156 | hbm.t.q_spt2 | 0.3 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 59.4 | drt_violations best 1 last 1 rows 51 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2778474-26546 | 2778474 | hbm.t.vsN1 | 0.3 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 29.5 | last meaningful line 20.4 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 20.4 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc10 | dpkit-coll_ftn-301545 | coll_ftn | 3_3_place_gp | 0.1 | overflow best 0.1418 last 0.1418 rows 47 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i3-2984355 | eco_20261126_045746_1995760-i3 | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (297/408 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftm-184580 | coll_ftm | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | klegacy-ot_s81sl_xs4_xs4pair44preview-77220-lec | ot_s81sl_xs4_xs4pair44preview | gate.ys | 0.3 | last meaningful line 0.2 h ago (76208/76208 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261127_032706_785961-i1-2319807 | eco_20261127_032706_785961-i1 | 5_2_route | 2.0 | drt_violations best 199 last 199 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 9.6 | drt_violations best 796 last 796 rows 21 | before-window best 468535, window best 796 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 64.1 | drt_violations best 8 last 8 rows 62 | before-window best 9, window best 8 | PROGRESS: drt_violations improved 11.1 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 16.1 | drt_violations best 85 last 85 rows 28 | before-window best 225882, window best 85 | PROGRESS: drt_violations improved 100.0 % in window |  |
