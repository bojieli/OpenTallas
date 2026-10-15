# Actual routed same-edge return drive repair; baseline failure preserved.
set ::ot_lg_repair_net {u_core.rr_d[235]}
set ::ot_lg_repair_bit 235
source /src/physical/ref_tile/vm_lg_native_common_1015/return_drive_repair.tcl
# ref_tile PRE_GLOBAL_ROUTE: io_ref boundary + pin-access keepout (the layer ABOVE the outer face-pin
# column; created here, removed by post_drt.tcl, so the abstract carries only real metal: DRT-0073 at the parent)
source /src/physical/qwen_die_masters/pre_ref_skew.tcl
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/common_flow/grt_macro_top_layer.tcl
