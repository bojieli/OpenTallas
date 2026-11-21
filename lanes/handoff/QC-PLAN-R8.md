# QC-PLAN-R8 handoff (started 2026-11-20 20:5x PST; succeeds QC-PLAN-R7). READ QC-PLAN-R7.md FIRST for V1/V2 context.

## V2 target apply 11-21 ~20:00 (one batched event). Work dir epyc9 W=/srv/opentallas-scratch2/claude/qc-plan-r7/v2 (R7's, reused)
- Compose job oth-ubuntu-1587840-1795236620 (epyc9, W/compose_v2.sh -> W/compose_v2.out) admitted 20:5x; R8 waits on it (ot-wait), not relaunched.
- srdreg RTL b2b7ea1247 (W/c345/clone, branch claude/qc-plan-r7-v2-srdreg): bench job oth-ubuntu-564392-1795234394 BASE 0 / SRD 0, qfd+production running.
  Push via ot-push-main when SRDQ/SRDP rc 0.
## Open V2 items
1. srdreg push. 2. 12 cb tile links 303-356 um (bind D 4->5 or station), coord FABLE-FIX-QC-CB (rows a3 ready 20:55, epyc9 fable-fix-qc-cb/W/a3).
3. 245 ps input-delay per-ring tool patch + tests. 4. CORE-PIN-RELAY-R2 rows only if A/B wins (no file yet). 5. FABLE-CLOSURE-1930 levers; no lockup rows until LOCKUP-STATION-R2 t39 TNS <= baseline.
6. compose -> census x3 -> bind/LATCHECK/G0 -> proof kit per changed family class to CTS/GRT -> apply. 7. On apply release 11 cb hold_items (65f9eaf04c5, 8cd505347e7).
8. Re-sign 12 N_PAD split clones of 6 signed hc bases on spare capacity, reps first.
- Cancel candidate: N46C cbn_q00__cldbcda913 a1 intel1 unit kw-qwenco-cbnq00cldbcda913-1-41017 at >3 h in route (~22:00), wave cancel path, evidence CTS -1107 / GRT -925.

## 21:1x state
- V2a compose (R7 rows) DONE: W/compose/p_v2a.json ccfec518b5aa, side_v2.json 8ed01c07ebdc; census HOP 40/36 types (non-cb), UNREG_READ? 38.
- COORD 21:0x: fold FABLE-FIX-QC-CB a3 (seg 1) in place of R7 r7_cb rows; cb reset rows from RESET-RELAY-GEN-R3 (epyc10 rrgen-r3/qc, qcleg.sh
  queued in ot-run from localhost pid 1542406 -> rrgen-r3/qc/out/plan_final.json); own proof p1 (epyc9 fable-fix-qc-cb/proof/p1, client pid 1689001,
  queued for memory since 20:54); push link_sites.py.
- DONE: link_sites.py + test_link_sites.py on main 1a0c00b146. ft_in_budget per-port key on main 4c4455dd3a:
  budgets.ft_in_budget_ps {"sle_ctl__cla4f6f12f/cws1_i": {"seam_um": 133.1}, ".../cws2_i": {"seam_um": 223.5}} (136.5 / 195.3 ps).
- R8 work dir epyc9 R=/srv/opentallas-scratch2/claude/qc-plan-r8/v2b: add_rows.py (new rows bc_i22/bc_i32 q11, bc_o31 cbx, y_o11 q00, y_o22 cbn_q11;
  private siting RTL copy with u_lpad_<bus> D1), sites_v2b.sh BASE OUT (a3 recipe + new rows + --pc-slack 60 on q11 tile links), apply_lanes.py.
  --pc-slack patch uncommitted in epyc9 lane clone /srv/opentallas-scratch2/claude/qc-plan-r8-linksites (branch qc-plan-r8-linksites).
  Trial on V1 base: R/trial1 (ot-run).
- V2b compose = base -> cb reset (R3, else R7 rleg) -> sites_v2b -> apply_lanes (+ft budget) -> R7 c345 steps -> r7_hop300 -> census; then 2-pass bind
  (bind -> re-site link_sites on real bound RTL -> final bind) because new in-row lane pads exist only after bind.

## 21:3x state (R=epyc9 /srv/opentallas-scratch2/claude/qc-plan-r8/v2b)
- On main: srdreg 2ddb19c08b; link_sites + test 1a0c00b146; --pc-slack + tests 04d2980e9c; ft_in_budget per-port 4c4455dd3a. V2 runtime rt/745c8f11e429 (has all).
  rt/cca022294010 (R7 pin) was pruned: R/compose_v2b.sh uses rt 745c precheck.
- V2b pass-1 compose R/c1 (RESET3=0 = R7 rleg reset rows): p_v2b b637003d0801, side_v2 8ed01c07ebdc; sites 0 legs >300 on all 17 cb types;
  lanes 576 raised (sum 2029); knee 0; schema ok (rt 745c); census HOP 40/36 types (non-cb; same as V2a), UNREG_READ? 38.
- Bind pass 1: R/bind_v2.sh PLAN SIDE RT OUT [R8] (tree = V1 live tree v1r6 + main ot_coll_tp8_static.sv) -> R/b1 (ot-run oth-ubuntu-2697363-1795239134).
  Then: land_r8_derive.py derive plan b1/bind/bus_groups.json --like <tree r8> --out R/r8_v2.json; re-site cb with real bound RTL
  (u_lpad_bc_i22/32 names), pass-2 compose with R3 reset rows (RESET3=1, needs rrgen-r3 qc/out/plan_final.json copied to
  /srv/opentallas-scratch2/claude/rrgen-r3-copy/plan_final.json on epyc9), final bind, LATCHECK, G0 (qc-plan-r6/v1/g0.sh pattern), census x3, proof kits.
- Lever 6 (cb tile insertion 818 vs 733 + SDC override): R8 helper agent fixing; stop item: no cb route release before it lands.
- Tap-grid rows: only from TAP-GRID-2130 after its proof. Note: 120/128 QC types use clock.tap_mode density (tap_pitch_um unused; levers are
  tap_radius_um / tap_target_sinks / tap_max_sinks / tap_span_um).
- Proof p1 (fable-fix-qc-cb/proof/p1, cbn_q00__cl622f65d2) running on epyc9 since ~21:2x.
