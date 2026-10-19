# ref_tile PRE_GLOBAL_PLACE (flop-first, hold_budget die): no pin hold stages; every port's single
# launch / capture flop is fixed at its pin.  ORFS takes one hook per step, so the repo hooks are
# sourced from this kit file.
source /src/physical/ref_tile/qkd_hr_core_order_s2b/band_fence.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
