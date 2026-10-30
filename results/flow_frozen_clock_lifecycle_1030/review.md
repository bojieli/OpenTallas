# RING frozen-clock lifecycle: source and read-only control

The opt-in callback runs immediately after native GLOBAL estimation, before the
first timing consumer and all MM/hold refresh consumers. Defaults leave the
native command/placement path unchanged. Exact tc/BC datasets receive only the
prequalified clock-only SPEF through the approved named helper. Existing active
routed freeze plus original graph/wire/pin/master/home identity is mandatory.
The late PRD path skips its old FULL-SPEF replay and original-freeze reset when
this feature is enabled. No coupling transformation or timing threshold changes.

One read-only same-DPL-seed control used the original1359clock wires and26394
clock instances, with0wire re-encodes and0movable clock instances. Existing
clk_dump/clk_geom_diff accepted the immutable original clock graph. All145605
native DATA nets retain exact total+wire capacitance at both corners/min+max
around the automatic named restore:0changed values/0delta. The FIRST consumer
after estimate returns TT255.238903871ps and FF206.799218479ps over2384boundary
pins, matching original clock RCX. POST_GLOBAL_ROUTE_TCL was never sourced;
no placement, routing or output ODB ran. This proves the lifecycle callback on
the qualified seed, not an end-to-end physical reroute or SIGNED result.

Three focused Tcl tests cover default command identity, all five initial/MM/
calibrated-refresh ordering points, unarmed/empty freeze, wrong-corner map,
changed clock graph, missing identity, and PRD refusal to replay old DATA.
The source proposal was independently reviewed by FLOW. Physical retry remains
HBM/root authority. Caller must stage helpers, arm the original clock freeze
before routing/estimation, and supply immutable source identity and qualified
clock-only files. An absent epcy2-local ot-run client caused the first launcher
to NOT RUN; the actual control ran once through intel2 ot-run on epyc2(unit1202087).
