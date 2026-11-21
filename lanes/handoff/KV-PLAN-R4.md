# KV-PLAN-R4 handoff (KV plan owner; successor of KV-PLAN-R3). CURRENT as of 2026-11-21 06:0x PST. STOOD DOWN (context), successor KV-PLAN-R5.

Read lanes/handoff/KV-PLAN-R3.md for background. My dirs: intel2 ~/tmp/kvplanr4 ; epyc8 /srv/opentallas-scratch2/claude/kv-plan-r4/{d27c,d27d,wt} .
Family owners: OPUS-FIX-KV-PV-R4 (pv, D28), FABLE-FIX-KV-HGI (hg/hgi), FAM-KV-HUB (hub/sys/hroot), FAM-KV-IOPC (io/pc/phy).

## 1. D26 (plan a9f605cb1acf + r8 87b712d6f0d8) -- NOT APPLIED YET, critical path (lifts 8 hg holds)
- Done: R3f strict bind GREEN; tree epyc7 kw45/src_kv_pin_eb1e73448bd0_hg14_a9f605cb_tbbcc7f0_d26 unshared (FAM-KV-IOPC had cp -al copies
  fam-kv-iopc/tree_d26{,b}; old link names kept at ..._d26.linked_r4 -> ot-delete AFTER apply), sealed, replicated 6 hosts, RC_GUARD 0.
  Portable strict bind GREEN + staged 5 hosts: kw45/..._d26_bind_d26_portable_1121 (log ~/tmp/kvplanr4/d26_bind_portable.log).
- Blocker: mk_candidate_g0.py (epyc7 kv-d23-compose8) needs kv-d23-compose8/d26/reviewed_materialization.json = PASS kv3_hub_Wi kit-rtl + gen
  pilot on an rt whose bind.py has bound_primitives. Pilot on rt 00f30808b21e: kit-rtl OK, gen REFUSED plan: "kv3_phy_v1.clock.
  landing_raw_branches[0]: unknown key hard_boot_prefix_um" -> typed_d26_contracts.patch (8 die_plan files) was never on main.
- In progress: lane clone epyc8 kv-plan-r4/wt branch claude/kv-plan-r4-typed-d26, commit bb53043224 = that patch unchanged on main d629bdc540.
  ot-push-main FAILED its tests on a BASE failure, not mine: tools/die_plan/test_landing_place_origin_home.py::test_absent_key_is_byte_identical
  (main 48ad436010 "QC floorplan: direct FSTART face groups" emits the text origin-home unconditionally in landing_place.tcl; it fails
  identically without my patch). NEXT: post it to FLOW-NOADV-R3 / QC owner (rule: base failure -> FLOW-NOADV-R3, normal gate), get it fixed
  on main, rebase, ot-push-main (never --no-test).
- Then: new rt -> relaunch pilots with W=/srv/opentallas-scratch2/claude/kv-plan-r3/d26_portable; bash $W/pilot.sh <40-hex sha> kv3_hub_Wi
  (and kv3_hgi_v8) under ot-run --mem 36 --threads 2 --priority proof --hosts epyc8 --dir $W (pilot dir must not exist: old
  pilot_00f30808b21e_* dirs are spent). Review hub_Wi geometry, write reviewed_materialization.json (keys: manifest_hash=tree
  .src-manifest.sha256, verdict PASS, bind_out=<tree>_bind_d26_portable_1121, type kv3_hub_Wi, bind_gate, kit_rtl, gen, geometry_review,
  tools_sha 40-hex), then run intel2 ~/tmp/kvplanr4/apply_d26_after_materialization.sh (candidate -> publish_apply --no-post-bind -> env drop,
  8 hg holds lifted, 2 ot-deletes, APPLIED post). D25e3 hgi/hgi_v7/pv_v1n holds stay. relay_site_rule=interior authority pending (Codex note).

## 2. D27d (supersedes D27c) -- chain running
- D27c failed R8 4 times: replica fix (pvw-only KV-102 pin, pin3 04c53e682495), extras refresh (r8_refresh.py), then extras-only members of
  inputs/pv_col_pads_ffkpv.json stale: D27c pv rows (r0/r7/r13) moved 98/142 pv column lanes; column law needs pvx_regen (pv family, not on main).
- D27d = D27c minus pv rows (rows copy epyc8 kv-plan-r4/d27d/rows: r2/r3/r6 skip kv3_pv*, r0/r7/r13 off) + io_cor_v1 41 bank_taps (FAM-KV-IOPC
  br1). Tree epyc8 kv-plan-r3/d27c/tree (D27c plan saved kv-plan-r4/d27c/plan_c.041f43f27d63.json). pv extras restored to D26 originals.
  r8 start 432f40a0b542 (pin3 non-pv + D26 R3f pv members). Chain intel2 ~/tmp/kvplanr4/d27d_chain.sh, out d27d_chain.out: compose -> G0
  d27c/g0gate_d27d + strict bind d27c/bindgate_d27d. If R8_STALE: rt/current tools/die_plan/r8_refresh.py PLAN BIND/bus_groups.json r8_ev.json
  --asbuilt asbuilt_vN.json --root TREE (chmod u+w inputs dir first, a-w after), rebind. On green: launch the R3 section-3 proof set
  (gen_d27_after_r4d.sh pattern, Codex; needs a gen_proof script for D27d) and apply D27 after D26.
- 7 strap-pad types (hg_v1, hg_v1p3, pc x2, pc_v1 x3, pc_v3) are OWNER 10-28 strap sites: --strap-pads types_conflicting 0. Not a blocker.

- D27d RESULT 05:23: compose plan 07a462a13e91 asbuilt 118905421f0a (HOP 662/22 types, event_census REGRESS 0); G0 GREEN; strict bind rc1
  = 30 R8_STALE kvs_ctl.dcfg__age_vport_* -> vport_E*.cfg_age (bound 32/47 vs table 31). NEXT (R5): r8_refresh.py on bindgate_d27d bus_groups
  (tree bind_of_record), rebind (run_gate_d27c.sh bind d27c/bindgate_d27d2).

## 3. D28 = pv split (OPUS-FIX-KV-PV-R4) + everything pv moved out of D27: r0 re-site, r7, r13 relay_depth, pv parts of r2/r3/r6, pv column-law
  regen (pvx_regen), RESET-RELAY-GEN-R3 pv bank_taps re-emitted two-pass on the split plan, hub_Eo/Wo/sys_c pass2 re-run on D27 plan. hub_C split
  may come from FAM-KV-HUB.

## 4. Open from COORD (not started): 7 new KV failure_breakdown rows "other flow error" this hour: classify (tool skew / old rt / functional /
  structural) and route (relaunch fix= or rows to hub/hgi/pv/iopc family lane).
