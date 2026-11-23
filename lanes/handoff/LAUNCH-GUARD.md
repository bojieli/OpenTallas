# LAUNCH-GUARD handoff (11-23 01:4x PST, Opus)
Lane clone: intel2:/srv/opentallas-scratch2/claude/launch-guard/wt (edits staged from localhost scratchpad wt/, scp'd in).
Files: tools/autopilot/lbl_gate.py (new), kit_wave.py (lbl_launch_refused + same_input_repeat_refused in launch(); private_lbl_refusal in run_item;
pending_row_live in release_pending), autopilot.py (lbl_queue_hold -> WAIT-LBL), noprog_watchdog.py (design_fail_pass, eco_flat_evidence, private kits judged,
UNSIGNABLE first-pass cancel, ot-run --cancel --reason design), tests test_launch_guard.py, test_noprog_design_fail.py, test_noprog_unsignable.py (grace fixture).
Leak paths found: (a) LBL relied on hand holds; hold_records inert on stops_off dies (5 HOLD-LEAK); RETRY-INFRA / FLOW relaunch paths; (b) FIX3: stale
kit_wave_pending.tsv rows (11-05/06, attempt numbers of older events) were permanent pre-release retry keys overriding structural/repeat stops
(c1x_C__t10@3, kv512_C__t1@5, col_h10_r1 cld01bb4ae@11); sle_su_c 28 identical INFRA retries; (c) FIX2: grt_flat skips lane/private kits, gf_cancelled
recorded but container alive never retried, private kits exempt from UNSIGNABLE, ECOs never judged, 30 min grace.
State: focused tests 49 pass; broader subset running; next: ot-push-main, deploy check (rt/current), first-pass count, REPORT to COORD.
WAVE-OPS-R1 told (post 00:54) that LAUNCH-GUARD builds FIX 3.

## 02:2x DONE
main 48869414f4, live rt 6734f6deff0f 01:56. First tick 02:17: 12 LBL refusals. NOPROG 02:00: 7 design-fail units cancelled, scopes verified gone. Lane goal done; watch only.
