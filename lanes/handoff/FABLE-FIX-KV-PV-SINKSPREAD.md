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

## Running (11-22 05:4x PST)
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
