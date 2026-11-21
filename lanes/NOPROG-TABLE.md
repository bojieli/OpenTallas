# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 23:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 2, 'GRT-LABEL': 65, 'YOUNG': 184, 'NO-DATA': 7, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 38}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | pregrt_ff_hold | 25.1 | repair_TNS best 82425.6 last 82425.6 rows 1 | before-window best 82425.6, window best - | NO-PROGRESS: no new repair_TNS row in 7.5 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 5_1_grt | 11.2 | grt rounds 6 overflow 5:2761 -> 10:2433 -> 15:2287 -> 20:2095 -> 25:2087 -> 30:2077 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -324.26 ps (< -300, gate TT >= -42); job age 11 | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | tt_setup_repair_grt | 7.2 | repair_Viol best 2885 last 2885 rows 262 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -312.17 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | 5_2_route | 12.2 | drt_violations best 136964 last 136964 rows 1 | before-window best 136964, window best 136964 | NO-PROGRESS: drt_violations best 136964 vs 136964 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | 5_2_route | 33.2 | drt_violations best 20 last 20 rows 53 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | 5_2_route | 28.2 | drt_violations best 33 last 33 rows 53 | before-window best 33, window best 33 | NO-PROGRESS: drt_violations best 33 vs 33 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | 5_1_grt | 3.3 | grt rounds 3 overflow 5:105728 -> 10:5561 -> 15:4342 | GRT-LABEL: DESIGN-FAIL: overflow 5561 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:22971 -> 10:2240 | GRT-LABEL: DESIGN-FAIL: overflow 2240 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | 5_1_grt | 2.8 | grt rounds 3 overflow 5:22749 -> 10:2145 -> 15:1350 | GRT-LABEL: DESIGN-FAIL: overflow 2145 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 5.5 | grt rounds 3 overflow 5:3873 -> 10:2267 -> 15:1587 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 29.7 | grt rounds 3 overflow 5:103028 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 14.9 | grt rounds 2 overflow 5:95762 -> 10:93332 | GRT-LABEL: DESIGN-FAIL: overflow 93332 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 26.0 | grt rounds 3 overflow 5:52450 -> 10:47147 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | 5_1_grt | 26.3 | grt rounds 2 overflow 5:77669 -> 10:64592 | GRT-LABEL: DESIGN-FAIL: overflow 64592 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 15.1 | grt rounds 6 overflow 5:10650 -> 10:7511 -> 15:4081 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 14.9 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 24.8 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:74610 -> 10:60436 -> 15:72289 | GRT-LABEL: DESIGN-FAIL: overflow 60436 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 13.7 | grt rounds 3 overflow 5:62494 -> 10:60571 -> 15:50065 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:64225 -> 10:59002 | GRT-LABEL: DESIGN-FAIL: overflow 59002 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | 5_1_grt | 14.9 | grt rounds 3 overflow 5:60186 -> 10:56777 -> 15:48789 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:56895 -> 10:53822 | GRT-LABEL: DESIGN-FAIL: overflow 53822 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | 5_1_grt | 14.8 | grt rounds 4 overflow 5:39637 -> 10:38572 -> 15:34810 -> 20:35539 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 13.6 | grt rounds 3 overflow 5:57986 -> 10:44299 -> 15:40589 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 33.9 | grt rounds 4 overflow 5:55847 -> 10:40238 -> 15:37035 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 28.1 | grt rounds 4 overflow 5:9213 -> 10:5561 -> 15:3613 -> 20:3104 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 28.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_1_grt | 3.6 | grt rounds 6 overflow 5:998 -> 10:763 -> 15:741 -> 20:704 -> 25:389 -> 30:135 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 17.3 | grt rounds 3 overflow 5:50575 -> 10:40102 -> 15:34585 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 17.5 | grt rounds 6 overflow 5:6798 -> 10:4941 -> 15:2610 -> 20:2287 -> 25:3051 -> 30:2207 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:25597 -> 10:20211 -> 15:15551 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 5_1_grt | 10.0 | grt rounds 4 overflow 5:19163 -> 10:15333 -> 15:11945 -> 20:8925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | 5_1_grt | 5.7 | grt rounds 1 overflow 5:7293 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 5_1_grt | 6.0 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_1_grt | 5.8 | grt rounds 6 overflow 5:932 -> 10:787 -> 15:732 -> 20:661 -> 25:275 -> 30:99 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | 5_1_grt | 11.2 | grt rounds 6 overflow 5:3688 -> 10:2561 -> 15:2268 -> 20:1901 -> 25:1852 -> 30:1871 | GRT-LABEL: DESIGN-FAIL: overflow 2561 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 7.2 | grt rounds 2 overflow 5:94966 -> 10:134399 | GRT-LABEL: DESIGN-FAIL: overflow 134399 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:49203 -> 10:42518 -> 15:36551 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 11.3 | grt rounds 2 overflow 5:49880 -> 10:49598 | GRT-LABEL: DESIGN-FAIL: overflow 49598 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 2.8 | grt rounds 3 overflow 5:46351 -> 10:38484 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: overflow 38484 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 2.8 | grt rounds 3 overflow 5:42154 -> 10:40024 -> 15:36226 | GRT-LABEL: DESIGN-FAIL: overflow 40024 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | 5_1_grt | 23.2 | grt rounds 5 overflow 5:707 -> 10:519 -> 15:231 -> 20:93 -> 25:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | 5_1_grt | 12.2 | grt rounds 4 overflow 5:5841 -> 10:2367 -> 15:1410 -> 20:1297 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:23091 -> 10:15850 | GRT-LABEL: DESIGN-FAIL: overflow 15850 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 23.2 | grt rounds 4 overflow 5:59133 -> 10:59535 -> 15:50667 -> 20:55563 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 24.6 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:24045 -> 10:2225 | GRT-LABEL: DESIGN-FAIL: overflow 2225 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 29.8 | grt rounds 3 overflow 5:70746 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 64.1 | grt rounds 3 overflow 5:80150 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 15.3 | grt rounds 3 overflow 5:26957 -> 10:14063 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 26.0 | grt rounds 4 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 26.3 | grt rounds 3 overflow 5:30207 -> 10:30821 -> 15:25780 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:54696 -> 10:6171 | GRT-LABEL: DESIGN-FAIL: overflow 6171 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 14.3 | grt rounds 3 overflow 5:38739 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 8.8 | grt rounds 4 overflow 5:18843 -> 10:14920 -> 15:12366 -> 20:11039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:53242 -> 10:44174 | GRT-LABEL: DESIGN-FAIL: overflow 44174 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | 5_1_grt | 3.3 | grt rounds 6 overflow 5:48103 -> 10:38508 -> 15:15585 -> 20:16567 -> 25:14112 -> 30:13066 | GRT-LABEL: DESIGN-FAIL: overflow 38508 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | 5_1_grt | 14.3 | grt rounds 5 overflow 5:14061 -> 10:13568 -> 15:10138 -> 20:8744 -> 25:9651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 14.3 | grt rounds 3 overflow 5:24849 -> 10:17793 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:36719 -> 10:33315 | GRT-LABEL: DESIGN-FAIL: overflow 33315 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | 5_1_grt | 14.3 | grt rounds 3 overflow 5:68246 -> 10:58233 -> 15:62629 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | 5_1_grt | 14.4 | grt rounds 3 overflow 5:45487 -> 10:45710 -> 15:41863 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 25.8 | grt rounds 4 overflow 5:43280 -> 10:40835 -> 15:38869 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 25.1 | grt rounds 3 overflow 5:55450 -> 10:53941 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 6.5 | grt rounds 3 overflow 5:54880 -> 10:2129 -> 15:845 | GRT-LABEL: DESIGN-FAIL: overflow 2129 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 20.3 | grt rounds 5 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | 5_1_grt | 23.8 | grt rounds 3 overflow 5:74621 -> 10:73777 -> 15:66169 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | 5_1_grt | 8.8 | grt rounds 2 overflow 5:36509 -> 10:31795 | GRT-LABEL: DESIGN-FAIL: overflow 31795 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | 5_1_grt | 7.8 | grt rounds 2 overflow 5:40733 -> 10:40101 | GRT-LABEL: DESIGN-FAIL: overflow 40101 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:53651 -> 10:46672 | GRT-LABEL: DESIGN-FAIL: overflow 46672 at round 10 > 1000 |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | 5_1_grt | 6.6 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | 5_1_grt | 2.8 | last meaningful line 0.2 h ago (208/214 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_2_route | 5.5 | drt_violations best 71562 last 71562 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | 5_1_grt | 3.3 | last meaningful line 0.1 h ago (208/211 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (208/213 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_1_grt | 2.8 | last meaningful line 0.3 h ago (209/221 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_1_grt | 2.8 | repair_Viol best 60 last 60 rows 3 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (208/214 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (208/214 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 3.4 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-3316818 | dsdv_slice_c1x_C__t7 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.3292 last 0.3292 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 4_1_cts | 3.7 | last meaningful line 0.1 h ago (10833/10833 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 3_5_place_dp | 3.7 | last meaningful line 0.4 h ago (115/115 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_1_grt | 5.0 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | eco-abs-3892911 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (636/636 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_2_route | 3.2 | drt_violations best 821 last 821 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1-102804 | eco_20261120_233525_2680444-i1 | 5_2_route | 2.4 | drt_violations best 2029 last 2029 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1-2427560 | eco_20261121_014354_2681516-i1 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | 5_1_grt | 4.3 | last meaningful line 0.6 h ago (202/229 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | 5_1_grt | 4.7 | last meaningful line 0.6 h ago (244/429 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | 5_1_grt | 4.5 | last meaningful line 0.1 h ago (833/848 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_2_route | 8.3 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 5_2_route | 5.9 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | postcts_gate_FF | 8.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | tt_setup_repair_grt | 5.7 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | tt_setup_repair_grt | 8.0 | last meaningful line 0.0 h ago (1086/1086 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | postcts_gate_TT | 8.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | 5_1_grt | 5.1 | last meaningful line 0.0 h ago (192/200 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | postcts_gate_TT | 8.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 5_1_grt | 8.3 | last meaningful line 0.0 h ago (1040/1072 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 5_2_route | 8.0 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_1_grt | 7.1 | last meaningful line 0.6 h ago (216/992 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | postcts_gate_FF | 8.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 9.7 | drt_violations best 117930 last 117930 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 3_3_place_gp | 8.3 | overflow best 0.3007 last 0.3168 rows 63 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 3_1_place_gp_skip_io | 4.7 | overflow best 0.9947 last 0.9947 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 4.9 | last meaningful line 0.9 h ago (665/665 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 4.9 | last meaningful line 1.0 h ago (651/651 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2t-458842 | eco_20261120_134605_3273412-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (234/1364 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1-1137379 | eco_20261120_170022_4017640-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 3.5 | drt_violations best 124200 last 124200 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2t-1141280 | eco_recover1120-i2t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | pregrt_ff_hold | 2.5 | repair_TNS best 3.60575e+06 last 3.60575e+06 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | tt_setup_repair | 1.4 | repair_Violations best 65 last 297 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 75466.2 last 75466.2 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.6 | last meaningful line 1.3 h ago (127/127 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | 1_2_yosys | 2.8 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 12.2 | last meaningful line 0.3 h ago (198/206 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 1.6 | last meaningful line 0.8 h ago (214/220 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 1.6 | last meaningful line 0.8 h ago (214/220 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv-2749034 | kv3_pv | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1918 last 0.1918 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 3_5_place_dp | 2.5 | last meaningful line 0.3 h ago (47/47 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 8.6 | last meaningful line 1.8 h ago (15720/15720 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-native59-304297 | native59 | pregrt_ff_hold | 2.5 | repair_TNS best 9356.46 last 9356.46 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t28-2944418 | ot_s81sl_leaf__t28 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1223391 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 1.9 | repair_Violations best 808 last 808 rows 73 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (3323/3323 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 7.3 | repair_Violations best 16143 last 16144 rows 124 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | tt_setup_repair | 1.1 | repair_Viol best 1187 last 1187 rows 708 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3897522 | ot_s81sl_leaf__t39 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-26511 | serdes__t13 | 2_4_floorplan_pdn | 2.6 | last meaningful line 2.0 h ago (130/130 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-2431677 | sle_ctl | 3_3_place_gp | 1.1 | overflow best 0.2299 last 0.2299 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2795334 | sle_hc0 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2989450 | sle_hc1 | 3_3_place_gp | 0.8 | overflow best 0.2978 last 0.3982 rows 123 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-2851055 | sle_hc1 | 3_3_place_gp | 0.8 | overflow best 0.2996 last 0.3054 rows 147 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | 5_2_route | 13.5 | drt_violations best 24884 last 24884 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | 5_1_grt | 2.4 | last meaningful line 0.8 h ago (211/644 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_1_grt | 6.4 | last meaningful line 2.0 h ago (223/1134 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 5_2_route | 8.6 | drt_violations best 143121 last 143121 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2725341 | slw_st_b_v2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 6.7 | drt_violations best 124819 last 124819 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t6-2568141 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 13.6 |  | NO-DATA: no log found |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 0.7 | repair_Violations best 7718 last 7718 rows 20 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | pregrt_ff_hold | 2.4 | repair_TNS best 7386.02 last 7386.02 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | 5_2_route | 12.2 | drt_violations best 134377 last 134377 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.2 h ago (206/213 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | 5_1_grt | 12.2 | last meaningful line 2.7 h ago (207/222 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.4 h ago (207/213 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (203/215 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_1_grt | 2.4 | last meaningful line 0.2 h ago (203/215 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | 5_2_route | 12.2 | drt_violations best 23916 last 23916 rows 2 | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | 5_1_grt | 2.4 | repair_Remaining best 100232 last 100232 rows 24 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | 5_1_grt | 2.4 | repair_Remaining best 82232 last 82232 rows 42 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | generate_abstract | 12.8 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | 5_1_grt | 2.4 | repair_Remaining best 65232 last 65232 rows 59 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | 6_report | 12.8 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | 5_1_grt | 2.4 | repair_Remaining best 81232 last 81232 rows 43 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | 5_1_grt | 2.4 | repair_Remaining best 101997 last 101997 rows 23 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-coll_core-4193397 | coll_core | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (7190/7190 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-4168642 | ot_s81sl_leaf__t45 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (202/209 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | 5_2_route | 2.4 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-4159358 | slice_station__t37 | 5_1_grt | 2.4 | repair_Viol best 26 last 26 rows 118 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_2_route | 2.4 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 42.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-dsdv-slice-lepw-mu-C--t1-grt-677885 | dsdv-slice-lepw-mu-C--t1-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_2_route | 13.8 | last meaningful line 0.1 h ago (295/296 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | 5_2_route | 3.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | 6_report | 15.8 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | 5_2_route | 15.1 | drt_violations best 36 last 36 rows 21 | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | tt_setup_repair | 1.5 | repair_Viol best 1038 last 1038 rows 30 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | postcts_gate_TT | 7.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_w-116304 | hd_host_w | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N-275476 | hd_lep0N | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-215841 | hd_mesh | 3_3_place_gp | 0.4 | overflow best 0.6859 last 0.6859 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 3.8 | repair_TNS best 554575 last 554575 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-78033 | hd_serdes | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 5.5 | last meaningful line 1.0 h ago (209/225 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 6.5 | last meaningful line 0.5 h ago (202/210 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t4-3289948 | serdes__t4 | 3_1_place_gp_skip_io | 1.0 | overflow best 0.2299 last 0.2299 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | postcts_gate_TT | 15.7 | last meaningful line -0.0 h ago (49374/49374 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3513710 | sle_hc2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 5_2_route | 6.5 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | postcts_gate_FF | 6.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | postcts_gate_TT | 6.4 | last meaningful line 0.1 h ago (1611/1611 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-2337581 | slw_hc1 | 3_3_place_gp | 1.7 | overflow best 0.0999 last 0.0999 rows 240 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-658988 | slw_hc3 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (360/360 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t2-3396484 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 2_4_floorplan_pdn | 8.3 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 107.2 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1-1722084 | eco_20261120_185716_1464729-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | so_566136_tt_69098 | so_566136_tt_69098 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-4158517 | cbx_q10 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_base-304391 | col_base | 3_3_place_gp | 0.2 | overflow best 0.4656 last 0.4656 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_e10-305013 | col_e10 | 3_3_place_gp | 0.2 | overflow best 0.4656 last 0.4656 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 45016.9 last 45016.9 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | 5_1_grt | 3.3 | last meaningful line 0.1 h ago (204/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (201/204 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | tt_setup_measure_grt | 3.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 31921.3 last 31921.3 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 213044 last 213044 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-502552 | col_h9_r0_p2__t1 | 4_1_cts | 0.2 | last meaningful line -0.0 h ago (3005/3005 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 52721 last 52721 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 40163.5 last 40163.5 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 75590.3 last 75590.3 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (208/209 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p6__t1__pv0012ba28-201902 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.3 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_rw3-305999 | col_rw3 | 3_3_place_gp | 0.2 | overflow best 0.4656 last 0.4656 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_rw4-306674 | col_rw4 | 3_3_place_gp | 0.2 | overflow best 0.4656 last 0.4656 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 4.6 | last meaningful line 0.3 h ago (29/29 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | 1_2_yosys | 3.5 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-297032 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-leaf_base-3975806 | leaf_base | 3_3_place_gp | 0.5 | last meaningful line 0.3 h ago (88/88 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-leaf_e10-305420 | leaf_e10 | 3_3_place_gp | 0.2 | last meaningful line 0.2 h ago (88/88 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-leaf_rw3-307449 | leaf_rw3 | 3_3_place_gp | 0.2 | last meaningful line 0.2 h ago (88/88 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-leaf_rw4-303510 | leaf_rw4 | 3_3_place_gp | 0.2 | last meaningful line 0.2 h ago (89/89 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-3863987 | sle_ctl | 2_1_floorplan | 0.5 | repair_Viol best 4007 last 4007 rows 1211 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_sc_v2-89418 | sle_sc_v2 | 3_3_place_gp | 0.4 | overflow best 0.4444 last 0.4444 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-205979 | sle_st_a_v1 | 3_3_place_gp | 0.3 | overflow best 0.5137 last 0.5171 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 4_1_cts | 3.3 | last meaningful line 0.1 h ago (5552/5552 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-93654 | sle_stm_v2 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | postcts_gate_TT | 3.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-4163143 | slice_station__t40 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3692 last 0.3692 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__clc8fb2c8c-4164253 | slice_station__t40 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3049 last 0.3049 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-4161917 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.5427 last 0.5427 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-4163465 | slw_fe_v2 | 3_3_place_gp | 0.4 | overflow best 0.5959 last 0.5959 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 11.1 | drt_violations best 67710 last 67710 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-498191 | slw_su_c | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (87/87 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1a1c1f8f-110077 | slw_su_l0 | 3_3_place_gp | 0.3 | overflow best 0.2617 last 0.2617 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | port_bind | 5.1 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | synth_odb_v | 4.6 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | synth_odb_v | 4.9 | last meaningful line 0.2 h ago (4/4 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 2_1_floorplan | 5.2 | last meaningful line 0.3 h ago (90/90 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 3_1_place_gp_skip_io | 8.3 | overflow best 0.2108 last 0.2984 rows 177 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 4.0 | last meaningful line 0.0 h ago (585/585 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-28461 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 0.4 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | eco-abs-332835 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 3.5 | drt_violations best 69729 last 69729 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1t-1859870 | eco_20261120_211023_313122-i1t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261120_221308_1904487-i1t-3602686 | eco_20261120_221308_1904487-i1t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 20.1 | last meaningful line 5.0 h ago (226/234 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | postcts_gate_TT | 6.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | postcts_gate_TT | 6.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_2_route | 6.6 | last meaningful line 0.1 h ago (249/250 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_2_route | 6.6 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | tt_setup_measure_grt | 6.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 5_2_route | 6.6 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_1_grt | 6.6 | last meaningful line 2.3 h ago (219/1368 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | postcts_gate_FF | 6.6 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | postcts_gate_TT | 6.6 | last meaningful line 0.1 h ago (918/918 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_1_place_gp_skip_io | 6.5 | overflow best 0.2105 last 0.4306 rows 70 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | prd-count-p1_tc-3320689 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1-3186007 | eco_20261120_162140_2433056-i1 | 5_1_grt | 1.3 | last meaningful line 0.6 h ago (234/1374 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 5.2 | drt_violations best 6296 last 6296 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 4.5 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 35.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 23.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 15.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 46.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 9.7 | drt_violations best 131 last 131 rows 30 | before-window best 3038, window best 131 | PROGRESS: drt_violations improved 95.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 20.2 | last meaningful line 0.9 h ago (1430/1430 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 11.8 | last meaningful line 0.1 h ago (1129/1129 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_1_grt | 5.9 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_1_grt | 5.8 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_1_grt | 8.0 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-24246 | cbn_q01 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_1_grt | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_1_grt | 2.8 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | 5_2_route | 12.2 | drt_violations best 355 last 355 rows 4 | before-window best 81345, window best 355 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | 5_2_route | 12.2 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | 5_2_route | 12.2 | drt_violations best 10 last 10 rows 8 | before-window best 81157, window best 10 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | 5_2_route | 15.3 | drt_violations best 29 last 29 rows 39 | before-window best 151250, window best 29 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | 5_2_route | 15.3 | drt_violations best 32 last 32 rows 28 | before-window best 151250, window best 32 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 7.4 | repair_TNS best 22.146 last 22.146 rows 8 | before-window best 147.449, window best 22.146 | PROGRESS: repair_TNS improved 85.0 % in window |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-3352856 | glue | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 8.3 | last meaningful line 0.0 h ago (595/595 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 8.2 | last meaningful line 0.8 h ago (975/975 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 20.1 | last meaningful line 5.5 h ago (225/234 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 6.6 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
