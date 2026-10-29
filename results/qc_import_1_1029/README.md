# QC-IMPORT-1 — fresh native provider import (QC die), 2026-10-29

Lane QC-IMPORT-1 (COORD 10-29, ASK default of DIE-QC-30). Run root `intel2:/srv/opentallas-scratch2/claude/qc-import-1`.

## Step 0 — QC plan of record (CHECKED)
`compose_plan.py` = native h800 plan (sha 0ff4c77a…) + START provider/reset_source (Codex `native_source_candidate2/plan.json`,
sha a941dfe8…) + form (a) tap pin growth (`plan_growth_candidate.json` sha bddfe45d…, 29 types). The two deltas are
disjoint (`/clock/landing_network/start_tree` vs `partition_types/*/clock/tap_pin_heights_um`).
Result `plan/plan_qc_import1.json` sha256 d0b301f8…: landing contract on this branch's tools 0 errors, 5,505 pins /
6,184 edges, START 313 uses / 0 open, provider 3,266 stages / 3,578 edges / max hop 404.784 um, local root reset
sl_E0_fw.rst_o_0 (172.9 um hop, release 15). b1 PHY stubs are parent M7 wires (fixed_tree prebuild), not plan data.
NK A0 V1 waits for DIE-QC-31; BTAB F2 pin move joins later as a fix event.

## Step 1 — combined island windows (CHECKED)
`provider_sites.py`: every placed provider body (Codex `proposal_qc_wave2_compact/placements.json`, 48,259 cells) as an
`ot_clock_sites/1` site with its actual body size (`cell_um`, new opt-in in `die_trial.load_island_sites` /
`island_windows`; absent = planned clock body, unchanged). Census on the plan of record (`island_census.json`):
clock 44,590 sites -> 13,651 windows / 119 types; provider 48,259 -> 17,651 / 111; combined 92,849 -> 31,302 / 119;
0 in hard core, 0 outside partitions (equals Codex's emit_islands 17,651 and mixed projection 31,302).

## Step 2 — fresh native source (RUNNING)
`fresh_target.py` (Codex `reframe_target119.py` recipe) regenerates all 119 abstracts with the combined islands +
landing infra + native reset outputs, route.v with landing + reset wavefront nets, frozen trial26 clock and PG
reservations copied unchanged. `run_fresh_source.sh` then runs the mechanics119_h800 prepare_clock / prepare_signal /
clock graft (graft_clock_targets6) -> `mechanics/clock_grafted.odb` = the fresh source for the provider import.

## Next (not run)
export_constraints (fresh) -> boundary bindings (ot_provider_boundary_bindings/1: 3,266 stage clocks, 313 pst outputs,
root reset = rstw_sl_E0_fw_rst_o_0) -> preflight -> GEOM visual review -> apply_cells -> native PG re-census ->
fixed_tree prebuild with b1 stubs -> strict bind (epyc2, QC-001) -> ot_clk mesh + die GRT0 incl clock -> clock check.

## Step 2 result (CHECKED, own run, unit oth-ubuntu-542175-1793283736 exit 0, 4 min)
Fresh native source `mechanics/clock_grafted.odb` sha256 cd4060c5…: 119 types / 377 parts, 31,302 island windows,
6,184 landing edges (313 provisional START), native reset wavefront (82 types carry rst_o_*), 7,889 actual partition
clock ITerms grafted (CONNECTED_UNROUTED), frozen trial26 clock unchanged (`fresh_source.json`).

## Step 3 — fresh-source preflight (CHECKED, unit oth-ubuntu-677587-1793284078)
`run_preflight.sh`: Codex export_constraints + preflight unchanged, bindings deliberately empty.
`preflight_nobind.json`: all 48,259 provider bodies vs the fresh source: actual OBS/keepout/PG hits 0 (old h800 source
15,981 / 26,497), frozen clock cells changed 0, new body overlap 0, mapped-vs-inventory mismatch 0, undriven/multi-driven
0. HOLD only on the boundary bindings: 3,580 unbound ports (3,266 stage clocks + 313 START outputs + rst_raw_n) and the
bindings source hash. Note: preflight flags any port NAMED rst_raw_n as a global raw-reset star; with the local root
reset (reset_source sl_E0_fw.rst_o_0) the binding must map rst_raw_n -> rstw_sl_E0_fw_rst_o_0 and the check must key
on the bound net, not the port name (fix in the bindings step).
`constraints.json` partition_macros = the 377 BLOCK instances (added post-export; export_constraints does not write it).
