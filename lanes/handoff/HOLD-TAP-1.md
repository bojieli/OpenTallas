# HOLD-TAP-1 handoff (clock/tap hold class lane, COORD coordinates) -- started 2026-11-13 03:28 PST

## Scope
Cross-tap hold class (RELAY-PLACE-1 11-13 HOLD-CLASS ANSWER): confirm mechanism, ONE family fix in the shared tap tooling,
private proof on hd_turn_b + S81 slice_station t41 to sign-off, class list, READY + RULEBOOK-1113.md section R-CLOCK. Then stop.

## Where
- Worktree: epyc9 /srv/opentallas-scratch2/claude/hold-tap-1/wt, branch claude/hold-tap-1-1113 off origin/main fbfb4fc6a6.
- Diagnostics (read-only STA, docker): epyc9 + epyc4 /srv/opentallas-scratch2/claude/hold-tap-1/diag (xtap_diag.tcl, run_diag.sh).
- Proof kits (inputs, not mine): turn_b epyc9 cland-relay-3/proof_turn_b_wc16/gen/hd_turn_b; t41 epyc9 relay-place-1/t41/gen/slice_station__t41;
  QC epyc4 kw43-wave-1109n/.../hcut1111/items/sle_st_a_v1__cl67389ecd/attempt_3/gen/...

## Findings so far (CHECKED on logs)
- 4_cts_final.rpt is written BEFORE cts_post.tcl (tap_balance): 4_1_cts.log order = CTS -> "Report metrics stage 4, cts final" -> clk_leaf_repeat ->
  cts_post/tap_balance.  The 120-185 ps "insertion mismatch" in that report is the UNBALANCED tree.  After tap_balance: turn_b tap means 435..458
  (sinks 425-472, target 450); QC sle_st_a 229..265 (target 250); t41 175..269 (spread 95: over-target trees stay as built).
- "Negative source latency" on the launch tap is the kit tap WINDOW (gen_phys.tap_window_tcl: set_clock_latency -source -early -W_p / -late 0 per tap
  port), not a real offset.  A cross-tap pair pays W_launch in full (no CRPR across ports); same-port pairs get it back.
- turn_b routed FF worst path (signoff/ff/sta.log): launch clk_t4 early -40, CK 276.8; capture clk_t3 CK 343.9: window 40 + tree 27 + unc 25 + hold 8
  vs data 86 -> -14.07.  Post-CTS (placement RC) only 34 reg-reg violators (ws -9); GRT repair reached +0.45; route lost it (tree 13 -> 27 ps).
- Hold repair stalls by RUNTIME/caps: QC sle_st_a GRT chunk 1 = 1384 buffers in 9432 s for 11074 violators.

## Next
Classification tables (t41, sle_st_a running), design, implement + tests, proofs, class list, READY, RULEBOOK R-CLOCK.

## 2026-11-13 03:59 classification + fix + first proof
- Class split of FF hold violators on the tap-balanced post-CTS DB (placement RC, hold_gate context):
  hd_turn_b 2312 = port_in 2278 (ws -117.9) + cross_tap 34 (-9.1); S81 t41 7049 = port_in 4817 (-68.2) + port_out 2220 (-34.4) + same_tap 9 + cross_tap 4;
  QC sle_st_a_v1__cl67389ecd 11403 = port_in 1038 + port_out 1330 + same_tap 563 (-35.8) + cross_tap 8472 (-79.4; median -14.5, median distance 11 um).
  So: t41 / turn_b = seam-contract port padding; QC st_a = cross-tap pairs under the flat 50 ps window.  No insertion mismatch after tap_balance.
- FIX (branch claude/hold-tap-1-1113, epyc9 hold-tap-1/wt, commit 6d148efc6f, not pushed yet): tools/die_plan/pregrt_ff_hold.py = the 11-03
  opt-in placement-basis pre-GRT FF hold repair made DEFAULT ON for every gen_phys kit (plan clock.pregrt_ff_hold false opts out), two scenes
  (TC setup + BC hold), register-to-register route guard (default 35 ps), port margin 5, clock cells FIRM, class report, fail-safe/advisory step.
  gen_phys.py (config lines + run_kit step with TLIBS), schema, tests test_pregrt_ff_hold.py (13) + test_grt_goal.py.
- turn_b proof, guard 25 (epyc9 hold-tap-1/proof/evidence/turn_b_g25): build 9 s, 1014 cells, GRT start hold +11.97 / 0 viol (was -126 / 2289),
  SIGNOFF LOCAL_PASS_NEEDS_PARENT: TT setup +101.46 (was +104.02), FF hold +2.71 (was -14.07 on 25), DRC 0.  Routed loss 22.3 -> default guard 35.
- t41 prototype on a copy of 4_cts.odb (guard 25): 7049 -> 0 violators, 12,805 hold cells, TT setup 124.64 unchanged, 1267 s.
- RUNNING: turn_b guard 35 (log localhost ~/ht1log/turn_b_route.log) and t41 full CTS -> sign-off (~/ht1log/t41_route.log), both ot-run epyc9,
  kits epyc9 hold-tap-1/proof/{turn_b,t41}/gen.  QC sle_st_a prototype epyc4 hold-tap-1/proof/sle_p1/pg.log.
- TODO: push branch, class list, READY, RULEBOOK-1113.md R-CLOCK.
