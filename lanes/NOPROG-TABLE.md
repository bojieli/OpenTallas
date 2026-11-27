# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 00:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'CANCEL-NOW': 3, 'NO-DATA': 4, 'YOUNG': 10, 'PROGRESS': 3}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 29.3 | last meaningful line 20.6 h ago (33/38 lines) | NO-PROGRESS: no new non-iteration log line for 20.6 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc10 | otc-85983-18648 | 85983 | hbm.t.q_spb1 | 0.1 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 24.8 | drt_violations best 7 last 33 rows 43 | before-window best 7, window best 33 | NO-PROGRESS: drt_violations best 33 vs 7 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-FWV1-HOLD decides; n |
| epyc8 | otc-3007156-16293 | 3007156 | hbm.t.q_spt2 | 0.1 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 59.1 | drt_violations best 1 last 1 rows 51 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2778474-26546 | 2778474 | hbm.t.vsN1 | 0.1 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 29.2 | last meaningful line 20.3 h ago (33/37 lines) | NO-PROGRESS: no new non-iteration log line for 20.3 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | hdmesh-lec-D_relay_norename | hdmesh-lec-D_relay_norename | - | 9.0 |  | NO-DATA: no log found |  |
| epyc11 | otc-704547-27344 | 704547 | s81.t.slice_station__t52 | 0.2 | last meaningful line 0.1 h ago (2/2 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | otc-800688-3541 | 800688 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261126_045746_1995760-i3-2984355 | eco_20261126_045746_1995760-i3 | 5_1_grt | 0.5 | repair_Remaining best 438363 last 438363 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-coll_ft__cl78c7b300-91388 | coll_ft | 3_3_place_gp | 0.1 | overflow best 0.3419 last 0.3419 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-coll_ftm-184580 | coll_ftm | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (201/201 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | klegacy-ot_s81sl_xs4_xs4pair44preview-77220-lec | ot_s81sl_xs4_xs4pair44preview | gate.ys | 0.0 | last meaningful line 0.0 h ago (72454/72454 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | klegacy-ot_s81sl_xs4_xs4pairfusedpreview-3944282-lec | ot_s81sl_xs4_xs4pairfusedpreview | gold.ys | 0.2 | last meaningful line 0.2 h ago (65549/65549 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-189067-23624 | 189067 | lec | 0.0 | LEC last write 0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc7 | prd-eco_20261127_032706_785961-i1-2319807 | eco_20261127_032706_785961-i1 | 5_2_route | 1.7 | drt_violations best 199 last 199 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-coll_n-3100112 | coll_n | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cla4a25d77-2842200 | coll_ft | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-coll_ftc-2843508 | coll_ftc | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2848871-31309 | 2848871 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-800056 | slw_sc_v1 | 5_2_route | 9.3 | drt_violations best 852 last 852 rows 20 | before-window best 468535, window best 852 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 63.9 | drt_violations best 8 last 8 rows 62 | before-window best 9, window best 8 | PROGRESS: drt_violations improved 11.1 % in window |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 15.9 | drt_violations best 116 last 116 rows 26 | before-window best 225882, window best 116 | PROGRESS: drt_violations improved 99.9 % in window |  |
