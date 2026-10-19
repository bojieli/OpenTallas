# ref_tile PRE_GLOBAL_PLACE (flop-first, hold_budget die): no pin hold stages; every port's single
# launch / capture flop is fixed at its pin.  ORFS takes one hook per step, so the repo hooks are
# sourced from this kit file.
source /src/physical/common_flow/pin_reg_split.tcl
source /src/physical/ref_tile/qfd_d2d_static_r8c/local_reset_capture.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
source /src/physical/ref_tile/qfd_d2d_static_safe4/reset_copy_select.tcl
source /src/physical/common_flow/same_edge_reset_copies.tcl

set ::ot_control_copy_regexp {.}
set ::ot_control_copy_manifest [file join $::env(RESULTS_DIR) ot_control_copy_manifest.tcl]
source /src/physical/common_flow/same_edge_control_copies.tcl
