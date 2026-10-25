# ref_tile PRE_GLOBAL_PLACE (kit recipe 2): the hold stages are inserted FIRM at the pins first, then every
# port's single launch / capture flop is traced THROUGH them (OT_OFLOP_HOPS) and fixed at its pin.  ORFS takes
# one hook per step, so the two repo hooks are sourced from this kit file.
source /src/physical/common_flow/pin_reg_split.tcl
source /src/physical/dsrom_window_source/leaf_iohold.tcl
source /src/tools/qwen_romleaf/rc14_2000/baseline/nk_rc13_regions.tcl
source /src/tools/qwen_romleaf/rc15_2000/local_request_decode.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
