export MACRO_PLACEMENT_TCL = /work/macro_placement.tcl
export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl
export SET_RC_TCL = /work/setRC_rcx.tcl
override export POST_CTS_TCL = /work/f4_chain_leaf.tcl
export OT_F4_NEXT_TCL = /work/tap_balance.tcl
# HBM-CORES-R10 2026-10-27T10:34:19: route of the R7 trial placement (GEOM-24 PASS-COND, GRT 50-it overflow 0) with the shared
# collar-a5 recipe (max_wire_length 60 POST_RESIZE, SLEW_MARGIN 20, GRT FF hold margin 10) + HB4 hold pad (core_grt_pre).
# Placement re-runs from 3_3 (3_4 onward deleted). Clock hooks unchanged from the kit.
export SLEW_MARGIN = 20
export OT_MAX_WIRE_UM = 60
export POST_RESIZE_TCL = /work/max_wire_repair.tcl
override export OT_HOLD_FF_MARGIN = 10
