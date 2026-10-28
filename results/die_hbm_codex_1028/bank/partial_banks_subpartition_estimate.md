# HBM partial payload banks and subpartition estimate

The naive bank-only W/E2 proposal does not close. Fixed-core, no-overlap packing plus the actual C20 station reach of405um retains3,801NW and3,770NE payload banks (1.000M /0.971M data flops). The original epochs stay soft; no pipeline edge is added. Bank placements whose per-bit hops plus opposing-face allowance exceed405um are removed and their original soft station positions retained. Existing worst hops404.112/404.184um remain the maxima. This is a geometry/source estimate, not routed or clock-qualified hardware.

|Quantity|NW hub|NE hub|
|---|---:|---:|
|Remaining estimated soft cells, F1.3|1,907,718|2,001,785|
|Minimum subpartitions at360k, lower bound|6|6|
|Greedy contiguous-x subpartitions|6|6|
|Actual transported bits at proposed cuts|36,577–62,924|39,617–52,666|
|Hard bodies intersected by each cut|30–81|33–96|
|Full4320um face pin capacity at6/um, edge insets removed|25,868|25,868|

These cuts are rejected: they cut existing hard bodies and exceed face pin density. They are not a revival of the earlier unsafe40–67k cut proposal. An optimistic metal-track upper bound (60% of unblocked M2/M4/M6 tracks, ignoring PG and escape) can carry many of the raw signals, but does not legalize the cut or its pin windows. No claim of routing capacity PASS follows from that upper bound.

The next physical lever is a source-aware hub bay/ownership recomposition with distributed legal interfaces, or larger local bank bays that preserve405um hops and remove enough soft logic to avoid these wide cuts. Keep the die outline fixed. Source slicing and current core-clock closure continue while that design is prepared; there is no bank-kit or route admission.

The older450um subset is retained only as rejected history. The source-aware tool now reads die.reach_um; the one-page numbers above use405. Full diagnostic layouts remain in intel2:/srv/opentallas-scratch2/claude/codex-hbm-die-1028/bank/.
