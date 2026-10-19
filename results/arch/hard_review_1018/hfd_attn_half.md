# Hard review: hfd_attn_half_lo / hfd_attn_half_hi (HBM attention halves) -- 10-18

## Verdict: NOT on the current HBM die (d4g GEN0/GEN1/GEN2). Retired lineage; no further work.

Evidence:
- d4g GEN0 die netlist `origin/claude/hd4g-1017:results/arch/hbm_die_d4g/gen0/die.v.gz`: 0 instances of `hfd_attn_half*` / `hfd_attn_tile*`. Attention is 16 x `ot_hbm_accel_smh_attn` (`sm_SW0..`, one per SM, 4 per quadrant). `gen0/view_bindings.json` names only `ot_hbm_accel_smh_attn`.
- GEN1 layers (`gen1/layers/l1_host_xload_stack.json`, `l2_su_sfu.json`, `l3_vm_hc_coll.json`) and `gen1_bindings_plan.json`: no attention-half references.
- GEN2 smoke (`origin/claude/hd4g-gen2b-1018:results/arch/hbm_die_d4g/gen2/smoke/port_bind.log`): DIE_PORT_BIND PASS, 97 masters / 1198 instances, no `hfd_attn*` master.
- Die element table (`/home/ubuntu/claude-takeover-20261007/gaps/die_element_table.md`, 10-18 03:29, HBM d4g section): no `hfd_attn_half` row. HBM attention rows are `ot_hbm_accel_smh_attn` (cluster, RTL-only, no owner) with children smh_xs, smh_fc_t/b/xl/xr, smh_tct (CLOSED, native owed), smh_tcl_gu and smh_bdc (CLOSED+native), and `ot_hbm_smh_rp4_one` (gate FAIL 16 h ago, no owner).
- The halves belong to the r25g/r25gq die (`physical/hbm_accel_die_views/index_r25g.json`, `results/arch/r25gq_refloorplan_20261010/floorplan.json`). RTL `rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv` and `physical/hbm_attn_tile_r/half{,_ps,_v2}` were last touched 10-12 (f55fbf5e1: "v12 half routes failed on one 1.78 mm clock root (spine 2.55 ns) and corner glue (hi -8.35 ns)").

## What replaced them
`ot_hbm_accel_smh_attn` (`rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv`, H-SM-ATT r2, 10-15, owner-adopted option B). It runs attention on the SM engines: QK goes through the closed tct / tcl halves, PV through `ot_hbm_sm_pv_merge`, and a KV converter plus probability store sit in the SM front. It uses a static calendar and has no credits. This is the "co-locate vector with matrix, small replicated slices" principle. It removes the separate attention tile and its 1,891-bit seam.

## Short post-mortem (historical only)
The structural cause, from the explorer story `~/.local/share/fleet-viz/stories/tier2.json` card `hbm-attn-split` and the commit log:
- The monolithic `hfd_attn_tile` was a central hub. Its 124 um middle channel carried about 2x the bits it had tracks for. Widening the channel moved the failure into 1.5-3.6 um slivers between pin banks.
- Cutting the tile into lo/hi halves kept the same hub topology and added a 1,891-bit registered seam. v8 to v12 then chased symptoms: the merge root was moved, an equal-delay clock spine was pre-placed, and the root/merge/ks glue was split into leaves.
- The v12 halves still failed on one clock root across 1.78 mm (2.55 ns spine) and on corner glue (hi -8.35 ns). These are the "one tree across mm" and "star hub" failures that the later rules (landed-regions-standard-1018, accelerator-design-principles-1016) forbid.
- Root cause: the partition was wrong. Attention was a separate wide hub tile, not distributed onto the SMs that feed it.
- The 48/41 route attempts were patches around that cut, not convergent iterations. I did not build a per-route table: the element is off-die and its data is pre-d4g.

## Rating
- On current die: NO.
- Verdict: ABANDON. This already happened in practice: superseded on 10-15 by `ot_hbm_accel_smh_attn`.
- Risk to release: LOW for this element.
- Live follow-up belongs to the replacement. `ot_hbm_accel_smh_attn` is an RTL-only cluster with no owner on d4g. `ot_hbm_smh_rp4_one` is gate FAIL with no owner. Five children owe native views. That cluster needs an owner and a hardening route. Review that cluster, not these halves.
- Redesign cost: 0 for the halves. The replacement was owner-adopted on 10-15 (option B), so it is already in the plan.
