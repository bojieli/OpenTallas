# NEARMISS-FIX-1 handoff (2026-11-14 21:50 PST, Sonnet lane)
Task: all 5 NEARMISS-ECO runs since 20:28 failed with prd_result.json passes [] (FABLE-CLOSURE-STRATEGY).

## Root cause (measured)
- 3 of 5 (slw cl76fb247e, slw cl1a1c1f8f on epyc2; sle cl7a55c676 epyc8; coll_ft cl78c7b300 intel1 = 4 of 5): eco_loop.json iteration rc prd_run_t = -13 (SIGPIPE).
  Their pass dirs show route OK, clk_freeze_check PASS, TC and BC counts "slew 0 cap 0 placement ok" (prd_count_p1_*.log), then NO prd_result.json update (still the initial {"passes": []}).
  Cause: tools/die_plan/post_route_drv/prd_run.sh inherits stdout = pipe to the ot-run client (checked /proc/PID/fd/1 = pipe on every host). When the client side is gone the first
  `echo "$ct"` after the 1-2 h route kills bash with SIGPIPE before addres writes the result. Wall 1.7-2.2 h. Nothing is wrong with the design or DB.
- 1 of 5 different: sle cl086d85ba (epyc7): real route failure, DRT-1231 "Pin u_bound.u_cland_x_su_c_p1_i/_13403_/A does not have access point" (detail_route, 1:05 h), route_rc 2.
  Same class as coll_ft cla4a25d77 eco_ko4b/ko4c rc 2 earlier (FlexPA/pin access in the ECO route), not the SIGPIPE class.

## Fix (branch claude/nearmiss-fix-1-1114 @966e3722ec6, hub ~/wt/nearmiss-fix-1, base origin/main 22c217df540)
- prd_run.sh: `trap '' PIPE`.
- eco_loop.py: prd_run stdout/stderr -> <pass dir>/prd_run.out (never the caller pipe); SIGPIPE rcs (13, 141, -13) are STOP_RCS = ABORTED, not a design ERROR.
- test: tools/die_plan/post_route_drv/test_prd_run_sigpipe.py (stub docker, closed stdout pipe): without fix rc -13 and 0 passes (reproduces), with fix 1 pass. test_eco_loop.py 88 pass.

## Proof runs (epyc2, private patched bundle /srv/opentallas-scratch3/claude/nmfix1-bundle = admission bundle 7513682b92f0b438b5cb + the 2 patched files; launched 21:42 via ot-heavy --mem 48)
- CONTROL coll_ft cla4a25d77: kit hardlink copy nearmiss-eco/ctl_collft_cla4a25d77/kit, out .../eco_fix1, log nearmiss-eco/logs/ctl.log. Earlier PASS took 3.9 h (eco_ko4d_095214).
- FAILED item slw_su_l0 cl76fb247e a4: nearmiss-eco/slw_cl76fb247e_a4/eco_fix1 (kit already has the patched M7 seed), log logs/fail.log. Expected ~2.2 h.
- Waiter armed in the lane session (Monitor on both eco_loop.json). Stop only via ot-heavy-stop --match <kit dir>.
- ECO runs on the OLD tree (prd_run.sh from bundle 7513682b92f0b438b5cb) will still hit SIGPIPE: new launches must use the patched bundle or main after merge.

## Re-queue
- After READY merges (or using nmfix1-bundle now): re-queue slw cl76fb247e, slw cl1a1c1f8f, sle cl7a55c676, coll_ft cl78c7b300 (all SIGPIPE class, counts were clean at 21:04 on epyc2 slw).
- NOT re-queue unchanged: sle cl086d85ba (DRT-1231 pin access; needs its own look: pin access of u_bound cland_x_su_c_p1_i, try OT_PRD_REPAIR_RC=placement / full route).
- coll_ft cla4a25d77 control is already a PASS (ingest + archive pending, FABLE-TYPES-QC-EAST F).
- Salvage idea (not done): the 4 SIGPIPE pass dirs are routed with count 0; a finish + sign-off + LEC only (OT_PRD_FINAL_ONLY) would save ~2 h each.
