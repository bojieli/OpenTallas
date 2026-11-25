# ref_tile PRE_GLOBAL_ROUTE: io_ref boundary + pin-access keepout (the layer ABOVE the outer face-pin
# column; created here, removed by post_drt.tcl, so the abstract carries only real metal: DRT-0073 at the parent)
source /src/physical/qwen_die_masters/pre_ref_skew.tcl
if {[file exists /src/physical/ref_tile/s81su_kvleaf_kvtcp_h18/stn_pin_keepout.tcl]} { source /src/physical/ref_tile/s81su_kvleaf_kvtcp_h18/stn_pin_keepout.tcl } else { puts "REF_TILE WARNING: /src/physical/ref_tile/s81su_kvleaf_kvtcp_h18/stn_pin_keepout.tcl is not in the kit: the face-pin keepout toggle is skipped" }
source /src/physical/common_flow/grt_macro_top_layer.tcl
