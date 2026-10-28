DIE-HBM/KITS 10-27 -- fixes for the 15 generator-blocked C18 types.  These are proposals and nothing is committed.
Generator: claude/hbm-streets3-kits-1027@6750f867b9 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py (unchanged).
The generator finds a recipe this way: --recipe-key, then recipes_b2.json[module], then the view's recipe_keys[0]. It reads
recipes_b2.json first, then harden/recipes_split.json, recipes_other.json and recipes.json, keeping entries that have "files".
The wrapper is --wrapper, otherwise wrappers/<module>.sv.

Trial runs: all 6 FIXED types generated rc=0 into trial/ (tag _c18fix). They used views_c18.json and the slices in
hbm-streets3-1027/kits/slices. No synthesis or P&R was run. Preflight and LEC have not been run (UNCHECKED).

1. canon_wrappers/  (pgslice type-reduction families, NO_RECIPE)
   lane_exp__canon_7cd691, lanes__canon_cf1e77, lanes_plain__canon_663526
   mk_canon_wrappers.py renames the proven sw2.py member wrappers (wrappers/<member>.sv, a02e858e91):
   g_bank_<n>_/g_lane_<n>_ become g_*_k<i>_, and the lane-id strap constants become the plan pin lane_lane_id
   (lane_exp: 11 bits; lanes4: id = {lane_lane_id[8:0], 2'd k}).  The script sorts the port-declaration and assign
   order (these differ between members, and binding is by name).  It REFUSES the family unless every member's text
   ends up identical; all 3 families passed.  Ports == C19 canon pin table: 0 diff (CHECKED).
   canon_wrappers_report.json lists each member's lane_lane_id value. The parent must tie these.
   run_canon_kit.py WT FIXES <the usual gen args> passes --recipe-key <canon> with recipe = member recipe. It checks
   that every member of the functional_type has the same files/top/params/defines/macros, and stops with
   ALIAS_NOT_EXACT if one differs.  It also passes --wrapper <canon>.sv.  For lane_exp canon it adds
   synth_memory_max_bits 15616 and the family placement, because the generator's lane_exp regex does not match
   the canon name.
2. B2n_inputs/exp_lane.json  (lane_exp0 MACRO_PLACEMENT, and lane_exp canon)
   This is git HEAD physical/die_plan/hbm_arch/B2n_inputs/exp_lane.json (6 x ot_sram_1r1w_128x256_m1_r2c2; it matches the
   C19 die_plan note).  The generator looks for <plan dir>/../B2n_inputs/exp_lane.json; that file is absent because the
   plan was copied out of the repo.  To use it, do ONE of these:
   - copy it to <plan parent>/B2n_inputs/ (C19: /srv/opentallas-scratch2/claude/hbm-streets3-1027/B2n_inputs/), or
   - pass --macro-placement FIXES/B2n_inputs/exp_lane.json --macro-inst-fmt 'u_core.u_bank.u_data.g_read[{k}].u_m'.
3. q2_oneclk_wrappers/  (q2_hard_v8g__reduce / __ring_ag PORT_MISMATCH)
   The C18/C19 "__oneclk" pin table has a single clk; the sw2.py wrappers still have clk_reduce[32:0] / clk_ring[16:0].
   The patched wrapper drives every one of those bits from clk.  This is the same wiring as Codex's qualified adapter
   results/clock/q3_vmface_1026/*_q2_*__q3sync__oneclk.sv (PASS_CLOCK_ADAPTER: the bits are native aliases).
   The data wiring is byte-identical. Use it with --wrapper, or put it into wrappers/ on the kits branch.
   Note: the reduce face shell reports dropped=33 (UNCHECKED whether this matches earlier kits).
4. Not fixed here (owned by other lanes). DIE-HBM re-generates these when the owner's recipe or driver lands.
   - HC bank128_pair (x2 tables), bank128_pair_first, subtree32: there is no recipe in any recipe table.  Codex's
     driver tools/hbm_b2/hc128_native_kit.py (already in HEAD; needs --masters <masters_drst>) gives them recipes,
     source overrides and a profile.  It is not run by mk_c18.py.
   - tailx_sk_step0: a probe with the old recipe tail0_sk_step0 fails with PORT_MISMATCH (sk_en_i is not a port of
     ot_hdc_sk_step0), because the plan uses the CE form.  Codex has it: codex/hbm-sk-ce-0835 tools/hbm_b2/sk_ce_kit.py
     (kitgen PASS4/4).
   - idx_score_quarter tailx v36d446 (=tail1 table) / v3fcb6a (=tail0 table): a probe with the tail1/tail0 recipe fails
     with PORT_MISMATCH (clk_tail is not a port of ot_hbm_idx_tail_native).  Needs the Codex native quarter profile
     (codex/hbm-quarter-reset-1027 recipes_delivered.json score_tail; codex/hbm-quarter-profile-1452).
   - q3_edge_core: Codex builder physical/die_plan/hbm/q3sync_kits/build_kit.py --core edge (in HEAD).  It needs a
     q3sync profile dir.
   - ot_hnx_fused_tnode: the RTL is in HEAD (rtl/hbm_next/fused/ot_hnx_fused_tree.sv).  With default parameters, the
     plan pins equal the RTL ports exactly (CHECKED).  The recipe still needs the owner to choose the file closure
     and DELIVERED_RESET.
   - hnx_fused_lane: this module is not in the kits HEAD RTL.  It exists only on origin/claude/hbm-mu-quad-8-1027
     (HBM-MU lane), so the recipe comes with that merge.
