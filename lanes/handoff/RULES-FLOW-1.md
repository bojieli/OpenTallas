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
