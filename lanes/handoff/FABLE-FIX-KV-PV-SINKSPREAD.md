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

## Results
- p1 (PV-R7 lever set on D28 base): under cap kv3_pv v1 v2 v4 v8; over v6ne 1128, v4ne 1328/1200, v5e 2122/1200, v5ne 2209, v12e 1789, v7e 1859.
- v12e / v7e residual = INHERITED: unsplit D28 base v7 clk_t9 (1805, 21.6) carries the same 1858 (base clock.sink_sites_um rows of the
  hard S-face ft rings, 921 x 4.923). Asked TAP-GRID-R5. G0 tap_sink_cap is a WARN; the kit cap pass (clock_taps.tcl) re-homes.
- v6n variant c3 (reserve 8.64:149.04,1397.52:1512.00, stacks off keep-outs): v6n 990/1000, v6ne 1000/1000, 0 over, radius <= 283.
  Final candidate plan sha 20b983e80b9c = tree por_d29_kv3_pv_v6n_1080_c3_composed/plan_c.json (19 taps added, 10 in-core ft moved,
  21 + 19 place_regions). Thin band i_vport_E_N_vo_d3: ring_place=ff kept on all 16 ff bands (INFO per FIX-SYNC 04:17).

## Running
- bind_chain v6n_c3: ot-run client intel2 log ~/tmp/ffkvpv/bind_v6n_c3.log, out epyc8 w/gates/v6n_c3{.out,_g0,_bind} (~1.2 h).
- all_p2 p2 (auto reserve, 10 types): intel2 ~/tmp/ffkvpv/all_p2.log, results epyc8 w/d29/run_*_p2.out.

## Next
- bind OK -> kit_wave private-spec qwen_kvsys kv3_pv_v6n --tree <tree> --plan <plan> --lane FABLE-FIX-KV-PV-SINKSPREAD --goal finish
  (sealed default) -> run-item under systemd-run + ot-wait --durable; read the tap loads at place (OT_CLOCK_TAPS, AUTO-GEOM tap_stuck).
- p2 results -> residual types; v1n v2n v3n v6 have no D23H place (use sibling regs: v6<-v6n, v2n<-v2, v1n<-v1, v3n<-?).
- Hand D29 rows to KV-PLAN-R6: per type spec keys (reserve spans, inset), place_regions rows, tap rows, in-core ft moves.
