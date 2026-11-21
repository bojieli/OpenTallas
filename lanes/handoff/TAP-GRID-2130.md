# TAP-GRID-2130 handoff (2026-11-20 22:xx PST)

Owner of FABLE-CLOSURE-STRATEGY 21:30 lever 2 (tools half) and lever 3. Lane clone intel2 /srv/opentallas-scratch2/claude/lanes/TAP-GRID-2130.
Commit 81cb7ca096 (push via ot-push-main started 22:xx, log intel2 /srv/opentallas-scratch2/claude/lanes/tg2130_push.log).

## A. Canonical CTS read (all dies)
- cts_post_report.tcl now re-runs ORFS report_metrics after the POST_CTS hooks: 4_cts_final.rpt + 4_1_cts.json cts__timing are POST-hook
  for kits generated on main >= this commit (log line OT_CTS_FINAL_POSTHOOK; pre-hook copy 4_cts_final_prehook.rpt; OT_CTS_FINAL_POSTHOOK=0 off).
- tools/die_plan/cts_read.py = the one reader for older kits (OT_CTS_POST_TIMING first, json only labelled prehook).
- noprog_watchdog UNSIGNABLE reads the post-hook setup; root_entry_scan prints PREHOOK and skips a pre-hook 4_cts_final.rpt.
- Already post-hook: stuckscan (01c4b1e891), kit_scan / skew_calib / tap_insertion_report (OT_TAP_INSERTION lines), failure classes (gates run on the post-hook DB).
- Test: tools/die_plan/test_tap_grid_2130.py.

## B. Tap grid, plan key clock.tap_grid (absent = off)
{pitch_um <= 300 (300), bank_sinks (1000), regs (placed register dump, tap_resolve --dump), pair_um (200), iters (8), win_ps, raise_ps (0)}
- grid-mode types: grid pitch capped at pitch_um. Table types (explicit / grid+explicit; S81 leaf/col): own taps for every bank over bank_sinks and every
  tap box over pitch via the existing tap_density solve (needs regs; appended taps keep names; changes the pinout -> bind).
- kit: OT_TAP_SPAN_UM = pitch, tap pair affinity pair_um 200, OT_TAP_CONVERGE=1.
- tap_balance OT_TAP_CONVERGE: per tap / core pin learned stage price, pad chain at the load centre (KV v8c: a port-side pad cost 82 ps/stage),
  latest-sink cap target+win+60, bounded passes, tap pass again after the core pass, final OT_TAP_CONVERGE DONE/OPEN line listing off-target taps/pins.

## Proofs in flight (CTS from the kit's own 3_place.odb, private copies; baseline = the source kit's 4_1_cts.log)
| case | host | dir (scratch2/claude/tap-grid-2130/) | settings | baseline |
|---|---|---|---|---|
| S81 col_h9_r1 col_A (COORD u_u_s6/s9 422 vs 450) | epyc9 | colA_conv | converge | setup -15.39 / hold -130.24; s6/s9 eff 422/421; spread 138 |
| S81 leaf t60 | epyc10 | t60_conv/ot_s81sl_leaf__t60 | converge + pair 200 + span 300 | setup -222.55 / hold -57.22; spread 62; 3 taps over cap |
| S81 leaf t60 raise | epyc10 | t60_convR/... | + raise 100 | same |
| KV pv v8c | epyc7 | v8c_conv/kv3_pv_v8 | converge | tap means 229..983 (spread 754), 15/24 core pins off |
Read: grep OT_CTS_POST_TIMING / OT_TAP_BALANCE done / OT_TAP_CONVERGE / OT_TAP_INSERTION skew_ps in run/logs/asap7/*/base/4_1_cts.log; tg_cts.log rc.

## Not done / next
- No new-port (pitch / bank-tap) kit yet: needs a regenerated kit on a bind with the added taps (J6 / V2 row), not a kit patch.
- Rows to S81-J6-ASSEMBLY (only if the proof lands before 11-21 13:00) and QC-PLAN-R8 (V2 ~11-21 20:00) after the proofs.

## Stop list
- No clock verdict from a pre-hook 4_cts_final.rpt or a report_clock_skew pair. No pipeline stage as a hold fix. No tap-grid volume before the proof.
