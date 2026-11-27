# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 04:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 2, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 29.3 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 33.7 | last meaningful line 20.9 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 20.9 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | prd-fin-3332824 | fin | 6_report | 0.1 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261127_032948_4033419-i1t-3360935 | eco_20261127_032948_4033419-i1t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (251/251 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 13.8 | drt_violations best 446 last 446 rows 31 | before-window best 1784, window best 446 | PROGRESS: drt_violations improved 75.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 68.4 | drt_violations best 8 last 8 rows 62 | before-window best 9, window best 8 | PROGRESS: drt_violations improved 11.1 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 20.4 | drt_violations best 83 last 83 rows 32 | before-window best 118, window best 83 | PROGRESS: drt_violations improved 29.7 % in window |  |
