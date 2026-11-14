# DIE-QC-101 handoff (2026-11-13 21:47 PST) - QC s29 final event

## State
- Strict bind NOT yet 0. QC is the last die out of the wave. Nothing adopted into kit_wave.json yet.
- Event tree (src): epyc9 /srv/opentallas-scratch2/claude/wt/qc-s29-tree2 @1e3b302be8 (protect from cleanup; also qc-s28-hf1c/bind, qc-s29-reach, die-qc-101).
- COORD 21:5x: READY must either build src on main >= 55713eb3c46 (train L: PG-track DRT-0255 + kit fixes J/K) or tell KIT-OPS-3 to overlay those 8 files onto tree2 (as for S81/KV). Recommend: overlay.
- Current plan: POR zz_s29_qc101_n.json (2da0e7a8b0ae) = f547 + per-port windows + pregrt_ff_hold + cl622 relay fix + cldbcda913 rings soft + local_copy_fix (lc1 + 17 copies slw_fw_v3) + fix_reach2 (su_l1 relay 72, fw_v3 child t87).
- Sidecar: die-qc-101/side_s29_qc101.json (d73f3b695f20) = Codex 2dc5994 with ONLY slw_fw_v3 child 1 node rst_n_t86 -> rst_n_t87 (bind reads collector children from the sidecar, not the plan).

## Bind chain (qc-s28-hf1c/bind)
- s29q101O_g0 (all-gaps, plan n): ONLY R8 class (30 R8_STALE + CS_RXV seam shift). All other types clean; su lane bound_groups source_matches_committed true.
- R8 derive -> qc-s29-reach/r8_s29q101O.json (bde81066d33f; 9050 members, 7853 changed).
- s29q101O_final: still 30 R8_STALE because manifest land_r8_extra (cb16_pads) overrides; fixed by R8_EXTRA_SPEC=qc-s29-reach/cb16_final_extra_hbm_codex.json.
- s29q101P (R8_SEED=r8_s29q101O + R8_EXTRA_SPEC, all-gaps): 2 errors:
  1. PARAM_REGEN W5: r_d of region 0 is not the latest; its r_v would need a pad  (R8-dependent class -> iterate derive)
  2. EMIT u_lane0: grouped source differs from committed actual module (tools/die_plan/bound_groups.py:89). sle_su_l0__cl086d85ba (and the other su_l0/su_l1 bound_group lanes): the derived R8 changes the lane cut so qc_su_lane_cut output != rtl/physical/qfd_qc_su_lane_w_l*.sv. In O_g0 (pre-derive R8) they matched. Fix: keep su-lane-internal R8 members at their O_g0 values (diff zz_r8_s29q101O_g0.json vs r8_s29q101O.json on sl?_su_l* members), OR regenerate+commit the lane modules in tree2 and re-sign those lane hard cores (re-sign is fast per owner). Fallback per COORD: hold the su_l0/su_l1 types - but holding does not remove them from the global bind; would need the lanes moved to soft (hard_cores_deferred style) in the plan.
- s29q101Q DONE: 2nd derive changed 0 members (R8 converged); same 2 errors (W5 pad + u_lane0). Both need structural fixes; W5 is not an R8-iteration item.

## Adopt packet once bind is 0 (post READY+ADOPT to KIT-OPS-3)
- plan: tree2 POR final plan; src: tree2 @1e3b302be8 + overlay of the 8 train-L files (main 55713eb3c46).
- kit_rtl.bind_out: qc-s28-hf1c/bind/bind_<final tag>; asbuilt: tree2 runtime zz_manifest_iso_<tag>.json; --clock-landing: tree2 runtime zz_sidecar_<tag>.json.
- hold_items: cbn_q00__cldbcda913 (D8 ring; child D8 kit SIGNED on epyc7 hard-qc-forms-1/d8_child/local32: TT +40.94, hold +14.96, DRC 0; parent adoption needs ring knobs DSREP4/READ32/WRITE16/RSTREP73/PLACEREP1) + phy_* holds.
- Remove PHYS-QC item_inputs sle_ctl__cl372cea1c, sle_ctl__cl503337ff. coll_core: LEC off, 20 formal differs advisory (root/lec).

## OPEN (advisory under R-MINIMAL)
- 320 c_* ports in 11 types capped at 208 ps window; coll_s clk_serdes/clk_coll windows + region (PHYS-QC measured delta); re-pick local resets after adoption; slw_sc_v3 bind_report copy (KIT-FIX-F).

## Tools (epyc9 die-qc-101)
- quick_final.sh PLAN SRC_TAG FINAL_TAG (R8 derive from an R8-only all-gaps bind + strict final; set R8_EXTRA_SPEC too), lc_loop.sh, fix_reach2.py, fix_cbn622_relay.py, soft_rings_type.py.

HANDOFF-TO-SONNET DIE-QC-102
