# Independent macro PG terminals experiment

This is a PDNSim-only experiment. Original kitC, its failed 468.4 mV IR result,
and all released physical sources are unchanged.

The pinned OpenROAD 6cb3f2b704 implementation does NOT inject a macro's full
power into one physical M1 point: it creates one virtual base node and links it
to every supply pin rectangle by a 0.001-ohm `TermConnection`. One row per macro
in the voltage CSV is therefore not proof of point loading. It does hide an
ideal cross-strap short inside a multi-rectangle supply terminal.

Primary implementation references at the pinned revision:

- https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/psm/src/ir_network.cpp (`generatePolygonsFromITerms`)
- https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/psm/src/connection.h (`TermConnection`)
- https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/psm/src/ir_solver.cpp (`buildNodeCurrentMap`)

`tools/die_plan/psm_distributed_load.py`, run with OpenROAD Python, aliases each
abstract master with a separate terminal for each original PG rectangle. The
rectangles, instance placement/orientation, original die wires/vias and bump
sources survive unchanged. Signal pins and master obstructions are deliberately
omitted: the output is solely a PG analysis database. Existing per-instance
power commands still apply to the same instance names. PDNSim shares current
equally across the independent nodes; unequal-area rectangle sets are rejected
because that weighting would misrepresent uniform areal current density.

Native tiny fixture: MX placement/location and two-terminal net connectivity
PASS; unequal-area mutant rejected. Full historical KV hm_r12 kitC preparation:
160 macro instances -> 47,032 independent supply terminals. The source ODB is
`intel1:/srv/opentallas-scratch2/claude/kv-pdn-m78-1026/kitC/psm/pdn_bumps.odb`.
Actual distributed IR analysis is running in the new, separately owned directory
`intel1:/srv/opentallas-scratch2/claude/codex-sta-pg-1027` (`analyze2.log`). No
current-plan droop or IR claim follows until that analysis completes.

Final controlled experiment: process exit0, VDD/VSS connectivity PASS, IR **FAIL**.
23,516 independent VDD stripe terminals produce worst modeled IR1,165.654mV,
versus original468.441mV, with the same grid, bumps and power. The worst remains
sys_SW/sys_SE, both without VDD bump targets inside their SerDes windows. The
negative linear-model voltage is an infeasible constant-current solution, not a
physical operating-point claim. Removing ideal cross-strap shorts worsens the
result; a single CSV M1-node count never justified dismissing the original IR
failure. Current KV owner is measuring truthful PHY-only supply domains with
the existing dedicated micro-bump lattice, keeping digital glue on VDD.

Run4552s, peak RSS98,169,220KiB; raw logs/CSV and output ODB retained in the new
run directory. `result.json` records per-instance terminal voltage summaries.
No droop table or plan was adopted from this failed diagnostic.
