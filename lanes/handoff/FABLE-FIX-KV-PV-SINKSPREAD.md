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
