# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 00:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 1, 'GRT-LABEL': 70, 'YOUNG': 163, 'NO-DATA': 12, 'KEEP': 3, 'EXCLUDED': 4, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | tt_setup_repair_grt | 12.2 | repair_Viol best 534 last 534 rows 20 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -928.49 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | pregrt_ff_hold | 3.5 | repair_TNS best 3.60575e+06 last 3.60575e+06 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -540.84 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-cbn_q01__clab6e67f2-24246 | cbn_q01 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -349.08 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 21.1 | last meaningful line 6.0 h ago (226/235 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:107046 -> 10:5611 -> 15:4511 | GRT-LABEL: DESIGN-FAIL: overflow 5611 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | 5_1_grt | 4.3 | grt rounds 4 overflow 5:105728 -> 10:5561 -> 15:4342 -> 20:4553 | GRT-LABEL: DESIGN-FAIL: overflow 5561 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:78045 -> 10:9505 | GRT-LABEL: DESIGN-FAIL: overflow 9505 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:78712 -> 10:9441 -> 15:5560 | GRT-LABEL: DESIGN-FAIL: overflow 9441 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:73297 -> 10:2715 | GRT-LABEL: DESIGN-FAIL: overflow 2715 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:4272 -> 10:1881 -> 15:1393 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:3628 -> 10:1762 -> 15:1404 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:23810 -> 10:2471 -> 15:1527 | GRT-LABEL: DESIGN-FAIL: overflow 2471 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:23451 -> 10:2277 -> 15:1587 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 6.5 | grt rounds 3 overflow 5:3873 -> 10:1801 -> 15:1471 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 15.9 | grt rounds 2 overflow 5:95762 -> 10:93332 | GRT-LABEL: DESIGN-FAIL: overflow 93332 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 27.0 | grt rounds 3 overflow 5:52450 -> 10:47147 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | 5_1_grt | 27.3 | grt rounds 3 overflow 5:77669 -> 10:64592 -> 15:70550 | GRT-LABEL: DESIGN-FAIL: overflow 64592 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 16.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:4081 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 15.9 | grt rounds 3 overflow 5:46824 -> 10:46641 -> 15:36400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 25.8 | grt rounds 4 overflow 5:27938 -> 10:16079 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:80287 -> 10:60436 -> 15:72289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 14.7 | grt rounds 3 overflow 5:62494 -> 10:60312 -> 15:50065 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:64225 -> 10:59002 | GRT-LABEL: DESIGN-FAIL: overflow 59002 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | 5_1_grt | 15.9 | grt rounds 4 overflow 5:60186 -> 10:56777 -> 15:48789 -> 20:49650 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | 5_1_grt | 6.5 | grt rounds 3 overflow 5:56895 -> 10:53822 -> 15:47011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | 5_1_grt | 15.8 | grt rounds 4 overflow 5:41163 -> 10:38572 -> 15:34810 -> 20:35458 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 14.6 | grt rounds 3 overflow 5:50445 -> 10:44299 -> 15:40589 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 34.9 | grt rounds 4 overflow 5:55847 -> 10:40238 -> 15:37035 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 29.1 | grt rounds 4 overflow 5:9414 -> 10:5163 -> 15:3613 -> 20:3104 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 29.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_1_grt | 4.6 | grt rounds 6 overflow 5:998 -> 10:763 -> 15:741 -> 20:704 -> 25:389 -> 30:135 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 18.3 | grt rounds 3 overflow 5:50575 -> 10:40510 -> 15:34585 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 18.5 | grt rounds 6 overflow 5:6798 -> 10:4941 -> 15:2610 -> 20:2287 -> 25:3051 -> 30:2207 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | 5_1_grt | 11.9 | grt rounds 4 overflow 5:25597 -> 10:20211 -> 15:15551 -> 20:13785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 5_1_grt | 11.0 | grt rounds 4 overflow 5:21059 -> 10:13278 -> 15:11945 -> 20:8925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | 5_1_grt | 6.7 | grt rounds 1 overflow 5:7293 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 5_1_grt | 7.0 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | 5_1_grt | 12.2 | grt rounds 6 overflow 5:3688 -> 10:2561 -> 15:2268 -> 20:1901 -> 25:1852 -> 30:1871 | GRT-LABEL: DESIGN-FAIL: overflow 2561 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 8.2 | grt rounds 2 overflow 5:94966 -> 10:134399 | GRT-LABEL: DESIGN-FAIL: overflow 134399 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 13.2 | grt rounds 2 overflow 5:83767 -> 10:75075 | GRT-LABEL: DESIGN-FAIL: overflow 75075 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | 5_1_grt | 9.6 | grt rounds 3 overflow 5:49890 -> 10:42666 -> 15:36551 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 12.3 | grt rounds 3 overflow 5:49880 -> 10:49598 -> 15:43557 | GRT-LABEL: DESIGN-FAIL: overflow 49598 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:38551 -> 10:38484 -> 15:36671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 3.8 | grt rounds 3 overflow 5:42154 -> 10:40024 -> 15:33847 | GRT-LABEL: DESIGN-FAIL: overflow 40024 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | 5_1_grt | 24.2 | grt rounds 5 overflow 5:707 -> 10:519 -> 15:231 -> 20:93 -> 25:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 3.4 | grt rounds 3 overflow 5:18159 -> 10:15850 -> 15:13113 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 24.2 | grt rounds 4 overflow 5:90869 -> 10:59535 -> 15:50667 -> 20:55563 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-4168642 | ot_s81sl_leaf__t45 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:45920 -> 10:32114 | GRT-LABEL: DESIGN-FAIL: overflow 32114 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 25.6 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 4.7 | grt rounds 3 overflow 5:3874 -> 10:2225 -> 15:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 65.1 | grt rounds 3 overflow 5:80150 -> 10:47564 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 16.3 | grt rounds 3 overflow 5:26957 -> 10:13844 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 27.0 | grt rounds 4 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 27.3 | grt rounds 3 overflow 5:30207 -> 10:30821 -> 15:26039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_1_grt | 8.4 | grt rounds 2 overflow 5:54696 -> 10:6171 | GRT-LABEL: DESIGN-FAIL: overflow 6171 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 15.3 | grt rounds 3 overflow 5:38739 -> 10:39458 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 9.8 | grt rounds 4 overflow 5:18843 -> 10:13916 -> 15:12366 -> 20:11039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:53242 -> 10:44174 | GRT-LABEL: DESIGN-FAIL: overflow 44174 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | 5_1_grt | 4.3 | grt rounds 6 overflow 5:48103 -> 10:38508 -> 15:15585 -> 20:16567 -> 25:14112 -> 30:13066 | GRT-LABEL: DESIGN-FAIL: overflow 38508 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | 5_1_grt | 15.3 | grt rounds 5 overflow 5:14061 -> 10:13568 -> 15:10138 -> 20:8744 -> 25:9651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 15.3 | grt rounds 3 overflow 5:24849 -> 10:17793 -> 15:14456 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:36719 -> 10:33315 | GRT-LABEL: DESIGN-FAIL: overflow 33315 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | 5_1_grt | 15.3 | grt rounds 3 overflow 5:68246 -> 10:58233 -> 15:62629 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | 5_1_grt | 15.4 | grt rounds 3 overflow 5:45487 -> 10:45710 -> 15:41863 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 26.8 | grt rounds 4 overflow 5:43280 -> 10:40835 -> 15:38869 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 26.1 | grt rounds 3 overflow 5:55450 -> 10:53941 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 7.5 | grt rounds 3 overflow 5:54880 -> 10:2129 -> 15:845 | GRT-LABEL: DESIGN-FAIL: overflow 2129 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 21.1 | grt rounds 2 overflow 5:60387 -> 10:47822 | GRT-LABEL: DESIGN-FAIL: overflow 47822 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 21.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | 5_1_grt | 24.8 | grt rounds 3 overflow 5:74621 -> 10:74300 -> 15:66169 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:36509 -> 10:31795 -> 15:9691 | GRT-LABEL: DESIGN-FAIL: overflow 31795 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | 5_1_grt | 8.8 | grt rounds 2 overflow 5:40733 -> 10:40101 | GRT-LABEL: DESIGN-FAIL: overflow 40101 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 5_1_grt | 7.6 | grt rounds 2 overflow 5:53651 -> 10:46672 | GRT-LABEL: DESIGN-FAIL: overflow 46672 at round 10 > 1000 |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | 5_1_grt | 7.6 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 3.8 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_2_route | 3.8 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_1_grt | 3.8 | last meaningful line 0.3 h ago (208/213 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 4_1_cts | 4.7 | last meaningful line 0.2 h ago (10940/10940 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 4_1_cts | 4.7 | last meaningful line 0.5 h ago (7031/7031 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | 5_1_grt | 26.1 | last meaningful line 0.3 h ago (157/157 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | 5_1_grt | 6.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | eco-abs-1301884 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_2_route | 4.2 | drt_violations best 821 last 821 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1-2427560 | eco_20261121_014354_2681516-i1 | 5_2_route | 2.0 | drt_violations best 7646 last 7646 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | so_712007_ff_91046 | so_712007_ff_91046 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (642/642 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | so_712007_tt_91046 | so_712007_tt_91046 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (642/642 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | 5_2_route | 5.5 | last meaningful line 0.2 h ago (256/257 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_1_grt | 6.8 | last meaningful line 2.5 h ago (220/1161 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_2_route | 9.3 | drt_violations best 106154 last 106154 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 5_2_route | 6.9 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_2_route | 9.5 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_1_grt | 7.4 | last meaningful line 0.1 h ago (1645/1651 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | postcts_gate_FF | 9.0 | last meaningful line 0.1 h ago (764/764 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | tt_setup_measure_grt | 7.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_2_route | 9.3 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | postcts_gate_FF | 9.5 | last meaningful line 0.0 h ago (841/841 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | postcts_gate_TT | 9.3 | last meaningful line 0.1 h ago (837/837 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 5_2_route | 9.0 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_1_grt | 8.1 | last meaningful line 1.6 h ago (216/1097 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | postcts_gate_FF | 9.3 | last meaningful line 0.1 h ago (1509/1509 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_1_grt | 7.4 | last meaningful line 2.3 h ago (263/1015 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 10.7 | drt_violations best 21067 last 21067 rows 4 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 6.8 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 3_3_place_gp | 9.3 | overflow best 0.3007 last 0.3115 rows 124 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 3_1_place_gp_skip_io | 5.7 | overflow best 0.214 last 0.2997 rows 110 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 5.9 | last meaningful line 0.3 h ago (914/914 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 5.9 | last meaningful line 0.3 h ago (868/868 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2t-458842 | eco_20261120_134605_3273412-i2t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1-1137379 | eco_20261120_170022_4017640-i1 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 4.5 | drt_violations best 9609 last 9609 rows 3 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2t-1141280 | eco_recover1120-i2t | 5_1_grt | 1.0 | last meaningful line 0.6 h ago (234/1441 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-hc1--cl22c1ff36--pve289215f-grt-1649506 | sle-hc1--cl22c1ff36--pve289215f-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | pregrt_ff_hold | 3.5 | repair_Violations best 11844 last 11844 rows 114 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1652842 | col_h10_r1__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3559 last 3559 rows 489 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (208/209 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 3.6 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | 3_3_place_gp | 3.8 | overflow best 0.7065 last 0.7113 rows 9 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_2_route | 8.2 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 2.6 | last meaningful line 1.8 h ago (214/223 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 2.6 | last meaningful line 1.8 h ago (214/223 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv-2749034 | kv3_pv | 3_4_place_resized | 1.9 | last meaningful line 0.0 h ago (551/551 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 4_1_cts | 3.5 | last meaningful line 0.1 h ago (14957/14957 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-native59-304297 | native59 | pregrt_ff_hold | 3.5 | repair_TNS best 9356.46 last 9356.46 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1223391 | ot_s81sl_leaf__t39 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (202/209 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 2_2_floorplan_macro | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (202/204 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 8.3 | last meaningful line 0.5 h ago (202/207 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 2.1 | repair_TNS best 335759 last 335759 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3897522 | ot_s81sl_leaf__t39 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3386/3386 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-26511 | serdes__t13 | 3_5_place_dp | 3.6 | repair_Violations best 9821 last 9821 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | 5_2_route | 14.5 | drt_violations best 44 last 44 rows 29 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | tt_setup_measure_grt | 3.8 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__clc8fb2c8c-1253409 | slice_station__t40 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 5_2_route | 9.6 | drt_violations best 143121 last 143121 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 7.7 | drt_violations best 38403 last 38403 rows 3 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t6-2568141 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 2.0 | last meaningful line 0.2 h ago (498/498 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 14.6 |  | NO-DATA: no log found |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 1.7 | repair_Violations best 574 last 574 rows 40 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-slw-st-a-v2--clf4365a62-grt-3375552 | slw-st-a-v2--clf4365a62-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-2982090 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | 5_1_grt | 3.4 | repair_Remaining best 27579 last 27579 rows 163 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | 5_1_grt | 13.2 | last meaningful line 3.7 h ago (207/228 lines) | YOUNG: evidence 4.3 h < 6 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | 5_1_grt | 3.4 | last meaningful line 1.3 h ago (207/219 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (1514/1520 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (1514/1529 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | tt_setup_repair_grt | 3.4 | repair_Viol best 759 last 759 rows 769 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | tt_setup_repair_grt | 3.4 | repair_Viol best 759 last 759 rows 690 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | tt_setup_measure_grt | 3.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | tt_setup_repair_grt | 3.4 | repair_Viol best 759 last 759 rows 704 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | tt_setup_repair_grt | 3.4 | repair_Viol best 777 last 777 rows 622 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-serdes__t12-2805048 | serdes__t12 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t2-3210518 | serdes__t2 | 1_2_yosys | 0.1 | last meaningful line 0.1 h ago (313/313 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl67389ecd-3177813 | sle_st_a_v1 | 3_3_place_gp | 0.1 | overflow best 0.5245 last 0.5269 rows 15 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2775300 | sle_su_l1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | 5_2_route | 3.4 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_2_route | 3.4 | last meaningful line 0.1 h ago (259/260 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-3158034 | slw_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.5318 last 0.5338 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 43.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h10-r0-p4--t1--pvcc166a6d-grt-2392544 | col-h10-r0-p4--t1--pvcc166a6d-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-sle-st-a-v2--pv30dda31f--pvd2ec7769-grt-2290370 | sle-st-a-v2--pv30dda31f--pvd2ec7769-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-slw-st-b-v1--cle6023ec2-grt-2310425 | slw-st-b-v1--cle6023ec2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-cbx_q10__cl89936551_h-2354851 | cbx_q10 | 2_1_floorplan | 0.0 | last meaningful line -0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_2_route | 14.8 | drt_violations best 219997 last 219997 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | 5_2_route | 4.9 | drt_violations best 73438 last 73438 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | 6_report | 16.3 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | 5_3_fillcell | 16.3 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2115159 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.5 | repair_TNS best 587996 last 587996 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.0 | repair_TNS best 768551 last 768551 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 5_2_route | 8.4 | last meaningful line 0.0 h ago (248/249 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_e-2096290 | hd_host_e | 3_3_place_gp | 0.2 | overflow best 0.2117 last 0.2117 rows 40 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_host_w-2401956 | hd_host_w | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N-275476 | hd_lep0N | 3_3_place_gp | 1.3 | overflow best 0.6423 last 0.6423 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-215841 | hd_mesh | 3_3_place_gp | 1.4 | overflow best 0.2054 last 0.2054 rows 208 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 4.8 | repair_TNS best 554575 last 554575 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.5 | repair_Remaining best 240290 last 240290 rows 109 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 7.5 | last meaningful line 1.5 h ago (202/221 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-2237995 | sle_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (397/397 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v3-1124729 | sle_sc_v3 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 5_2_route | 7.5 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-1593826 | slice_station__t40 | 3_3_place_gp | 0.4 | overflow best 0.2367 last 0.2367 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t51-1555365 | slice_station__t51 | 3_2_place_iop | 0.5 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2126924 | slice_station__t52 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9989 last 0.9989 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2315415 | slw_fe_v1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_2_route | 7.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-1199736 | slw_fe_v2 | 3_3_place_gp | 0.7 | overflow best 0.5573 last 0.5573 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2349988 | slw_fw_v1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (158/158 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-2391069 | slw_fw_v3 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clb036e152-2321689 | slw_st_a_v1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2344707 | slw_st_a_v1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-1481079 | slw_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.7546 last 0.7546 rows 15 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t2-3396484 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 2.0 | last meaningful line 0.3 h ago (463/463 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 3_3_place_gp | 9.3 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 108.2 |  | NO-DATA: empty log |  |
| epyc9 | otc-2369446-279 | 2369446 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-2369896-19610 | 2369896 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-2369904-6750 | 2369904 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1-1722084 | eco_20261120_185716_1464729-i1 | 5_2_route | 3.1 | drt_violations best 5965 last 5965 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_1_grt | 1.0 | last meaningful line 0.5 h ago (205/213 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | 5_1_grt | 4.3 | last meaningful line 0.1 h ago (187/200 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (581/587 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 5_2_route | 4.1 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 213044 last 213044 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (209/212 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | pregrt_ff_hold | 4.1 | repair_Violations best 750 last 757 rows 11 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | 5_1_grt | 4.5 | last meaningful line 1.0 h ago (208/215 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | 3_4_place_resized | 5.6 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 4.5 | last meaningful line 0.2 h ago (28/28 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-297032 | dsdv_slice_c1x_C__t6 | sdc_lint | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-leaf_e10-305420 | leaf_e10 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-leaf_rw3-307449 | leaf_rw3 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-leaf_rw4-303510 | leaf_rw4 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v2-89418 | sle_sc_v2 | postplace_setup | 1.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | pregrt_ff_hold | 4.3 | repair_TNS best 24935.2 last 24935.2 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | 5_2_route | 4.8 | last meaningful line 0.2 h ago (245/245 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-4161917 | slw_fe_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-4163465 | slw_fe_v2 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 12.1 | drt_violations best 67710 last 67710 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-498191 | slw_su_c | 3_3_place_gp | 1.2 | overflow best 0.1956 last 0.1956 rows 43 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 2_3_floorplan_tapcell | 6.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 2_4_floorplan_pdn | 5.6 | last meaningful line 0.3 h ago (23/23 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 2_4_floorplan_pdn | 5.9 | last meaningful line 0.3 h ago (23/23 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 3_1_place_gp_skip_io | 6.2 | overflow best 0.9544 last 0.9544 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 3_1_place_gp_skip_io | 9.3 | overflow best 0.2108 last 0.3028 rows 246 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 5.0 | last meaningful line 0.2 h ago (674/674 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-28461 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 1.4 | last meaningful line 0.0 h ago (310/310 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_synth | 9.2 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 4.5 | drt_violations best 69729 last 69729 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1t-1859870 | eco_20261120_211023_313122-i1t | 5_2_route | 2.8 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261120_221308_1904487-i1t-3602686 | eco_20261120_221308_1904487-i1t | 5_2_route | 1.7 | last meaningful line 0.5 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | postcts_gate_TT | 7.6 | last meaningful line 0.1 h ago (2149/2149 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | postcts_gate_FF | 7.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 5_1_grt | 7.6 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 5_2_route | 7.6 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_1_grt | 7.6 | repair_TNS best 5534.1 last 5534.1 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | postcts_gate_TT | 7.6 | last meaningful line -0.0 h ago (24861/24861 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | postcts_gate_FF | 7.6 | last meaningful line 0.1 h ago (2092/2092 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_1_place_gp_skip_io | 7.5 | overflow best 0.2105 last 0.266 rows 152 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1-1392033 | eco_20261120_155439_476619-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1-1499386 | eco_20261120_162132_484876-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1-3186007 | eco_20261120_162140_2433056-i1 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 6.2 | drt_violations best 6296 last 6296 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 5.5 | drt_violations best 6951 last 6951 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 36.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 24.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 16.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_1_grt | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 47.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_1_grt | 6.0 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 10.7 | drt_violations best 124 last 213 rows 35 | before-window best 1981, window best 124 | PROGRESS: drt_violations improved 93.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 21.2 | last meaningful line 0.6 h ago (1432/1432 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 12.8 | last meaningful line 0.1 h ago (1166/1166 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_1_grt | 6.9 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_1_grt | 9.0 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 9.6 | last meaningful line 0.5 h ago (15747/15747 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | 5_1_grt | 3.4 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_1_grt | 7.4 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_1_grt | 7.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_1_grt | 3.8 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 5_1_grt | 7.4 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | 5_2_route | 13.2 | drt_violations best 3084 last 3084 rows 4 | before-window best 134377, window best 3084 | PROGRESS: drt_violations improved 97.7 % in window |  |
| epyc8 | dpkit-slice_station__t37-4159358 | slice_station__t37 | 5_1_grt | 3.4 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | 5_2_route | 16.1 | drt_violations best 20 last 20 rows 60 | before-window best 22975, window best 20 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 8.4 | last meaningful line 0.0 h ago (1048/1048 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-3352856 | glue | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 9.3 | last meaningful line 0.0 h ago (721/721 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | pregrt_ff_hold | 7.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | pregrt_ff_hold | 7.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
