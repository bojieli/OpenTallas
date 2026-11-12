# QC s27 = s26 + VIS stm re-site (QC-VIS-RESITE, 11-12)

Plan: `plan_of_record/plan_qc99_s27.json` (sha 820f14a689b7)
Base: plan_qc99_s26 779178a990b5 (claude/qc-event-s26-1111@ca28bc4738dd)
Sidecar: `sidecar_pv_s27.json.gz` (sidecar_pv.json sha 27b0eca895ef). This is ONE merged sidecar:
s26 sidecar 2b526c0f8849 with only `collector.types[T].{tree,local_sources,children}` replaced, for the 11 stm types below.
Every other key is byte-equal to s26 (evidence/s27diff.out).

## What changed (positions only, no re-shape)
- 11 stm types: hard_cores origin_um/orient snapped to the 8.64 um lattice from the VIS placement (delta_stm_vis.json).
- Density taps are re-derived from the moved macros. landing_contract.pins source_clock_port/_tap are re-pointed to the nearest new tap (at most 71 um).
- Reset collector_tree is re-solved through added_tap_recentre.republish (plan + sidecar). Then collector_reattach re-picks the source relays: +0 cycles on all 11, tree depth 4->4.
- No other type, top-level key, ft_slot or station changed.

Recipe: scripts/s27full.sh. That is: apply_vis_resite.py s26 delta --sidecar s26 -> collector_reattach.py --sidecar -> gates27.sh + strict bind.

## Gates (s26 vs s27; same tools, src_s26b + this branch's collector_reattach)
- schema: 0 / 0
- G0: 265 err/296 warn on both; 0 new, 0 gone (evidence/g0_diff_s26_s27.txt)
- G0C: 313/553 on both; 0 new, 0 gone
- station_lint: the same 3 NONMONOTONE advisory rows (sle_sc_*)
- strict bind (bind-strict-src bind.py 8e7a26b0dd81, sidecar 27b0eca895ef): rc0, 377 parts, 1921 crossings, 790,393 bits, 0 errors
- bus_groups 315252676904 equal to s26
- Bind RTL differences vs s26 are only the stm reset_tree/.sv files and bound_top (evidence/bind_realdiff_s26_s27.txt). native_topology changes only through clock_table_sha256 (the sidecar sha).
- route_supply p99, s26 -> s27: sle_stm_v1 x2 1.352->0.827; sle_stm_v2 1.328/1.181->0.822; sle_stm_v3 1.152->0.617; slw_stm_v1 x3 1.151->0.842; slw_stm_v2 x2 1.129->0.842; slw_stm_v3 1.029->0.842

## EQ
Positions and reset-relay re-solve only. Logic, ports, bus_groups, pipeline cycles and collector cycles are unchanged (+0 on all 11; reset depth unchanged).

## Tool change: collector_reattach for a collector rooted at a local reset relay
slw_stm_v1__cle34a73c3 has collector_root_node rst_n_t8. Before this change, reattach_plan passed the validated root through to landing_collector.reattach_sources. A root whose name and site did not change then hit that function's blanket "rerooted collector reattachment requires an explicit parent seam event". A moved root that _reroot had re-picked at the old site passed. Now _reroot validates the root and the sources are reattached from the delivered root. Test: test_rerooted_collector_unchanged_root_reattaches. cle34a73c3 is therefore included (11 stm, not 10).

## Not adopted
The 16 st_a/st_b types are REVERTED-BY-DECISION; see qc_vis_resite_1111/README.md on claude/qc-vis-resite-1111.
