# Actual source-clock/return ledger and bounded marker

**Current correction:** marker03 ages1/4/5 below are route-to-slice-entry samples, not CAP. Marker04 adds actual DR6 and measures logical CAP sample ages7/10/11. The original marker03 receipts remain historical; see FULL_GRAPH.md and marker_dr6. Native phase/regional reset/actual selected ARR remain NULL. Actual source macro commit1260 is now measured by retained_xs_result, replacing the earlier structural-only annotation there.

Selected die SHA61b683b... is rechecked from the immutable ep7 final source.
`selected_return_cone_inventory.json` preserves exact lines/line numbers and
external source fingerprints. Routed returns start at ICGx4_ASAP7_75t_R on
ck_cl3S. Its low-transparent enable latch admits the source reset epoch.

| Return | Gate enable | Actual station clocks | Landing reset | Landing K |
|---|---|---|---|---|
|3L01|rsg_rs_31_10_2_cl3S_6|SN posedge gate0; next clock inverted|rs_34_13_2|2|
|3L03|rs_33_30_3|NS posedge gate0, then posedge inverted clock; next clock restores phase|rsg_rs_34_13_2_cl3S_15|2|
|3R01|rsg_rs_38_10_1_cl3S_0|SN posedge gate0; next clock inverted|rs_34_13_2|2|
|3R03|rs_36_30_2|NS posedge gate0, then posedge inverted clock; next clock restores phase|rsg_rs_34_13_2_cl3S_16|2|
|3L02/3R02|direct frame source|direct to packed CAP lane1/4|slice regional reset|none|

Each actual station uses ot_s81_rly RSREG1: local reset asynchronously clears
rq, rq releases one station edge later, then data can pass on the following
edge. Clock forwarding is a kept inverter, not a data delay. The landing writes
on posedge forwarded clock, reads on posedge ck_cl3S, tracks write/read epochs,
and warms after K. It stores complete70-bit return words, including status,
valid, tag and data. These bodies are exact ceaed19c4 snapshots in marker_sources.
The ICG functional body is the existing dv_rtl_kit library-function model.
It is not a native timed-cell or CTS proof.

The marker experiment uses a declared logical G=R0 epoch with settled reset,
a834ps bench period, and three actual path classes (direct, one SN+K2, two
NS+K2). It does not assign selected physical/reset dates. Markers are phase
stimulus only; no Q or fixture return value drives an endpoint. Measured CAP
sample ages are1/4/5 edges respectively (source launch identity→next CAP pin
sample, with NBA visibility accounted for),32 samples per path. Native gate
insertion, local reset release dates and the actual selected ARR times remain
NULL until their source cones/calendar are resolved.

Final unpinned 4GB/two-thread job3690352 exited0, Verilator5.050. A gate epoch
one late, a dropped live forwarded-clock edge, and an advanced source marker
all fail the frozen age/identity ABI. Opening the gate before reset release is
masked by the real reset logic; it is an observation, not a causal negative.
Earlier failed harness admission records are retained: landing epoch fault
alone did not detect the shifted gate date, and the first checker only tested
constant age. The fixed checker tests exact baseline ages. No token deadline
or production calendar changed. Objects remain in marker_03/obj; no old object
was deleted or used with a different source fingerprint.

The next source step uses this logical profile only if its epoch prerequisites
are made explicit. Six-frame arrival dates cannot be inferred by simply adding
station counts to frame return edges. Full frame/CAP/VP source proof still
requires real emission plans, input forwarded clocks/LK epochs, reset dates,
slot/config/dual-port lifetimes and SRAM commit timestamps.
