# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 04:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'NO-DATA': 1, 'YOUNG': 2, 'PROGRESS': 4}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 29.0 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 33.2 | last meaningful line 20.8 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 20.8 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | h10-mask-pg-1572239 | h10-mask-pg | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | prd-count-p1_tc-3332824 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261127_032948_4033419-i1t-3360935 | eco_20261127_032948_4033419-i1t | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (1285/1353 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 13.6 | drt_violations best 448 last 448 rows 30 | before-window best 2996, window best 448 | PROGRESS: drt_violations improved 85.0 % in window |  |
| epyc7 | otc-376547-15081 | 376547 | grt_only | 1.2 | repair_TNS best 0 last 0 rows 153 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 68.1 | drt_violations best 8 last 8 rows 62 | before-window best 9, window best 8 | PROGRESS: drt_violations improved 11.1 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 19.9 | drt_violations best 83 last 83 rows 31 | before-window best 174, window best 83 | PROGRESS: drt_violations improved 52.3 % in window |  |
