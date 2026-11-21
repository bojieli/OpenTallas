# FABLE-FIX-QC-CB handoff (2026-11-20 ~20:20 PST). READ THIS FIRST.

Owner of the QC cb family (17 V1 types: cbf_q00 x2, cbf_q00_s2, cbf_q01, cbf_q01_s2, cbf_q11, cbn_q00 x3, cbn_q01 x3, cbn_q11 x2,
cbx_q10 x3). Goal: fix set -> census 0 hops over 300 -> one private proof kit to sign-off -> rows to QC-PLAN-R7 for V2 (apply 11-21
~20:00) -> representative + siblings to sign-off after V2 -> export AGIdock + rtx-pro ~/signed-export-1114.

## Where things are
- Work dir W = epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-cb. Lane clone W/src (branch fable-fix-qc-cb off main c88d681578, cone tools; nothing committed yet).
- Tool W/link_sites.py (lane script, not on main yet; put it in tools/die_plan + a test before any push).
  `python3 -I link_sites.py PLAN TYPE BOUND.sv OUT_PLAN REPORT.json --pins-root <tree>/physical/die_plan/qwen_compute/plan_of_record
   [--flops NAMES] [--seg 1] [--target 299] [--min-stations BUS=N]`
- V1 inputs (QC-PLAN-R6, read-only): V = epyc9 /srv/opentallas-scratch2/claude/qc-plan-r6/v1 (p_h.json plan, side_e.json, r8_v1a.json,
  b_n4 = strict bind tree/launch/bind, bind_v1.sh, launch_bind.sh, proof_gen.sh, r6_bus_stations.py, r6_lat_sync.py). Runtime pinned rt/65f3f85d7c5f.
- W/v1rtl/<type>/rtl/<type>_bound.sv = PRE-split bound RTL of each cb type from b_n4 (W/kitrtl_all.sh, log W/kitrtl_all.log).
  Do NOT feed link_sites.py the V/rleg/*_bound.sv copies: they are kit RTL after kit_dly_lockup (u_d10 already _sg0/_sg1).
- First run on the representative cbn_q00__cl622f65d2: W/rep/plan_*.json, W/rep/rep_*.json (legs, positions), W/show.py REPORT REGEX.

## Root cause (measured, A4 kit epyc2 .../s29q103S4Q9N46R4A4/items/cbn_q00__cl622f65d2/attempt_2)
1. budgets.r_dly_lockup {cbf_,cbn_,cbx_: {}} = seg 8 + r_dly_spread SEG form: the stages between two lockup latches are ONE station.
   u_d10_u_t_1_0_n_y (t10.n_y -> t11.n_a, about 1,500 um around t10/t11) = 2 stations: sg0 all at (1157, 1298), sg1 all at (1157, 1990):
   hops 630 / 690 um. u_d3_u_t_0_1_n_y (t01.n_y -> t11.n_b, 1,120 um over the top of t11) has no latch, hops 380 um, left at GPL sites.
   This is FABLE-PD-QC-1840 class A. kit_dly_lockup selects u_d<N>_* and u_lpad_* only (u_lpad .q is a concat, so it is skipped);
   u_r8b_* strap pads and u_pc_nk_* are never selected.
2. u_pc_nk_* (core_input_lockup +1 pipe) and the R8 strap pads have no plan site.
3. internal_stations rows are 405-um rows (63 census HOP rows on cb, worst 678). The census measures window far end -> regs -> to_um and
   does not count the ring read bank u_bin or the pin register u_pc as registers.
4. Tile pins (cores/a0_nk_pins_ck1109.json): n_a / n_b / n_y / t_out on the WEST edge (x 0.1), tap on the EAST edge; MY tiles mirror.

## Fix set (rows per type, written by link_sites.py)
- relay_sites: one site per bit for every delay-line stage (u_d<N>_*, names follow the seg-1 split <inst>_sg<j>.q), strap bank
  (u_r8b_*), fabric station register (u_st.b_d / tap_d / cap / cnt / run), ring read bank (u_bin_*); u_pc_nk_* bit by bit AT its
  core pin (core-pin register form). 0 cycles. Routes go around the tiles (channel routes), legs <= 300.
- budgets.r_dly_lockup.<type> = {seg: 1}: a hop lockup latch on every stage hop of the tile-link / fabric delay lines (hold by
  structure; no clock change). Open: proof kit must show the latch count / place are fine; fallback seg 2.
- internal_stations: regs re-spaced on the route; stations added where the census needs them. Representative, target 299:
  na_i00 4->6, nb_i00 7->10, y_o00 2->4, bc_i00 1->2, bc_i10 1->5 (5 is an artefact of the relaxation: census minimum is 3;
  the crossing class needs ONE count on bc_i00/10/20/30 -> use --min-stations and re-run; expect 3).
  Lane fixed_cycles are NOT edited by the tool: use V/r6_bus_stations.py logic (+delta on lanes ending on that bus of a changed
  type), then V/r6_lat_sync.py, then R8 re-derive (rt tools/die_plan/qc_r8_pinned.sh derive PLAN bus_groups TABLE), then strict bind.
- Reset legs: RESET-RELAY-GEN-R2 owns rows for the 11 cb types without reset.inst_taps + cbn_q11__cl5cc92dfe local tap. Not received yet.
- Core-pin clock pair (COORD, FABLE-CLOSURE-1930 lever 6: kit flop / u_lk_nk latch -> tile ck about 690 ps after CTS): CORE-PIN-RELAY-1930
  form is plan budgets.core_pin_relay / core_pin_relay_types (uncommitted in epyc9 core-pin-relay-1930/src: relay_depth.pin_weight,
  relay_mid.tcl PIN, gen_phys._core_pin_relay). It seats registers at pins; it carries no clock-tap rule yet. cb types go into
  core_pin_relay_types when it lands. The proof kit must report which tap u_pc_nk / u_lk_nk land on and the pair after CTS.
  STOP LIST (COORD): no cb route release on sites alone.

## Known open items in the tool
- One leg over 300 on the representative: u_t11.n_y -> u_bout_y_o11 353 um (pin centre to window far end + half pin span; a direct
  pin -> face register, no station row; real per-bit hop is shorter). Needs a y_o11 station row (+1) or a per-bit check.
- u_bin_bc_i10 landed under the ring macro (696.9, 14.3): add neighbour-route midpoints to the relaxation candidates.
- Key names are filtered by an A4 flop list (--flops, from a kit geom.tsv: C rows, kind S) so pruned bits get no key.

## Next steps
1. v1rtl done -> run link_sites.py on all 17 types (pre-split RTL), class-equal bc_i counts, 0 legs over 300.
2. Compose plan = p_h + rows; lanes + latency + R8; census (rt tools/precheck/plan_geom_census.py run --die qwen_compute --plan P --tools
   <rt>/tools/die_plan --types 'cb*' --out DIR): 0 HOP rows on cb.
3. Private strict bind (pattern V/launch_bind.sh; own dir, OT_LANE=FABLE-FIX-QC-CB), proof GEN (V/proof_gen.sh pattern), then the kit
   with run_kit.sh GOAL=route on current runtime: place WNS >= -42, CTS, GRT, route, sign-off.
4. Post rows + report to QC-PLAN-R7 (V2), cc RESET-RELAY-GEN-R2, CORE-PIN-RELAY-1930.
Nothing launched except W/kitrtl_all.sh (ot-run, epyc9, light). No job cancelled. No wave row touched.

NOTE: every W/*.py / *.sh named here lives on epyc9 in W; the session scratchpad is SHARED between lanes (my handoff.md there was overwritten by another lane at 20:1x and two wrong copies of this file were committed 20:16-20:18; this version replaces them).

## State 20:20 PST (supersedes the "first run" numbers above)
- Tool committed in the lane clone: W/src 9fbc898cd1 tools/die_plan/link_sites.py (not pushed: needs a unit test first). W/link_sites.py is the same file.
- Rows now lie on each row's OWN planned polyline (window far end / from_um -> regs -> to_um), re-spaced; count = census need.
  Class rule: every bc_i<NN> row gets --min-stations 4 (one count on the crossing class; FABLE-PD-QC-1840 said 1 -> 4).
- Representative cbn_q00__cl622f65d2 (W/rep3/plan_*.json, rep_*.json, target 292): na_i00 4->6, nb_i00 7->9, y_o00 2->4, bc_i00 1->4,
  bc_i10 1->4; 136 legs, all <= 300 except t11.n_y -> y_o11 face register (353 by pin centre + half span; direct pin -> face, no row,
  not a census row; optional +1 station row for R7). Census (rt a4fc295c2a05 plan_geom_census.py --types 'cb*'): 0 HOP rows on the
  representative (was 5); W/rep3/census.
- W/run_all.sh OUTDIR [args] chains link_sites.py over every type with staged RTL (W/v1rtl; 6 of 17 staged at 20:15, W/kitrtl_all.sh
  still running, about 5 min per type). Run: bash run_all.sh a2 --target 292 --min-stations bc_i00=4 --min-stations bc_i10=4
  --min-stations bc_i20=4 --min-stations bc_i30=4 ; then the census on a2/plan_all.json must show 0 HOP rows on cb*.
- Proof GEN p1: W/proof.sh TYPE TAG PLAN (current runtime, private launch tree W/proof/p1; the lane-pad depth of the staged bound RTL
  is set from the plan rows = PRIVATE proof input, not a bind). Launched 20:1x via ot-run --priority proof, waiting for memory on
  epyc9; log W/proof_p1.log. Then: OT_LANE=FABLE-FIX-QC-CB ot-run --mem 64 --threads 16 --hosts epyc9 --dir W/proof/p1 --
  bash W/proof/p1/gen/run_kit.sh W/proof/p1/gen/cbn_q00__cl622f65d2 route 64 16 ; read 3_detailed_place.rpt / 4_cts_final.rpt:
  class A endpoints (u_d*_sg* -> u_pc_nk) must be gone, place WNS >= -42 (the -296 u_lk_nk latch class L clears at CTS).
- Cycles for R7 per changed row = station delta on every lane ending on that bus of the type (V/r6_bus_stations.py rule) + R8 re-derive.

## State 20:55 PST: rows for V2 are ready for QC-PLAN-R7 (proof kit not yet run)
- ROW SET a3 = epyc9 W/a3: plan_all.json (V1 p_h aeae20148627 + rows on all 17 cb types, lanes NOT edited), rep_<type>.json (every leg,
  positions), ROWS.tsv (63 changed station rows), LANES.tsv (480 lanes, fixed_cycles +1..+6, sum 1,621; rule of V/r6_bus_stations.py),
  census a3/census: `ABS-CENSUS ... 17 types: no finding` on cb* (V1: 63 HOP rows, worst 678). Runtime of the census: rt/current 20:45.
- Re-apply on another base: `BASE_PLAN=<plan> bash W/run_all.sh <outdir> --target 292 --min-stations bc_i00=5 --min-stations bc_i10=5
  --min-stations bc_i20=5 --min-stations bc_i30=5 --min-stations nb_i00=10` (needs W/v1rtl/<type>/rtl staged bound RTL; all 17 staged),
  then `python3 -I W/rows_table.py <plan> <outdir>`. The tool is deterministic; rows depend on the plan rows / cores / pins only.
- Station counts (before > after): cbf_q00 x2 / cbf_q00_s2 / cbn_q00 x3: na_i00 4>6, nb_i00 7>10 (the representative alone came out 11:
  set --min-stations nb_i00=11 for one count on the family, or accept 10/11), y_o00 3>4 (cbn: 2>4), bc_i00 1>5, bc_i10 1>5.
  cbf_q01 / cbf_q01_s2 / cbn_q01 x3: y_o12 2>4, nb_i12 3>5, bc_o13 2>4 (cbn only). cbf_q11 / cbn_q11 x2: na_i22 2>3, nb_i22 2>4,
  y_o23 1>2, bc_o33 2>4 (cbn). cbx_q10 x3: y_o21 1>2, bc_i20 1>5, bc_i30 1>5. bc_i class = 5 (cbf_q00 bc_i00 far window end needs 5).
- NOT closed by rows (tool legs over 300 that the census does not see; each needs a NEW station row = +1 cycle, R7's call):
  cbf_q11 / cbn_q11 x2: u_bin_bc_i22 -> xstn x_2_2 -> tap -> pc 360-363 um legs, u_bin_bc_i32 -> x_3_2 390 (no bc_i22 / bc_i32 row today);
  cbx_q10 x3: xstn x_3_1 in -> tap / -> bc_o31 face 383; t11.n_y -> y_o11 face 302-353 (cbf_q00 / cbn_q00), t00/t21.n_y -> first y_o
  station 303-309 (pin half-span counted). Details in rep_<type>.json "over".
- r_dly_lockup.<type>.seg = 1 is written for every type by the tool (--seg 1): the relay_sites keys of the u_d<N>_* lines use the
  <inst>_sg<j>.q names of that split. If R7 drops seg 1, re-run the tool without --seg (keys then follow seg 8).
- Proof GEN p1 (representative, rows of W/rep3: nb_i00 9, bc_i 4): prepare-stations PASS (planned = bound pads on all rows), gen.py phys
  running since 20:19 (same long step after m8_grant.json as the V1 proof GEN). Kit not launched yet.

## State 21:00 PST: proof kit p1 launched (successor: start here)
- Proof GEN p1 PASS 20:53 (PROOF_GEN_RC 0, rt 1c1857d4d157 = rt/current at 20:19). dly_lockup.json: seg 1, 4 lines selected (u_d6 x2, u_d3, u_d10),
  25 segments, 21 latches, 10,814 latch bits. istations.tcl carries the new station sites (u_lpad_bc_i10 r[0..3] etc).
- Kit: epyc9 W/proof/p1, launched 20:54 with OT_LANE=FABLE-FIX-QC-CB:
  ot-run --priority proof --mem 64 --threads 16 --hosts epyc9 --dir W/proof/p1 -- bash W/proof/p1/gen/run_kit.sh W/proof/p1/gen/cbn_q00__cl622f65d2 route 64 16
  log W/proof/p1/kit.log (ot-run posts DONE/DIED to lanes/posts/FABLE-FIX-QC-CB.md). At 20:55 it was waiting for memory admission on epyc9
  (unit name = the oth-ubuntu-* line in kit.log once admitted; cancel only with ot-run --cancel <that unit>). A4 kits of this type took
  about 4 h to a placed DB on loaded hosts.
- READ, in this order, under W/proof/p1/gen/cbn_q00__cl622f65d2/run:
  1. logs .../2_* or 3_1 place log: "OT_RELAY_SITES placed N flops FIRM (plan keys unmatched: M of 38818)". M must be small. A large M =
     key names wrong (first suspect: <inst>_sg<j>.q of the seg-1 split, or '/' vs '.'); fix names in link_sites.py put() and re-GEN.
  2. reports .../3_resizer.rpt + 3_detailed_place.rpt: WNS; worst paths must NOT be u_d*_sg* / u_r8b_* -> u_pc_nk_* (class A). The -296
     u_lk_nk_* DLATCH -> u_tXY/n_b class L is an ideal-clock artefact that clears at CTS (do not count it).
  3. 4_cts_final.rpt: setup >= -42, and the COORD lever-6 pair: clock arrival of u_lk_nk_* / u_pc_nk_* vs u_tXY/ck (was about 690 ps on N46C);
     report the pair and which tap the pin registers landed on. Then GRT, route, sign-off (gates: DRC 0, TT >= -42, FF hold >= 0).
  4. Hold failing on the u_r8b_* strap pads (not in the lockup selection) -> plan clock.zl_lockup rows, never a clock change.
- This kit is a PHYSICAL proof only: its bound RTL has the lane-pad depths hand-set from the plan rows (proof.sh), so it is not a
  die-plan sign-off and must not be exported. The countable sign-off is the representative rebuilt on the V2 bind.
- After V2 applies (QC-PLAN-R7, target 11-21 20:00): relaunch the representative + 16 siblings through the wave (R7 lifts the cb
  hold_items only after this proof posts place / CTS numbers and COORD agrees), take them to sign-off, export to AGIdock + rtx-pro
  ~/signed-export-1114.
- Still to do in the tool before a push to main (W/src branch fable-fix-qc-cb, 9fbc898cd1 is older than W/link_sites.py: copy + commit):
  unit test (two cores, one chain around them, one row grown to the cap), then ot-push-main (never --no-test).
- Incident 20:16-20:18: the session scratchpad on localhost is shared by all lanes; my handoff.md there was replaced by FLOW-NOADV-R4's and
  I committed two wrong copies of this file, then appended to their scratch file. Both repaired (their file back to its 7 lines 20:18).
  My local files now live in scratchpad/fable-fix-qc-cb/.
- Correction 21:05: W/src HEAD 9fbc898cd1 already equals W/link_sites.py (sha256 7549bd5f861d62c1); only the unit test is missing before a push.

## STAND-DOWN (COORD order): FABLE-FIX-QC-CB is closed
- QC-PLAN-R8 owns the proof kit epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-cb/proof/p1 (left running, untouched) and folds the a3 rows into V2.
- link_sites.py clone path: epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-cb/src (git worktree, branch fable-fix-qc-cb, HEAD 9fbc898cd1, file tools/die_plan/link_sites.py; not pushed, no unit test). Same file: /srv/opentallas-scratch2/claude/fable-fix-qc-cb/link_sites.py.
- My waiters: none left alive (checked localhost + epyc9 by cmdline); nothing killed, nothing cancelled.

## p1 RESULT 21:56 PST (after stand-down): FAILED at global place, not running
- unit oth-ubuntu-1691144-1795236854 exit 2 at 3_3_place_gp: [ERROR ODB-0359] Attempt to change the origin of FIRM instance u_bound.u_pc_nk_u_t_0_0_n_a.q[0] (global_place.tcl).
- Keys matched: OT_RELAY_SITES placed 38542 flops FIRM, 276 of 38818 unmatched; OT_ISTATIONS placed 13898.
- Reading (not verified): a later kit hook moves the u_pc_nk pipe registers (core_input_anchor / core_input_chain class) and my relay_sites made them FIRM first. Likely fix: do not write u_pc_* keys (delete the kind == pc branch in link_sites.py main, keep the node fixed at the pin for the solver), re-run run_all.sh, re-GEN, relaunch. The a3 rows carry those u_pc_* keys on all 17 types: do NOT bind them into V2 as they are.
## 2026-11-21 02:21 PST Codex notes
- PASS candidate generation: `cbf_q00__cl1b5a6458` fp3 GEN RC 0 on epyc9 `oth-ubuntu-118033-1795251730`, 1,588 s. fp3 is a private row-plan diagnostic, while b9 carries canonical V2 reset and tile-clock contract.
- FAIL p1: duplicate FIRM `u_pc_nk` sites from relay rows and the core input hook. Main `a4ae603e36` drops those sites by default. Reviewed fp3 to start a place-only probe of that interaction. V2 CB proof will take its strict-bound kit and include the updated tile-clock contract.

