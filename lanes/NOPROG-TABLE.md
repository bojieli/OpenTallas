# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 08:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 33.3 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 37.7 | last meaningful line 21.2 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 21.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | prd-count-p1_tc-680284 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 17.8 | drt_violations best 391 last 391 rows 40 | before-window best 658, window best 391 | PROGRESS: drt_violations improved 40.6 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 72.4 | drt_violations best 7 last 7 rows 64 | before-window best 8, window best 7 | PROGRESS: drt_violations improved 12.5 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 24.4 | drt_violations best 53 last 53 rows 44 | before-window best 83, window best 53 | PROGRESS: drt_violations improved 36.1 % in window |  |
