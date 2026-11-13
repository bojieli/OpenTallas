# QC-S28-B: lane-B delta for the QC s28 structural event (DIE-QC-99)

DO_NOT_COUNT. Stage S2/S3 (plan event delta). Base: plan_qc99_s28 2f0c17d5f1a3 (claude/qc-event-s28-1111@88018018ef),
sidecar_pv 38a30992accc. Independent of QC-S28-A (land_r8 / st_b substitution, a0c views, coll_n): coll_n is NOT touched.

## Files
- `delta_s28b.json.gz`: leaf-path plan + sidecar ops (before/after, list-element identities), built by
  `apply_s28b.py mkdelta`. Re-apply on any base (e.g. s28 + QC-S28-A):
  `python3 -I apply_s28b.py apply BASE.json delta_s28b.json OUT.json --sidecar SC_IN.json SC_OUT.json --report r.json`
  (three-way: a path is applied only if the base holds the delta's `before`; otherwise CONFLICT, exit 3, nothing written).
- `street_rule_bins/` (repo path physical/die_plan/qwen_compute/street_rule_bins/): sink bins of the street-moved types.
- Recipe: `apply_s28b.py stage1` (B1/B3/B4/B5) -> `sr.sh` (STREET-RULE-1 legalize da9ad4d161, pass-2 levers) ->
  type picks -> `pin_boundary.py` -> `reanchor.py` -> `fix_b5.py` (START pins, reverts) -> `reattach_loop.sh` (collector_reattach) -> `gates.sh`.
- `evidence/`: gate logs, G0/G0C diffs, legalize event/rows, boundary/reanchor/reattach reports, route_supply rescore.

## Items
See evidence/RESULT.md for the per-item result, the p99 table and the gaps.
