# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 07:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 32.5 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 37.0 | last meaningful line 21.2 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 21.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | prd-eco_20261127_032948_4033419-i1-680284 | eco_20261127_032948_4033419-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (260/261 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 17.1 | drt_violations best 394 last 394 rows 39 | before-window best 724, window best 394 | PROGRESS: drt_violations improved 45.6 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 71.6 | drt_violations best 8 last 8 rows 62 | before-window best 8, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 23.6 | drt_violations best 53 last 53 rows 44 | before-window best 83, window best 53 | PROGRESS: drt_violations improved 36.1 % in window |  |
