# RULES-CAP-1 handoff (Fable expert lane, rule R-CAP: partition size, cell cap, outline sizing)

Task (COORD 11-13): set R-CAP once, implement a pre-launch check, prove the estimator on past runs, list over-cap
types per die, write the RULEBOOK section, post READY, stop.

Where: epyc7 /srv/opentallas-scratch2/claude/rules-cap-1/ (wt = clone of hub main, branch claude/rules-cap-1;
base = worktree at fbfb4fc6a6 for test baselines; h/ harvest script; shards/ suite logs). Harvest helper dirs
/srv/opentallas-scratch2/claude/rules-cap-1/h on epyc2/4/7/8/9, intel1/2 hold only harvest.py + the kit list.
Launch logs intel2 ~/rules-cap-1-logs/. No build was run; only test jobs through ot-run on epyc7.

Status (2026-11-13 04:12 PST): DONE, lane stopped. Nothing of mine is running.
- Branch claude/rules-cap-1@daf4c190d3 pushed to the hub (parent main fbfb4fc6a6, 1 commit; the files it touches
  are unchanged on main up to fa10860f1a). READY posted in lanes/COORD-REVIEW-QUEUE.md. Not merged.
- RULEBOOK R-CAP section committed (coord/state b6b02fe16a5 + header restore), verified on origin.
- Tests: test_cap_estimate.py 19 passed. tools/die_plan suite in 24 shards on epyc7 (ot-run): 7,408 passed; every
  failing or uncollectable file (50 files: missing tkinter, "No module named tools", LEC/yosys cases) was rerun on
  a baseline worktree at fbfb4fc6a6 and fails identically there (fail_base.txt == fail_wt.txt, f19_base == f19_wt).
  Not run to the end: test_bind_wavefront_keep.py (a yosys case over 20 min; it does not touch the changed files).

Rule and evidence: ~/coord/lanes/RULEBOOK-1113.md section R-CAP (the table of 376 runs, budgets, split rule,
per-die list). Data: tools/die_plan/testdata/cap_runs_1113.json on the branch (295 distinct runs).

Files on the branch (tools/die_plan/): cap_estimate.py (new), test_cap_estimate.py (new), testdata/cap_runs_1113.json
(new), check.py (G0C cell_budget), kit_preflight.py (check cell_budget), native_cell_cap.tcl (pre-floorplan
projection), cell_census.tcl (place stop), signoff.py (stage cap_estimate.py with the preflight bundle),
test_check.py (450k type now also raises cell_budget).

Open items for whoever continues:
1. gen_phys does not yet write cap_budget.json (plan cell estimate + macro count) into a kit, so a FIRST attempt is
   judged before synthesis only when preflight gets --plan-dir; otherwise the pre-floorplan projection is the first
   stop (after synthesis, before any repair). Small follow-up in gen_phys next to budget.json.
2. Autopilot failure classes: add OT_CELL_BUDGET (preflight cell_budget, pre_floorplan, place) to the STRUCTURAL
   cell-cap class so that it is not retried (EXPERT-REVIEW-1 lever 5).
3. The splits themselves (S81 dsdv_slice_*_C x16, QC sle_ctl + st_a x4, KV kv3_pv x10 + hub_Wo/Eo; HBM SU on
   resume) are die-owner plan events after the freeze (11-15 04:00). Not started by this lane.
4. S81 cells_est.json is stale for gunit__t1 / eng__t1 (429-484k listed, 105k measured).
5. Model limit: placement blow-ups (dsdv_slice second repair pass, 230-740k buffers) are R-REACH / R-FLOW items.
6. My RULEBOOK insert dropped the empty "## R-FLOW" header for about a minute (b6b02fe16a5); restored in the next
   commit, verified on origin/coord/state. RULES-FLOW-1 lost no text.

## CODEX follow-up 2026-11-13
READY hub claude/rules-cap-1@9b7a830e2f: gen_phys cap_budget.json emitter +5targeted tests, existing worktree E7 rules-cap-1/wt. Safe first-attempt plan estimate, no flat core totals, measured native count wins, stale unsound receipts overwritten, macro instance accounting. Focused25pass/final5pass via ot-run unit E7 oth-ubuntu-581868-1794606568. Shared owner holds integration with KV4b95fb; no P&R or merge/tag. Files committed/pushed; no source work left uncommitted.
CODEX second READY hub d34bfdb117 after9b7a830e2f: kit_wave actual cell-budget failures -> PLAN, not retryable INFRA; summaries/NEAR/probe negative controls. 10classifier tests pass E4unit3245443. Only kit_wave.py +test_kit_wave_cell_budget.py. Shared notified; all source committed/pushed.
