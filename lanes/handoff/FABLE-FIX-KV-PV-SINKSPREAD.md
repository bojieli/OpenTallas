# FABLE-FIX-KV-PV-SINKSPREAD handoff (Fable fix lane, KV pv D29 form; pairs with OPUS-FIX-KV-PV-R7)

Started 2026-11-22 04:08 PST by COORD. Posts: lanes/posts/FABLE-FIX-KV-PV-SINKSPREAD.md. Client logs: intel2 ~/tmp/ffkvpv/.
Brief: scratchpad fable_fix_brief.txt + family_brief.txt + rules.txt; lanes/FABLE-CLOSURE-0235.md 2.6 / 3.

## Goal
1. pv form with no tap over the cap on the 15 unsplit pv types (v3 = row 1 = PV-R7 / D28). Spread sinks, not taps.
2. Proof: tap load report on a fresh place, plan_gate_pre (rt >= 6d2e187f0d65) 0 findings, strict bind on a private fork.
3. One sealed representative private kit to sign-off (private-spec, --goal finish, run-item, ot-wait --durable).
4. D29 rows to KV-PLAN-R6. 5. Post every 2 h.

## Where
- epyc8 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/
  - tree/   ot-tree-fork of kw45/src_kv_d28_work_r6 (KV D28 work tree, plan dry5 fcfa38bdb65b, tools rt 6d2e187f0d65)
  - clone/  lane clone (ot-lane-clone) for the main push
  - w/      my scripts; w/regs/ = D23H placed register dumps of 11 pv types (kv3_pv v1 v12 v2 v4 v4n v5 v5n v6n v7 v8)
  - tmp/    own temp files
- epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/regs (register dump scripts + outputs)
- PV-R7 material (read-only): epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4/split28/r7 (compose_d29c.py, d29/)

## Facts
- 16 pv types: kv3_pv v1 v1n v2 v2n v3 v3n v4 v4n v5 v5n v6 v6n v7 v8 v12. No D23H place: v1n v2n v3 v3n v6.
- PV-R7 lever set (tap model only, base_d27, old tree5 tools): cut 1080 + bank inset 25.92 + cut-face reserve y 8.6-60
  + place_regions stacks (util 0.3) on cut-adjacent vo delay banks + tap_split rows. v6n (draft 78fe00f580fd) and v2
  under the cap on both pieces; v12e 1789, v7e 1859 (mid-slot pass-through banks, bottom right of e), v5ne 2114 over.
- tap cap = clock.tap_max_sinks per type (1000 or 1200); G0 counts the nearest-tap load (tools/die_plan/tap_split.py).
- RANKSEAT key form: main d219668949 (partition_types[].relay_rank_sites {rank: {line_um, order}}, rs_rank_line).
- main already has: spec cut_window_pref, cut_face_margin_um; plan key place_regions; budgets.face_flop_ew_types.
- Thin band (FIX-SYNC-KVHEAD 04:06): kv3_pv_v6n i_vport_E_N_vo_d3 [1135.5,28.1,1379.5,38.9] 10.8 x 244 um: to fix or justify.

## Tools ON MAIN 6390b7bfa650 (11-22 05:1x, pushed from intel2 clone2)
- type_split spec cut_face_bank_inset_um, cut_face_reserve_um {type: [[lo, hi]]} (windows_for reserved=), drop_clock_keys also
  drops reserved_sites_um / start_capture_um; face_flops OT_FF_EW_INSET_UM <- budgets.face_flop_ew_types[].inset_um; schema json.
- My tree has the same patch applied by hand (w/patch_main.py, patch_drop.py, patch_res2.py); re-pin to an rt >= 6390b7bfa650 when one exists.
- epyc8 clone/ is a broken half-widened sparse worktree (push timed out there): ot-delete it later. intel2 clone2/ is the good one.

## Method (scripts in epyc8 w/)
- run_d29.sh TYPE 1080 VAR: mk_bins7 (D23H regs, vo delay banks as place_regions stacks, stacks slide off ring keep-outs with
  D29_MAPVAR) -> compose.py (PV-R7 composer on base plan_of_record.base_d28, spec keys) -> tap_split report. env D29_RESERVE=lo:hi,..
- map1.sh TYPE VAR: legal_map.py per piece (ASCII map + json: boxes, keepouts, legal sites, tap loads).
- auto_reserve.py MAPW MAPE 1080 25.92 64.8: cut-face spans where the inset bank meets a tap-closed box or has no legal tap in 65 um.
- all_p2.sh NEWVAR MAPVAR: auto reserve + compose + taps + maps for the 10 other placed types.
- finish.sh TYPE 1080 VAR: in-core ft fix + place_regions + tap rows (--out-plan) + landing_remap -> $O/plan_c.json (final).
- bind_chain.sh TYPE 1080 VAR NAME: install as tree plan_of_record + gate_g0.sh (precheck, PLAN-GATE-PRE vs D28 dry5, G0) + gate_bind.sh.

## KEY FINDINGS
1. Cut overloads = cut-face bank / bank stack on or beside a landing-ring keep-out at the cut corner (no legal tap). Fix by
   construction: auto cut-face reserve (auto_reserve.py from legal_map json) + stacks slide off keep-outs (mk_bins7/8).
   A reach-bounded ft cut window wins over a reserve (trim_reserve.py; v12 ft57, v8 ft5).
2. v12e / v7e over-cap taps are INHERITED from the unsplit base (S-face hard ft ring sink_sites_um rows); PV-R7 agrees (05:03).
3. The composer's SWAP table is the v3 recipe: pure x swap on the 10 v3-like types, but on the 6 n types (v1n v2n v3n v4n v5n
   v6n) it also moves 6 of 8 cores to OTHER ROWS (up to 1054 um). Fix: D29_SWAPMODE=purex (compose.py + mk_bins8.py). Posted 05:3x.
   c3 (row-permuted) is DEAD; c4 (purex) is the candidate.
4. mk_bins8: per-core registers (name _pvg<g>_p<k>_) of a moved core are carried with the core; stacks keyed to the real core row.
5. G0 tap_sink_cap is a WARN; the kit's clock_taps.tcl cap pass re-homes; AUTO-GEOM reports tap_stuck. Real proof = kit place.
6. Thin band v6n i_vport_E_N_vo_d3: INFO (FIX-SYNC 04:17); ring_place=ff survives the split on all 16 ff bands.

## Results (nearest-tap model, D28 base)
- p2 (v3 table, mk_bins7, auto reserve): 0 over on kv3_pv v1 v2 v4 v4n v5 (v8 at p1); v5ne 1172/1000; v7e, v12e inherited.
- v6n c4 (purex, mk_bins8, reserve 8.64:149.04,1397.52:1512.00): v6n 991/1000, v6ne 996/1000. FINAL a4830a316287 =
  tree por_d29_kv3_pv_v6n_1080_c4_composed/plan_c.json (rt 6390b7bfa650 tools; 23 taps added, 10 in-core ft moved, 21+19 place_regions).
- unplaced (plan bins, v3 table, no reserve; n1): v3n closes 1182/1134 (cap 1200); v2ne 2 over, v6 3 over; v1n cut face full (16,267 pins).

## STATE 11-22 18:20 PST (newest; read this first; older blocks are history)
- K1 (first sealed v6n kit, admitted 11:5x) FAILED at global place 16:24: "explicit FT site outside core: ft48,3,0". Cause:
  type_split leaves explicit bit sites (ft_slots[].bit_sites_um) of crossing slots past the piece core edge. Fix w/fix_bit_sites.py
  IN OUT RECEIPT TYPES (re-sites only those cells; 61 on v6n/v6ne, 2,079 on the 14-type event, 0 unfixable); multi.sh runs it.
  ROW A as handed 09:3x is WITHDRAWN until re-issued from the fixed plan.
- T1 (tree/): fixed v6n plan installed by w/resite_rebind.sh tree w/gates/bs/plan_v6n_bs.json v6n6u1 v6n6v1: PLAN-GATE-PRE 0,
  G0 PASS 0 errors, strict bind 0 errors (161 / 57 / 2558), LATCHECK 0, R8CHECK = baseline. Gates w/gates/v6n6v1_*.
- K2 = new sealed kit of that plan, --goal route (COORD ruling: never finish), --rt 0890cc9405b7, started 18:14:
  spec intel2 ~/coord/autopilot/private_specs/FABLE-FIX-KV-PV-SINKSPREAD/qwen_kvsys_kv3_pv_v6n_1122181350/spec.json,
  log ~/tmp/ffkvpv/runitem_v6n_k2.log, unit runitem-kv3_pv_v6n, kit epyc8 .../private/FABLE-FIX-KV-PV-SINKSPREAD/
  kv3_pv_v6n_1122181338/gen/kv3_pv_v6n. Watcher ~/tmp/ffkvpv/watch_k2.sh (state watch_k2.state) posts stages + verdict.
  DO NOT TOUCH tree/ while K2 runs. At place: tap loads, then real tap rows (see RESUME block a.).
- T2 (tree2/): m7 bound clean but final G0 1 error (KITFIT-OUTLINE v1 ring 0.444 um past kit core at the cut) -> compose.py
  ringside rings now 8.64 off the cut. Chain m8 (w/chain_full3.sh m8 tree2, D29_RINGSIDE=w/d29/ringside_all_m8.json, log intel2
  ~/tmp/ffkvpv/chain_m8.log): compose ok (plan 9d9579bd19c9), PLAN-GATE-PRE 0, G0 PASS 0 errors, first bind R8 30+30 (expected),
  pad loop running. On CHAIN_FULL_DONE m8 with final G0 PASS: cd tree2; python3 -I w/package_d29.py m8 tree2
  w/handoff/D29_pv_14types_package.json; post ROWS-READY (row B contains v6n, so it supersedes row A).
- ot-tree-fork --no-manifest on main a087287d53. epyc10 <lane>/tree fork (old plan, unused) -> ot-delete. The epyc2 failed fetch
  /srv/opentallas-scratch2/claude/tree-cache/fa1d8c9906a306e4.fetch-3335283: ot-delete was issued 11:05, verify it is gone.
- KV-PLAN-R6 is sealing D28 (rh12 plan 44c3cbf51e50): when its seal tree is posted, re-compose rows on it (RESUME block d.).

## STATE 11-22 10:30 PST (newest; supersedes the T2 lines of the blocks below)
- T2 m5 bind after ONE pad regeneration got past R8 and failed on 2 real classes (gates/m5s1_bind):
  (a) 9 HARD_CORE_PARAM_WRAP "expected one bound instance u_cland_<bus>, found 0": type_split binds a landing ring in the piece of
      its bus WINDOW (bus_piece) but keeps the hard core in the piece its box is in. Fix: w/ringside.py (core vs band piece of a
      composed plan) -> env D29_RINGSIDE {type:{core:"w"|"e"}} -> compose.py ring loop re-sites those cores (also non-straddling)
      in the band's half. multi.sh now composes twice (pass 1 tag <tag>_p1 finds the list, pass 2 = real tag) unless D29_RINGSIDE
      is given. m5 list (9 rings, 8 types): w/d29/ringside_all_m7.json. v6n alone has none (K1 unaffected).
  (b) EMIT kv3_hgi_v6 "original rst_n_t35 D=rst_rl_381 != literal predecessor rst_rl_389": the event republished the reset
      collector tree of an UNTOUCHED type (report trees_republished_untouched) whose clock.landing_raw_branches name relays
      literally. Fix: w/remap_untouched.sh (landing_remap, OLD = base plan, --bound-rtl = tree's bind of the v6n plan, where
      hgi_v6 is unchanged); 29 names rewritten on m5 (gates/m5_remapu). multi.sh runs it at the end.
- Chain now: w/chain_full3.sh m7 tree2 <14 picks :r1> (composes IN tree2, D29_RINGSIDE given), client log intel2
  ~/tmp/ffkvpv/chain_m7.log, started 10:27. m6 = a failed launch (composer refuses an existing out dir), ignore; its dirs in
  tree2 (por_d29_all_m6_composed, plan_of_record.all_m6*) go to ot-delete later.
- The watcher only knows chain m5 (it posted the m5 stop). For m7: on CHAIN_FULL_DONE m7 run
  python3 -I w/package_d29.py m7 tree2 w/handoff/D29_pv_14types_package.json (run from tree2; it finds the composed dir in tree2) and post ROWS-READY row B.

## RESUME HERE (11-22 10:00 PST)
Unattended pieces that keep running without the lane:
 1. K1 = sealed kit kv3_pv_v6n (systemd user unit runitem-kv3_pv_v6n on intel2, goal finish). The whole fleet is over its load cap
    (every host 20-30 waiters), so each kit stage queues: expect hours per stage.
 2. T2 = chain_full2.sh m5 on tree2 (14-type event): bind m5s1 got past R8 after ONE pad-table regeneration and is emitting RTL;
    then LATCHECK, then the final G0 gate, then CHAIN_FULL_DONE.
 3. Watcher intel2 ~/tmp/ffkvpv/watch.sh (pid in watch.log / pgrep -f watch.sh; state ~/tmp/ffkvpv/watch.state): posts one lane
    line per K1 stage from kit_rtl on (with the place tap-load lines), the K1 verdict, and for T2 builds
    w/handoff/D29_pv_14types_package.json + posts ROWS-READY row B on CHAIN_FULL_DONE (or a STATUS line if the chain stops).
What the lane still owes (in order):
 a. K1 place: read the tap loads (watcher post; kit place log OT_CLOCK_TAPS; AUTO-GEOM tap_stuck), dump the placed registers
    (regs.tcl form, docker openroad on epyc8), taps.py bins -> tap_split -> real tap rows of kv3_pv_v6n; if a tap stays over the
    cap after the kit cap pass, fix the plan (bank / reserve) and relaunch (cancel only on setup < -300, flat repair, functional bug).
 b. K1 sign-off (DRC 0, TT >= -42, FF hold >= 0, LEC EQUIVALENT routed): report to COORD; standard export.
 c. v6ne (e piece, 171k cells) has no wave item: a second private-spec needs ITEM kv3_pv_v6ne (untested) = the A/B slot.
 d. Rebase rows A / B on the SEALED D28 plan when KV-PLAN-R6 posts its tree (fork, chain_full2.sh, package, ROWS-READY).
 e. epyc2 fork of the bound tree (hedge): if unused, ot-delete epyc2:/srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/tree.
 f. Cleanup via ot-delete when done: epyc8 <lane>/clone (broken sparse worktree), tree/.../por_d29_* trial dirs, por_before_*,
    aside*, tree2 after row B is merged; intel2 <lane>/clone2 can stay for pushes.

## STATE 11-22 09:45 PST (newest; read this first; the 08:55 block below still holds for T1 / K1 facts)
- ROW A HANDED 09:3x: post ROWS-READY to KV-PLAN-R6; package epyc8 w/handoff/D29_pv_v6n_package.json (sha 0123d278f8fc) made by
  w/package_d29.py v6n6 tree OUT. KV-PLAN-R6 must re-merge on the SEALED D28 plan: when it posts the D28 tree, fork it
  (ot-tree-fork), re-run w/chain_full2.sh (compose + G0 + bind + pad loop) on that base, re-issue the package.
- K1 kit (kv3_pv_v6n w piece): stages mkdir..kit_rtl_probe all rc 0 (src_manifest seal ok: main 315cc722d686, manifest 2c58b770003a);
  kit_rtl has been WAITING on the epyc8 load cap since 09:01 (load1 130-160 >= 115). Just wait; check with
  intel2 `bash ~/tmp/ffkvpv/st.sh` (one-screen status of K1 stages + T2 gates).
  Once <work>/gen/kv3_pv_v6n exists: ot-wait --durable --kit <kit dir> --host epyc8 --stage place --timeout 3000.
- Hedge: ot-tree-fork of the bound tree to epyc2 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/tree
  (intel2 ~/tmp/ffkvpv/fork_epyc2.log). Use it for a second private-spec (--host epyc2) ONLY if epyc8 stays blocked and epyc2 load
  is under its cap (153); otherwise ot-delete it later. A second kit of the same item = the allowed A/B slot.
- R3 (vport leaf rows) probe on the bound v6n pieces (w/r3_probe.sh tree kv3_pv_v6n,kv3_pv_v6ne v6n6u1): 0 anchors, 0 rows: nothing to add.
- T2 m5 (14 types, plan 04e1457da0fe): G0 PASS 0 errors, PLAN-GATE-PRE PASS, first bind R8 30 + 30; loop_pv iteration m5s1: tables
  regenerated (col law TRUNK_D 89 / FLAG_D 87 / C 35; vport_w 20, col 164 rebound), bind m5s1 running since 09:08 (slow host).
  When CHAIN_FULL_DONE: python3 -I w/package_d29.py m5 tree2 w/handoff/D29_pv_14types_package.json and post ROWS-READY row B.
  If the loop stops with non-R8 errors (PARAM_REGEN kv_pv_col_regen: TRUNK_D / FLAG_D changed) read gates/m5s<i>_bind/gate.out first.

## STATE 11-22 08:55 PST (newest; read this first)
*** v6n D29 FORM PROVEN AT PLAN + BIND LEVEL; SEALED KIT K1 RUNNING ***
T1 = epyc8 <lane>/tree (ot-tree-fork of the D28 work tree at dry5, tools rt 6390b7bfa650 + type_split cap patch = main d4f31de6bc6e):
- plan_of_record/plan_c.json 3cce60482b76, r8_ev 4ab587194002, pv_col_pads 6a05b8e990a5, pv_v_pads 7ab283f710d0, asbuilt 3ae20d52501c.
- gate w/gates/v6n6u1_g0: bind_fast precheck PASS, PLAN-GATE-PRE PASS findings=0 (base dry5 in its own root), G0 PASS 0 errors.
- gate w/gates/v6n6u1_bind: strict bind --all-gaps RC 0, BIND_ERRORS 0 (161 partitions, 57 types, 2558 crossings, 432,005 bits);
  LATCHECK rc 0 (only INTERNAL_PIPE_UNACKED warn); R8_RECHECK 91 / R8CHECK 32 unequal groups, 7 types = the D28 baseline exactly.
- DO NOT TOUCH tree/ (plan_of_record, bind_of_record, tools) while K1 runs: it is the kit's source of record.
KIT K1: spec intel2 ~/coord/autopilot/private_specs/FABLE-FIX-KV-PV-SINKSPREAD/qwen_kvsys_kv3_pv_v6n_1122085105/spec.json
  (private-spec qwen_kvsys kv3_pv_v6n --tree <tree> --plan <tree plan> --host epyc8 --goal finish; src_manifest seal; env = wave + 1;
   rt 0890cc9405b7 = the bind's generators, has OT_FF_EW_INSET_UM and both spec keys).
  run-item: systemd user unit runitem-kv3_pv_v6n.service on intel2, log ~/tmp/ffkvpv/runitem_v6n.log (KW_STAGE lines), result.json next to the spec.
  kit dir: epyc8 /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D27d3/private/FABLE-FIX-KV-PV-SINKSPREAD/kv3_pv_v6n_1122085056/gen/kv3_pv_v6n
  wait: ot-wait --durable --kit <kit dir> --host epyc8 --stage place|cts|grt|route|finish --timeout 3000 (re-run on exit 75).
  AT PLACE: read the tap loads (OT_CLOCK_TAPS lines in the place log, AUTO-GEOM tap_stuck), check config.mk OT_FF_EW_INSET_UM = E:25.92,
  dump registers of 3_place.odb (epyc7 regs/regs.tcl form) -> taps.py bins -> tap_split = the REAL tap rows of the v6n w piece.
  Cancel only if setup < -300, flat repair or a functional bug.
T2 = epyc8 <lane>/tree2: chain_full2.sh m5 (14 types, plan 04e1457da0fe) gate + first bind + loop_pv (pad regen) + final G0
  running since 08:38 (intel2 ~/tmp/ffkvpv/chain_m5.log; gates m5, m5s<i>, m5_final_g0).

## STATE 11-22 08:40 PST (newest; read this first)
T1 (tree, v6n only), plan 3cce60482b76 (= v6n6 fe2e828014f3 + 1 station on the two forwarded response-data rows, L51 / L219 back to 6):
- R8: w/rebind_pv.sh v6n6t1 v6n6u1 (PV_HEAD_KEPT=1 REBIND_NO_G0=1) = r8_refresh + pvx_regen.py (--min-pad 10 --e-min-pad 10
  --extra-first vport_w_pads_b5.json; copy in w/pv/) -> new inputs/pv_col_pads_ffkpv.json + pv_v_pads_ffkpv.json installed
  (88 V members bound +2/+3, pad -2/-3, landed same; V-D-H bad 0). The strict bind v6n6u1 got PAST R8 (SPLIT_REFERENCE_PREFILL
  ok, RTL being emitted at 08:30). Waiting for END: epyc8 w/gates/v6n6u1.out, v6n6u1_bind/gate.out (BIND_ERRORS, LATCHECK, BPC).
- Final G0 gate on this state running: w/gates/v6n6u1_g0 (intel2 ~/tmp/ffkvpv/g0_v6n6u1.log).
- IF BIND_ERRORS 0 and LATCHECK rc 0: KIT K1 (private-spec command in the 07:00 block; tree = <lane>/tree).
  The kit must run gen on rt >= 6390b7bfa650 (budgets.face_flop_ew_types inset): the tree tools are rt 6390b7bfa650 + type_split
  cap patch (d4f31de6bc6e on main); check the spec's tools_rt / rt_from line and config.mk has OT_FF_EW_INSET_UM = E:25.92.
T2 (tree2, 14 types): chain_full2.sh m5 (cap 11.9, v3n pvg2_p0 -8.64, v5 reserve fitted to 8.64-133.92 + 1389.96-1512) composing;
  then G0 gate + first bind + loop_pv.sh (pad regen loop, max 4) + final G0. intel2 ~/tmp/ffkvpv/chain_m5.log; gates m5, m5s<i>, m5_final_g0.
  fit at the cap (fit_cap.sh): v2 v2n v3n v4 v4n v5n fit with their auto reserve; v5 needed the smaller reserve.

## STATE 11-22 08:10 PST (newest; read this first)
T1 (tree, v6n only):
- v6n6 fe2e828014f3: G0 PASS 0 errors; PLAN-GATE-PRE PASS 0 findings after the r8 refresh WHEN the base is in its own root
  (w/pre_only.sh tree NAME; base copy epyc8 <lane>/base_d28_root/.../plan_of_record/plan_c.json = dry5 fcfa38bdb65b).
  The 2 R8STALE in gates/v6n6r_g0 were an artefact: a baseline inside the same tree resolves its R8 tables to the tree under test.
  gate_g0.sh now defaults to base_d28_root.
- r8 loop did NOT converge on v6n6: after the first refresh the same 30 R8_STALE stay: pv_v_pads_ffkpv.json members
  (id pvw_1__u_s0_b<k>.pe2[..]<-astk_EN..owner_7..response_data@67: table bound 71, bind 70). That pad table is an EXTRA table
  (authoritative, ids are not in the derivation, r8_refresh cannot rebind them; its generator is pvx_regen.py / r8/kv_pv_v_pads.py,
  not mine). Cause: the split lowered the depth of the forwarded lanes L51 / L219 (pv_N_6 o_astk_{E,W}..owner_response_data ->
  pv_N_5) from 6 to 5 ("legs cut at the piece boundary").
- FIX IN FLIGHT: restore that depth: w/addstation.sh v6n6s1 v6n6t tree <pieces> "<type:bus:1,...>" = restation.py ADD (+1 station
  on both rows, lanes priced +1) -> plan 3cce60482b76 installed in tree (08:01) -> rebind_loop (gates v6n6t1..; intel2
  ~/tmp/ffkvpv/add_v6n6t.log). If CLEAN: run w/pre_only.sh tree v6n6t + a full G0 (w/gate_g0.sh), then the KIT.
  If the same R8 errors repeat (loop exits 7): look at which lanes the pad members ride (member "lane") and restore more depth,
  or ask KV-PLAN-R6 for the pv_v pad regen recipe.
T2 (tree2, 14 types):
- m3 2fc442c938cc: first bind R8_STALE 30 + R8_UNCOVERED 30 only; G0 FAIL 3 errors: (1) landing_band_core [new] kv3_pv_v3n band
  i_vport_W_N_vo_d2 vs moved core pvg2_p0 (6.6 um) -> composer D29_CORE_TWEAK kv3_pv_v3n:pvg2_p0=-8.64,0 (default in multi.sh);
  (2,3) faces on two v5 / v5n cut ports "33 pins on 52 M6 tracks = 0.63 > 0.6": the cut spent the type N/S budget (15.5 x 0.9) on
  M4/M6 -> new spec key cut_pins_per_um_cap (ON MAIN d4f31de6bc6e; trees patched by w/patch_cap.py), multi.sh default 11.9.
- m4 (cap + tweak) compose FAILED: kv3_pv_v5 cut face full at 11.9/um with its 345 um reserve (63 pins short).
  RUNNING: w/fit_cap.sh (intel2 ~/tmp/ffkvpv/fit_cap.log; epyc8 w/d29/fit_<type>.out, fit_<type>.reserve): per capped type
  (v2 v2n v3n v4 v4n v5 v5n) compose alone with reserve trimming until the cut fits. THEN: write the fitted reserves into
  d29/rows_<t>_1080_r1.json spec_keys.cut_face_reserve_um and run chain_full.sh m5 tree2 <14 picks :r1> (plan job).
- A CLEAN strict bind of the 14-type event needs the three KV pad tables regenerated for many lanes (m3 PRE: pv_v_pads 370
  members / 16 lanes, pv_col_pads 18 lanes, vport_w_pads 2 lanes) = the die seal's job (as for row 1). Deliverable for the 14
  types = composed plan + G0 PASS + PLAN-GATE-PRE (only R8STALE) + first bind with R8 classes only.
Tools on main now: 6390b7bfa650 (inset, reserve, drop keys) and d4f31de6bc6e (cut_pins_per_um_cap).

## STATE 11-22 07:40 PST (newest; read this first)
FINAL CANDIDATES (D28 dry5 base, rt 6390b7bfa650 tools, lane reference, stack-free r1 bins, pure column swap):
- v6n-only: v6n6 = plan fe2e828014f3 (tree por_d29_all_v6n6_composed; installed as tree plan_of_record).
  gate v6n6: precheck PASS, PLAN-GATE-PRE 2 x R8STALE only, G0 PASS 0 errors, bind#1 30 x R8_STALE (fail fast, as expected).
  rebind v6n6r RUNNING since 07:35 PST (r8_refresh OK: vport_w_pads 8, pv_col_pads 54 rebound; r8 557793f1f300):
  intel2 ~/tmp/ffkvpv/chain_v6n6r.log, epyc8 w/gates/v6n6r{.out,_g0,_bind}. bind#1 output kept in gates/v6n6_bind/bind_of_record.
- 14 types: m3 = plan 2fc442c938cc (tree por_d29_all_m3_composed; installed in tree2). gate m3: PLAN-GATE-PRE 4 x R8STALE only,
  bind#1 R8_STALE 30 + R8_UNCOVERED 30 (no crash: the lane reference works for all 14). rebind m3r queued behind the m3 G0
  (intel2 chain_m3r.log; epyc8 w/gates/m3r*). Model on newest-placement bins: 23/28 pieces 0 over; v12e, v7e inherited;
  v2ne 1376/1200 (plan bins), v5ne 1145/1000, v6n 1136/1000 (1 tap each; stale-census model, the piece place decides).
- restation on m3: 33 rows re-spaced, +4 stations, 3 lanes priced (+4 cycles); on v6n6: 2 rows, 0 added.
- v1n: cut face still full on the pure swap (129 pins short; margin 8.64 -> 2.16 does not help: fragmentation by pinned windows).
  Stays HELD unsplit until PV-R7's shared-crossing row (posted 11-21 20:24 to KV-PLAN-R6) lands.
WHEN v6n6r ENDS:
 - 0 errors + LATCHECK rc 0 -> KIT K1 now (see the 07:00 block for the command; tree = .../fable-fix-kv-pv-sinkspread/tree).
   bind RTL then exists: T2 path (R3 rows) can also start: r3chain.sh r3 m3r m3r3 <pieces> with FF_TREE=tree2 (plan job).
 - errors -> read gates/v6n6r_bind/gate.out + errdiff (w/r3/errdiff.py base_bind_report new_bind_report).
KIT READING: at place read OT_CLOCK_TAPS lines (run_place log) + AUTO-GEOM tap_stuck; then taps.py bins of 3_place.odb -> tap_split
 -> real tap rows for v6n (and post them); the D23H-based bins are only a seed.

## STATE 11-22 07:00 PST (newest; read this first)
- Lane reference DONE: epyc8 w/ref_base_d28.json (2404 lanes, 428,278 bits, payload sha 05b9c281af98 = same payload as PV-R7 D27 ref).
- G0 PASS 0 errors on the v6n-only recomposition v6n5 c359ae8d0050 (window + ring fixes, restation): gates/v6n5_g0. PLAN-GATE-PRE there
  showed 153 findings only because the baseline pointed at the LIVE D28 work tree plan, which moved to dry6 (ef3219e1ae74 06:29);
  gate_g0.sh now uses my pinned dry5 copy tree/.../plan_of_record.base_d28/plan_c.json. Expect 2 R8STALE only before the r8 refresh.
- D23H census is STALE (posted 06:4x): current netlists have ~1.5x the registers (segmented delay lines _sg0..2, hop latches u_fl_*).
  -> place_regions stack rows DROPPED from the form. Bins variant r1 (w/bins_r1.sh): newest placement per type (regs/regs_<t>_new.txt
  from FIX-SYNC geom dumps: D26 pv v1 v3n v6 v8, D25e3 v12 v5n, D25e v2; D23H only for v4 v4n v5 v6n v7; v2n none = plan bins),
  no stacks, per-core registers carried with their core. Real tap rows must come from each piece's own first place.
- RUNNING: final_compose.sh (intel2 ~/tmp/ffkvpv/final_compose.log): multi.sh v6n6 kv3_pv_v6n:r1 and multi.sh m3 <14 types>:r1 with
  FF_LANEREF. Then chain_bind.sh v6n6 tree (log chain_v6n6.log) and chain_bind.sh m3 tree2 (log chain_m3.log) start by themselves
  (plan jobs, already admitted, waiting for plan_final.json): gates epyc8 w/gates/{v6n6,m3}{.out,_g0,_bind}.
- AFTER the first binds (expect R8_STALE / R8_UNCOVERED only): T1 (tree, v6n-only): w/rebind.sh v6n6 v6n6r kv3_pv_v6n,kv3_pv_v6ne
  (station fix + ONE r8_refresh + gate) -> clean bind -> kit K1. T2 (tree2, 14 types): w/r3chain.sh r3 m3 m3r3 <pieces> -> banks ->
  rebind (full PV-R7 row-1 chain) -> K2 only if K1 fails on leaf first hops. Run them as plan jobs:
  ot-run --priority plan --plan-job bind --mem 64 --threads 8 --hosts epyc8 --dir <lane root> -- [env FF_TREE=<lane>/tree2] bash w/<script> ...
- KIT (after a strict bind with 0 errors in the tree): on intel2
  python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/autopilot/kit_wave.py private-spec qwen_kvsys kv3_pv_v6n --tree <tree>
    --plan <tree>/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json --lane FABLE-FIX-KV-PV-SINKSPREAD --host epyc8 --goal finish
  (dry probe 06:45: the only refusal was the missing strict bind) then nohup ... kit_wave.py run-item <spec.json>; ot-wait --durable.

## STATE 11-22 06:25 PST (supersedes any "Running / Next" below)
Candidates so far (all on D28 base dry5, tools rt 6390b7bfa650, pure column swap):
- all-14-types ONE event m1 = plan 54ac7f32109f (tree por_d29_all_m1_composed): model 26/28 pieces 0 over cap; v12e, v7e inherited.
  Picks: kv3_pv:q1 v1:q1 v12:q1 v2:q1 v2n:s2 v3n:n2 v4:q1 v4n:q1 v5:q1 v5n:q1 v6:s2 v6n:c4 v7:q1 v8:q1 (w/multi.sh NAME picks...).
- v6n-only c4 = a4830a316287. Its gate v6n_c4: PLAN-GATE-PRE 3 findings (1 in-core internal station -> fix_st_in_core.py now
  covers internal_stations; 2 R8STALE -> r8_refresh after a bind), G0 13 errors, strict bind CRASHED:
  "native stations pv_N_4.o_vport_W_N_vo: expected one outgoing lane".
What that taught (each one fixed or in flight):
 a. BIND CRASH = no split lane reference. A split bind needs spec lane_reference = split_lane_reference_export.py of the UNSPLIT
    base bind (PV-R7 ref_base.json is D27: not usable). Export from D28 base RUNNING: w/refexp.sh in tree2 (plan job), client log
    intel2 ~/tmp/ffkvpv/refexp.log, out epyc8 w/refbind + w/ref_base_d28.json (~35 min from 06:13). Then compose with
    FF_LANEREF=/srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/w/ref_base_d28.json (multi.sh passes it through).
    refexp.sh moves tree2 plan_of_record.base_d28 -> plan_of_record and back at the end: check it was moved back.
 b. G0 errors: abutment/faces (a straddling N/S window moved onto a neighbour window: the composer compared face labels only)
    and landing_band_core (re-sited ring cl_i_vport_W_N_vo on band ft3_i). Both fixed in compose.py (06:1x). m2 / v6n5 =
    recomposition with those fixes (no restation, no laneref): only to re-check G0 (w/g0only.sh TAG NAME).
 c. G0C hop > 405 on 33 rows of the 14 types (j-core rows fault_d1/d3, y_valid, cut legs; v12e o_vport_E_N_vqN): w/restation.py
    (core-clear path, equal arc length, STEP 400, +stations priced on lane fixed_cycles, then gen.py latency --inplace).
    Now a step of multi.sh. Test on m1: 33 rows fixed, few stations added.
 d. R-REACH-1 START fan WARNs exist on the D28 row-1 form (v3) too: not fixed here (reach_rules.py fix --rules 1,4 is the tool).
 e. After a bind: PV-R7 row-1 chain = r3 rows from bound RTL -> bind -> leaf banks + reprice + latency -> bind -> r8_refresh -> bind.
    My type-generic copies: w/r3/*.py, w/r3chain.sh (r3 | banks), w/rebind.sh (station fix + r8_refresh + gate).
Scripts added: w/multi.sh (MULTI_REFINISH=1 re-runs the finish steps on an existing composed dir), w/g0only.sh, w/restation.py,
 w/hopfix.py (superseded by restation), w/refexp.sh, w/rebind.sh, w/r3chain.sh, w/repin.sh RT [tree2].
ot-run notes: --dir must be the lane root when a job names paths in two trees; binds / G0 / export go with
 --priority plan --plan-job bind|g0 (jumps the host load cap); other jobs wait while epyc8 load1 > 115.
NEXT:
 1. refexp done -> multi.sh m3 (14 types) and multi.sh v6n6 kv3_pv_v6n:c4 with FF_LANEREF -> g0only / bind_chain:
    T1 = tree (v6n-only), T2 = tree2 (all types; FF_TREE=tree2 FF_O=<tree composed dir>, ot-run --dir lane root).
 2. bind result -> r3chain r3 -> banks -> rebind (r8) -> clean bind + LATCHECK -> kit (private-spec ... --goal finish; run-item).
 3. Hand rows to KV-PLAN-R6 (composer recipe + composed dir + receipts).

## (older) Running (11-22 05:4x PST)
- bind_chain v6n_c4 (G0 gate + strict bind): intel2 ~/tmp/ffkvpv/bind_v6n_c4.log, epyc8 w/gates/v6n_c4{.out,_g0,_bind}; started 05:36, ~1.2 h.
- all_p2.sh q1 p1 with D29_SWAPMODE=purex + mk_bins8 (10 placed types): intel2 ~/tmp/ffkvpv/all_q1.log, epyc8 w/d29/run_*_q1.out.
- pass4.sh (v2n v3n v6 v1n: n2 = plan bins + auto reserve, s2 = sibling-register estimate; purex): intel2 ~/tmp/ffkvpv/pass4.log.
- ot-tree-fork -> epyc8 tree2 (for the all-types bind), log epyc8 tmp/fork2.log; then w/repin.sh needs a tree2 variant.

## Next
- bind c4 OK -> on intel2: python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/autopilot/kit_wave.py private-spec qwen_kvsys
  kv3_pv_v6n --tree <epyc8 tree> --plan <tree>/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json --lane FABLE-FIX-KV-PV-SINKSPREAD
  --host epyc8 --goal finish [--rt 6390b7bfa650]; then nohup ... kit_wave.py run-item <spec.json> (re-execs itself under a systemd
  user unit); ot-wait --durable --kit <kit> --stage place|cts|grt|route|finish. Read OT_CLOCK_TAPS + AUTO-GEOM tap_stuck at place.
- pick final variant per type from q1 / n2 / s2 -> one multi-type event (compose.py D29_CFG json) -> finish -> bind in tree2.
- Hand D29 rows to KV-PLAN-R6 (composer recipe + composed plan dir + per-type reserve / place_regions / tap rows).
- compose.py still monkey-patches type_split.relay_tx_sites (rstart pin at CUT-86.4, from the v3 recipe); a spec key would remove it.
- Cleanup later (ot-delete): epyc8 clone/ (broken sparse worktree), tree por_d29_*_{a,b,c,c2,c3,p1,p2,n1}_*, por_before_*, aside/.
