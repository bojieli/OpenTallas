# S81 physical DME leg feasibility (opt-in coupon)

Measured failure: go16 bk_sel actual gap653.4um spans a652.32um core;
post-DME reach17 adds4 stages and a channel bypass on this branch. Reach
and duty improve, but its unpriced delay widens FF kit window239->316.93ps.
The added77.7ps is consistent with4 fitted FF stages plus bypass wire.
Uniformly adding those costs before DME balancing can move the merge and
price the other child paths, rather than insert delay after balancing.

The candidate uses one legal physical leg object (chain/stages/wire/delay)
for merge cost, snapped snake candidate cost and exact export. A snapped
hop over405um uses the existing legal_detour A* channel route and the
minimum geometry-derived paired-inverter insertion that meets reach.
The same immutable chain is stored on the chosen node; export rejects
changed endpoints or lost legality. Default mode remains unchanged.
No per-tap offset, clock relaxation, new corner or new gate is introduced.

First vehicle: the51-tap bk_sel region only, using exact go16 plan_s11e,
SiteMap and inv2_stage_cal_s81_go15 calibration. Compare baseline and new
analytic TT/FF windows and actual exported hops. No whole-die rebuild.
Only a feasible coupon is rendered/reviewed before any routed STA trial;
S81 owner holds reach18 routing. A geometry or predictor failure is kept.
