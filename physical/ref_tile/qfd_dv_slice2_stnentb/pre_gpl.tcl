# ref_tile PRE_GLOBAL_PLACE (flop-first, hold_budget die): no pin hold stages; every port's single
# launch / capture flop is fixed at its pin.  ORFS takes one hook per step, so the repo hooks are
# sourced from this kit file.
source /src/tools/ref_tile/specs_qw_slice4/qfd_dv_slice2_stnentb_fences.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
