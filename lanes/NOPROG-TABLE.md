# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 06:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 1, 'PROGRESS': 4}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 31.3 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 35.7 | last meaningful line 21.1 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 21.1 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | prd-eco_20261127_032948_4033419-i1-680284 | eco_20261127_032948_4033419-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 15.8 | drt_violations best 421 last 421 rows 37 | before-window best 783, window best 421 | PROGRESS: drt_violations improved 46.2 % in window |  |
| epyc7 | prd-eco_20261127_032706_785961-i2-2106540 | eco_20261127_032706_785961-i2 | 5_2_route | 1.9 | drt_violations best 0 last 0 rows 16 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 70.4 | drt_violations best 8 last 8 rows 62 | before-window best 8, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 22.4 | drt_violations best 54 last 54 rows 43 | before-window best 85, window best 54 | PROGRESS: drt_violations improved 36.5 % in window |  |
