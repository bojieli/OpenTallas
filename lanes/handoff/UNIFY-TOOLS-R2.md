# UNIFY-TOOLS-R2 handoff (2026-11-20 ~19:10 UTC)

## Done (main)
- (3) `tools/die_plan/class_window_solve.py --column` - whole-column window solver, main 5176daec13e, tests 5/5. Not yet run on S81 leaf data.
- (1) `tools/die_plan/class_merge.py` - class -> one type, children tieable spares + use straps, edges/dst_index re-indexed by site; main f64c1e8092c, tests 7/7.
- (2) `landing_role_strap` (origin/relay role as strap `strap_ca_relay`; clock_landings, count_align_bind, landing_tie_children, clock_landing_verify, landing_local_resets, schema), main 219c38c9c28, tests green.

## Private proofs (epyc9 /srv/opentallas-scratch2/claude/unify-tools-r2-work)
- Base: QC A4+CBX plan `/srv/opentallas-scratch2/claude/qc-plan-r3-n41p/n46/v1_merge/plan_n46cbxm_r4_provider27.json` + `sidecar_n46cbxm_r4.json` (strict 0 at cbx_r4_strict), runtime 22a689dfc092, scripts `bind_core.sh` / `bind_core_rs.sh` (overlay/ = my tools on top of rt).
- `slectl/` (sle_ctl 7->1): strict bind 5 errors - sle_ctl 12 inst -> 5 variants, plus slw_hc3 x2 and slw_su_c split (side effect).
- `rs/bind_r2` (slectl + slw_stm v1 + slw_fw v1 role-strap merges): 10 errors; role split and landing EMIT gone; remaining = per-instance pads.

## Blocker and COORD ruling (b)
Splits are per-instance lane/R8 pads inside the merged partition (sle_ctl x_su_l0_i E 1/3 vs W 29/30; slw_fw x_ctl_i/x_ctl_p1_i/x_fe_p1_i;
slw_stm core vm_waddr/vm_wdata; one dv-variant glue $or name on sle_ctl E1-3/E5/W5). COORD: take (b) - hoist the per-instance pad out of the
partition (parent/ft stations), internal pad = class minimum.

## Next (owned by this lane)
1. `pad_hoist` step (class_merge.py or sibling) rewriting plan latency/ft rows; tests.
2. Prove QC sle_ctl strict 0 privately (12 inst -> 1 module), then slw_fw, slw_stm incl. slw_hc3/su_c side effect; rows -> QC-PLAN-R5 (V1).
3. Column solver on S81 class s81.leaf_nogrowth_j4e; rows -> S81-DIE-R4 (J6).
4. netlist_inherit summary/prove once a merged kit is synthesized.

Clones: epyc7 /srv/opentallas-scratch2/claude/unify-tools-r2 (work), /srv/opentallas-scratch2/claude/unify-tools-r2-push (push, cone tools+rtl+physical).
