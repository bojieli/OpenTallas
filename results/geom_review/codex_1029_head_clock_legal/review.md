# Independent hd_tile clock geometry review

Verdict: PASS-COND for one diagnostic CTS/GRT TT/FF continuation. No timing, die-freeze or sign-off claim.

Reviewed candidate: HEAD tile owner results/head_tile_clock_legal_1029/reg_spine_plan.json, successor of a052fcee54. Independently viewed clock_overview.png and predecessor fold.png. Checked actual placement row/macro/island/fixed rectangles from a052fcee54 blk.tsv.gz against fresh pad/tap footprints.

The five macro bodies leave a continuous central vertical street and two horizontal crossbars; the trunk follows those streets. Taps sit along macro edges and beside the upper macro, distributing local groups instead of driving across the full tile. Folded pads remain compact in adjacent legal rows, including tap9 beside the island row. No macro wall or long unbuffered trunk leg appears. The existing data placement's PG topology is unchanged by this clock-only change; this review does not independently qualify PG connectivity or IR.

Independent actual-body check: 45 tap drivers +333 pad stages =378 rectangles, zero macro/halo/row/island/fixed overlaps. Maximum plan Manhattan trunk/tap leg365 um; zero above405 um. Owner radius97.225 um/25749 sinks is a planning result, not routed timing.

Four existing trunk drivers (RD,RL,RR,ER1) overlap retained fixed tapcells at their initial sites. reg_spine.tcl rsp_inst sets PLACED, so these are movable during detailed placement; they are not FIRM collisions. Condition: post-DPL all clock rectangles must be legal and all physical legs rechecked. A residual DPL failure returns to the footprint plan before another route. The333-pad model and predicted ranges are not a substitute for routed TT/FF measurement. Prior candidate a052fcee54's tap33 fixed-cell collision remains historical; the fresh candidate excludes that exact fixed tapcell.
