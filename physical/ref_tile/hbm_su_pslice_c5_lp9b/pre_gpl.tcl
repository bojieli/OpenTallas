# ref_tile PRE_GLOBAL_PLACE (flop-first, hold_budget die): no pin hold stages; every port's single
# launch / capture flop is fixed at its pin.  ORFS takes one hook per step, so the repo hooks are
# sourced from this kit file.
source /src/tools/ref_tile/specs_hbm_su/hbm_su_pslice_c5_lp9b_fences.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
