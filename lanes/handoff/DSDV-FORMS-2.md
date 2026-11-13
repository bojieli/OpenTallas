# DSDV-FORMS-2 handoff (S81 dsdv_slice_*_C family, R-CAP-3 point 3; Opus successor of HARD-S81-DSDV-1; COORD)
started 2026-11-13 06:56 PST, handed back 2026-11-13 07:27 PST. All paths below are on the host named; epyc7 work dir W = /srv/opentallas-scratch2/claude/hard-s81-dsdv-1,
worktree WT = epyc7 /srv/opentallas-scratch2/claude/wt/hard-s81-dsdv-1 (branch claude/hard-s81-dsdv-1-1113 off 87b85b86bd, NO commits yet).

## RUNNING JOBS (none cancelled; they pass to HARD-S81-DSDV-1)
1. xs4 hard-core kit to sign-off: epyc2 container klegacy-ot_s81sl_xs4_xs4h-2195230 (unit oth-ubuntu-2195141-1794582250), started 07:04 by
   the HARD-S81-DSDV-1 helper, kit epyc2 W/run/xs4h_r1/ot_s81sl_xs4_xs4h, kit_hash 6e80a8657ec1d541, goal finish, 64 GB / 32 CPU.
   At handback: in synth (1_1_yosys_canonicalize). Renders will be in <kit>/run/layout_review/. THE ONLY xs4 build.
2. Strict bind + lane latency check of plan g4 (fb7f60293915): epyc8 W/run_bind_xs4.sh plan_xs4_g4.json g4 with NOSEED=1 (elab first),
   ot-run unit oth-ubuntu-3892515-1794583517 on epyc8, client log intel2 ~/tmp/dsdv_forms2_bind_g4.log; outputs epyc8 W/out_g4, W/g4.{run.out,elab.log,bind.log,lat.tsv,lat.json,lat.log}.
3. G0 + G0C of plan g4: epyc7 W/chain5.sh (pid 4153745), G0 = check.py pid 9022 -> W/g0_g4, then G0C -> W/g0c_g4; status W/chain5.status.
   Compare with W/g0cmp.py W/g0base W/g0_g4 (base G0 = 74 errors, the record).
(Stopped by me: my duplicate xs4 build on epyc4 (COORD 07:3x); superseded G0/G0C of d2b and f4; the hung kit-gen yosys pids 3110311/3110733/3587533.)

## PLAN STATE: g4 = candidate event plan (sha fb7f60293915), WT physical/die_plan/s81/plan_xs4_g4.json (+ g1..g3a intermediates)
- chain5: base 18c864518844 -> g1 delta_xs4_core_1113.py -> g2 reach_fix classes 1-5 -> g3 delta_xs4_collector_1113.py (sidecar W/landed_sidecar_h2_psplit_all.xs4g.json)
  -> g3a/g4 stage_kit_source_table_refresh (+ --dest): 0 lanes each (the delta now prices its own stations).
- R-STREET check (street_rule.py from origin/claude/rules-street-1113 8dd3028a50, NOT on main; exported to W/rs_tool): g4 = 0 violations in all 16 C types
  (base: face_street/station_alley/street/sliver in 16). Report W/rstreet/chk_g4.json.
- reach_fix after: 0 violating types, 0 errors. FIXED-CYCLES: 55 lanes, +85 lane cycles (pre-approved), native rule broken on none.
- Renders: W/f4_png/*.png (f4 = g4 except lepw_mus xr). Viewed c1x t3, c1x t1 (mirrored, xs4 R180), c1x t8, iq t1: xf wall 3+2 with 43.2 street, cap clear of
  W/S bars, xs4 pin face to the ring band, station columns in streets. Advisory: ft chains in c1x t8 / iq run up the 43.2 W strip (transit WARN only).

## UNCOMMITTED EDITS (all in WT; nothing committed or pushed)
- physical/die_plan/s81/delta_xs4_core_1113.py (untracked, predecessor file) -- my edits:
  a) TEMPLATE for R-STREET-1: cap y 535.68, xs4 y 432.0 (43.2 under the xf row), egn nh|nk ABUTTED at y 604.8 (43.2 street under egg), xf cores
     abutted per group (x 146.88.. pitch 181.44 | 734.4..), street 691.2-734.4 kept; lepw_mus cap dy -406.08, xr dx 51.84 (60.48 street, 2,070 pins);
     c1x t1 xr dy -34.56 (86.4 street to xs4). Docstring coordinates NOT yet updated.
  b) assert: a core pair abuts (gap 0) or keeps >= 8.64, never overlaps.
  c) NEW: reach_fix.sync_fixed_cycles(base, out) before writing: without it strict bind fails "native stations rt_W1_out_1: fixed_cycles must
     equal source 1 + destination 4" (that is why the helper bind b3 on plan d3 failed). Copy of the predecessor version: W/delta_xs4_core_1113.e1.py.
- physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py (M): predecessor plan_type_pending branch + my ansi_port_dirs() fast path (port directions
  from a constant-width ANSI header; yosys hierarchy took > 1 h on xs4). Tested: 4,365 bits.
- physical/die_plan/s81/cores/legacy/recipes_xs4h_1113.json (untracked): regional_taps 4x3 -> 4x4 (generator needs powers of 2). Codex halo edit reverted (below).
- rtl/dsrom_sys/s81_dv/slice/cap_end/ot_s81sl_slice_w3.sv (M): predecessor (14:33 UTC): iq/kv512 u_xg -> ot_s81sl_xgt_xo, x relay D = DX - 1.
  CHECK in the latency results: mkq[1] alignment in xw4 now that xw_d is one edge later.
- Other untracked predecessor files unchanged by me: xs4_core_contract_1113.py, delta_xs4_collector_1113.py, inputs/core_pins/ot_s81sl_xs4.json,
  ref_tile/s81sl_xs4h/, cores/views/xs4_prov_1113/, plan_xs4_*.json.

## CODEX halo=0 EDIT (COORD 07:1x) -- REVERTED
- Codex (06:59-07:04) set macro_rows_halo=0 and orfs_vars MACRO_PLACE_HALO "0 0" in recipes_xs4h_1113.json and regenerated the epyc7 kit
  (W/gen5_nohalo.log). No measured reason: both keys removed, kit regenerated once (W/gen6.log): MACRO_PLACE_HALO 4.32 4.32, MACRO_ROWS_HALO 4.32,
  kit_hash 6e80a8657ec1d541 = the running epyc2 build, which never had the Codex change. No in-place regen since.

## DECISIONS
- xs4 outline/pins kept as HARD-S81-DSDV-1 chose: 648.0 x 518.4, one N face, M5, 0.144 pitch, 4,365 pins, 37 macros; R-CAP projection ~200k movable.
- R-STREET applied by hand in the template (no legalize growth): every C type 0 violations; slivers removed by abutting 0-pin faces.

## ft0_i (DIEVIEW F4) -- OPEN
- In c1x t3 (RULES-STREET-1 proof2 kit) ft0_i is declared in land_slots.json (D 4, hold_mux), its cland instance has the same params as every
  other landed bus (DSREP 8, WNEG 1), face_guard PASS. So the 1,224 "unregistered" are a placement or cone result, not RTL or declaration.
- Next: read pin_unreg / land rejected for ft0_i in that proof placement geom (epyc7 /srv/opentallas-scratch2/claude/rules-street-1/proof2/
  dsdv_slice_c1x_C__t3/gen/dsdv_slice_c1x_C__t3, in place repair at handback); if the ring flops sit far from the E window, pin the ft0 landing
  ring to the window (landing_placement) in the plan/kit.

## NEXT STEPS
1. g4 bind: on BIND_RC=0 read g4.lat.* (LATCHECK_RC, mkq alignment); on failure fix in the delta and rerun chain5 (writes g-series; use h-series next).
2. G0/G0C of g4 vs base (74 errors); new errors only in C types are mine.
3. Place proofs c1x t3 + one other row (e.g. c1x t8 or iq): private kit_wave.py run-item (intel2 /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_wave.py)
   with a copy of the 7073a6b4a59 spec (intel2 ~/coord/autopilot/kit_wave/s81_dsdv_slice_c1x_C__t3_b78ddadab579a/a1/spec.json): src = epyc8 W/bsrc_xs4,
   plan = its plan_h2_2249.json (run_bind_xs4.sh copies g4 there), kit_rtl bind_out = epyc8 W/out_g4, asbuilt = W/asbuilt_xs4b.json,
   --clock-landing = epyc8 W/landed_sidecar_h2_psplit_all.xs4g.json, private work/root/AP_DIR, hosts without epyc7.
4. Watch the epyc2 xs4 build and its renders; replace the provisional xs4 libs (cores/views/xs4_prov_1113) with the signed views.
5. Event branch off origin/main (>= 24b08535da): events/s81_xs4core_1113/ (plan gz, record.json, chain5.sh, g0 gz, latcheck, bind log gz, sidecar gz,
   asbuilt) + tool/RTL/core files; READY via coord-commit.sh, adopted after 11-15 04:00. Coordinate with S81-FORMS-1, FRAME-FORMS-1, HARD-S81-SVC-1
   (all branch from 18c864518844; the chain is scripted, so it re-applies on a composed base).

HANDBACK 2026-11-13 07:27 to HARD-S81-DSDV-1
