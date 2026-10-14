# ref_tile PRE_GLOBAL_ROUTE: io_ref boundary + pin-access keepout (the layer ABOVE the outer face-pin
# column; created here, removed by post_drt.tcl, so the abstract carries only real metal: DRT-0073 at the parent)
source /src/physical/qwen_die_masters/pre_ref_skew.tcl
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/common_flow/grt_macro_top_layer.tcl

# Published structural macroedge routing guard; toggle adds beforeGRT/removes afterDRT.
source /src/physical/common_flow/macro_edge_via_guard.tcl
