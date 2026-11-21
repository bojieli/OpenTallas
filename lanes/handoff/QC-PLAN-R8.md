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

## 22:1x state (R=epyc9 /srv/opentallas-scratch2/claude/qc-plan-r8/v2b)
- 22:00 CANCELLED N46C cbn_q00__cldbcda913 a1 (intel1 oth-ubuntu-2003451-1795229956) at 3h00: pre-GRT setup -724.5, GRT repair -373.8 / TNS -15.4k.
- p1 (FABLE proof) FAILED at GPL ODB-0359 (FIRM u_pc_nk from relay_sites vs kit core-input hook). Fix on main a4ae603e36: link_sites writes no u_pc_*
  sites by default (--pc-sites opt-in; --pc-slack needs it). Consequence: q11 tile link u_t22.t_out (1233 um) needs +1 stage -> relay_depth row
  {inst u_t22, port t_out, D 1} on cbn_q11 x2 + cbf_q11 (add_rows.py). p1 must be re-GEN'd with V2 rows (die priority, read post-hook).
- Lever 6 in compose (tile_contract.py): 65 qfd_tile_nk_a0c core taps on 17 cb types 733.25/586 -> 818.1/658.07, 65 clk_cN per_port_ps rows removed.
- lat_fix.py: r7_hop300 left latency.stations short of ft-slot stations (FIXEDCYC 231 lanes) -> fixed in compose.
- Bind b1 refused FIXEDCYC; b2 (c1 + lat_fix) R8_STALE only (expected) -> R/r8_v2a.json dbbe6a24fce6 (qc_r8_pinned derive, 7892 members).
  Bind confirms the mimic: b2 emits u_lpad_bc_i22 D2 exactly as the siting copy.
- Pass-2 compose R/c2 running (oth-ubuntu-3463971-1795240983; RESET3=0 R7 rleg: RESET-RELAY-GEN-R3 qcleg.sh still queued on epyc10 since 20:2x).
  Next: bind b3 (c2 + r8_v2a) -> re-site cb with b3 bound RTL (BOUND=staged b3/bind/rtl; u_y_xd relay names) -> c3 -> b4 final + LATCHECK + G0.
- Re-sign: 6 N_PAD split reps added to dies.qwen_compute.only_items (coord ddaf212d693): *__pvcaa93304, *__pve289215f, *__pv97423966,
  *__pvcf529cc9, slw_hc3__clccfc3e6b__pvcca9ff41, slw_hc3__cld86a7ad4__pvfd488b8f. Siblings after reps sign.

## 11-21 ~00:xx state (R=epyc9 /srv/opentallas-scratch2/claude/qc-plan-r8/v2b; read this first)
- Main fixes pushed: a4ae603e36 link_sites no u_pc_* sites; 77440fa43c land_slots share_trunk (V1 slw_hc3 pv gen);
  2bdea13bb1 ft_spread avoids exact station banks (V1 slw_st_a_v2__clf4365a62 place); 758e5d6cbd bind relay_depth stages BEFORE
  the NK pipe (+chain hook single placer). V1 rows of those 3 types need re-GEN on tools >= 2bdea13bb1 (wave tool snapshot).
- V2 bind blockers found + fixed on the plan side (compose tail final_v2.sh: post_fix.py + clk_remap.py):
  relay_depth leaf name u_t_2_2; sle_su_c r8_strap_pad_max 31 (pads 17); land_r8_extra zz_extra_*_0 rebound (extra_rebound.py,
  install via bind_v2.sh env EXTRA0); forwarded clock pins follow V1 tap position (sle_ctl clk_t267 gone, coll_ftc renumbered);
  PARAM_REGEN W5 S = na_i00 +2 vs nb_i00 +3/+4 row imbalance -> siting min-stations na_i00=8 nb_i00=11, na_i22=4 (uniform deltas).
- R8: r8_v2c.json (qc_r8_pinned derive); rebinding after c4 needs a fresh derive + extra rebound.
- Running: compose c4 (balanced stations) -> final_v2 -> bind on rt/758e5d6cbd3e.

## 11-21 ~02:xx HANDOFF for QC-PLAN-R9 (read this first; R=epyc9 /srv/opentallas-scratch2/claude/qc-plan-r8/v2b)
- LIVE: bind b9 = epyc9 unit oth-ubuntu-1464365-1795255189 (log R/b9.out, out R/b9/). Plan R/c5/p_final4.json, side R/c5/side_v2.json
  (= c1), rt 639df6b7b265. bind_v2.sh loops bind -> R8_STALE -> r8_refresh.py (main 5d76c70f71) -> re-bind (<=3); final tables
  copied to R/b9/r8_final.json + extra_final_{0,1}.json. After rc 0 it runs LATCHECK (latcheck.json/tsv).
- If b9 still fails: PARAM_REGEN W5 S (fabric tree row balance) and HARD_CORE_PARAM_WRAP/ALL (sle_st_a HI_PAD/SKEW, sle_sc HARD_PINREG)
  were seen on b7 while R8 was stale; both are outputs of coll_regen (qc_fabric_transport + sc_hard_params), so expect them to clear
  with the fresh table. If PARAM_REGEN persists: compare per-type na_*/nb_* lane deltas (R/c5/rep_lanes.json changed) - they must be
  equal at each tree join (siting min-stations in R/sites_v2b.sh).
- Pipeline (all in R): compose_v2b.sh OUT (RESET3=1 R3 overlay, sites_v2b.sh, apply_lanes, R7 c345, hop300, lat_fix, tile_contract,
  schema, census) -> final_v2.sh IN OUT LAUNCH (post_fix, fam_rows, clk_remap) -> sle_apply.py (FABLE-FIX-QC-SLE-R3 rows, bumps
  latency.lanes AND lanes[].fixed_cycles) -> clk_remap again (sle_ctl core move) -> bind_v2.sh (EXTRA0=R/extra_v2_0.json).
  c5/p_final4 = c5 + sle rows + clk_remap + fixed_cycles fix (b8 refused FIXEDCYC: lanes[].fixed_cycles not bumped).
- Rows carried: cb a3/link_sites (no u_pc sites) + R8 new rows + balanced na/nb (na_i00=8 nb_i00=11 na_i22=4) + q11 relay_depth
  u_t_2_2.t_out D1 (+1 declared cycle, stage before NK pipe, main 758e5d6cbd) + lever 6 tile contract (65 taps 818.1/658.07) +
  RESET-RELAY-GEN-R3 cb reset rows (incl cbf_q00__cl1b5a6458 inst_taps) + FAM-QC-CB cbn_q11__cl5cc92dfe reset.local_taps_um +
  sle_ctl rows_v2b + su_c s2 x3 + slw_su_c__cl19bb38ef s3 (+1 on 3 lanes) + sle_su_c r8_strap_pad_max 31 + fclk clk_remap.
  place_precheck on c4/p_final: 0 findings.
- NEXT after bind+LATCHECK PASS: G0 (qc-plan-r6/v1/g0.sh pattern), plan_geom_census + event_adopt_diff + event_census
  (qc-plan-r7/census_v1.sh pattern), proof kits (R/proof_gen_v2.sh TYPE BIND_DIR; one per changed family class to CTS/GRT, die
  priority, read CTS post-hook), then pack/seal/apply as V1; on apply release 11 cb hold_items (R7 65f9eaf04c5/8cd505347e7) + the 3 fe
  holds (76a934188b0/56a3cbdebf0/678d61ae6c4) + cbn_q00__cldbcda913 via kit_wave_edit. Family lanes now own types (FAM-QC-CB/COLL/HCST,
  FABLE-FIX-QC-SLE): assemble their rows.
- Re-sign: 6 N_PAD reps in only_items (ddaf212d693); add the 6 siblings after the reps sign.
- V1 fixes on main (77440fa43c land_slots share_trunk, 2bdea13bb1 ft_spread) need a wave tool refresh to re-GEN slw_hc3 pv x2 and
  slw_st_a_v2__clf4365a62 (FAM-QC-HCST retried slw_hc3 at 7d30ba435f7).
