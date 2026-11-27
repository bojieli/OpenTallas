# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 04:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'YOUNG': 2, 'PROGRESS': 2}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 29.5 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 68.6 | drt_violations best 8 last 8 rows 62 | before-window best 8, window best 8 | NO-PROGRESS: drt_violations best 8 vs 8 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 34.0 | last meaningful line 20.9 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 20.9 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | prd-eco_20261127_032706_785961-i2-2106540 | eco_20261127_032706_785961-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261127_032948_4033419-i1t-3360935 | eco_20261127_032948_4033419-i1t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 14.1 | drt_violations best 446 last 446 rows 31 | before-window best 1501, window best 446 | PROGRESS: drt_violations improved 70.3 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 20.6 | drt_violations best 72 last 72 rows 33 | before-window best 118, window best 72 | PROGRESS: drt_violations improved 39.0 % in window |  |
