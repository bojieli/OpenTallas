# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 00:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'CANCEL-NOW': 1, 'YOUNG': 3, 'NO-DATA': 1, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 29.8 | last meaningful line 20.7 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 20.7 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 25.3 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best 33 | NO-PROGRESS: drt_violations best 33 vs 7 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| epyc8 | otc-3701829-19909 | 3701829 | hbm.t.q_spt2 | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 59.6 | drt_violations best 1 last 1 rows 51 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 29.7 | last meaningful line 20.4 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 20.4 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc2 | prd-eco_20261126_045746_1995760-i3-2984355 | eco_20261126_045746_1995760-i3 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-639223-14937 | 639223 | s81_head.t.hd_turn_a--signoff-ef1e47f1ac7d | 0.2 | last meaningful line 0.2 h ago (4/4 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-818762-20323 | 818762 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261127_032706_785961-i1-2319807 | eco_20261127_032706_785961-i1 | 5_2_route | 2.2 | drt_violations best 3 last 3 rows 14 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-2778474-26546 | 2778474 | qwen_compute.t.slw_hc2__cla3497502__cldc737267 | 0.6 |  | KEEP: qwen_compute.t.slw_hc2__cla3497502__cldc737267	FLOW-OPS-R2	same job (type ident) |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 9.8 | drt_violations best 783 last 783 rows 22 | before-window best 468535, window best 783 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 64.4 | drt_violations best 8 last 8 rows 62 | before-window best 9, window best 8 | PROGRESS: drt_violations improved 11.1 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 16.4 | drt_violations best 85 last 85 rows 28 | before-window best 225882, window best 85 | PROGRESS: drt_violations improved 100.0 % in window |  |
