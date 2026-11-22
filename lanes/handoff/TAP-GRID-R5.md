# TAP-GRID-R5 handoff (live; updated 11-21 ~19:40 PST)
Predecessor: lanes/handoff/TAP-GRID-R4.md. Posts lanes/posts/TAP-GRID-R5.md. Lane dirs: intel2 + epyc7 /srv/opentallas-scratch2/claude/tap-grid-r5 (intel2 repo = ot-lane-clone).

## Landed
- main 3c2f3758f4: tools/die_plan/tap_split.py (plan tap splitter, lever 6.1: every tap incl explicit <= type cap under nearest split, radius <= 300, append-only) + opt-in clock.tap_balance_to slowest / tap_slowest_max_ps (lever 6 fix 3, tap_balance.tcl OT_TAP_BALANCE_TO=slowest, OT_TAP_CHECK bound from target). Tests test_tap_split.py, test_tap_balance_slowest.py.
- Pre-existing main failure seen (not ours): test_tapbal_grt.py prepass tests (RUN_KIT now has [ -z "$G5X" ]).

## QC V3 tap rows (priority 1, cut 06:00, QC-PLAN-R12 needs strict+LAT receipt by 04:00)
- Base V3p3 f5d51696a2eb (epyc7 qc-plan-r12/ctl_strap/v3p3_static/plan.json), tools v3p3_launch (rt 55344f311cde).
- epyc7 tap-grid-r5/v3all2: rows.json (104 types, +346 taps), plan.json (applied), split.log. 95 SPLIT to 0 over, 9 PARTIAL (st_a x6 2078-2804, sle_ctl 1378, coll_n 1113, cbn_q00 1248; sinks under macros / heavy bins), 4 UNSUPPORTED (grid/grid+sinks). slw_su_c__cl19bb38ef not touched (Codex SU C 43-tap row separate).
- landing_remap OLD=V3p3 NEW=tap plan -> v3all2/plan_remap.json + remap_receipt.json (unit on epyc7, remap.log).
- Strict bind + LATCHECK queued by epyc7 tap-grid-r5/bindq.sh (waits remap + real snapshot copy qcsnap, then bind_v3p3_tap.sh = QC-PLAN-R12 bind_v3p3_pinned.sh with real copy instead of cp -al) -> v3tap_bound/, log bindq.log.
## KV D28 (priority 2)
- intel2 tap-grid-r5/kv/tree = real copy of D27d3 tree (plan_c.json restored to gated 48b92c30c8f6; HUB-R4 had overwritten it with 2724689bf511; eW_sidecar 12668ba83109 = HUB base copy, assumed unchanged content).
- kv_compose.py carries TAP-GRID-R4 d28_tap_rows onto D27d3 -> kv/plan_d27d3_tap.json + compose_report.json. Next: landing_remap OLD=D27d3 NEW=composed on row types, then G0 + strict bind + LATCHECK (gate like tap-grid-r4 gate_d28tap.sh).
- pv rows superseded: OPUS-FIX-KV-PV-R5 all-16 split (por_all16_composed) -> run tap_split.py on its composed plan for the 32 halves when it posts the sha.
## J8 (priority 4)
- intel2 tap-grid-r5/j8: j8_hold.tcl / j8_run.sh per-path FF hold on FABLE-FIX-S81-LEAF-R7 t39kit 5_1_grt.odb (J6 rg3 proof) -> t39_grt.out. Parse launch/capture tap port + clock latency per violating path.
## Open
- 5: CTS re-merges reset taps (lever 6.2), QC cb q01 S2 clock form (6.3), hg_v3 11 taps on macros.
