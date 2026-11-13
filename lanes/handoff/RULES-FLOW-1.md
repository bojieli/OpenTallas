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
