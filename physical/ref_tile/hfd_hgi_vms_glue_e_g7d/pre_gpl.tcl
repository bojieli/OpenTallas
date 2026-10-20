# ref_tile PRE_GLOBAL_PLACE (flop-first, hold_budget die): no pin hold stages; every port's single
# launch / capture flop is fixed at its pin.  ORFS takes one hook per step, so the repo hooks are
# sourced from this kit file.
source /src/tools/hbm_die_v16/vms_relay_lattice.tcl
source /src/tools/hbm_die_v16/vms_inplace_hold.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
