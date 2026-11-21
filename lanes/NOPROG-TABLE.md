# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 00:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'GRT-LABEL': 71, 'YOUNG': 196, 'NO-DATA': 16, 'EXCLUDED': 6, 'KEEP': 3, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | tt_setup_repair | 5.2 | repair_Violations best 50 last 50 rows 47 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -643.26 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | pregrt_ff_hold | 4.0 | repair_TNS best 3.89284e+06 last 3.89284e+06 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -540.84 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 12.6 | drt_violations best 67710 last 67710 rows 1 | before-window best 67710, window best 67710 | NO-PROGRESS: drt_violations best 67710 vs 67710 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:107046 -> 10:5611 -> 15:4511 | GRT-LABEL: DESIGN-FAIL: overflow 5611 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | 5_1_grt | 4.8 | grt rounds 4 overflow 5:105728 -> 10:5561 -> 15:4342 -> 20:4553 | GRT-LABEL: DESIGN-FAIL: overflow 5561 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | 5_1_grt | 4.8 | grt rounds 3 overflow 5:78045 -> 10:9505 -> 15:5664 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:57082 -> 10:9441 -> 15:5560 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:73297 -> 10:2715 -> 15:1964 | GRT-LABEL: DESIGN-FAIL: overflow 2715 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:4272 -> 10:1881 -> 15:1312 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:3628 -> 10:1762 -> 15:1404 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:4951 -> 10:2471 -> 15:1527 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:4548 -> 10:1905 -> 15:1587 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 7.0 | grt rounds 3 overflow 5:4957 -> 10:1801 -> 15:1471 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 16.4 | grt rounds 2 overflow 5:95762 -> 10:93332 | GRT-LABEL: DESIGN-FAIL: overflow 93332 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 27.5 | grt rounds 3 overflow 5:52450 -> 10:47147 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | 5_1_grt | 27.8 | grt rounds 3 overflow 5:77669 -> 10:64592 -> 15:70550 | GRT-LABEL: DESIGN-FAIL: overflow 64592 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 16.6 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 16.4 | grt rounds 3 overflow 5:46824 -> 10:46291 -> 15:36400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 26.3 | grt rounds 4 overflow 5:27938 -> 10:20130 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 15.2 | grt rounds 3 overflow 5:62592 -> 10:60312 -> 15:50065 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:64225 -> 10:59002 -> 15:49395 | GRT-LABEL: DESIGN-FAIL: overflow 59002 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | 5_1_grt | 16.4 | grt rounds 4 overflow 5:67974 -> 10:56777 -> 15:48789 -> 20:49650 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | 5_1_grt | 7.0 | grt rounds 3 overflow 5:54149 -> 10:53822 -> 15:47011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | 5_1_grt | 16.3 | grt rounds 4 overflow 5:41163 -> 10:38473 -> 15:34810 -> 20:35458 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 15.1 | grt rounds 3 overflow 5:50445 -> 10:43383 -> 15:40589 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 35.4 | grt rounds 4 overflow 5:55847 -> 10:40235 -> 15:37035 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 29.6 | grt rounds 4 overflow 5:9414 -> 10:5163 -> 15:3613 -> 20:3104 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 30.1 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_1_grt | 5.1 | grt rounds 6 overflow 5:998 -> 10:763 -> 15:741 -> 20:704 -> 25:389 -> 30:135 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 18.8 | grt rounds 3 overflow 5:50575 -> 10:40510 -> 15:34585 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 19.0 | grt rounds 6 overflow 5:6798 -> 10:4941 -> 15:2610 -> 20:2287 -> 25:3051 -> 30:2207 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | 5_1_grt | 12.4 | grt rounds 4 overflow 5:29295 -> 10:20211 -> 15:15551 -> 20:13785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 5_1_grt | 11.5 | grt rounds 4 overflow 5:21059 -> 10:13278 -> 15:11945 -> 20:8925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | 5_1_grt | 7.2 | grt rounds 1 overflow 5:7293 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 5_1_grt | 7.5 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 8.7 | grt rounds 2 overflow 5:94966 -> 10:134399 | GRT-LABEL: DESIGN-FAIL: overflow 134399 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 13.7 | grt rounds 2 overflow 5:83767 -> 10:75075 | GRT-LABEL: DESIGN-FAIL: overflow 75075 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | 5_1_grt | 10.1 | grt rounds 3 overflow 5:49890 -> 10:42666 -> 15:36551 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:56566 -> 10:49891 | GRT-LABEL: DESIGN-FAIL: overflow 49891 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:57966 -> 10:49002 | GRT-LABEL: DESIGN-FAIL: overflow 49002 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:46084 -> 10:49598 -> 15:43557 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1223391 | ot_s81sl_leaf__t39 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:52034 -> 10:41607 | GRT-LABEL: DESIGN-FAIL: overflow 41607 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:38551 -> 10:38976 -> 15:36671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 4.3 | grt rounds 3 overflow 5:35093 -> 10:40024 -> 15:33847 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | 5_1_grt | 24.7 | grt rounds 5 overflow 5:707 -> 10:519 -> 15:231 -> 20:93 -> 25:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 3.9 | grt rounds 3 overflow 5:18159 -> 10:14391 -> 15:13113 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 24.7 | grt rounds 4 overflow 5:90869 -> 10:59722 -> 15:50667 -> 20:55563 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-4168642 | ot_s81sl_leaf__t45 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:45920 -> 10:32114 | GRT-LABEL: DESIGN-FAIL: overflow 32114 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 26.1 | grt rounds 5 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 -> 25:36016 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:3874 -> 10:1838 -> 15:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 65.6 | grt rounds 3 overflow 5:80150 -> 10:47564 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 16.8 | grt rounds 3 overflow 5:26957 -> 10:13844 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 27.5 | grt rounds 4 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 27.8 | grt rounds 3 overflow 5:30207 -> 10:30821 -> 15:26039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_1_grt | 8.9 | grt rounds 2 overflow 5:54696 -> 10:6171 | GRT-LABEL: DESIGN-FAIL: overflow 6171 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:45133 -> 10:28997 | GRT-LABEL: DESIGN-FAIL: overflow 28997 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 15.8 | grt rounds 3 overflow 5:38739 -> 10:39458 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 10.3 | grt rounds 4 overflow 5:18843 -> 10:13916 -> 15:12366 -> 20:11039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:53242 -> 10:44174 | GRT-LABEL: DESIGN-FAIL: overflow 44174 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | 5_1_grt | 15.8 | grt rounds 5 overflow 5:14061 -> 10:13568 -> 15:10138 -> 20:8744 -> 25:9651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 15.8 | grt rounds 3 overflow 5:24659 -> 10:17793 -> 15:14456 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 5.3 | grt rounds 3 overflow 5:36719 -> 10:33315 -> 15:25641 | GRT-LABEL: DESIGN-FAIL: overflow 33315 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | 5_1_grt | 15.8 | grt rounds 3 overflow 5:68246 -> 10:58233 -> 15:62629 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | 5_1_grt | 15.9 | grt rounds 3 overflow 5:45487 -> 10:45710 -> 15:41451 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 27.3 | grt rounds 4 overflow 5:50603 -> 10:40835 -> 15:38869 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 26.6 | grt rounds 3 overflow 5:55450 -> 10:53941 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 8.0 | grt rounds 4 overflow 5:54880 -> 10:2129 -> 15:845 -> 20:1134 | GRT-LABEL: DESIGN-FAIL: overflow 2129 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 21.6 | grt rounds 2 overflow 5:60387 -> 10:47822 | GRT-LABEL: DESIGN-FAIL: overflow 47822 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 21.6 | grt rounds 2 overflow 5:61726 -> 10:48832 | GRT-LABEL: DESIGN-FAIL: overflow 48832 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 21.8 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | 5_1_grt | 25.3 | grt rounds 3 overflow 5:74621 -> 10:74300 -> 15:66169 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | 5_1_grt | 10.3 | grt rounds 3 overflow 5:36509 -> 10:31795 -> 15:9691 | GRT-LABEL: DESIGN-FAIL: overflow 31795 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 5_1_grt | 8.1 | grt rounds 3 overflow 5:53651 -> 10:46672 -> 15:39210 | GRT-LABEL: DESIGN-FAIL: overflow 46672 at round 10 > 1000 |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | 5_1_grt | 8.1 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 4.3 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_2_route | 4.3 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_1_grt | 4.3 | last meaningful line 0.8 h ago (208/220 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 4_1_cts | 5.2 | last meaningful line 0.0 h ago (7227/7228 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | 5_1_grt | 26.6 | last meaningful line 0.3 h ago (214/217 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | 5_1_grt | 6.5 | last meaningful line 0.4 h ago (219/1572 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i2t-1482642 | eco_20261120_233525_2680444-i2t | 5_2_route | 0.4 | last meaningful line 0.1 h ago (253/253 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1-2427560 | eco_20261121_014354_2681516-i1 | 5_2_route | 2.5 | drt_violations best 1176 last 1176 rows 8 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-fin-2847364 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | 5_2_route | 6.0 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_2_route | 9.8 | drt_violations best 106154 last 106154 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 5_2_route | 7.4 | drt_violations best 89507 last 89507 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_1_grt | 9.5 | last meaningful line 2.2 h ago (217/1208 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_2_route | 10.0 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | postcts_gate_FF | 7.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 5_2_route | 9.5 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (852/852 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_2_route | 9.8 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 5_2_route | 10.0 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | postcts_gate_FF | 9.8 | last meaningful line 0.0 h ago (734/734 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 5_2_route | 9.5 | last meaningful line 0.3 h ago (282/283 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_1_grt | 8.6 | last meaningful line 2.1 h ago (216/1153 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_2_route | 9.8 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 11.2 | drt_violations best 16642 last 16642 rows 7 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 7.3 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 3_3_place_gp | 9.8 | overflow best 0.1991 last 0.1991 rows 138 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 3_1_place_gp_skip_io | 6.2 | overflow best 0.214 last 0.3313 rows 149 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2t-458842 | eco_20261120_134605_3273412-i2t | 5_2_route | 2.0 | drt_violations best 16158 last 16158 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1-1137379 | eco_20261120_170022_4017640-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 5.0 | drt_violations best 5042 last 5042 rows 5 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2t-1141280 | eco_recover1120-i2t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h10-r1--t1--cl95b37463--pv86f5e3b9-grt-2409665 | col-h10-r1--t1--cl95b37463--pv86f5e3b9-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-pv-grt-2365472 | kv3-pv-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-1782532 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.4932 last 0.4932 rows 30 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-bk_sel__t2-2134272 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.91 last 0.9719 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | 5_1_grt | 3.8 | last meaningful line 0.5 h ago (208/215 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | 3_4_place_resized | 4.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | 3_4_place_resized | 4.3 | repair_Remaining best 309419 last 309419 rows 66 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_host_e-2131252 | hd_host_e | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2333832 | hd_serdes | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_2_route | 8.7 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 4_1_cts | 4.0 | last meaningful line 0.1 h ago (15546/15546 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_sys_c-2103423 | kv3_sys_c | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (3276/3276 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.5 | overflow best 0.2654 last 0.2654 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1938916 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.4 | overflow best 0.6323 last 0.6323 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | 5_1_grt | 2.7 | last meaningful line 0.5 h ago (202/208 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 8.8 | last meaningful line 1.0 h ago (202/209 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 2.6 | repair_TNS best 335759 last 335759 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3897522 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 1.8 | repair_Violations best 483 last 483 rows 51 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t52-2149380 | ot_s81sl_leaf__t52 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7377 last 0.7377 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 5_1_grt | 4.3 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | 6_report | 15.0 | last meaningful line 0.0 h ago (754/754 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | postcts_gate_TT | 4.3 | last meaningful line 0.0 h ago (1685/1685 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v2__cl55be2264-2104562 | sle_stm_v2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | postcts_gate_FF | 3.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-2242051 | slice_station__t40 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.998 last 0.998 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_1_grt | 7.9 | last meaningful line 0.3 h ago (1251/1268 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 5_2_route | 10.1 | drt_violations best 22861 last 22861 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | tt_setup_repair_grt | 4.3 | repair_Remaining best 156556 last 156556 rows 314 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | tt_setup_repair_grt | 7.9 | last meaningful line -0.0 h ago (609/609 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 8.2 | drt_violations best 23459 last 23459 rows 5 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t6-2568141 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 2.5 | last meaningful line 0.1 h ago (501/501 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 15.1 |  | NO-DATA: no log found |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 2.2 | repair_Violations best 156 last 345 rows 73 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | 5_1_grt | 13.7 | last meaningful line 4.2 h ago (207/231 lines) | YOUNG: evidence 4.8 h < 6 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | last meaningful line 1.8 h ago (207/223 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | postcts_gate_FF | 3.9 | last meaningful line -0.0 h ago (692/692 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | postcts_gate_FF | 3.9 | last meaningful line 0.0 h ago (363/363 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | 5_2_route | 3.9 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | 5_2_route | 3.9 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | 5_2_route | 3.9 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | 5_2_route | 3.9 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | 5_2_route | 3.9 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v7-3713215 | kv3_hgi_v7 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (488/488 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v8-3715561 | kv3_hgi_v8 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (492/492 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v1-3737021 | kv3_pv_v1 | 2_1_floorplan | 0.3 | repair_Viol best 1055 last 1055 rows 669 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v2-3742293 | kv3_pv_v2 | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (99/99 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2n-3736265 | kv3_pv_v2n | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (100/100 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3-3744611 | kv3_pv_v3 | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (104/104 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3743971 | kv3_pv_v3n | 2_1_floorplan | 0.3 | repair_Viol best 1058 last 1058 rows 442 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v4-3749853 | kv3_pv_v4 | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (107/107 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-3749196 | kv3_pv_v4n | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (106/106 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5-3751877 | kv3_pv_v5 | 2_1_floorplan | 0.3 | repair_Viol best 1554 last 1554 rows 643 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v5n-3751077 | kv3_pv_v5n | 2_1_floorplan | 0.3 | repair_Viol best 1553 last 1553 rows 497 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v7-3753752 | kv3_pv_v7 | 2_1_floorplan | 0.2 | repair_Viol best 1091 last 1091 rows 553 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-serdes__t12-2805048 | serdes__t12 | 3_3_place_gp | 0.9 | overflow best 0.6631 last 0.6631 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3990175 | serdes__t1 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (316/316 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t2-3210518 | serdes__t2 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8607 last 0.8718 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3774913 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.3002 last 0.3019 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4118864 | sle_st_a_v2 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | 5_2_route | 3.9 | drt_violations best 21502 last 21502 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-4159358 | slice_station__t37 | postcts_gate_FF | 3.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t45-3915474 | slice_station__t45 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.3318 last 0.3318 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_2_route | 3.9 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-4021993 | slw_fe_v1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cle6023ec2-3925892 | slw_st_b_v1 | synth_odb_v | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 43.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-slw-st-a-v1--clb036e152-grt-3207891 | slw-st-a-v1--clb036e152-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-slw-st-a-v1--clfc5867a6--pvf82a6c28-grt-3172346 | slw-st-a-v1--clfc5867a6--pvf82a6c28-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbx_q10__cl89936551_h-2354851 | cbx_q10 | 3_3_place_gp | 0.5 | overflow best 0.4866 last 0.4866 rows 15 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_2_route | 15.3 | drt_violations best 219997 last 219997 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | 5_2_route | 5.4 | drt_violations best 73438 last 73438 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-2936234 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4087 last 0.4087 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-2412903 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | generate_abstract | 16.6 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2115159 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.7 | overflow best 0.3363 last 0.3366 rows 21 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-coll_core-2715822 | coll_core | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (1412/1412 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2939391 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3000844 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_C__t1-2944273 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.0 | repair_TNS best 587996 last 587996 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 768551 last 768551 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2950877 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 5_2_route | 8.9 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_w-2401956 | hd_host_w | 3_3_place_gp | 0.5 | overflow best 0.2991 last 0.4709 rows 122 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-hd_lep0N-275476 | hd_lep0N | 3_5_place_dp | 1.8 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 5.3 | repair_TNS best 554575 last 554575 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-3042541 | hd_serdes | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v3-2824977 | kv3_hgi_v3 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (482/482 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v5-2829058 | kv3_hgi_v5 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (485/485 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v6-2832834 | kv3_hgi_v6 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Eo-3105101 | kv3_hub_Eo | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Wo-2840584 | kv3_hub_Wo | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (83/83 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v12-2850495 | kv3_pv_v12 | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v1n-2894902 | kv3_pv_v1n | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.0 | repair_Remaining best 199290 last 199290 rows 150 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t31-2959974 | ot_s81sl_leaf__t31 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7683 last 0.7683 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 8.0 | last meaningful line 2.0 h ago (202/225 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t14-2543182 | serdes__t14 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-2601962 | serdes__t15 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-2886708 | sle_ctl | 2_1_floorplan | 0.2 | repair_Viol best 2867 last 2867 rows 958 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2433248 | sle_hc0 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.2446 last 0.2446 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2867389 | sle_hc1 | reg_fanout | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-2237995 | sle_hc1 | 3_3_place_gp | 0.6 | overflow best 0.8656 last 0.8656 rows 18 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_sc_v2-2664497 | sle_sc_v2 | 3_3_place_gp | 0.4 | overflow best 0.4055 last 0.4055 rows 6 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-2590015 | sle_st_a_v1 | 3_4_place_resized | 0.4 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_c-2738922 | sle_su_c | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9345 last 0.9345 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-2958788 | slice_station__t29 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9889 last 0.9889 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 5_2_route | 8.0 | last meaningful line 0.4 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-1555365 | slice_station__t51 | 3_3_place_gp | 1.0 | overflow best 0.1998 last 0.1998 rows 44 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-slice_station__t52-2126924 | slice_station__t52 | 3_3_place_gp | 0.7 | overflow best 0.3503 last 0.3503 rows 18 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2995877 | slice_station__t6 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2226/2226 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-3091447 | slw_fe_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2315415 | slw_fe_v1 | 3_3_place_gp | 0.5 | overflow best 0.2085 last 0.2085 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_2_route | 7.9 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-1199736 | slw_fe_v2 | 3_4_place_resized | 1.2 | repair_Remaining best 50915 last 50915 rows 229 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | postcts_gate_TT | 8.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2349988 | slw_fw_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.554 last 0.554 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v3-2391069 | slw_fw_v3 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4487/4488 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3206688 | slw_hc1 | postplace_setup | 0.1 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3221813 | slw_hc3 | 1_synth | 0.1 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-1481079 | slw_st_b_v2 | 3_3_place_gp | 1.0 | overflow best 0.1357 last 0.1357 rows 42 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-slw_su_c__cl19bb38ef-2932395 | slw_su_c | 3_2_place_iop | 0.2 | last meaningful line -0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_su_l0__cl1a1c1f8f-2717727 | slw_su_l0 | 3_3_place_gp | 0.3 | overflow best 0.2677 last 0.2861 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t2-3396484 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 2.5 | last meaningful line 0.8 h ago (463/463 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 3_3_place_gp | 9.8 | last meaningful line 0.0 h ago (213/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 108.7 |  | NO-DATA: empty log |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3356064-26636 | 3356064 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1-1722084 | eco_20261120_185716_1464729-i1 | 5_2_route | 3.6 | drt_violations best 5965 last 5965 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_1_grt | 1.5 | last meaningful line 1.0 h ago (205/222 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | so_3229608_ff_74129 | so_3229608_ff_74129 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_3229608_tt_74129 | so_3229608_tt_74129 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (609/638 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | tt_setup_repair_grt | 4.8 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | 5_1_grt | 4.8 | last meaningful line 0.5 h ago (201/210 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | postcts_gate_TT | 5.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 5_2_route | 4.6 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 213044 last 213044 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_1_grt | 4.6 | last meaningful line 0.5 h ago (209/215 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (159/159 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | 3_5_place_dp | 6.1 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 5.0 | overflow best 0.7344 last 0.7369 rows 15 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-297032 | dsdv_slice_c1x_C__t6 | selrange | 1.7 |  | NO-DATA: empty log |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | 5_2_route | 5.3 | last meaningful line 0.1 h ago (250/251 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-498191 | slw_su_c | 3_5_place_dp | 1.7 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 2_4_floorplan_pdn | 6.6 | last meaningful line 0.3 h ago (23/23 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 3_1_place_gp_skip_io | 6.1 | overflow best 0.8421 last 0.8421 rows 37 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 3_1_place_gp_skip_io | 6.4 | overflow best 0.9293 last 0.9293 rows 31 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 3_3_place_gp | 6.7 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 3_1_place_gp_skip_io | 9.8 | overflow best 0.2108 last 0.3039 rows 285 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 5.5 | last meaningful line 0.6 h ago (674/674 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-28461 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 1.9 | last meaningful line 0.0 h ago (431/431 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | synth_odb_v | 9.7 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 5.0 | drt_violations best 4965 last 4965 rows 3 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1t-1859870 | eco_20261120_211023_313122-i1t | 5_2_route | 3.3 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | prd-eco_20261120_221308_1904487-i1t-3602686 | eco_20261120_221308_1904487-i1t | 5_2_route | 2.2 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | postcts_gate_FF | 8.1 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | postcts_gate_FF | 8.1 | last meaningful line 0.0 h ago (1898/1898 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 5_1_grt | 8.1 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (257/257 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 5_2_route | 8.1 | last meaningful line 0.5 h ago (266/267 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_1_grt | 8.1 | last meaningful line 3.8 h ago (219/1438 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | postcts_gate_FF | 8.1 | last meaningful line 0.2 h ago (986/986 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 5_2_route | 8.1 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 5_1_grt | 8.1 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_1_place_gp_skip_io | 8.0 | overflow best 0.2105 last 0.2697 rows 186 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1-1392033 | eco_20261120_155439_476619-i1 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (171/171 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1-3186007 | eco_20261120_162140_2433056-i1 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 6.7 | drt_violations best 6296 last 6296 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 6.0 | drt_violations best 6951 last 6951 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc10 | otc-1530555-8836 | 1530555 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-1580274-12324 | 1580274 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 37.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 24.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 17.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 47.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_1_grt | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 11.2 | drt_violations best 124 last 136 rows 37 | before-window best 1708, window best 124 | PROGRESS: drt_violations improved 92.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 21.7 | last meaningful line 1.1 h ago (1432/1432 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 13.3 | last meaningful line 0.6 h ago (1166/1166 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_1_grt | 7.4 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_1_grt | 7.3 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | pregrt_ff_hold | 7.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 6.4 | last meaningful line 0.8 h ago (914/914 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 6.4 | last meaningful line 0.8 h ago (868/868 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 10.1 | last meaningful line 0.1 h ago (15751/15751 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-native59-304297 | native59 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-serdes__t16-2214281 | serdes__t16 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | 5_2_route | 13.7 | drt_violations best 908 last 908 rows 10 | before-window best 134377, window best 908 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-3352856 | glue | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 9.8 | last meaningful line 0.0 h ago (784/784 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | pregrt_ff_hold | 8.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261120_162132_484876-i1-1499386 | eco_20261120_162132_484876-i1 | 5_1_grt | 0.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
