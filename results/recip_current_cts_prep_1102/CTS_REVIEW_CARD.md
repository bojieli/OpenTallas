# Current RECIP CTS release review card — source proposal only

The input is the actual saved compact RECIP placement, ODB SHA256 `9ba70335e4f85dc5bd467e67629ab9a1db18143f8c319ea86656e531d3f9586f`, with its exact saved SDC. Its active outline is 216 × 138.24 µm. The original 94 inputs and current saved PLACE bytes are pinned in CTS_SOURCE_INPUTS.json; the completed PLACE subject remains separate and unchanged.

There is one existing clock boundary root, `clk`, at **[0.042, 113.916] µm**, and **8,994 actual CLK pins**, all currently on that net. CURRENT_ODB_STATIC.json.gz contains their exact current coordinates and masters. The cohort is 5,621 DFFHQNx1, 3,364 DFFASRHQNx1, six DFFHQNx3 and three DFFHQNx2. Current pin capacitance totals are **4,229.959441 fF TT** and **4,631.520459 fF FF**. The nine strength changes contribute only 0.003525 fF TT / 0.000831 fF FF relative to SYNTH; actual current master loads are used rather than assuming identity.

The exact ordinary requested native CTS arguments are:

```
clock_tree_synthesis -sink_clustering_enable -repair_clock_nets
```

There is no CTS_ARGS, buffer-list, cluster-size, cluster-diameter or buffer-distance override in the resolved CTS configuration. The unchanged macro wrapper is a no-op for zero macros. Requested `::clock_tree_synthesis` and final native `::ot_mcc_cts_orig` remain separately observed. PRE is the entire unchanged max_fanout hook. The ordinary inverter-repair call precedes CTS. The entire POST is retained: leaf_affinity followed by the normal conditional setup repair. No flag, constraint or algorithm is changed by observation.

**Clustering and tap geometry intent:** the normal constructor must generate a fresh tree from this exact current sink distribution and its current loaded Liberty capacitances. The current physical tap count is zero; exact new buffer/tap coordinates or a new cluster count are not claimed before the constructor runs. No old 410-cluster tree, clock graph or hard model is transferred. The actual input cloud and all 67 boundary-register mappings are rendered in current_sink_boundary_review.png and have been personally LOOKED. The raw unbuilt root-to-sink Manhattan maximum is 321.196 µm; this is explicitly not a completed clock-reach PASS. Existing TT 250 ps / FF 202.5 ps binding values remain budgets, not new measured insertion.

Data geometry is resolved: pin-to-register p90 / max are 7.831 / 9.993 µm against 30 / 150 µm limits; all-pair register-centre reach is 340.578 µm against 405 µm; actual fill / empty bins are 21.66% / 30.47%. The current x[31] geometry has one BPin with both legitimate rectangles. The existing actual source-to-SYNTH proof joins EQUIVALENT 11,074 / 11,074. Independent saved PG audit checks 106,210 terms with zero failures and persisted rules. Optimized-PLACE functional EQ and the future physical clock gates are not claimed by these facts.

**Next gate:** one parent-reviewed private CTS lifecycle canary, using original manual OT_PG_STRICT unset, actual e19/8c native callback dependencies and helper `5ffb56fa…`. Strict production still refuses the inverter and CTS APIs. Every input PG0 audit remains mandatory; a failure must not be repaired late. Zero clock-net inverter instances are an input fact, so zero inverter births would not qualify the general inserting inverter case. Actual newly generated clock geometry, event counts, saved PG0 and clock/source/master inventories must be reviewed before any further stage.

The self-contained source proposal is staged at Intel2 `/srv/opentallas-scratch2/claude/codex-recip-cts-lifecycle-prep-1102r0`. Its complete disposable make-n passed, with only the normal 4_1_cts command and 4_cts copy, no changed inputs or stage4 output. Normal resource proposal is **4 GB / 1 thread / 2 GB disk**, supported by actual old CTS capacity measurements at the same source and sink count; only capacity is reused. Source proposal digest: `213eeea1406e82b5349feafc37dce3cf803d218359ed1084a93ae4774e6e950f`. No native CTS, solver, timing or route job is released or queued by this card.
