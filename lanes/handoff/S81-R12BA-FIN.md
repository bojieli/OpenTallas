# S81-R12BA-FIN handoff (narrow successor of DIE-S81-88; only job: post S81 ready12b-A tonight, then stop)

Updated: 17:5x PST 11-12.

## State
- LATCHECK-1 (COORD 17:1x): switch-ON bind out_r12bA_ist (plan af9967df9f89 = c9f88 + B5) still had 19 UNPRICED_KIT_STATIONS
  lanes (receiver kit IN stations, receiver pad 0). The ist verify was moot and was stopped (exact PIDs 3910744/56483 + children).
- B6 = tools/die_plan/stage_kit_source_table_refresh.py --dest (branch claude/s81-r12ba-fin-1112 @9489114321, worktree
  epyc8 /srv/opentallas-scratch2/claude/wt/s81-r12ba-fin, +9 tests, 16 pass). af9967df9f89 -> 18c864518844, 19 lanes, +21
  cycles, selection == LATCHECK-1 FAIL set (19/19). Receipt epyc8 s81-r12ba-fin/r6_kdst.json.
- Final rebind: epyc8 /srv/opentallas-scratch2/claude/s81-r12ba-fin/bin/run_r12bA_dst.sh (ot-heavy --mem 230): G0, strict bind,
  LATCHECK CLI (must be 0), copy OUT -> out_r12bA_dst_main + launch run_verify_main_dst.sh (ot-heavy --mem 200, main 14685c8552d3
  tools via git archive in main_tools/), then merged-tools verify. Log run_dst.out; logs g0dst.log, bind_dst.log, lc/dst.log,
  verify_dst.log, verify_main_dst.log.
- Token: reform_rebaseline --die s81 base plan_r12bA3 (c9f88) vs s6_kdst -> s81-r12ba-fin/tok_dst.log / tok_dst_vs_A3.json.
- Verify OOM fix: lint parallelism = asbuilt lint_jobs (6 in asbuilt_ist); memory bounded by ot-heavy --mem >= 6x23+26 GB.

## Next
1. When verifies + LATCHECK 0 pass: package plan branch off origin/main (no file > 95 MB), post READY + plan event with open list.
2. Report to COORD and stop.
