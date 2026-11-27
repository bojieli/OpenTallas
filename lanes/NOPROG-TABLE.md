# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 09:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 34.3 | drt_violations best 7 last 32 rows 44 | before-window best 7, window best 32 | NO-PROGRESS: drt_violations best 32 vs 7 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 18.8 | drt_violations best 388 last 389 rows 42 | before-window best 448, window best 388 | PROGRESS: drt_violations improved 13.4 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 73.4 | drt_violations best 7 last 7 rows 64 | before-window best 8, window best 7 | PROGRESS: drt_violations improved 12.5 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 25.4 | drt_violations best 53 last 53 rows 45 | before-window best 83, window best 53 | PROGRESS: drt_violations improved 36.1 % in window |  |
