# QC trial25 clock review — FAIL for physical continuation

Personally viewed `results/codex_qc_1029/clock_tree.png` and
`results/codex_qc_1029/floorplan_ft.png`, rendered from the unchanged ev_qc25
plan and the final body-overlay tree.

The repeated A0 columns leave continuous narrow vertical channels and horizontal
seams. The central SU strip sits beside its collective/feedthrough traffic;
the E crh_rp1 footprint fits inside the preceding larger crh slot. The top-level
picture shows no new macro wall or die-outline overlap. It does not resolve
pin stacks, PDN continuity or detailed signal congestion, so those are not
claimed as passes.

Clock review finds repeated long U-shaped compensation legs, with different
depth and length distributions in opposing branches of a quad. The routed
failure confirms that this is material: in c_E2_bf_10 the refit-generated
b9424→b9462 snake is 2,406.4 um across ten stages near the 250-um limit, with
97–129 ps input slew. Its early arrival exceeds the stateless fitted model by
55.0 ps. Together with the opposite branch's early residual, the differential
model error is 101.5 ps; quad glue spread increases from 35.48 to 156.24 ps.
Nominal quad spread reaches 209.5 TT / 181.0 FF before variation. This candidate
does not proceed to physical clock materialization or signal route.

Action: reject the refit clock candidate, preserve the validated trial24 model
and generate a successor on ev_qc25 so the required E crh lineage change is
included. The successor must be reviewed before P&R/STA. A0 parent real-view
closure and the already-running mesh trial continue independently.

The drawing's historical SS color label is not a timing result; this review
uses the routed TT/FF artifacts in the accompanying diagnosis.
