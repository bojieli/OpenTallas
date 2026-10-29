# QC-IMPORT-2 — provider boundary bindings + preflight READY (QC die), 2026-10-29

Lane QC-IMPORT-2 (successor of QC-IMPORT-1, base claude/qc-import-1-1029@980d580a471). Run root
`intel2:/srv/opentallas-scratch2/claude/qc-import-1` (outputs under `bound/`).

## Step 1 — native boundary nets + bindings (CHECKED, own runs)
The fresh source `mechanics/clock_grafted.odb` (cd4060c5) carries the 313 START nets only as die-top INPUT
placeholder BTerms (no partition ITerm) and has no reset net, so no binding could satisfy the importer
(`apply_cells`: output must be undriven + native endpoint on the net; reset needs one native driver).
`boundary_bind.py` copies, from the SAME fresh build's `target_signal.odb`, exactly the native ITerms of
(a) the 313 START nets (`<dst_part>/cland_tstart_in`, one each, checked equal) and (b) the plan reset_source net
`rstw_sl_E0_fw_rst_o_0` (driver sl_E0_fw/rst_o_0 + sink sl_E0_stm/arst_n, 2 ITerms), and removes the 313
placeholder BTerms (the provider is their only driver). Clock cells/placements/all ck_* nets: hash unchanged
(0a0caa56); other BTerms unchanged (root, rst_n). Output `bound/source_bound.odb` sha256 60d6fc07.
Bindings (`bindings.json.gz`, ot_provider_boundary_bindings/1, 3,580/3,580 ports):
- 3,266 `t_st_*__clk` -> `ck_<clock_net>`, role clock; checked: that net's single OUTPUT driver is
  `ck_<actual_clock_driver>/Y` and the stage node cell's `clock_from` pin is on it (2,345 tap Y, 921 tap A =
  the node inverter's input net; polarity is the RTL's edge_fall contract, not re-qualified here, UNCHECKED).
- 313 `pst_*` -> same-named net, role start_output, endpoint `<dst_part>/cland_tstart_in`.
- `rst_raw_n` -> `rstw_sl_E0_fw_rst_o_0`, role reset, endpoint sl_E0_fw/rst_o_0 (local root, release 15).

## Preflight fix (reset check keyed on the bound net)
`preflight.py` = codex/provider-import-1029@9e7df79e4 results/provider_import_1029/preflight.py with one change:
`global_raw_reset_star_forbidden` no longer fires on the port NAME rst_raw_n. A reset binding passes only if role
= reset, net is not a die-top raw reset net, net == plan reset_source net (`--die-plan`, fail-closed without it),
and its single native endpoint is reset_source part/pin on an actual partition macro.
`test_preflight_reset.py` 8 tests PASS.

## Preflight on the bound source (CHECKED)
`run_preflight.sh`: export_constraints (bound ODB, partition_macros 377) + preflight -> `preflight.json`
READY_FOR_REVIEW, issues {} (48,259 cells; 0 OBS/keepout/PG, 0 overlap, 0 mapping, 0 unbound).

## GEOM render (VIEWED)
`bind_review.png`: provider cells + 313 START links + root reset; reset pin -> b0 centroid 167.7 um; max
stage-centroid -> bound clock driver 355.2 um, max START stage -> cland_tstart_in 394.4 um (pst_coll_core,
centroid Manhattan, UNCHECKED vs routed; registered reach 404.784 max was CHECKED by Codex).

## Next
GEOM PASS -> `apply_cells` (needs review record) -> PG re-census -> b1 fixed_tree prebuild -> strict bind epyc2 ->
ot_clk mesh + die GRT0 -> clock check. Note: strict bind must replace the die-level pst_* placeholder inputs in
route.v with the provider outputs (same nets).
