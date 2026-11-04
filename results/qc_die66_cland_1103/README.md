# CLAND class fix (DIE-QC-66/CLK, 2026-11-03 18:59 PST)

Items: slw_sc_v1__cl63e5a7a2, slw_sc_v1__cl64543eaf__cl4590432d, slw_sc_v1__cl64543eaf__cl5e017c6f
(3_3 place: "OT_CLAND no legal nonoverlapping row/site in reserved band for ...collect_rst_rl_15").

Root cause: DIE-KV-32 resize_undersized_bands grew ring band x_fw_fe_p1_i to 17.28..62.64 x 629.16..730.84 um
(4612 um2 vs 4521.6 um2 ring_ff reserve, 98% full) over wire reset relay u_rrl_15 (45.72, 669.6). Reset-site
avoidance (FLOW-7) only runs for types in budgets.cland_avoid_reset_types, empty on QC, so the rst_rl_15 collector
grow window (up to +-17.28 um) sat 99% inside a full band: no site.

Fix (plan, one delta): delta_cland_avoid_reset_1103.py adds the 2 base types to budgets.cland_avoid_reset_types and
re-runs resize_undersized_bands for these 3 types; 25 bands move, max hop 145.9 um, 0 bands over reset sites; every
other type byte-identical. Applied to plan_qc52.json; wave plan plan_qc52_ucie1103.json + wave sidecar -> identical
report, fixed sha e96a5f4da5c8 (relaunch: run the delta on the wave plan).

Proof (copies of the failed d90b109213 kits, only landing_placement.tcl/landing_contract.json swapped for fix-gen
output; base-gen files byte-identical to the failed kits): ORFS do-3_3_place_gp from 3_2_place_iop.odb
- cl4590432d: OT_CLAND placed 164988 cells FIRM, GPL running (evidence/proof/.../proof_3_3.log)
- cl5e017c6f: OT_CLAND placed 164978 cells FIRM
Regression: sle_fw_v3 (placed in the wave) fix-plan gen landing files byte-identical to its kit.
Tests: test_delta_cland_avoid_reset_1103.py (3 pass).
Note: all 3 types are RF-QC-1 REFORM targets (>400k cells); the delta keeps the class out of their re-forms.
