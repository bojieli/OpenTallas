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

## 11-23 03:5x
- main feedad5ec7 (rt feedad5ec7e6): FIX 3 hardened (PLACE-SETUP-STOP < -300 ps = design; older design fail not hidden by later cancel/infra attempt) + ENV-EFFECT run_item gate (kit_wave.env_effect_refusal, tools/autopilot/env_effect.py; scan CLI). seqhost/kv512/c1x repeats all launched before 01:56 via stale pending keys.
- Scan 03:4x: 1 mismatch col_h10_r1__t1__cl95b37463__pv1a6ec9c2@2 OT_KEEP_WIRES (stage-resumed kit). MISC kit 1 did have OT_TAP_GRT_PRE=1.

## 11-23 07:37 PST Codex takeover
- Exact reviewed-wave dispatch guard 53a303bb9822, canonical 207/207 GREEN, running in intel2 rt/current 441cd5b7bc9d. User autopilot drop-in zzzzzz-codex-takeover-viewed-route.conf sets AP_REQUIRE_VIEWED_WAVE_ROUTE=1. No service restart or change to running work. Matching exact kit/attempt/build-start minute on enqueue and submit, route below visual wait, generation and placed renders proceed.
- QC obsolete pending E10 V2 slw_fe_v1__clfe325744__cl08d14f0d queue 4ca96043ff34 withdrawn via cfdc0297d83a, AP confirmed. Already-started E2 V2 and E9 V3 survive.
- PHY-B sealed LINT basename-collision correction 8b86009b6f87, canonical 5/5 GREEN, E9 exact GEN_LINT PASS. Wrapper preflight independent structural failure remains held, see TL-QCPHYSDB.
