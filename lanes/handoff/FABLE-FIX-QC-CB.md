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
