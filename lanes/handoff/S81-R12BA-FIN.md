# S81-R12BA-FIN handoff (narrow successor of DIE-S81-88; job: post S81 ready12b-A, then stop) -- STOPPED

Updated: 19:3x PST 11-12.

## Done
- PLAN EVENT (READY except verify) + ASK posted to COORD (queue). Default (a): post as is; verify classes to tool lanes.
- Plan 18c864518844 = ready12ng + B1 lfcs + B2 tapwin + B3 band + B3b sidecar sync (c9f88) + B5 kit source refresh (22 lanes)
  + B6 kit dest refresh (19 lanes, LATCHECK-1 set). Asbuilt asbuilt_ist.json f969c08b916e (kit_source_station_pricing ON).
- Package: origin claude/s81-ready12bA-1112@cdeca6e28c79 (off main 66e6607e3f), events/s81_ready12bA_1112/ (record.json).
- Tool branch: origin claude/s81-r12ba-fin-1112@9489114321 (stage_kit_source_table_refresh --dest + 9 tests) - needs approval/merge.
- Gates: G0 74 = base (0 lat/reset rows); strict bind 0; LATCHECK-1 873/873; token AR 842.8 / MTP 2713.5 unchanged.
- Merged verify FAIL: (1) 3966 depth mismatches = kit source stations not counted by bind_verify under the switch (tool gap,
  all dies); (2) 2 CLOCK_LANDING reset-contract rows s_0S_L1 (leaf__t3) rst_rl_283/284, pre-existing in c9f88 (same in GEN-CLASS-1 out_t45).
- Main-tools verify (14685c8552d3) NOT run (chained on merged PASS). Must run IN PLACE on out_r12bA_dst (bind.f has absolute
  OUT paths): epyc8 s81-r12ba-fin/bin/run_verify_main_dst2.sh (it refuses unless run_dst.out has VERIFY_RC=0; edit that guard
  if COORD accepts (a)). Tree bsrc_verify_main_dst ready.

## Files (epyc8 /srv/opentallas-scratch2/claude/s81-r12ba-fin)
- out_r12bA_dst (bind + verify_report.json), bsrc_r12bA_dst, g0dst, lc/dst.tsv, run_dst.out, bind_dst.log, verify_dst.log,
  rtl_changed_vs_m2.json (71 modules), r6_kdst.json, s6_kdst.json. Token: epyc9 same dir tok_dst.log.
- out_r12bA_dst_main = useless copy (6.5 GB), safe to delete (not a link). Worktrees: wt/s81-r12ba-fin, wt/s81-r12ba-pkg (sparse).
- Stopped by exact PID: the moot out_r12bA_ist verify (run_r12bA_ist.sh) and my duplicate m2 baseline verify.
