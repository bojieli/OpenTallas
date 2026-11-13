# RULES-FLOW-1 handoff (R-FLOW: ORFS flow settings; COORD coordinates)

## 2026-11-13 03:50 start
- Worktree: epyc7 /srv/opentallas-scratch2/claude/rules-flow-1/wt (branch claude/rules-flow-1-1113 off origin main; clone in progress).
- A/B dir: epyc7 /srv/opentallas-scratch2/claude/rules-flow-1/ab/<kit>/gen/ (kit copies; `ab/apply_rflow.py KIT stage/die_plan` writes the new set).
- Launcher: intel2 ~/rules-flow-1-logs/otr.sh NAME MEM THREADS -- cmd (ot-run --hosts epyc7); logs ~/rules-flow-1-logs/*.otrun.log.
- Running: turn_b_old and turn_b_new (HEAD hd_turn_b, copy of HEAD-ROUTE-1 proof2 kit), route goal + sign-off.
- Findings so far (measured on 40 routed kits, sign-off sta.log + 6_final.v):
  - routed TT slew violations: 85-99 % of the pins sit on a few dozen nets of fanout 17..154 (landing-ring select / enable
    nets, one BUFx2..BUFx6f driver); the rest are fanout-1 long wires. No clock pin in any gen_phys kit.
  - cause: repair_design repairs to exactly the 320 ps limit on the estimate (GRT worst slew slack 0.00..0.29), and the GRT
    repair runs on FF libs only; routed TT slack -0.10..-1.44. Kits with SLEW_MARGIN 50 (S81 t14/t22/t44): 0 violations.
  - hold: GRT repair stops at 0 on the estimate; 16 kits miss routed FF hold by 7..29 ps on 2..596 endpoints.
  - timing-driven GPL keeps repair buffers from its first pass (overflow 0.41-0.63): +18..+51 % area there, re-done at 0.19.
- Candidate set under test: SLEW_MARGIN 50, CAP_MARGIN 20, GPL_KEEP_OVERFLOW 0.25, place max fanout 32, max wire 120 um,
  hold repair target +30 ps (gate unchanged), hold budget report 10 %. CTS unchanged. RA=0 stays on M8-grant kits only.

## 2026-11-13 04:16 set final, HEAD A/B done
- Worktree ready: epyc7 rules-flow-1/wt, branch claude/rules-flow-1-1113 off origin main 055e36edab. UNCOMMITTED edits:
  tools/die_plan/{gen_phys.py (RFLOW defaults), gen.py (help), hold_repair_pre.tcl (OT_HOLD_BUDGET line),
  test_rflow_defaults.py (new), test_place_fanout_cap.py}, tools/autopilot/test_gp_noconverge_gate.py. 60 focused tests pass.
- FINAL SET: SLEW_MARGIN 50, CAP_MARGIN 20, GPL_KEEP_OVERFLOW 0.25, OT_PLACE_MAX_FANOUT 32, OT_MAXWIRE_UM 120 (smaller explicit
  value wins), OT_HOLD_BUDGET_PCT 10 (report only). CTS unchanged. RA=0 only on M8-grant kits (as merged). OT_RFLOW=0 = old kit.
- DROPPED: +30 ps hold repair target. turn_b arm ab/turn_b (m30): hold cells 631 -> 3,323 (18.5 % of logic), TT setup +100 ->
  -45.09 on 463 endpoints (FF-only repair cannot see TT setup). Hold guard belongs to R-CLOCK (HOLD-TAP-1 pre-GRT two-scene repair).
- HEAD hd_turn_b A/B (same netlist sha1 ed0f30376e1c; old arm rerun reproduces the 11-12 proof kit exactly):
  old ab/turn_b_old: NOT SIGNED, TT slew 1408 (worst 424 ps), setup +100.36, hold -26.35 / 47 endpoints, 31,190 cells.
  new ab/turn_b_v2:  TT slew 0 (worst routed 283 ps), setup +100.52, hold -24.27 / 32 endpoints (R-CLOCK class), 31,453 cells (+0.8 %),
  wire +0.7 %, DRC 0. drv check PASS; left: hold tail only.
- RUNNING (ot-run epyc7, logs intel2 ~/rules-flow-1-logs/): t21 + t21_old (S81 slice_station__t21), coll_ftc + coll_ftc_old (QC),
  tb_A_margins / tb_B_fanout / tb_C_gplkeep / tb_D_maxwire (single-knob arms on turn_b), pt_new2 (test shards).
- Results: `python3 -I ab/abres.py <kitdir>` on epyc7. Kit patcher: ab/apply_rflow.py KIT wt/tools/die_plan [KEY=-].
- NEXT: collect t21 / coll_ftc, write R-FLOW section in lanes/RULEBOOK-1113.md (coord-commit.sh), commit + push branch, READY.

## 2026-11-13 04:45 RULEBOOK R-FLOW v1 posted (coord/state, verified on origin); code committed locally aa1d118875 (NOT pushed)
- Single-knob arms on turn_b (ab/tb_*): margins only 0 slew pins; fanout 32 only 31; max wire only 1,342; GPL keep only 1,486
  and setup +34 (one landing-origin path with 40 repeaters/hold pads). So GPL_KEEP_OVERFLOW is OPEN: default only if S81 + QC show no loss.
- Extra arms launched for that decision: ab/tb_E_nokeep, ab/t21_nokeep, ab/coll_ftc_nokeep (= set without GPL_KEEP_OVERFLOW).
- t21 arms take ~2.3 h each (GRT 1 h 15, route 51 min in the original run); coll_ftc longer. Started 04:01 (keep) / 04:28 (nokeep).
- Tests: focused 60 pass. The 12-shard multi-file run has 27 failures, the same set with OT_RFLOW=0 (cross-file import
  pollution: die_sta_related, tkinter); per-file run in progress: epyc7 rules-flow-1/pf_new/summary.txt (perfile.sh TAG [ENV=V]).
- TO FINISH: (1) collect t21 / coll_ftc old, new, nokeep with `python3 -I ab/abrow.py <kitdirs>`; (2) decide GPL keep: if dropped,
  remove gpl_keep_overflow from gen_phys.RFLOW + rflow_cfg + tests, amend with a NEW commit; (3) update RULEBOOK R-FLOW (status line,
  R-FLOW-7, proof 2/3 rows); (4) run perfile.sh off OT_RFLOW=0 and compare; (5) push branch, READY in COORD-REVIEW-QUEUE.md.

## 2026-11-13 resumed after FLOW-FIN-2 handback; RULEBOOK R-FLOW v2 posted (coord/state, on origin)
- Branch claude/rules-flow-1-1113 = 5209be699f (2 commits on main 99b30dde2a), NOT pushed. Commit 2 = per-kit-class defaults
  (gen_phys.RFLOW_DIES: s81, s81_head, qwen_kvsys, qwen_compute; HBM unchanged; OT_RFLOW=1 forces, =0 old kit).
- STAGED, UNCOMMITTED in the worktree: tools/die_plan/relay_bay.py + test_relay_bay.py = hop pitch to OT_FT_MAXWIRE_UM (station
  hop nets only) instead of kit-wide OT_MAXWIRE_UM. Commit it only if ab/t21_ft50 holds (see below). Tests pass (7).
- Results in: QC coll_ftc old 2,280 slew / setup -90.92 / hold -16.48 on 347; R-FLOW 7 slew pins on 2 nets / -59.94 on 96 /
  -27.21 on 465; cells +5.7 %; DRC 0. KV + S81 + HEAD rows in the RULEBOOK table. R-FLOW-7 decided: GPL keep 0.25 stays.
- RUNNING (ot-run epyc7): ab/t21_ft50 (R-FLOW + kit-wide 100 um + OT_FT_MAXWIRE_UM 50; compare with ab/t21),
  ab/t21_mw100 (R-FLOW no GPL keep + kit-wide 100 um, no hop pitch; compare with ab/t21_nokeep), ab/coll_ftc_nokeep (sign-off).
  Each t21 arm takes about 2.3 h (launched 15:27 and 15:44 UTC).
- Regression: perfile.sh fin3 = 297 files, same 13 failing as OT_RFLOW=0 baseline (pf_fin2off).
- TO FINISH: read t21_ft50 / t21_mw100 with `python3 -I ab/abrow.py <kitdir>` (buffers = rep, cells, hold_ff, setup); if hop
  hold does not get worse than ab/t21 and cells drop: commit relay_bay change, update the R-FLOW-3 paragraph + status line in
  the RULEBOOK (post_rb.py pattern: replace only the R-FLOW section), add the coll_ftc_nokeep line under R-FLOW-7,
  push the branch, post READY in lanes/COORD-REVIEW-QUEUE.md. If it does not hold: git checkout the two relay_bay files, say so.

## 2026-11-13 09:55 READY posted; lane STOPPED
- Branch claude/rules-flow-1-1113 @ 06a9b2cf28 (3 commits on origin/main 7d5f821bd2), pushed and verified on origin.
  Commits: R-FLOW defaults; per-kit-class switch (RFLOW_DIES); relay_bay (hold no longer picks the pitch).
- RULEBOOK R-FLOW v3 final on origin coord/state; READY line in lanes/COORD-REVIEW-QUEUE.md (d0f9d83af83).
- The staged OT_FT_MAXWIRE_UM variant of the relay_bay change was DROPPED (built: 33,863 repeaters against 27,285); the committed
  change is the pitch criterion (setup + slew only).
- Tests: 58 focused pass; perfile.sh fin5 / fin5off: 299 files, same 14 failing with and without the change.
- Still running, harmless, nobody waits on it: ot-run epyc7 ab/t21_ft50 (sign-off). No other job of this lane is alive.
- Disk: epyc7 /srv/opentallas-scratch2/claude/rules-flow-1/ab holds 20 kit copies (proof evidence). Keep until the branch is
  merged and the RULEBOOK numbers are no longer questioned; then the whole rules-flow-1 dir can go. epyc9 rules-flow-1/d255 = one log.
- Open items listed in the RULEBOOK (not defaults): ECO slew margin 50 / 120 (HEAD-97), GRT repair on TT libs, HBM proof kit,
  75 um fallback if a station kit shows slew pins at 100 um.
