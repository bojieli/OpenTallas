W2 SAFE calibration packaging repair — PREPARED, NOT SUBMITTED

Pinned source: claude/takeover-hbm-w2-20261006 @
206a3037e32ee0a8773d21ff7c61fa20de586743. NO2 and NO3 are separate masters.
The original jobs run calibration in the final route directory, do not stop at
CTS, and then search an absent _cal directory. run_owned.py neither appends
CL_LABEL_SUFFIX nor consumes CL_STOP_AFTER automatically. These successor specs
explicitly use --run {RUN}/routes/{NAME}_cal --pnr-stop-after cts for calibration.
The later route retains its separate directory and receives measured CK_* values
through the unchanged source runner. No clocks, uncertainty, geometry, budgets,
RTL, numerical gates, or closure-loop implementation change.

Both specs pass closure_loop.py validate and the focused packaging regression.
No workload was run. They are intentionally outside tools/closure_loop/jobs and
/tmp/claude-review-20261003/closure_jobs, so the daemon cannot launch them.
merge_target is null: parent integration only. Result destinations are additive.

NEXT ACTION FOR PARENT:
1. Harvest the existing 206a3037e SAFE gate terminals after they finish naturally.
   At collection both were in neg_S8_rel_q_decision_removed, not a completed gate.
   Do not duplicate/cancel those runs or modify their frozen job specs.
2. Inspect S8 explicitly: the pinned gate script treats a 3600-second vvp timeout
   (rc 124), and even a compilation failure, as a rejected negative. Such a result
   is not a qualifying negative-control PASS. This packaging repair deliberately
   does not modify that source; a timeout/crash must remain unresolved and needs
   a source-level gate repair before physical admission. No wall-time limit was
   added or changed here. Do not adopt a green terminal based on that shortcut.
3. Once bench evidence qualifies and the existing job is terminal, use the
   closure-loop owner for successor admission. The loop forbids a duplicate
   route for a (block, source commit); do not bypass it with a renamed block or
   dummy source bump. If the original calibration already performed a route,
   the loop owner must handle preserved checkpoints under its recovery policy.
4. Revalidate the specs against the then-current loop, update the source pin only
   for an actual source fix, and submit only through closure-loop/admission.
   Never invoke run_owned.py manually. Validate, do not auto-submit this directory.

Validation:
 python3 -m unittest discover -s tests -p test_hbm_w2_safe_job_packaging.py -v
 python3 tools/closure_loop/closure_loop.py validate physical/hbm_w2_safe_packaging_20261006/no2.json
 python3 tools/closure_loop/closure_loop.py validate physical/hbm_w2_safe_packaging_20261006/no3.json

This fixes packaging only; it makes no new exactness, timing, closure, cycle-cost,
or adoption claim. Inherited cycles_added=15 has not been independently composed.
