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
