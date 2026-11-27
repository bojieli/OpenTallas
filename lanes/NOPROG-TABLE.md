# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 07:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 2, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 31.8 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 36.2 | last meaningful line 21.1 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 21.1 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | eco-abs-4018587 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261127_032948_4033419-i1-680284 | eco_20261127_032948_4033419-i1 | 5_1_grt | 0.6 | repair_TNS best 18.969 last 18.969 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 16.3 | drt_violations best 421 last 421 rows 37 | before-window best 724, window best 421 | PROGRESS: drt_violations improved 41.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 70.9 | drt_violations best 8 last 8 rows 62 | before-window best 8, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 22.9 | drt_violations best 54 last 54 rows 43 | before-window best 83, window best 54 | PROGRESS: drt_violations improved 34.9 % in window |  |
