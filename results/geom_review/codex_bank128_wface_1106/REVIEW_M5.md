# Bank128 M5 resource alternative — pre-build review

`bank128_M5_reference.png` viewed PASS-COND for one canonical fullshape trial. It is a pre-build reference using the same macro/pin/register plan and the existing M6 B placement positions; it is not a measured M5 placement or route. Candidate generated config is M5/0.40/single-root, same525bit+1write stage and3enableguide; all timing constraints unchanged.

Measured rationale: old canonical vA achieved initial M5GRT0 before hold padding. The new form preserves bus widths and outline, balances previously1.032um macro gap into12.792um corridors, and replaces weak direct-port SRAM driving with local input capture plus a full-cycle register-Q path. Thus M5 has a fullshape track witness and a concrete correction to the measured slew cause. M5 leaves the original parent M6/M7 budget available; actual routability and clock/hold repairs must be measured. No assumption of horizontal over-macro M6 resources is made for this variant.

Dataflow/pin faces/register reach and macro clearance are the same reviewed plan. Actual M5 placement, GRT, clock and routed STA must be reviewed before adoption; native write guard remains+1 and parent projection qualification remains open. M6 trials continue independently.
