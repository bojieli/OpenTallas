source /src/physical/ref_tile/dsdv_mu_hwin_c21q/hwin_native_fences.tcl
# ref_tile PRE_GLOBAL_ROUTE: io_ref boundary + pin-access keepout (the layer ABOVE the outer face-pin
# column; created here, removed by post_drt.tcl, so the abstract carries only real metal: DRT-0073 at the parent)
source /src/physical/qwen_die_masters/pre_ref_skew.tcl
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/common_flow/grt_macro_top_layer.tcl
source /src/physical/qwen_die_masters/sram_edge_guard.tcl

# S81-HWIN-1021: skip ORFS post-GRT vt_swap/reroute WNS pass (EST-0104 after in-DPL PG birth bind)
set ::env(OPT_POST_GRT_WNS) 0
puts "HWIN_OPT_POST_GRT_WNS=0"
