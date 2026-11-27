# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 05:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 2, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 30.0 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 34.5 | last meaningful line 20.9 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 20.9 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | prd-eco_20261127_032706_785961-i2-2106540 | eco_20261127_032706_785961-i2 | 5_1_grt | 0.6 | last meaningful line 0.4 h ago (304/967 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261127_032948_4033419-i1t-3360935 | eco_20261127_032948_4033419-i1t | 5_2_route | 1.7 | drt_violations best 65737 last 65737 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 14.6 | drt_violations best 438 last 438 rows 32 | before-window best 1145, window best 438 | PROGRESS: drt_violations improved 61.7 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 69.1 | drt_violations best 8 last 8 rows 62 | before-window best 8, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 21.1 | drt_violations best 71 last 71 rows 36 | before-window best 118, window best 71 | PROGRESS: drt_violations improved 39.8 % in window |  |
