- 2026-11-15 16:10 PST READY [NOPROG-FIX-1115 -> COORD; cc MERGE-QUEUE-1, FLOW-HEALTH-1] branch claude/noprog-fix-1115 @b22bf6e0afc GATE main=a05b2ffab8c pass=3/3. New tools/autopilot/noprog_stage.py: advisory per-stage classes PROGRESSING / SLOW / NO-PROGRESS with an evidence line for EVERY running container (no exclusion list, no cancel, no new limit). Parsers for synth, floorplan, place gp/resize/dp, cts, grt (incl. GRT-0102 loop counter), route DRT iterations, sta, lec file activity, no-log jobs; tests use real snippets from live kits (noprog_fixtures/, 33 tests). Evidence age is bounded by job age and takes the best across series restarts. Dry scan 15:5x on 7 hosts (first pass, interpolated line times): 225 jobs, 0 hits of EXCLUDED/YOUNG; the epyc9 col_h9_r0_p5 jobs in GRT-0102 iteration 13-19/30 are PROGRESSING (they would be false NO-PROGRESS if the loop counter were noise). Also: watchdog action log moves to lanes/NOPROG-ACTIONS.tsv (old content copied by the first hub run), and its table-row regex now accepts repair_timing rows with a star (3154* |). After merge: run tools/autopilot/install_noprog_stage.sh on the hub (timer noprog-stage every 15 min: refreshes lanes/NOPROG.tsv, hourly summary line through post.sh); no other host needs an install.
- 2026-11-15 16:11 PST STATE [NOPROG-FIX-1115 -> COORD] Correction to the READY above: the dry scan covered 193 running jobs (not 225): 173 PROGRESSING, 9 SLOW, 11 NO-PROGRESS before the GRT-0102 loop-counter fix, none after it on epyc8/9/10. First-pass line times are interpolated; classes sharpen after the hub has sampled for a few ticks.
- 2026-11-15 16:39 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 16:39 PST: 187 running jobs, PROGRESSING 179, SLOW 8, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-15 17:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 17:52 PST: 164 running jobs, PROGRESSING 158, SLOW 6, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-15 18:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 18:52 PST: 142 running jobs, PROGRESSING 138, SLOW 4, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-15 19:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 19:52 PST: 148 running jobs, PROGRESSING 145, SLOW 3, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-15 20:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 20:52 PST: 140 running jobs, PROGRESSING 138, SLOW 2, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-15 21:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 21:52 PST: 107 running jobs, PROGRESSING 105, SLOW 2, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-15 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 22:52 PST: 156 running jobs, PROGRESSING 151, SLOW 3, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 s81-colgen-1-c4 5_1_grt stage 23.9 h job 24.4 h: no new meaningful log line for 8.4 h; last: global_route -congestion_report_file /work/run/reports/asap7/dp_col_h10_r1__t1__cl95b37463__pv799da6
  NO-PROGRESS epyc10 s81-colgen-1-c4 5_1_grt stage 23.8 h job 24.4 h: no new meaningful log line for 8.4 h; last: global_route -congestion_report_file /work/run/reports/asap7/dp_col_h10_r1__t1__cl95b37463__pv799da6
- 2026-11-15 23:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-15 23:52 PST: 238 running jobs, PROGRESSING 234, SLOW 3, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc10 s81-colgen-1-c4 5_1_grt stage 24.8 h job 25.4 h: no new meaningful log line for 9.4 h; last: global_route -congestion_report_file /work/run/reports/asap7/dp_col_h10_r1__t1__cl95b37463__pv799da6
- 2026-11-16 00:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 00:52 PST: 146 running jobs, PROGRESSING 141, SLOW 4, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc10 s81-colgen-1-c4 5_1_grt stage 25.8 h job 26.4 h: no new meaningful log line for 10.4 h; last: global_route -congestion_report_file /work/run/reports/asap7/dp_col_h10_r1__t1__cl95b37463__pv799da6
- 2026-11-16 01:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 01:52 PST: 145 running jobs, PROGRESSING 136, SLOW 9, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-16 02:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 02:52 PST: 149 running jobs, PROGRESSING 140, SLOW 9, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-16 03:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 03:52 PST: 127 running jobs, PROGRESSING 120, SLOW 6, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 25.7 h job 25.7 h: drt_violations best 14534 last 14534 rows 2 window-gain 0.0%; stagnant 6.2 h; last event 0.7 h ago, log write 0.3 h ago (1505 lines)
- 2026-11-16 04:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 04:52 PST: 121 running jobs, PROGRESSING 111, SLOW 8, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 26.7 h job 26.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 7.2 h; last event 0.7 h ago, log write 0.7 h ago (1548 lines)
  NO-PROGRESS epyc8 svc_lo_dsdv_svc_rs__t6 1_2_yosys stage 9.5 h job 11.6 h: no new meaningful log line for 6.5 h; last: 3.16.2. Executing OPT_MEM_PRIORITY pass (removing unnecessary memory write priority relations).
- 2026-11-16 05:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 05:52 PST: 102 running jobs, PROGRESSING 93, SLOW 5, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 27.7 h job 27.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 8.2 h; last event 1.5 h ago, log write 0.1 h ago (1550 lines)
  NO-PROGRESS epyc10 fullroute 5_1_grt stage 15.1 h job 15.1 h: grt_overflow best 0 last 18 rows 2 window-gain 0.0%; stagnant 11.1 h; last event 0.4 h ago, log write 0.4 h ago (1072 lines)
  NO-PROGRESS epyc8 svc_lo_dsdv_svc_rs__t6 1_2_yosys stage 10.5 h job 12.6 h: no new meaningful log line for 7.5 h; last: 3.16.2. Executing OPT_MEM_PRIORITY pass (removing unnecessary memory write priority relations).
  NO-PROGRESS epyc10 hd_lep0N pregrt_ff_hold stage 6.6 h job 7.9 h: no new meaningful log line for 6.5 h; last: 0 |       0 |       0 |            0 |    +0.0% | -195.610 | -2132201.000 | u_core.u.g_pp[2].u_pair/
- 2026-11-16 06:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 06:52 PST: 93 running jobs, PROGRESSING 86, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 28.7 h job 28.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 9.2 h; last event 2.5 h ago, log write 1.1 h ago (1550 lines)
  NO-PROGRESS epyc8 svc_lo_dsdv_svc_rs__t6 1_2_yosys stage 11.5 h job 13.6 h: no new meaningful log line for 8.5 h; last: 3.16.2. Executing OPT_MEM_PRIORITY pass (removing unnecessary memory write priority relations).
- 2026-11-16 07:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 07:52 PST: 77 running jobs, PROGRESSING 73, SLOW 3, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 29.7 h job 29.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 10.2 h; last event 2.0 h ago, log write 0.1 h ago (1552 lines)
- 2026-11-16 08:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 08:52 PST: 111 running jobs, PROGRESSING 102, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 30.7 h job 30.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 11.2 h; last event 3.0 h ago, log write 1.1 h ago (1552 lines)
  NO-PROGRESS epyc8 svc_lo_dsdv_svc_rs__t6 1_2_yosys stage 13.5 h job 15.6 h: no new meaningful log line for 10.5 h; last: 3.16.2. Executing OPT_MEM_PRIORITY pass (removing unnecessary memory write priority relations).
- 2026-11-16 09:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 09:52 PST: 125 running jobs, PROGRESSING 116, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 31.7 h job 31.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 12.2 h; last event 2.0 h ago, log write 0.1 h ago (1554 lines)
  NO-PROGRESS epyc8 svc_lo_dsdv_svc_rs__t6 1_2_yosys stage 14.5 h job 16.6 h: no new meaningful log line for 11.5 h; last: 3.16.2. Executing OPT_MEM_PRIORITY pass (removing unnecessary memory write priority relations).
- 2026-11-16 10:07 PST READY [NOPROG-FIX-1115 -> COORD, MERGE-QUEUE-1; cc KIT-OPS-7, FABLE-DIE-HEAD] CODEX advisory-only correction claude/kit-ops-7-skewv2-1116 @4877c82f376 (pushed/forwarded GitHub), 38/38 advisory tests PASS epyc10. p16g was falsely NO-PROGRESS because completed iteration2 stayed 14445 while live iteration3 Completing10/20/30 percent reads13437/12438/11462 (epyc2 die-head-route-1/head/p16g/drt7_cut_small_TT/drt_TT.log, CPU1102percent). Parser now tracks partial counts only within the current incomplete iteration, separately from completed totals; discards on iteration boundary/completion/percent rewind. At least2percent reduction within six-hour window is a progress witness; advancing-percent flat/worse, stale witness, and rewind negative cases remain NO-PROGRESS. No cancelling-watchdog or policy change, no process touched. Normal gate/deploy pending.
- 2026-11-16 10:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 10:52 PST: 114 running jobs, PROGRESSING 102, SLOW 10, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 32.7 h job 32.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 13.2 h; last event 3.0 h ago, log write 1.1 h ago (1554 lines)
  NO-PROGRESS epyc8 svc_lo_dsdv_svc_rs__t6 1_2_yosys stage 15.5 h job 17.6 h: no new meaningful log line for 12.5 h; last: 3.16.2. Executing OPT_MEM_PRIORITY pass (removing unnecessary memory write priority relations).
- 2026-11-16 11:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 11:52 PST: 121 running jobs, PROGRESSING 111, SLOW 7, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 33.7 h job 33.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 14.2 h; last event 2.0 h ago, log write 0.1 h ago (1556 lines)
  NO-PROGRESS epyc8 svc_lo_dsdv_svc_rs__t6 1_2_yosys stage 16.5 h job 18.6 h: no new meaningful log line for 13.5 h; last: 3.16.2. Executing OPT_MEM_PRIORITY pass (removing unnecessary memory write priority relations).
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 9.6 h job 9.7 h: no new meaningful log line for 6.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
- 2026-11-16 12:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 12:52 PST: 111 running jobs, PROGRESSING 100, SLOW 9, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 34.7 h job 34.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 15.2 h; last event 3.0 h ago, log write 1.1 h ago (1556 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 10.6 h job 10.7 h: no new meaningful log line for 7.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
- 2026-11-16 13:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 13:52 PST: 131 running jobs, PROGRESSING 122, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 35.7 h job 35.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 16.2 h; last event 2.0 h ago, log write 0.5 h ago (1558 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 11.6 h job 11.7 h: no new meaningful log line for 8.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
- 2026-11-16 14:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 14:52 PST: 116 running jobs, PROGRESSING 106, SLOW 8, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 36.7 h job 36.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 17.2 h; last event 3.0 h ago, log write 1.5 h ago (1558 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 12.6 h job 12.7 h: no new meaningful log line for 9.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
- 2026-11-16 15:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 15:52 PST: 115 running jobs, PROGRESSING 101, SLOW 12, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 37.7 h job 37.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 18.2 h; last event 2.3 h ago, log write 0.8 h ago (1560 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 13.6 h job 13.7 h: no new meaningful log line for 10.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
- 2026-11-16 16:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 16:52 PST: 94 running jobs, PROGRESSING 81, SLOW 10, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 38.7 h job 38.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 19.2 h; last event 3.2 h ago, log write 1.8 h ago (1560 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 14.6 h job 14.7 h: no new meaningful log line for 11.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 6.4 h job 6.4 h: no new meaningful log line for 6.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
- 2026-11-16 17:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 17:52 PST: 100 running jobs, PROGRESSING 84, SLOW 12, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 39.7 h job 39.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 20.5 h; last event 2.7 h ago, log write 0.8 h ago (1562 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 15.6 h job 15.7 h: no new meaningful log line for 12.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 7.4 h job 7.4 h: no new meaningful log line for 7.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 7.3 h job 7.4 h: no new meaningful log line for 6.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
- 2026-11-16 18:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 18:52 PST: 105 running jobs, PROGRESSING 89, SLOW 11, NO-PROGRESS 5 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 40.7 h job 40.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 20.6 h; last event 1.8 h ago, log write 0.1 h ago (1564 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 16.6 h job 16.7 h: no new meaningful log line for 13.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 8.4 h job 8.4 h: no new meaningful log line for 8.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 8.3 h job 8.4 h: no new meaningful log line for 7.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc10 hd_lep0N pregrt_ff_hold stage 6.4 h job 8.1 h: no new meaningful log line for 6.4 h; last: 0 |       0 |       0 |            0 |    +0.0% | -194.538 | -2108990.750 | u_core.u.g_pp[2].u_pair/
- 2026-11-16 19:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 19:52 PST: 78 running jobs, PROGRESSING 69, SLOW 4, NO-PROGRESS 5 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 41.7 h job 41.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 20.7 h; last event 2.8 h ago, log write 1.1 h ago (1564 lines)
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 9.4 h job 9.4 h: no new meaningful log line for 9.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 9.3 h job 9.4 h: no new meaningful log line for 8.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc7 phy__t1 5_1_grt stage 7.5 h job 7.5 h: no new meaningful log line for 6.8 h; last: global_route -end_incremental -congestion_report_file /work/run/reports/asap7/dp_phy__t1/base/conges
  NO-PROGRESS epyc10 hd_lep0N pregrt_ff_hold stage 7.4 h job 9.1 h: no new meaningful log line for 7.4 h; last: 0 |       0 |       0 |            0 |    +0.0% | -194.538 | -2108990.750 | u_core.u.g_pp[2].u_pair/
- 2026-11-16 20:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 20:52 PST: 114 running jobs, PROGRESSING 101, SLOW 7, NO-PROGRESS 6 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 42.7 h job 42.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 20.8 h; last event 2.0 h ago, log write 0.4 h ago (1566 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 18.6 h job 18.7 h: no new meaningful log line for 15.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 10.4 h job 10.4 h: no new meaningful log line for 10.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 10.3 h job 10.4 h: no new meaningful log line for 9.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc7 phy__t1 5_1_grt stage 8.5 h job 8.5 h: no new meaningful log line for 7.8 h; last: global_route -end_incremental -congestion_report_file /work/run/reports/asap7/dp_phy__t1/base/conges
  NO-PROGRESS epyc10 hd_lep0N pregrt_ff_hold stage 8.4 h job 10.1 h: no new meaningful log line for 8.4 h; last: 0 |       0 |       0 |            0 |    +0.0% | -194.538 | -2108990.750 | u_core.u.g_pp[2].u_pair/
- 2026-11-16 21:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 21:52 PST: 101 running jobs, PROGRESSING 88, SLOW 8, NO-PROGRESS 5 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 43.7 h job 43.7 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.0%; stagnant 20.8 h; last event 3.0 h ago, log write 1.4 h ago (1566 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 19.6 h job 19.7 h: no new meaningful log line for 16.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 11.4 h job 11.4 h: no new meaningful log line for 11.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 11.3 h job 11.4 h: no new meaningful log line for 10.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc7 phy__t1 5_1_grt stage 9.5 h job 9.5 h: no new meaningful log line for 8.8 h; last: global_route -end_incremental -congestion_report_file /work/run/reports/asap7/dp_phy__t1/base/conges
- 2026-11-16 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 22:52 PST: 96 running jobs, PROGRESSING 85, SLOW 7, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 20.6 h job 20.7 h: no new meaningful log line for 17.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 12.4 h job 12.4 h: no new meaningful log line for 12.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 12.3 h job 12.4 h: no new meaningful log line for 11.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc7 phy__t1 5_1_grt stage 10.5 h job 10.5 h: no new meaningful log line for 9.8 h; last: global_route -end_incremental -congestion_report_file /work/run/reports/asap7/dp_phy__t1/base/conges
- 2026-11-16 23:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-16 23:52 PST: 101 running jobs, PROGRESSING 91, SLOW 6, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 21.6 h job 21.7 h: no new meaningful log line for 18.5 h; last: 15.42. Extracting gate netlist of module `\s81p_svc_hi_dsdv_svc_rs__t3' to `<abc-temp-dir>/input.bli
  NO-PROGRESS epyc9 svc_hi_dsdv_svc_rs__t3 1_2_yosys stage 13.4 h job 13.4 h: no new meaningful log line for 13.0 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 13.3 h job 13.4 h: no new meaningful log line for 12.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc7 phy__t1 5_1_grt stage 11.5 h job 11.5 h: no new meaningful log line for 10.8 h; last: global_route -end_incremental -congestion_report_file /work/run/reports/asap7/dp_phy__t1/base/conges
- 2026-11-17 00:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 00:52 PST: 73 running jobs, PROGRESSING 68, SLOW 4, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 14.3 h job 14.4 h: no new meaningful log line for 13.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
- 2026-11-17 01:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 01:52 PST: 107 running jobs, PROGRESSING 101, SLOW 5, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 15.3 h job 15.4 h: no new meaningful log line for 14.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
- 2026-11-17 02:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 02:52 PST: 93 running jobs, PROGRESSING 84, SLOW 8, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 16.3 h job 16.4 h: no new meaningful log line for 15.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
- 2026-11-17 03:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 03:52 PST: 111 running jobs, PROGRESSING 100, SLOW 10, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 17.3 h job 17.4 h: no new meaningful log line for 16.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
- 2026-11-17 04:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 04:52 PST: 102 running jobs, PROGRESSING 92, SLOW 8, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 50.7 h job 50.7 h: drt_violations best 2967 last 2967 rows 4 window-gain 0.0%; stagnant 6.7 h; last event 1.7 h ago, log write 0.9 h ago (1618 lines)
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 18.3 h job 18.4 h: no new meaningful log line for 17.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
- 2026-11-17 05:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 05:52 PST: 93 running jobs, PROGRESSING 81, SLOW 8, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 51.7 h job 51.7 h: drt_violations best 2967 last 2967 rows 4 window-gain 0.0%; stagnant 7.7 h; last event 1.7 h ago, log write 0.9 h ago (1620 lines)
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 19.3 h job 19.4 h: no new meaningful log line for 18.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc8 gen_rm4 5_1_grt stage 9.6 h job 11.0 h: repair_Remaining best 179322 last 179322 rows 26 window-gain 0.0%; stagnant 6.8 h; last event 7.0 h ago, log write 7.0 h ago (974 lines)
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 3_5_place_dp stage 6.1 h job 11.9 h: no new meaningful log line for 6.0 h; last: [INFO DPL-1101] Legalizing using diamond search.
- 2026-11-17 06:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 06:52 PST: 96 running jobs, PROGRESSING 84, SLOW 9, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 52.7 h job 52.7 h: drt_violations best 2967 last 2967 rows 4 window-gain 0.0%; stagnant 8.7 h; last event 0.7 h ago, log write 0.1 h ago (1624 lines)
  NO-PROGRESS epyc9 svc_lo_dsdv_svc_rs__t7 1_2_yosys stage 20.3 h job 20.4 h: no new meaningful log line for 19.3 h; last: 3.15. Executing SHARE pass (SAT-based resource sharing).
  NO-PROGRESS epyc8 gen_rm4 5_1_grt stage 10.6 h job 12.0 h: repair_Remaining best 179322 last 179322 rows 26 window-gain 0.0%; stagnant 7.8 h; last event 8.0 h ago, log write 8.0 h ago (974 lines)
- 2026-11-17 07:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 07:52 PST: 88 running jobs, PROGRESSING 79, SLOW 6, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS intel1 cbf_q00__cl870de686 5_1_grt stage 16.4 h job 19.6 h: repair_Viol best 145 last 145 rows 276 window-gain 0.0%; stagnant 6.3 h; last event 0.0 h ago, log write 0.0 h ago (1032 lines)
  NO-PROGRESS epyc8 gen_rm4 5_1_grt stage 11.6 h job 13.0 h: repair_Remaining best 179322 last 179322 rows 26 window-gain 0.0%; stagnant 8.8 h; last event 9.0 h ago, log write 9.0 h ago (974 lines)
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 8.1 h job 12.1 h: no new meaningful log line for 6.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
- 2026-11-17 08:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 08:52 PST: 84 running jobs, PROGRESSING 76, SLOW 5, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS intel1 cbf_q00__cl870de686 5_1_grt stage 17.4 h job 20.6 h: repair_Viol best 145 last 145 rows 314 window-gain 0.0%; stagnant 7.3 h; last event 0.1 h ago, log write 0.0 h ago (1070 lines)
  NO-PROGRESS epyc8 gen_rm4 5_1_grt stage 12.6 h job 14.0 h: repair_Remaining best 179322 last 179322 rows 26 window-gain 0.0%; stagnant 9.8 h; last event 10.0 h ago, log write 10.0 h ago (974 lines)
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 9.1 h job 13.1 h: no new meaningful log line for 7.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
- 2026-11-17 09:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 09:52 PST: 79 running jobs, PROGRESSING 67, SLOW 9, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS intel1 cbf_q00__cl870de686 5_1_grt stage 18.4 h job 21.6 h: repair_Viol best 145 last 145 rows 341 window-gain 0.0%; stagnant 8.3 h; last event 0.1 h ago, log write 0.0 h ago (1097 lines)
  NO-PROGRESS epyc8 gen_rm4 5_1_grt stage 13.6 h job 15.0 h: repair_Remaining best 179322 last 179322 rows 26 window-gain 0.0%; stagnant 10.8 h; last event 11.0 h ago, log write 11.0 h ago (974 lines)
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 10.1 h job 14.1 h: no new meaningful log line for 8.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
- 2026-11-17 10:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 10:52 PST: 106 running jobs, PROGRESSING 98, SLOW 6, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS intel1 cbf_q00__cl870de686 5_1_grt stage 19.4 h job 22.6 h: repair_Viol best 145 last 145 rows 371 window-gain 0.0%; stagnant 9.3 h; last event 0.1 h ago, log write 0.0 h ago (1127 lines)
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 11.1 h job 15.1 h: no new meaningful log line for 9.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
- 2026-11-17 11:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 11:52 PST: 84 running jobs, PROGRESSING 77, SLOW 3, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS intel1 cbf_q00__cl870de686 5_1_grt stage 20.4 h job 23.6 h: repair_Viol best 145 last 145 rows 408 window-gain 0.0%; stagnant 10.3 h; last event 0.0 h ago, log write 0.0 h ago (1164 lines)
  NO-PROGRESS epyc8 gen_rm4 5_1_grt stage 15.6 h job 17.0 h: grt_overflow best 0 last 96 rows 2 window-gain 0.0%; stagnant 13.1 h; last event 0.8 h ago, log write 0.8 h ago (1070 lines)
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 12.1 h job 16.1 h: no new meaningful log line for 10.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
  NO-PROGRESS intel1 slw_st_a_v2__cl9f076a5c 5_1_grt stage 8.9 h job 9.5 h: repair_Viol best 2186 last 2186 rows 1414 window-gain 0.0%; stagnant 6.9 h; last event 0.0 h ago, log write 0.0 h ago (2377 lines)
- 2026-11-17 12:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 12:52 PST: 99 running jobs, PROGRESSING 92, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 13.1 h job 17.1 h: no new meaningful log line for 11.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
  NO-PROGRESS intel1 slw_st_a_v2__cl9f076a5c 5_1_grt stage 9.9 h job 10.5 h: repair_Viol best 2186 last 2186 rows 1632 window-gain 0.0%; stagnant 7.9 h; last event 0.0 h ago, log write 0.0 h ago (2595 lines)
- 2026-11-17 13:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 13:52 PST: 94 running jobs, PROGRESSING 89, SLOW 4, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 14.1 h job 18.1 h: no new meaningful log line for 12.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
- 2026-11-17 14:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 14:52 PST: 81 running jobs, PROGRESSING 76, SLOW 4, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 15.1 h job 19.1 h: no new meaningful log line for 13.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
- 2026-11-17 15:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 15:52 PST: 72 running jobs, PROGRESSING 68, SLOW 3, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 serdes__t13 5_2_route stage 16.1 h job 20.1 h: no new meaningful log line for 14.5 h; last: Elapsed time: 1:17:54.38[h:]min:sec. CPU time: user 59004.96 sys 965.81 (1282%). Peak memory: 528858
- 2026-11-17 16:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 16:52 PST: 94 running jobs, PROGRESSING 88, SLOW 6, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-17 17:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 17:52 PST: 107 running jobs, PROGRESSING 102, SLOW 5, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-17 18:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 18:52 PST: 102 running jobs, PROGRESSING 97, SLOW 5, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-17 19:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 19:52 PST: 75 running jobs, PROGRESSING 70, SLOW 5, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-17 20:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 20:52 PST: 97 running jobs, PROGRESSING 92, SLOW 5, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-17 21:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 21:52 PST: 97 running jobs, PROGRESSING 90, SLOW 6, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 slw_st_a_v1__clb036e152 5_1_grt stage 8.6 h job 8.9 h: repair_Viol best 2143 last 2143 rows 1662 window-gain 0.0%; stagnant 6.6 h; last event 0.0 h ago, log write 0.0 h ago (2666 lines)
- 2026-11-17 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 22:52 PST: 123 running jobs, PROGRESSING 114, SLOW 8, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 slw_st_a_v1__clb036e152 5_1_grt stage 9.6 h job 9.9 h: repair_Viol best 2143 last 2143 rows 1890 window-gain 0.0%; stagnant 7.6 h; last event 0.0 h ago, log write 0.0 h ago (2894 lines)
- 2026-11-17 23:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-17 23:52 PST: 123 running jobs, PROGRESSING 111, SLOW 11, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 cbn_q11__cl5cc92dfe 5_1_grt stage 34.4 h job 36.2 h: repair_Viol best 908 last 908 rows 207 window-gain 0.0%; stagnant 6.0 h; last event 0.1 h ago, log write 0.0 h ago (1137 lines)
- 2026-11-18 00:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 00:52 PST: 127 running jobs, PROGRESSING 120, SLOW 7, NO-PROGRESS 0 (advisory, no cancel); table lanes/NOPROG.tsv
- 2026-11-18 01:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 01:52 PST: 123 running jobs, PROGRESSING 109, SLOW 13, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kv3_pc_v1__cl4ea58a5c pregrt_ff_hold stage 6.3 h job 8.5 h: no new meaningful log line for 6.2 h; last: 0 |       0 |       0 |            0 |    +0.0% | -278.803 | -2768225.750 | u_bound.u_hsl2.u_slice.u
- 2026-11-18 02:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 02:52 PST: 124 running jobs, PROGRESSING 112, SLOW 11, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 sle_st_a_v1__cl989804f6__cl18eece69 5_1_grt stage 9.0 h job 9.5 h: repair_Viol best 2151 last 2151 rows 1853 window-gain 0.0%; stagnant 6.4 h; last event 0.0 h ago, log write 0.0 h ago (2822 lines)
- 2026-11-18 03:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 03:52 PST: 143 running jobs, PROGRESSING 130, SLOW 10, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 20.5 h job 33.9 h: no new meaningful log line for 6.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc8 sle_st_a_v1__cl989804f6__cled3c1d7b 5_1_grt stage 9.9 h job 10.6 h: repair_Viol best 2143 last 2143 rows 1551 window-gain 0.0%; stagnant 6.7 h; last event 0.0 h ago, log write 0.0 h ago (2621 lines)
  NO-PROGRESS epyc8 sle_st_a_v1__cl989804f6__cl18eece69 5_1_grt stage 8.8 h job 9.5 h: repair_Viol best 2151 last 2151 rows 1452 window-gain 0.0%; stagnant 6.5 h; last event 0.0 h ago, log write 0.0 h ago (2421 lines)
- 2026-11-18 04:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 04:52 PST: 133 running jobs, PROGRESSING 122, SLOW 9, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 sle_st_a_v1__cl989804f6__cled3c1d7b 5_1_grt stage 10.9 h job 11.6 h: repair_Viol best 2143 last 2143 rows 1726 window-gain 0.0%; stagnant 7.7 h; last event 0.0 h ago, log write 0.0 h ago (2796 lines)
  NO-PROGRESS epyc8 sle_st_a_v1__cl989804f6__cl18eece69 5_1_grt stage 9.8 h job 10.5 h: repair_Viol best 2151 last 2151 rows 1672 window-gain 0.0%; stagnant 7.5 h; last event 0.0 h ago, log write 0.0 h ago (2641 lines)
- 2026-11-18 05:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 05:52 PST: 92 running jobs, PROGRESSING 84, SLOW 7, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 6.5 h job 7.7 h: no new meaningful log line for 6.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 06:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 06:52 PST: 126 running jobs, PROGRESSING 122, SLOW 3, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 7.5 h job 8.7 h: no new meaningful log line for 7.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 07:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 07:52 PST: 289 running jobs, PROGRESSING 282, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 24.1 h job 24.1 h: drt_violations best 14534 last 14534 rows 2 window-gain 0.0%; stagnant 6.7 h; last event 1.0 h ago, log write 0.3 h ago (1505 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 8.5 h job 9.7 h: no new meaningful log line for 8.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 08:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 08:52 PST: 210 running jobs, PROGRESSING 205, SLOW 3, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 25.1 h job 25.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 7.7 h; last event 0.5 h ago, log write 0.5 h ago (1548 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 9.5 h job 10.7 h: no new meaningful log line for 9.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 09:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 09:52 PST: 284 running jobs, PROGRESSING 277, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 26.1 h job 26.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 8.7 h; last event 1.5 h ago, log write 1.5 h ago (1548 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 10.5 h job 11.7 h: no new meaningful log line for 10.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 10:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 10:52 PST: 301 running jobs, PROGRESSING 294, SLOW 4, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 27.5 h job 40.9 h: no new meaningful log line for 6.5 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc2 kit drt_TT stage 27.1 h job 27.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 9.7 h; last event 2.2 h ago, log write 0.2 h ago (1550 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 11.5 h job 12.7 h: no new meaningful log line for 11.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 11:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 11:52 PST: 288 running jobs, PROGRESSING 282, SLOW 3, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 28.5 h job 41.9 h: no new meaningful log line for 7.5 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc2 kit drt_TT stage 28.1 h job 28.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 10.7 h; last event 3.2 h ago, log write 1.2 h ago (1550 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 12.5 h job 13.7 h: no new meaningful log line for 12.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 12:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 12:52 PST: 268 running jobs, PROGRESSING 262, SLOW 3, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 29.5 h job 42.9 h: no new meaningful log line for 8.5 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc2 kit drt_TT stage 29.1 h job 29.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 11.7 h; last event 4.2 h ago, log write 2.2 h ago (1550 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 13.5 h job 14.7 h: no new meaningful log line for 13.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 13:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 13:52 PST: 365 running jobs, PROGRESSING 359, SLOW 5, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 14.5 h job 15.7 h: no new meaningful log line for 14.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 14:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 14:52 PST: 382 running jobs, PROGRESSING 377, SLOW 4, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 15.5 h job 16.7 h: no new meaningful log line for 15.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 15:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 15:52 PST: 347 running jobs, PROGRESSING 338, SLOW 8, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 16.5 h job 17.7 h: no new meaningful log line for 16.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 16:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 16:52 PST: 388 running jobs, PROGRESSING 380, SLOW 7, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 17.5 h job 18.7 h: no new meaningful log line for 17.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 17:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 17:52 PST: 271 running jobs, PROGRESSING 267, SLOW 2, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 phy__t1 5_1_grt stage 74.0 h job 87.9 h: no new meaningful log line for 6.0 h; last: [INFO GRT-0102] Start extra iteration 13/30
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 18.5 h job 19.7 h: no new meaningful log line for 18.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 18:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 18:52 PST: 340 running jobs, PROGRESSING 332, SLOW 7, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 19.5 h job 20.7 h: no new meaningful log line for 19.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 19:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 19:52 PST: 299 running jobs, PROGRESSING 291, SLOW 6, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 36.5 h job 49.9 h: no new meaningful log line for 6.4 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 20.5 h job 21.7 h: no new meaningful log line for 20.2 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 20:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 20:52 PST: 455 running jobs, PROGRESSING 448, SLOW 4, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 37.5 h job 50.9 h: no new meaningful log line for 7.4 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc7 kv3_pc_v1__cl23f6a148 5_1_grt stage 28.9 h job 33.1 h: no new meaningful log line for 6.8 h; last: global_route -end_incremental -congestion_report_file /work/run/reports/asap7/dp_kv3_pc_v1__cl23f6a1
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 21.5 h job 22.7 h: no new meaningful log line for 21.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 21:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 21:52 PST: 505 running jobs, PROGRESSING 498, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 38.5 h job 51.9 h: no new meaningful log line for 8.4 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 22.5 h job 23.7 h: no new meaningful log line for 22.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 22:52 PST: 524 running jobs, PROGRESSING 517, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 39.5 h job 52.9 h: no new meaningful log line for 9.4 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 23.5 h job 24.7 h: no new meaningful log line for 23.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-18 23:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-18 23:52 PST: 529 running jobs, PROGRESSING 521, SLOW 6, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 40.5 h job 53.9 h: no new meaningful log line for 10.4 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 24.5 h job 25.7 h: no new meaningful log line for 24.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 00:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 00:52 PST: 439 running jobs, PROGRESSING 433, SLOW 4, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 41.5 h job 54.9 h: no new meaningful log line for 11.4 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 25.5 h job 26.7 h: no new meaningful log line for 25.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 01:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 01:52 PST: 504 running jobs, PROGRESSING 497, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 42.5 h job 55.9 h: no new meaningful log line for 12.4 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 26.5 h job 27.7 h: no new meaningful log line for 26.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 02:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 02:52 PST: 386 running jobs, PROGRESSING 379, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 kv3_pc_v1__cl7f648944 5_1_grt stage 34.8 h job 39.1 h: repair_Viol best 5526 last 5526 rows 205 window-gain 0.0%; stagnant 6.8 h; last event 0.1 h ago, log write 0.0 h ago (1423 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 27.5 h job 28.7 h: no new meaningful log line for 27.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 03:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 03:52 PST: 334 running jobs, PROGRESSING 328, SLOW 3, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 kv3_pc_v1__cl23f6a148 5_1_grt stage 35.9 h job 40.1 h: repair_Viol best 5330 last 5330 rows 130 window-gain 0.0%; stagnant 6.6 h; last event 0.1 h ago, log write 0.0 h ago (1302 lines)
  NO-PROGRESS epyc7 kv3_pc_v1__cl7f648944 5_1_grt stage 35.8 h job 40.1 h: repair_Viol best 5526 last 5526 rows 266 window-gain 0.0%; stagnant 7.8 h; last event 0.0 h ago, log write 0.0 h ago (1484 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 28.5 h job 29.7 h: no new meaningful log line for 28.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 04:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 04:52 PST: 312 running jobs, PROGRESSING 307, SLOW 3, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 kv3_pc_v1__cl23f6a148 5_1_grt stage 36.9 h job 41.1 h: repair_Viol best 5330 last 5330 rows 143 window-gain 0.0%; stagnant 7.6 h; last event 0.1 h ago, log write 0.1 h ago (1315 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 29.5 h job 30.7 h: no new meaningful log line for 29.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 05:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 05:52 PST: 313 running jobs, PROGRESSING 307, SLOW 4, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 kv3_pc_v1__cl23f6a148 5_1_grt stage 37.9 h job 42.1 h: repair_Viol best 5330 last 5330 rows 156 window-gain 0.0%; stagnant 8.6 h; last event 0.1 h ago, log write 0.0 h ago (1328 lines)
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 30.5 h job 31.7 h: no new meaningful log line for 30.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 06:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 06:52 PST: 229 running jobs, PROGRESSING 221, SLOW 7, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 31.5 h job 32.7 h: no new meaningful log line for 31.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 07:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 07:52 PST: 192 running jobs, PROGRESSING 186, SLOW 5, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 32.5 h job 33.7 h: no new meaningful log line for 32.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 08:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 08:52 PST: 173 running jobs, PROGRESSING 168, SLOW 3, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv; hosts without report ['epyc7']
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 49.5 h job 62.9 h: no new meaningful log line for 6.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 33.5 h job 34.7 h: no new meaningful log line for 33.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 09:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 09:52 PST: 233 running jobs, PROGRESSING 229, SLOW 2, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 50.5 h job 63.9 h: no new meaningful log line for 7.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 34.5 h job 35.7 h: no new meaningful log line for 34.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 10:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 10:52 PST: 228 running jobs, PROGRESSING 222, SLOW 4, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 51.5 h job 64.9 h: no new meaningful log line for 8.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 35.5 h job 36.7 h: no new meaningful log line for 35.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 11:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 11:52 PST: 278 running jobs, PROGRESSING 272, SLOW 4, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 52.5 h job 65.9 h: no new meaningful log line for 9.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 36.5 h job 37.7 h: no new meaningful log line for 36.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 12:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 12:52 PST: 340 running jobs, PROGRESSING 333, SLOW 4, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 53.5 h job 66.9 h: no new meaningful log line for 10.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 37.5 h job 38.7 h: no new meaningful log line for 37.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc9 ot_s81sl_leaf__t11 5_1_grt stage 12.7 h job 14.5 h: repair_Viol best 97 last 97 rows 274 window-gain 0.0%; stagnant 6.5 h; last event 0.0 h ago, log write 0.0 h ago (934 lines)
- 2026-11-19 13:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 13:52 PST: 305 running jobs, PROGRESSING 296, SLOW 6, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 54.5 h job 67.9 h: no new meaningful log line for 11.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 38.5 h job 39.7 h: no new meaningful log line for 38.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc9 ot_s81sl_leaf__t11 5_1_grt stage 13.7 h job 15.5 h: repair_Viol best 97 last 97 rows 302 window-gain 0.0%; stagnant 7.5 h; last event 0.0 h ago, log write 0.0 h ago (962 lines)
- 2026-11-19 14:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 14:52 PST: 275 running jobs, PROGRESSING 268, SLOW 3, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc8 svc_hi_dsdv_svc_rs__t3 4_1_cts stage 55.5 h job 68.9 h: no new meaningful log line for 12.1 h; last: [WARNING STA-0450] virtual clock vclk can not be propagated.
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 39.5 h job 40.7 h: no new meaningful log line for 39.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc9 ot_s81sl_leaf__t11 5_1_grt stage 14.7 h job 16.5 h: repair_Viol best 97 last 97 rows 336 window-gain 0.0%; stagnant 8.5 h; last event 0.0 h ago, log write 0.0 h ago (996 lines)
  NO-PROGRESS epyc10 proof 4_2_tapbal_grt stage 10.7 h job 11.1 h: no new meaningful log line for 6.0 h; last: delta HPWL                    0 %
- 2026-11-19 15:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 15:52 PST: 272 running jobs, PROGRESSING 266, SLOW 4, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 40.5 h job 41.7 h: no new meaningful log line for 40.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc10 proof 4_2_tapbal_grt stage 11.7 h job 12.1 h: no new meaningful log line for 7.0 h; last: delta HPWL                    0 %
- 2026-11-19 16:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 16:52 PST: 261 running jobs, PROGRESSING 256, SLOW 3, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 41.5 h job 42.7 h: no new meaningful log line for 41.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc10 proof 4_2_tapbal_grt stage 12.7 h job 13.1 h: no new meaningful log line for 8.0 h; last: delta HPWL                    0 %
- 2026-11-19 17:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 17:52 PST: 254 running jobs, PROGRESSING 246, SLOW 6, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 42.5 h job 43.7 h: no new meaningful log line for 42.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc8 ot_s81sl_leaf__t26 5_1_grt stage 17.5 h job 20.1 h: repair_Viol best 128 last 128 rows 333 window-gain 0.0%; stagnant 9.7 h; last event 0.0 h ago, log write 0.0 h ago (1099 lines)
- 2026-11-19 18:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 18:52 PST: 302 running jobs, PROGRESSING 294, SLOW 7, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 43.5 h job 44.7 h: no new meaningful log line for 43.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 19:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 19:52 PST: 303 running jobs, PROGRESSING 294, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 44.5 h job 45.7 h: no new meaningful log line for 44.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc8 ot_s81sl_leaf__t26 5_1_grt stage 19.5 h job 22.1 h: repair_Viol best 128 last 128 rows 410 window-gain 0.0%; stagnant 11.7 h; last event 0.0 h ago, log write 0.0 h ago (1176 lines)
- 2026-11-19 20:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 20:52 PST: 454 running jobs, PROGRESSING 447, SLOW 6, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 45.5 h job 46.7 h: no new meaningful log line for 45.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 21:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 21:52 PST: 510 running jobs, PROGRESSING 502, SLOW 7, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 46.5 h job 47.7 h: no new meaningful log line for 46.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
- 2026-11-19 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 22:52 PST: 553 running jobs, PROGRESSING 546, SLOW 4, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 47.5 h job 48.7 h: no new meaningful log line for 47.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc7 kv3_hgi_v1__cl141fc26e 5_1_grt stage 28.6 h job 46.0 h: repair_Viol best 5670 last 5670 rows 314 window-gain 0.0%; stagnant 6.6 h; last event 0.0 h ago, log write 0.0 h ago (1031 lines)
  NO-PROGRESS epyc7 kv3_hgi_v3 5_1_grt stage 14.2 h job 30.0 h: repair_Viol best 2955 last 2955 rows 234 window-gain 0.0%; stagnant 6.1 h; last event 0.0 h ago, log write 0.0 h ago (859 lines)
- 2026-11-19 23:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-19 23:52 PST: 520 running jobs, PROGRESSING 513, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 48.5 h job 49.7 h: no new meaningful log line for 48.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc7 kv3_hgi_v1__cl141fc26e 5_1_grt stage 29.6 h job 47.0 h: repair_Viol best 5670 last 5670 rows 361 window-gain 0.0%; stagnant 7.6 h; last event 0.0 h ago, log write 0.0 h ago (1109 lines)
- 2026-11-20 00:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 00:52 PST: 493 running jobs, PROGRESSING 486, SLOW 5, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 49.5 h job 50.7 h: no new meaningful log line for 49.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc7 kv3_hgi_v1__cl141fc26e 5_1_grt stage 30.6 h job 48.0 h: repair_Viol best 5670 last 5670 rows 402 window-gain 0.0%; stagnant 8.6 h; last event 0.0 h ago, log write 0.0 h ago (1168 lines)
- 2026-11-20 01:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 01:52 PST: 475 running jobs, PROGRESSING 459, SLOW 14, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 50.5 h job 51.7 h: no new meaningful log line for 50.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc7 kv3_hgi_v1__cl141fc26e 5_1_grt stage 31.6 h job 49.0 h: repair_Viol best 5670 last 5670 rows 451 window-gain 0.0%; stagnant 9.6 h; last event 0.0 h ago, log write 0.0 h ago (1242 lines)
- 2026-11-20 02:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 02:52 PST: 380 running jobs, PROGRESSING 360, SLOW 16, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 51.5 h job 52.7 h: no new meaningful log line for 51.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc7 kv3_hgi_v1__cl141fc26e 5_1_grt stage 32.6 h job 50.0 h: repair_Viol best 5670 last 5670 rows 503 window-gain 0.0%; stagnant 10.6 h; last event 0.0 h ago, log write 0.0 h ago (1333 lines)
  NO-PROGRESS epyc8 sle_st_a_v1__cl67389ecd 5_2_route stage 11.1 h job 15.7 h: drt_violations best 72 last 72 rows 54 window-gain 0.0%; stagnant 6.3 h; last event 0.3 h ago, log write 0.2 h ago (3297 lines)
  NO-PROGRESS epyc8 slw_st_a_v1__clfc5867a6__pvdf8e5ca4 5_2_route stage 10.8 h job 15.7 h: drt_violations best 72 last 72 rows 54 window-gain 1.4%; stagnant 6.2 h; last event 0.3 h ago, log write 0.2 h ago (3296 lines)
- 2026-11-20 03:57 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 03:52 PST: 349 running jobs, PROGRESSING 333, SLOW 13, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 52.5 h job 53.7 h: no new meaningful log line for 52.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc8 sle_st_a_v1__cl67389ecd 5_2_route stage 12.1 h job 16.7 h: drt_violations best 72 last 72 rows 54 window-gain 0.0%; stagnant 7.3 h; last event 0.2 h ago, log write 0.1 h ago (3307 lines)
  NO-PROGRESS epyc8 sle_st_a_v1__cl989804f6__cled3c1d7b 5_2_route stage 11.8 h job 16.7 h: drt_violations best 72 last 72 rows 54 window-gain 0.0%; stagnant 6.7 h; last event 0.1 h ago, log write 0.1 h ago (3283 lines)
- 2026-11-20 04:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 04:52 PST: 326 running jobs, PROGRESSING 310, SLOW 13, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 53.5 h job 54.7 h: no new meaningful log line for 53.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_pc_v3 5_1_grt stage 25.1 h job 51.3 h: repair_Viol best 1971 last 1971 rows 193 window-gain 0.0%; stagnant 6.3 h; last event 0.0 h ago, log write 0.0 h ago (709 lines)
  NO-PROGRESS epyc8 sle_st_a_v1__cl989804f6__cled3c1d7b 5_2_route stage 12.8 h job 17.7 h: drt_violations best 72 last 72 rows 54 window-gain 0.0%; stagnant 7.7 h; last event 0.2 h ago, log write 0.1 h ago (3295 lines)
- 2026-11-20 05:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 05:52 PST: 324 running jobs, PROGRESSING 312, SLOW 8, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 54.5 h job 55.7 h: no new meaningful log line for 54.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 42.9 h job 53.2 h: drt_violations best 247 last 247 rows 52 window-gain 0.0%; stagnant 7.0 h; last event 0.8 h ago, log write 0.8 h ago (3299 lines)
  NO-PROGRESS intel1 kv3_pc_v3 5_1_grt stage 26.1 h job 52.3 h: repair_Viol best 1971 last 1971 rows 218 window-gain 0.0%; stagnant 7.3 h; last event 0.1 h ago, log write 0.0 h ago (734 lines)
  NO-PROGRESS epyc9 ot_s81sl_leaf__t27 stage_odb_cap stage 14.9 h job 14.9 h: no new meaningful log line for 6.6 h; last: 2026-11-20 07:17:00 STAGE-CAP skip /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave
- 2026-11-20 06:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 06:52 PST: 317 running jobs, PROGRESSING 301, SLOW 11, NO-PROGRESS 5 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 55.5 h job 56.7 h: no new meaningful log line for 55.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 43.9 h job 54.2 h: drt_violations best 246 last 246 rows 53 window-gain 0.4%; stagnant 8.0 h; last event 0.5 h ago, log write 0.6 h ago (3345 lines)
  NO-PROGRESS epyc7 dsdv_slice_lepe_mu_LP__t2 stage_odb_cap stage 37.1 h job 37.1 h: last event 1.2 h ago, log write 1.2 h ago (2133 lines), cpu idle (hung)
  NO-PROGRESS intel1 kv3_pc_v3 5_1_grt stage 27.1 h job 53.3 h: repair_Viol best 1971 last 1971 rows 249 window-gain 0.0%; stagnant 8.3 h; last event 0.0 h ago, log write 0.0 h ago (765 lines)
  NO-PROGRESS epyc9 ot_s81sl_leaf__t27 stage_odb_cap stage 15.9 h job 15.9 h: no new meaningful log line for 7.6 h; last: 2026-11-20 07:17:00 STAGE-CAP skip /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave
- 2026-11-20 07:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 07:52 PST: 324 running jobs, PROGRESSING 305, SLOW 14, NO-PROGRESS 5 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 56.5 h job 57.7 h: no new meaningful log line for 56.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 44.9 h job 55.2 h: drt_violations best 246 last 246 rows 53 window-gain 0.4%; stagnant 9.0 h; last event 0.3 h ago, log write 0.4 h ago (3355 lines)
  NO-PROGRESS epyc7 dsdv_slice_lepe_mu_LP__t2 stage_odb_cap stage 38.1 h job 38.1 h: last event 2.2 h ago, log write 2.2 h ago (2133 lines), cpu idle (hung)
  NO-PROGRESS intel1 kv3_pc_v3 5_1_grt stage 28.1 h job 54.3 h: repair_Viol best 1971 last 1971 rows 289 window-gain 0.0%; stagnant 9.3 h; last event 0.1 h ago, log write 0.1 h ago (805 lines)
  NO-PROGRESS epyc9 ot_s81sl_leaf__t27 stage_odb_cap stage 16.9 h job 16.9 h: no new meaningful log line for 8.6 h; last: 2026-11-20 07:17:00 STAGE-CAP skip /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave
- 2026-11-20 08:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 08:52 PST: 358 running jobs, PROGRESSING 339, SLOW 16, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 57.5 h job 58.7 h: no new meaningful log line for 57.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 45.9 h job 56.2 h: drt_violations best 246 last 246 rows 54 window-gain 0.4%; stagnant 10.0 h; last event 0.5 h ago, log write 0.5 h ago (3401 lines)
  NO-PROGRESS epyc9 ot_s81sl_leaf__t27 stage_odb_cap stage 17.9 h job 17.9 h: no new meaningful log line for 9.6 h; last: 2026-11-20 07:17:00 STAGE-CAP skip /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave
- 2026-11-20 09:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 09:52 PST: 390 running jobs, PROGRESSING 374, SLOW 13, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 58.5 h job 59.7 h: no new meaningful log line for 58.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 46.9 h job 57.2 h: drt_violations best 246 last 246 rows 54 window-gain 0.4%; stagnant 11.0 h; last event 0.4 h ago, log write 0.4 h ago (3405 lines)
  NO-PROGRESS epyc9 ot_s81sl_leaf__t27 stage_odb_cap stage 18.9 h job 18.9 h: no new meaningful log line for 10.6 h; last: 2026-11-20 07:17:00 STAGE-CAP skip /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave
- 2026-11-20 10:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 10:52 PST: 433 running jobs, PROGRESSING 417, SLOW 13, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 59.5 h job 60.7 h: no new meaningful log line for 59.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 47.9 h job 58.2 h: drt_violations best 246 last 246 rows 54 window-gain 0.4%; stagnant 12.0 h; last event 1.4 h ago, log write 1.4 h ago (3405 lines)
  NO-PROGRESS epyc9 ot_s81sl_leaf__t27 stage_odb_cap stage 19.9 h job 19.9 h: no new meaningful log line for 11.6 h; last: 2026-11-20 07:17:00 STAGE-CAP skip /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave
- 2026-11-20 11:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 11:52 PST: 373 running jobs, PROGRESSING 355, SLOW 14, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 60.5 h job 61.7 h: no new meaningful log line for 60.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 48.9 h job 59.2 h: drt_violations best 246 last 246 rows 54 window-gain 0.4%; stagnant 13.0 h; last event 0.2 h ago, log write 0.2 h ago (3415 lines)
  NO-PROGRESS epyc10 hd_lep0N pregrt_ff_hold stage 8.8 h job 14.9 h: no new meaningful log line for 6.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.002 |   0.000 | u_core.u.g_pin.g_s[0].u_st.q[5
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 8.3 h job 13.0 h: no new meaningful log line for 6.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
- 2026-11-20 12:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 12:52 PST: 322 running jobs, PROGRESSING 309, SLOW 9, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 61.5 h job 62.7 h: no new meaningful log line for 61.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS intel1 kv3_io_cor 5_2_route stage 49.9 h job 60.2 h: drt_violations best 243 last 243 rows 55 window-gain 1.2%; stagnant 14.0 h; last event 0.0 h ago, log write 0.0 h ago (3457 lines)
  NO-PROGRESS epyc10 hd_lep0N pregrt_ff_hold stage 9.8 h job 15.9 h: no new meaningful log line for 7.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.002 |   0.000 | u_core.u.g_pin.g_s[0].u_st.q[5
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 9.3 h job 14.0 h: no new meaningful log line for 7.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
- 2026-11-20 13:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 13:52 PST: 293 running jobs, PROGRESSING 284, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 serdes__t13 signoff_meas_072023 stage 62.5 h job 63.7 h: no new meaningful log line for 62.1 h; last: - hold_ff: FAIL WNS -55.85 ps < 0
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 10.3 h job 15.0 h: no new meaningful log line for 8.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
- 2026-11-20 14:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 14:52 PST: 272 running jobs, PROGRESSING 261, SLOW 7, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pvf1512c16 5_2_route stage 23.7 h job 27.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 6.7 h; last event 1.7 h ago, log write 1.3 h ago (3371 lines)
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pvcd889288 5_2_route stage 23.7 h job 27.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 6.5 h; last event 1.2 h ago, log write 0.7 h ago (3371 lines)
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pv16277ca6 5_2_route stage 23.7 h job 27.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 6.5 h; last event 1.2 h ago, log write 0.9 h ago (3371 lines)
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 11.3 h job 16.0 h: no new meaningful log line for 9.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
- 2026-11-20 15:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 15:52 PST: 323 running jobs, PROGRESSING 315, SLOW 4, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pvf1512c16 5_2_route stage 24.7 h job 28.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 7.7 h; last event 2.7 h ago, log write 2.3 h ago (3371 lines)
  NO-PROGRESS epyc9 coll_core 5_1_grt stage 12.7 h job 21.2 h: repair_Viol best 910 last 910 rows 267 window-gain 0.0%; stagnant 6.4 h; last event 0.1 h ago, log write 0.0 h ago (2246 lines)
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 12.3 h job 17.0 h: no new meaningful log line for 10.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
  NO-PROGRESS epyc7 serdes__t13 lec stage 6.5 h job 6.5 h: LEC last file/log write 6.5 h ago
- 2026-11-20 16:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 16:52 PST: 346 running jobs, PROGRESSING 338, SLOW 4, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pvf1512c16 5_2_route stage 25.7 h job 29.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 8.7 h; last event 3.2 h ago, log write 0.2 h ago (3373 lines)
  NO-PROGRESS epyc9 coll_core 5_1_grt stage 13.7 h job 22.2 h: repair_Viol best 910 last 910 rows 296 window-gain 0.0%; stagnant 7.4 h; last event 0.1 h ago, log write 0.0 h ago (2275 lines)
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 13.3 h job 18.0 h: no new meaningful log line for 11.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
  NO-PROGRESS epyc7 serdes__t13 lec stage 7.5 h job 7.5 h: LEC last file/log write 7.5 h ago
- 2026-11-20 17:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 17:52 PST: 362 running jobs, PROGRESSING 354, SLOW 5, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pvf1512c16 5_2_route stage 26.7 h job 30.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 9.7 h; last event 1.0 h ago, log write 0.7 h ago (3375 lines)
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 14.3 h job 19.0 h: no new meaningful log line for 12.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
  NO-PROGRESS epyc7 serdes__t13 lec stage 8.5 h job 8.5 h: LEC last file/log write 8.5 h ago
- 2026-11-20 18:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 18:52 PST: 350 running jobs, PROGRESSING 340, SLOW 6, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pvf1512c16 5_2_route stage 27.7 h job 31.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 10.7 h; last event 0.2 h ago, log write 0.1 h ago (3379 lines)
  NO-PROGRESS epyc9 col_h10_r2__t1__cl99efd374__pv4c1f67ff 5_2_route stage 26.0 h job 29.0 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 7.0 h; last event 2.2 h ago, log write 1.8 h ago (3371 lines)
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 15.3 h job 20.0 h: no new meaningful log line for 13.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
  NO-PROGRESS epyc7 serdes__t13 lec stage 9.5 h job 9.5 h: LEC last file/log write 9.5 h ago
- 2026-11-20 19:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 19:52 PST: 302 running jobs, PROGRESSING 290, SLOW 8, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 col_h10_r2__t1__cl1f5d6c2a__pvf1512c16 5_2_route stage 28.7 h job 32.7 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 11.7 h; last event 1.0 h ago, log write 1.0 h ago (3381 lines)
  NO-PROGRESS epyc9 col_h10_r2__t1__cl99efd374__pv4c1f67ff 5_2_route stage 27.0 h job 30.0 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 8.0 h; last event 0.8 h ago, log write 0.3 h ago (3375 lines)
  NO-PROGRESS epyc10 native59 pregrt_ff_hold stage 16.3 h job 21.0 h: no new meaningful log line for 14.2 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_388.q
  NO-PROGRESS epyc7 serdes__t13 lec stage 10.5 h job 10.5 h: LEC last file/log write 10.5 h ago
- 2026-11-20 20:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 20:52 PST: 348 running jobs, PROGRESSING 338, SLOW 8, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h10_r2__t1__cl99efd374__pv4c1f67ff 5_2_route stage 28.0 h job 31.0 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 9.0 h; last event 1.8 h ago, log write 1.3 h ago (3375 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 11.5 h job 11.5 h: LEC last file/log write 11.5 h ago
- 2026-11-20 21:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 21:52 PST: 332 running jobs, PROGRESSING 323, SLOW 5, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h10_r2__t1__cl99efd374__pv4c1f67ff 5_2_route stage 29.0 h job 32.0 h: drt_violations best 20 last 20 rows 53 window-gain 0.0%; stagnant 10.0 h; last event 0.6 h ago, log write 0.6 h ago (3381 lines)
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 14.4 h job 14.8 h: drt_violations best 1 last 42 rows 44 window-gain 0.0%; stagnant 8.2 h; last event 3.5 h ago, log write 3.3 h ago (2524 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 12.5 h job 12.5 h: LEC last file/log write 12.5 h ago
  NO-PROGRESS epyc9 coll_core 5_1_grt stage 12.5 h job 22.0 h: repair_Viol best 221 last 221 rows 141 window-gain 0.0%; stagnant 6.0 h; last event 0.1 h ago, log write 0.0 h ago (2113 lines)
- 2026-11-20 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 22:52 PST: 312 running jobs, PROGRESSING 301, SLOW 8, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 15.4 h job 15.8 h: drt_violations best 1 last 42 rows 44 window-gain 0.0%; stagnant 9.2 h; last event 4.5 h ago, log write 4.3 h ago (2524 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 13.5 h job 13.5 h: LEC last file/log write 13.5 h ago
  NO-PROGRESS epyc9 coll_core 5_1_grt stage 13.5 h job 23.0 h: repair_Viol best 221 last 221 rows 174 window-gain 0.0%; stagnant 7.0 h; last event 0.0 h ago, log write 0.0 h ago (2146 lines)
- 2026-11-20 23:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-20 23:52 PST: 295 running jobs, PROGRESSING 286, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 serdes__t13 lec stage 14.5 h job 14.5 h: LEC last file/log write 14.5 h ago
  NO-PROGRESS epyc9 coll_core 5_1_grt stage 14.5 h job 24.0 h: repair_Viol best 221 last 221 rows 202 window-gain 0.0%; stagnant 8.0 h; last event 0.1 h ago, log write 0.0 h ago (2174 lines)
- 2026-11-21 00:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 00:52 PST: 308 running jobs, PROGRESSING 292, SLOW 14, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 serdes__t13 lec stage 15.5 h job 15.5 h: LEC last file/log write 15.5 h ago
  NO-PROGRESS epyc9 coll_core 5_1_grt stage 15.5 h job 25.0 h: repair_Viol best 221 last 221 rows 230 window-gain 0.0%; stagnant 9.0 h; last event 0.1 h ago, log write 0.0 h ago (2202 lines)
- 2026-11-21 01:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 01:52 PST: 276 running jobs, PROGRESSING 265, SLOW 9, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 serdes__t13 lec stage 16.5 h job 16.5 h: LEC last file/log write 16.5 h ago
  NO-PROGRESS epyc9 coll_core 5_1_grt stage 16.5 h job 26.0 h: repair_Viol best 221 last 221 rows 259 window-gain 0.0%; stagnant 10.0 h; last event 0.1 h ago, log write 0.0 h ago (2231 lines)
- 2026-11-21 02:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 02:52 PST: 276 running jobs, PROGRESSING 262, SLOW 10, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 serdes__t13 lec stage 17.5 h job 17.5 h: LEC last file/log write 17.5 h ago
  NO-PROGRESS epyc8 opentallas-scratch2 svc_lo_dsdv_svc_rs__t7.C.yosys stage 6.3 h job 6.3 h: no new meaningful log line for 6.3 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
  NO-PROGRESS epyc8 opentallas-scratch2 svc_hi_dsdv_svc_pvso_entry__t1.C.yosys stage 6.3 h job 6.3 h: no new meaningful log line for 6.0 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
  NO-PROGRESS epyc8 opentallas-scratch2 svc_hi_dsdv_svc_rs__t4.C.yosys stage 6.3 h job 6.3 h: no new meaningful log line for 6.3 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
- 2026-11-21 03:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 03:52 PST: 278 running jobs, PROGRESSING 262, SLOW 12, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 serdes__t13 lec stage 18.5 h job 18.5 h: LEC last file/log write 18.5 h ago
  NO-PROGRESS epyc8 opentallas-scratch2 svc_lo_dsdv_svc_rs__t7.C.yosys stage 7.3 h job 7.3 h: no new meaningful log line for 7.3 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
  NO-PROGRESS epyc8 opentallas-scratch2 svc_hi_dsdv_svc_pvso_entry__t1.C.yosys stage 7.3 h job 7.3 h: no new meaningful log line for 7.0 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
  NO-PROGRESS epyc8 opentallas-scratch2 svc_hi_dsdv_svc_rs__t4.C.yosys stage 7.3 h job 7.3 h: no new meaningful log line for 7.3 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
- 2026-11-21 04:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 04:52 PST: 262 running jobs, PROGRESSING 246, SLOW 12, NO-PROGRESS 4 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 serdes__t13 lec stage 19.5 h job 19.5 h: LEC last file/log write 19.5 h ago
  NO-PROGRESS epyc8 opentallas-scratch2 svc_lo_dsdv_svc_rs__t7.C.yosys stage 8.3 h job 8.3 h: no new meaningful log line for 8.3 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
  NO-PROGRESS epyc8 opentallas-scratch2 svc_hi_dsdv_svc_pvso_entry__t1.C.yosys stage 8.3 h job 8.3 h: no new meaningful log line for 8.0 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
  NO-PROGRESS epyc8 opentallas-scratch2 svc_hi_dsdv_svc_rs__t4.C.yosys stage 8.3 h job 8.3 h: no new meaningful log line for 8.3 h; last: Warning: Replacing memory \arr with list of registers. See /srv/opentallas-scratch2/claude/s81-svc-s
- 2026-11-21 05:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 05:52 PST: 244 running jobs, PROGRESSING 229, SLOW 13, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 22.4 h job 22.8 h: drt_violations best 1 last 34 rows 50 window-gain 0.0%; stagnant 16.2 h; last event 5.7 h ago, log write 5.6 h ago (2799 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 20.5 h job 20.5 h: LEC last file/log write 20.5 h ago
- 2026-11-21 06:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 06:52 PST: 241 running jobs, PROGRESSING 224, SLOW 15, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 23.4 h job 23.8 h: drt_violations best 1 last 34 rows 50 window-gain 0.0%; stagnant 17.2 h; last event 6.7 h ago, log write 6.6 h ago (2799 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 21.5 h job 21.5 h: LEC last file/log write 21.5 h ago
- 2026-11-21 07:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 07:52 PST: 240 running jobs, PROGRESSING 221, SLOW 16, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 24.4 h job 24.8 h: drt_violations best 1 last 34 rows 50 window-gain 0.0%; stagnant 18.2 h; last event 7.7 h ago, log write 7.6 h ago (2799 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 22.5 h job 22.5 h: LEC last file/log write 22.5 h ago
  NO-PROGRESS epyc9 hd_mesh pregrt_ff_hold stage 10.6 h job 12.7 h: no new meaningful log line for 6.3 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_core.u_la.u_r1.rx_d[6]$_DFF_
- 2026-11-21 08:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 08:52 PST: 233 running jobs, PROGRESSING 217, SLOW 13, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 25.4 h job 25.8 h: drt_violations best 1 last 34 rows 50 window-gain 0.0%; stagnant 19.2 h; last event 8.7 h ago, log write 8.6 h ago (2799 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 23.5 h job 23.5 h: LEC last file/log write 23.5 h ago
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 19.3 h job 38.5 h: repair_Viol best 737 last 737 rows 141 window-gain 0.0%; stagnant 6.1 h; last event 0.1 h ago, log write 0.1 h ago (598 lines)
- 2026-11-21 09:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 09:52 PST: 167 running jobs, PROGRESSING 150, SLOW 15, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 26.4 h job 26.8 h: drt_violations best 1 last 34 rows 50 window-gain 0.0%; stagnant 20.8 h; last event 9.7 h ago, log write 9.6 h ago (2799 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 20.3 h job 39.5 h: repair_Viol best 737 last 737 rows 169 window-gain 0.0%; stagnant 7.1 h; last event 0.1 h ago, log write 0.0 h ago (626 lines)
- 2026-11-21 10:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 10:52 PST: 198 running jobs, PROGRESSING 181, SLOW 14, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 27.4 h job 27.8 h: drt_violations best 1 last 34 rows 50 window-gain 0.0%; stagnant 21.7 h; last event 10.7 h ago, log write 10.6 h ago (2799 lines)
  NO-PROGRESS epyc7 serdes__t13 lec stage 25.5 h job 25.5 h: LEC last file/log write 25.5 h ago
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 21.3 h job 40.5 h: repair_Viol best 737 last 737 rows 189 window-gain 0.0%; stagnant 8.1 h; last event 0.1 h ago, log write 0.1 h ago (646 lines)
- 2026-11-21 11:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 11:52 PST: 188 running jobs, PROGRESSING 172, SLOW 13, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 serdes__t13 lec stage 26.5 h job 26.5 h: LEC last file/log write 26.5 h ago
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 22.3 h job 41.5 h: repair_Viol best 737 last 737 rows 219 window-gain 0.0%; stagnant 9.1 h; last event 0.1 h ago, log write 0.1 h ago (676 lines)
  NO-PROGRESS epyc10 ot_s81sl_leaf__t11 5_1_grt stage 15.8 h job 28.0 h: repair_Viol best 739 last 739 rows 828 window-gain 0.0%; stagnant 6.5 h; last event 0.0 h ago, log write 0.0 h ago (1391 lines)
- 2026-11-21 12:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 12:52 PST: 199 running jobs, PROGRESSING 180, SLOW 16, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 23.3 h job 42.5 h: repair_Viol best 737 last 737 rows 240 window-gain 0.0%; stagnant 10.1 h; last event 0.1 h ago, log write 0.0 h ago (697 lines)
  NO-PROGRESS epyc10 ot_s81sl_leaf__t11 5_1_grt stage 16.8 h job 29.0 h: repair_Viol best 739 last 739 rows 977 window-gain 0.0%; stagnant 7.5 h; last event 0.0 h ago, log write 0.0 h ago (1540 lines)
  NO-PROGRESS epyc2 slw_su_l1__cla2a78701 5_2_route stage 16.3 h job 23.5 h: drt_violations best 9406 last 22242 rows 19 window-gain 0.8%; stagnant 7.5 h; last event 0.1 h ago, log write 0.1 h ago (1391 lines)
- 2026-11-21 13:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 13:52 PST: 183 running jobs, PROGRESSING 166, SLOW 15, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 24.3 h job 43.5 h: repair_Viol best 737 last 737 rows 273 window-gain 0.0%; stagnant 11.1 h; last event 0.0 h ago, log write 0.0 h ago (730 lines)
  NO-PROGRESS epyc7 slw_su_l0__cl1a1c1f8f 5_2_route stage 8.7 h job 11.3 h: drt_violations best 4 last 4 rows 47 window-gain 0.0%; stagnant 6.4 h; last event 1.8 h ago, log write 1.8 h ago (2488 lines)
- 2026-11-21 14:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 14:52 PST: 178 running jobs, PROGRESSING 166, SLOW 10, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 36.1 h job 36.1 h: drt_violations best 14534 last 14534 rows 2 window-gain 0.0%; stagnant 6.2 h; last event 1.8 h ago, log write 1.2 h ago (1497 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 25.3 h job 44.5 h: repair_Viol best 737 last 737 rows 309 window-gain 0.0%; stagnant 12.1 h; last event 0.0 h ago, log write 0.0 h ago (766 lines)
- 2026-11-21 15:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 15:52 PST: 164 running jobs, PROGRESSING 154, SLOW 8, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 37.1 h job 37.1 h: drt_violations best 14534 last 14534 rows 2 window-gain 0.0%; stagnant 7.2 h; last event 2.0 h ago, log write 1.0 h ago (1499 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 26.3 h job 45.5 h: repair_Viol best 737 last 737 rows 362 window-gain 0.0%; stagnant 13.1 h; last event 0.0 h ago, log write 0.0 h ago (819 lines)
- 2026-11-21 16:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 16:52 PST: 160 running jobs, PROGRESSING 142, SLOW 15, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 38.1 h job 38.1 h: drt_violations best 14534 last 14534 rows 2 window-gain 0.0%; stagnant 8.2 h; last event 1.7 h ago, log write 0.8 h ago (1501 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 27.3 h job 46.5 h: repair_Viol best 737 last 737 rows 398 window-gain 0.0%; stagnant 14.1 h; last event 0.0 h ago, log write 0.0 h ago (855 lines)
  NO-PROGRESS intel1 qc_sle_ctl2 pregrt_ff_hold stage 7.3 h job 15.4 h: no new meaningful log line for 6.1 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.003 |   0.000 | u_bound.u_lpad_x_su_l0_i.r[17]
- 2026-11-21 17:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 17:52 PST: 141 running jobs, PROGRESSING 126, SLOW 13, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 39.1 h job 39.1 h: drt_violations best 14534 last 14534 rows 2 window-gain 0.0%; stagnant 9.2 h; last event 0.7 h ago, log write 0.1 h ago (1505 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 28.3 h job 47.5 h: repair_Viol best 737 last 737 rows 442 window-gain 0.0%; stagnant 15.1 h; last event 0.0 h ago, log write 0.0 h ago (899 lines)
- 2026-11-21 18:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 18:52 PST: 151 running jobs, PROGRESSING 136, SLOW 12, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 40.1 h job 40.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 10.2 h; last event 0.4 h ago, log write 0.4 h ago (1548 lines)
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 35.4 h job 35.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 26.4 h; last event 5.5 h ago, log write 1.7 h ago (3167 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 29.3 h job 48.5 h: repair_Viol best 737 last 737 rows 508 window-gain 0.0%; stagnant 16.1 h; last event 0.0 h ago, log write 0.0 h ago (965 lines)
- 2026-11-21 19:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 19:52 PST: 124 running jobs, PROGRESSING 115, SLOW 6, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 41.1 h job 41.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 11.2 h; last event 1.4 h ago, log write 1.4 h ago (1548 lines)
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 36.4 h job 36.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 27.2 h; last event 6.5 h ago, log write 2.7 h ago (3167 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 30.3 h job 49.5 h: repair_Viol best 737 last 737 rows 557 window-gain 0.0%; stagnant 17.1 h; last event 0.0 h ago, log write 0.0 h ago (1014 lines)
- 2026-11-21 20:53 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 20:52 PST: 86 running jobs, PROGRESSING 80, SLOW 3, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 42.1 h job 42.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 12.2 h; last event 2.2 h ago, log write 0.5 h ago (1550 lines)
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 37.4 h job 37.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 28.4 h; last event 7.5 h ago, log write 3.7 h ago (3167 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 31.3 h job 50.5 h: repair_Viol best 737 last 737 rows 596 window-gain 0.0%; stagnant 18.1 h; last event 0.0 h ago, log write 0.0 h ago (1053 lines)
- 2026-11-21 21:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 21:52 PST: 106 running jobs, PROGRESSING 92, SLOW 11, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc2 kit drt_TT stage 43.1 h job 43.1 h: drt_violations best 14445 last 14445 rows 3 window-gain 0.6%; stagnant 13.2 h; last event 3.2 h ago, log write 1.5 h ago (1550 lines)
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 38.4 h job 38.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 28.9 h; last event 8.5 h ago, log write 4.7 h ago (3167 lines)
  NO-PROGRESS epyc10 slw_su_c__cl92142dac 5_1_grt stage 32.3 h job 51.5 h: repair_Viol best 737 last 737 rows 630 window-gain 0.0%; stagnant 19.1 h; last event 0.0 h ago, log write 0.0 h ago (1087 lines)
- 2026-11-21 22:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 22:52 PST: 160 running jobs, PROGRESSING 151, SLOW 6, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 39.4 h job 39.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 29.4 h; last event 9.5 h ago, log write 5.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 7.9 h job 7.9 h: no new meaningful log line for 6.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
  NO-PROGRESS epyc7 cbf_q11 5_1_grt stage 6.4 h job 9.5 h: no new meaningful log line for 6.4 h; last: OT_PG_TRACK_TRUTH add 5347 temporary GRT obstructions (layer=stripes/tracks) M5=1424/5696 M6=3300/19
- 2026-11-21 23:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-21 23:52 PST: 155 running jobs, PROGRESSING 146, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 40.4 h job 40.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 29.7 h; last event 10.5 h ago, log write 6.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 8.9 h job 8.9 h: no new meaningful log line for 7.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 00:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 00:52 PST: 153 running jobs, PROGRESSING 145, SLOW 6, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 41.4 h job 41.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 30.2 h; last event 11.5 h ago, log write 7.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 9.9 h job 9.9 h: no new meaningful log line for 8.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 01:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 01:52 PST: 150 running jobs, PROGRESSING 140, SLOW 7, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 42.4 h job 42.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 30.7 h; last event 12.5 h ago, log write 8.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 10.9 h job 10.9 h: no new meaningful log line for 9.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
  NO-PROGRESS epyc8 cbn_q00__cld7bf7197 5_1_grt stage 6.3 h job 11.6 h: no new meaningful log line for 6.3 h; last: OT_PG_TRACK_TRUTH add 5351 temporary GRT obstructions (layer=stripes/tracks) M5=1416/5664 M6=3312/19
- 2026-11-22 02:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 02:52 PST: 156 running jobs, PROGRESSING 143, SLOW 11, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 43.4 h job 43.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 31.1 h; last event 13.5 h ago, log write 9.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 11.9 h job 11.9 h: no new meaningful log line for 10.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 03:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 03:52 PST: 152 running jobs, PROGRESSING 141, SLOW 9, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 44.4 h job 44.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 31.6 h; last event 14.5 h ago, log write 10.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 12.9 h job 12.9 h: no new meaningful log line for 11.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 04:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 04:52 PST: 218 running jobs, PROGRESSING 210, SLOW 5, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 45.4 h job 45.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 32.1 h; last event 15.5 h ago, log write 11.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 13.9 h job 13.9 h: no new meaningful log line for 12.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
  NO-PROGRESS epyc8 kv3_hg_v1p2 5_1_grt stage 3.9 h job 3.9 h: last event 3.5 h ago, log write 3.5 h ago (1614 lines), cpu idle (hung)
- 2026-11-22 05:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 05:52 PST: 267 running jobs, PROGRESSING 261, SLOW 4, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 46.4 h job 46.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 32.5 h; last event 16.5 h ago, log write 12.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 14.9 h job 14.9 h: no new meaningful log line for 13.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 06:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 06:52 PST: 298 running jobs, PROGRESSING 291, SLOW 4, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 47.4 h job 47.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 33.0 h; last event 17.5 h ago, log write 13.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 15.9 h job 15.9 h: no new meaningful log line for 14.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
  NO-PROGRESS epyc8 i1 generate_abstract stage 1.4 h job 1.4 h: last event 1.3 h ago, log write 1.3 h ago (656 lines), cpu idle (hung)
- 2026-11-22 07:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 07:52 PST: 318 running jobs, PROGRESSING 309, SLOW 6, NO-PROGRESS 3 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 48.4 h job 48.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 34.3 h; last event 18.5 h ago, log write 14.7 h ago (3167 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 16.9 h job 16.9 h: no new meaningful log line for 15.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
  NO-PROGRESS epyc2 native59 pregrt_ff_hold stage 8.3 h job 9.6 h: no new meaningful log line for 6.6 h; last: 0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_bound.u_pd5_emb_code_q_436.r
- 2026-11-22 08:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 08:52 PST: 297 running jobs, PROGRESSING 288, SLOW 7, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 49.4 h job 49.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 35.1 h; last event 15.5 h ago, log write 0.7 h ago (3169 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 17.9 h job 17.9 h: no new meaningful log line for 16.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 09:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 09:52 PST: 280 running jobs, PROGRESSING 268, SLOW 10, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc9 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 5_2_route stage 50.4 h job 50.8 h: drt_violations best 1 last 29 rows 57 window-gain 0.0%; stagnant 36.3 h; last event 16.5 h ago, log write 1.7 h ago (3169 lines)
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 18.9 h job 18.9 h: no new meaningful log line for 17.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 10:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 10:52 PST: 263 running jobs, PROGRESSING 254, SLOW 8, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 19.9 h job 19.9 h: no new meaningful log line for 18.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
- 2026-11-22 11:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 11:52 PST: 223 running jobs, PROGRESSING 209, SLOW 12, NO-PROGRESS 2 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 20.9 h job 20.9 h: no new meaningful log line for 19.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
  NO-PROGRESS epyc7 slw_su_l1__clcc9d0155 5_2_route stage 20.1 h job 23.5 h: drt_violations best 48926 last 48926 rows 16 window-gain 0.8%; stagnant 6.5 h; last event 0.4 h ago, log write 0.5 h ago (1243 lines)
- 2026-11-22 12:52 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-22 12:52 PST: 201 running jobs, PROGRESSING 191, SLOW 9, NO-PROGRESS 1 (advisory, no cancel); table lanes/NOPROG.tsv
  NO-PROGRESS epyc7 array_direct_cli_1121 tiled_diagnostic stage 21.9 h job 21.9 h: no new meaningful log line for 20.3 h; last: "notch" in: asap7_tiled_diagnostic.lydrc:185
