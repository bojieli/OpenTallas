# Constructed G9e die floorplans: diagnostic review

The PNG was generated from the actual completed EP7 MAIN4/FB4 route plans and visually inspected. It is a die assembly plan, not a physical gate PNG or a closure verdict. Both plans retain all 72 frames and the existing block bodies; nothing shrinks. TOPK reserves 907.2 by4536 micrometres, including the new VMUX allowance and parent margin.

| Check | Actual fact / remaining obligation |
|---|---|
| Bodies and reticle | Both construction checks pass:33 by26mm,100um seal, at least86.4um between bodies. |
| Center street | MAIN302.4um; FB1296um. FB moves Engram/sequencer/bank collector into the free East inner column above frame f_4R01 and below gunit. |
| Routing | MAIN:zero construction failures,18,548 stations,1,673,167 bit-mm; FB:zero failures,19,365 stations,1,748,957 bit-mm. |
| Modeled capacity | Final peak ratios1.599 MAIN /1.541 FB against150.9 bits/um modeled capacity. Both remain above the intended capacity target; actual GRT is required. |
| 43.2um lattice | Child kits use the project lattice; complete actual die placement/lattice audit remains OPEN. The coarse model contains fractional coordinates and must not be claimed lattice qualified. |
| Standard-cell bands | Unhardened parent interiors are explicitly stand-ins. A complete physical one-band check is OPEN. |
| Full-face pins and density | Wrapper endpoint projection follows pin faces/ranges; actual generated LEFs and final full-face density must be checked after GEN/physical gating. No <=6pins/um claim yet. |
| Clock topology | Geometric die roots, per-slice regional roots and explicit receiving-root reset captures are in the source. Actual insertion/spread and neighboring boundaries remain OPEN; no >80ps waiver. |
| Shape and utilization | All existing bodies retained; composite slices remain tall hierarchical parents. No utilization-driven shrink. Final mapped utilization and internal leaf shape checks remain OPEN. |
| Timing | No G9e GRT/STA result yet. G9d is a separate preserved live run. TT/FF/SS evidence must come from each exact generated case. |
| Source/functional scope | Five new service-bus ring widths have full positive and causal-mutant behavior receipts93c10bec4. Their physical views and current die/token integration remain OPEN. |

Source f2ab1ca15, actual route paths EP7 `/srv/opentallas-scratch/claude/codex-s81-g9e-probe-2022-1021/{main4,fb4}`. MAIN strict-bind transport failure is immutable; recovery output is a separate directory. Source/view dependency bundle resolves27 selected refs and does not alias any CLOSED leaf.
