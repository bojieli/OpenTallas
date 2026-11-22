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

## Tool change (in clone, to push)
- face_flops.tcl OT_FF_EW_INSET_UM; gen_phys budgets.face_flop_ew_types[].inset_um; schema; type_split spec
  cut_face_bank_inset_um + cut_face_reserve_um; tests. Patch script: w/patch_main.py.

## Next
- push tools -> compose v6n on the D28 base in tree/ with spec keys -> tap report + plan_gate_pre -> strict bind ->
  private-spec kit (v6n or v6ne) -> sign-off. In parallel: model for the other 14 types.
