# H16Z: same-region spatial clock distribution; source clock/edge unchanged.
set ::env(OT_SPINE_PORTS) ck_head
set ::env(OT_SPINE_SYM) 1
set ::env(OT_SPINE_RC_CAL) 0
set ::env(OT_SPINE_ITERS) 10
set ::env(OT_SPINE_BIN) 30
set ::env(OT_SPINE_LEAF_N) 16
source /src/physical/common_flow/clock_spine.tcl
