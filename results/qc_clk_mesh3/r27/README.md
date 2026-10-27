# INFRA-FIRST-QC-R27 (2026-10-27): full dry-build census of the R26/R8 QC clock export

Source: codex/qc-clock-1027@77c339e5bc (Codex QC clock, parked 10:13) + one opt-in tool change:
`OT_V2_COLLECT_PLAN_ERRORS=1` makes `die_clock_mesh._explicit_v2_wires` record every failing edge
(PlanError / net_trunk_layer) and continue. The build still fails closed and lists every error. The default path does not change.

Why: dry8 (Codex) and dry9 (here) stop at the FIRST failing edge (one PlanError per piece), so
"1 plan error" (17747 driver jog) was not a census. Each per-site fix only exposed the next error.

Inputs: prototype8 clock_spec.json (export8 rowpins/inset, 33,416 edges), prototype8 plan.json.

| run | die.pg.grid M8/M9 offset | plan errors | failing groups |
|---|---|---|---|
| c_dry9a2 | 4.32 (current) | 15,774 (no_clock_track 15,653, reserve_overflow 109, net_trunk_layer 12) | 12,258 |
| c_dry9b | 2.16 (Codex per-plan alternative) | 25,656 no_clock_track | 17,092 |
| c_dry9b_chan216 | 2.16 + 266 channel cells y-2.16 (what-if) | 25,572 | 17,030 |

All three numbers come from my own runs, so they are CHECKED as runs. The collect-mode cascade is UNCHECKED: a failed edge can leave a
partial reservation behind, and that can inflate the count. Failing ideal y values cluster at 8.64k+0.13 and 8.64k-0.41/-0.14,
i.e. pins sited on the VSS / mesh lane (8.64k). Cells are VSS-phase locked (R15) and the mesh straps sit on 8.64k.
At offset 4.32 the straps lie ON the VSS stripes: 3,299/3,299 shorts (Codex inventory; my own check is mod 8.64 = 0 for all
178 M8 + 3,121 M9 segments). The 2.16 shift clears the mesh but breaks the VSS-locked tree tracks: errors rise 15.8k -> 25.7k.
The 2.16 shift alone is therefore NOT a successor.

Structural options for the ONE plan event (ruling needed):
 (A) keep offset 4.32 and cut VSS out under the mesh straps (die_infra holes_um). The removed length is 5,271 mm M9 + 5,264 mm M8, about 5.5 % of VSS
     M8/M9 each (CHECKED arithmetic, die 31,216 x 26,317 um). The R22 convention puts straps ON VSS lanes, so this is the intended form.
     Needs IR re-solve; the tree track census must be re-run with the carved PG.
 (B) phase-aware re-site of all tree groups in the planner (V2 exporter) for offset 2.16. This moves in-partition islands by 2.16 um.
Either way the remaining driver-jog / trunk scarcity at the lane (col_node driver jogs 6,479; band_node trunks 3,733) is a
planner track-budget issue to fix in qc_clk_mesh3/export. It is not a router relaxation.
