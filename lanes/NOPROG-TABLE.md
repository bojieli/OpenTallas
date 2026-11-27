# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 07:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'YOUNG': 3, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 32.3 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 36.7 | last meaningful line 21.1 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 21.1 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | so_15203_ff_4110 | so_15203_ff_4110 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | so_15203_tt_4110 | so_15203_tt_4110 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261127_032948_4033419-i1-680284 | eco_20261127_032948_4033419-i1 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (243/243 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 16.8 | drt_violations best 420 last 420 rows 38 | before-window best 724, window best 420 | PROGRESS: drt_violations improved 42.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 71.4 | drt_violations best 8 last 8 rows 62 | before-window best 8, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 23.4 | drt_violations best 54 last 54 rows 43 | before-window best 83, window best 54 | PROGRESS: drt_violations improved 34.9 % in window |  |
