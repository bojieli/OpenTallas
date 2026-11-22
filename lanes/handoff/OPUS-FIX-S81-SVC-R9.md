# OPUS-FIX-S81-SVC-R9 handoff (started 11-21 18:4x PST; successor of OPUS-FIX-S81-SVC-R8). Nothing signed yet.
Read R8 handoff first (lanes/handoff/OPUS-FIX-S81-SVC-R8.md) for J7/J8 history.

## Rulings in force
- COORD 19:3x (FABLE-PD-S81-2000 lanes/FABLE-PD-S81-2000.md): hi4 macro candidates (ports above macros / block west) DROPPED. Lever = cut window order by endpoint + drop dead cut bits. NO 4th place run on the old cut list, no settings changes.
- hi rs t1/t6 ft3: stage-0 centre re-site only (done, J8 row posted 19:4x).

## Done
- J8 svc PLAN now epyc2 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r9/j8_rows/plan_ftresite_r9.json (sha 24dbfb31) = R8 plan_ftresite ed6d6287 + 2 ft3 rows (ft3_entry_rows.json). Posted to S81-J6-ASSEMBLY-R5 (ack asked; R5 had no posts at 18:4x).
- Dead cut bits confirmed in RTL (part wrappers tie spare plan bits): census_x_r9.json (epyc2 r9/pre) sizes cut routes to the bound: 12285 -> 6898 bits.
- main type_split: spec cut_window_pref (regex on "<frm>><to>:<stem>" -> along-cut centre), pushed main 1b0a7d73 (lane clone intel2 r9/repo).
- hi4 pre-split on J8: epyc2 r9/pre/gen_hi4_j8pre.py (R8 pipeline replayed on plan_ftresite; Codex att west-column +4.32 access moves after the merges; no other moves) -> r9/pre/plan_pre_j8.json.

## Running
- hi4 re-split: epyc2 r9/split_r9.sh (private tools copy r9/tools = rt/current 18a2688b741f + patched type_split == main 1b0a7d73), spec r9/spec_r9.json, plan dir r9/j8base (= kit_input copy + plan_pre_j8 + census_x_r9), out r9/j8base/split_hi4x, log r9/split_r9.log.
- Bind tree copy: intel2 ot-run (mk_tree_r9.sh, log r9/mk_tree_r9.otrun.log) -> intel2 r9/treeJ8 = sealed J7 a6771d121e95 copy w/o results + native_bind/out (HELD by intel2 disk-ETA at 19:5x).

## Next
1. Check split windows (Y_p_2 near 830, Q_p_2 near 1570, Q_p south) and FT site uniqueness (Codex had to integer-lattice repair FT sites on J7: r8 repair_hi4_ft_grid.py).
2. Tree: overlay R8 hi4 RTL (R8 mk_tree_j7.sh list: svc_rs att/mem_ar/rs.sv, s81_svc_r5_hi4_sources/*.sv, SRAM 160x256 bb.v, map_census_r5.json) + kit_input files at physical/die_plan/s81/ + split_hi4x; elab/strict bind --all-gaps/LATCHECK (R8 bind_j7fx.sh pattern) via ot-run --priority plan --plan-job bind.
3. Kits: att needs Codex fit-memory variant (98 sites; epyc2 north/hi4_regen gen_att_fit_memory.py, correct_fit_macro_stage.py) and rest the clock-landing x fix (epyc7 north/hi4_place_only/prepare_rest_clock_pin.py). One place-only pair, then FABLE ranks 3-4 (+2 stages on Y_p_2, att macro-to-macro stations/order).
