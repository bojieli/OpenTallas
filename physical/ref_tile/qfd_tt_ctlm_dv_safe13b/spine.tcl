# Same clock families/edges; physical local subroots, no new domain boundary.
set ::env(OT_SPINE_PORTS) ck_core,ck_hr
set ::env(OT_SPINE_SYM) 1
set ::env(OT_SPINE_RC_CAL) 0
set ::env(OT_SPINE_ITERS) 10
set ::env(OT_SPINE_BIN) 30
set ::env(OT_SPINE_LEAF_N) 8
source /src/physical/common_flow/clock_spine.tcl
