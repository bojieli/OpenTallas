# RESET-RELAY-GEN-1530 handoff (FABLE-CLOSURE-1515 lever 1; 2026-11-20 PST)

Owner of the reset-leg generator rule and, from 15:5x, of S81-DIE-R4's die reset/monitor relay patch (reach_relay_plan.py,
reset_tree.py die_relays). Posts: lanes/posts/RESET-RELAY-GEN-1530.md. Work dirs: epyc10 /srv/opentallas-scratch2/claude/rrgen-1530/src
(lane clone), epyc7 /srv/opentallas-scratch2/claude/rrgen-1530/ (dumps, legs, proofs).

## Main commits
- e9af887233 S81-DIE-R4 relay patch (die reset relays + monitor relays, no-provider guard), applied unchanged.
- f02ccd50eb reset_leg_plan.py + reset.inst_taps (schema, bind, kit-rtl) + apply_inst_taps + 7 tests.
- aa05a04543 stage site key = `u_y_xd_<sid>_<port>_k<k>_<s>.q` (Yosys name measured on the lepe proof netlist).
- 73717f6992 form R skips hard-core (macro) sinks (cbx proof: re-tapping u_t30 by its centre cost -296 -> -763 ps).

## The rule (tools/die_plan/reset_leg_plan.py)
`python3 -I tools/die_plan/reset_leg_plan.py PLAN TYPE BOUND_SV GEOM OUT_PLAN REPORT.json [--reach 300] [--local-taps]`
- BOUND_SV = the type kit's rtl/<type>_bound.sv. GEOM = the geom_dump.tcl dump (tools/autopilot/geom_dump.tcl) of the
  newest placed kit's 3_place.odb (read-only, 6-9 GB, 2 threads; epyc7 rrgen-1530/gdump.sh ODB OUTDIR TOOLS).
- Form R (QC cb*, KV pv/sys_c banks, any soft sub-instance): instance reset port on the leaf alias or a far tap ->
  `reset.inst_taps [{tap, sinks, port?}]` (new schema key), the equal-depth tap with the smallest worst leg to its PLACED
  sinks. bind (after bank_taps) and kit-rtl (after KIT-RD-1) apply it with reset_port_relays.apply_inst_taps. 0 cycles, 0 flops.
  No tap in reach -> report.needs_local_tap (centre), `--local-taps` writes reset.local_taps_um (needs a re-bind).
- Form L (S81 lepe u_u_land.u_rstr, leaf u_vp.u_rr, g_rsreg, rst_q): each relay copy seated FIRM at its own fanout centre
  (`relay_sites`); a single-copy relay fed by a signal register gets `relay_depth {inst, port, side: sink, D}` with
  D = ceil(L/300) - 1 (cap 4 = schema), reset release cycles only (rst_n held >= 64). relay_mid.tcl spreads the u_y_xd_*
  stages; `--stage-sites` seats them on the line instead.
  Replicated relays (REGIONS copies) move only their far copies; a copy radius over 300 is listed under split (not fixed).
- Not a gate. report.legs_over_before / legs_over_after per type.

## Read-only results (placed kits, no build)
| type | event | legs > 300 before -> after | detail |
|---|---|---|---|
| QC cbx_q10__cl94a12200 | s29q103S4Q9N46C | 5 -> 0 | u_u_fab_u_x_{2_0,2_1,3_0,3_1} on leaf tap 0 at 1,306-1,536 um -> taps 15/62/11/70 at 38-207 um; u_t30 326 -> 280 |
| KV kv3_pv_v2 | D25e3 a4 | 13 -> 0 | 13 banks on leaf tap 0 (u_bin_i_vport_W_N_vo 1,291 -> 65 um, the -2,218 ps path); CBC bank_taps skipped them (per-port buses unplaced) |
| S81 lepe_mu_LP__t2 | b05c98f7919 | 5 -> 2 | u_u_land.u_rstr out 846 -> 253 um at (212.2, 244.7); D 4 on u_u_land.rst_n, 292 um/hop; lep balanced relay copy radius 454 (split) |
| S81 lepe_nh_mus_LP__t1 | b05c98f7919 | 6 -> 3 | u_u_land.u_rstr out 1,825 -> 152 um at (544.1, 798.1); D 4 at 337 um/hop (over the cap of 4); lep relay split |

Item 6 compare (OPUS-FIX-S81-LEPE, hand row on proof6 placement): u_rstr (349.8, 355.8), D 3 on the land rst_n. From the
same E-face source (1436.7, 6.9) that is 1,436 um / 4 = 359 um per hop. The generator on b05c mu_LP t2 seats u_rstr at the
measured land centre (212.2, 244.7) and takes D 4 (292 um/hop). Use the generator row, not the hand row.

## Private proofs (epyc7 rrgen-1530/proof/{cbx,pv,lepe}: kit copy, delta applied by prep_proof.py, run_kit.sh GOAL=place)
| kit | worst reset path before -> after | WNS before -> after | note |
|---|---|---|---|
| S81 lepe_nh_mus_LP t1 (r1) | -456.1 (u_u_land.u_rstr -> ri_, 22 buf) -> +211.9 | -644.4 -> -652.2 (same SRAM rx_mem -> rid path, not reset) | u_rstr placed at (542, 797) as planned; land legs fixed. KIT-RD-1 stages: k0_0 stayed at the source, k0_1..3 bunched at (674, 793): relay_mid does not spread them -> r2 uses --stage-sites. Remaining over-300: lep balanced relay (copy radius 687, split) |
| QC cbx_q10 (r1) | -473.5 (u_rrl_147 -> u_x_3_1 cnt, 22 buf) -> +566.6 | -473.5 -> -763.5 | the new worst is u_rrl_234 -> u_t30 (hard core, clk group): my row re-tapped a macro by its centre. Fixed in 73717f6992 (macros skipped); r2 without the u_t30 row is running |
| KV kv3_pv_v2 (r1) | -2,218.1 | pending | at floorplan pdn (slow kit) |
r2 proofs: epyc7 rrgen-1530/proof2/{cbx,lepe} (GOAL=place, launched 11-21 ~00:3x). Check with rpt_sum.py PROOF/3_detailed_place.rpt.

## Rows / plan keys handed over (lanes/handoff/RESET-RELAY-GEN-1530-rows.json)
- S81-DIE-R4 (J6, cut 11-21 13:00): run the tool per J5/J6 type with a placed kit (lepe x4, leaf, bk_sel, col g_rsreg); rows
  for lepe_mu_LP t2 / nh_mus t1 are in the rows file. Item 9 die relays: the S81-DIE-R4 patch is on main as commit 1 above.
- QC-PLAN-R5 (V1, 09:30): reset.inst_taps for every cb* type from its newest placed kit (cbx_q10 rows in the file; DROP the u_t30 row, or re-run on main: macros are skipped).
- KV-PLAN-R2 (D27): reset.inst_taps for pv / sys_c / hub_Wo from their newest placed kits (pv_v2 rows in the file).
- Rows are plan-local to the bound module they were read from: tap indices are that bind's tree taps. Re-run the tool on a
  new bind (taps move with the event).

## Open
- relay_mid.tcl does not spread KIT-RD-1 reset stages (lepe r1); r2 proves --stage-sites. If it works, make --stage-sites the default.
- Replicated relays with copy radius > 300 (lepe u_u_lep g_reset_balanced): REGIONS / split by quadrant.
- D > 4 legs (lepe nh_mus t1 land): either the cap goes to 8 for reset sink rows or the source moves.
- PRECHECK can read report.legs_over_* (estimator only).

## Stop list
- No hand rows per type for local reset relays: run the tool.
