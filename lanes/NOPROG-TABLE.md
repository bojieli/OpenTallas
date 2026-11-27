# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 06:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 2, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 30.8 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 35.2 | last meaningful line 21.0 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 21.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | prd-eco_20261127_032706_785961-i2-2106540 | eco_20261127_032706_785961-i2 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (296/297 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261127_032948_4033419-i1t-3360935 | eco_20261127_032948_4033419-i1t | 5_2_route | 2.5 | drt_violations best 9803 last 9803 rows 2 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 15.3 | drt_violations best 426 last 426 rows 35 | before-window best 852, window best 426 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 69.9 | drt_violations best 8 last 8 rows 62 | before-window best 8, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 21.9 | drt_violations best 54 last 54 rows 42 | before-window best 116, window best 54 | PROGRESS: drt_violations improved 53.4 % in window |  |
