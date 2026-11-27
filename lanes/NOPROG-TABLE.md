# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-27 12:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'NO-DATA': 18, 'YOUNG': 8, 'PROGRESS': 1}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 5_2_route | 28.1 | drt_violations best 53 last 53 rows 49 | before-window best 54, window best 53 | NO-PROGRESS: drt_violations best 53 vs 54 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | lecr3-0dc797b4d1 | lecr3-0dc797b4d1 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | lecr3-c0045a7e3b | lecr3-c0045a7e3b | - | 2.1 |  | NO-DATA: no log found |  |
| epyc10 | lecr3-f8402a963f | lecr3-f8402a963f | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | lecr3qc-225c4e75d4 | lecr3qc-225c4e75d4 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc10 | lecr3qc-a053025a93 | lecr3qc-a053025a93 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc11 | hdmesh-lec-E_relay_first | hdmesh-lec-E_relay_first | - | 1.8 |  | NO-DATA: no log found |  |
| epyc11 | lecr3qc-9a5e106dcf | lecr3qc-9a5e106dcf | - | 0.9 |  | NO-DATA: no log found |  |
| epyc11 | lecr3qc-bf3db095ce | lecr3qc-bf3db095ce | - | 1.0 |  | NO-DATA: no log found |  |
| epyc11 | lecr3qc-dbc087d84e | lecr3qc-dbc087d84e | - | 0.8 |  | NO-DATA: no log found |  |
| epyc12 | otc-2188194-26009 | 2188194 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-ot_s81sl_leaf__t12-853126 | ot_s81sl_leaf__t12 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (8285/8285 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-2122148 | sle_fw_v1 | 5_2_route | 2.6 | drt_violations best 192025 last 192025 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | lecr3qc-070ea464a2 | lecr3qc-070ea464a2 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc7 | lecr3qc-690c806c46 | lecr3qc-690c806c46 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-1740065-27456 | 1740065 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-kv3_pv_v6ne-3329758 | kv3_pv_v6ne | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_sys_c-2772428 | kv3_sys_c | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3359712 | sle_st_b_v1 | 3_3_place_gp | 1.5 | overflow best 0.0992 last 0.0992 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-3334747 | slw_st_b_v1 | 3_4_place_resized | 1.5 | repair_Remaining best 136780 last 136780 rows 273 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | lecr3qc-16390a86af | lecr3qc-16390a86af | - | 0.9 |  | NO-DATA: no log found |  |
| epyc8 | lecr3qc-af0dd3edae | lecr3qc-af0dd3edae | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | lecr3qc-e9d9a8c65d | lecr3qc-e9d9a8c65d | - | 0.9 |  | NO-DATA: no log found |  |
| intel1 | dpkit-hd_ctl_n-2148668 | hd_ctl_n | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-496488 | sle_st_b_v1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | lecr3-b24a0a4fa1 | lecr3-b24a0a4fa1 | - | 1.9 |  | NO-DATA: no log found |  |
| intel1 | lecr3-d8097d4d45 | lecr3-d8097d4d45 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 76.1 | drt_violations best 7 last 7 rows 64 | before-window best 8, window best 7 | PROGRESS: drt_violations improved 12.5 % in window |  |
