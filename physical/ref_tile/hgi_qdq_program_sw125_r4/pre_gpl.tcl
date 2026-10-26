# ref_tile PRE_GLOBAL_PLACE (kit recipe 2): the hold stages are inserted FIRM at the pins first, then every
# port's single launch / capture flop is traced THROUGH them (OT_OFLOP_HOPS) and fixed at its pin.  ORFS takes
# one hook per step, so the two repo hooks are sourced from this kit file.
source /src/physical/common_flow/pin_reg_split.tcl
source /src/physical/dsrom_window_source/leaf_iohold.tcl
source /src/physical/ref_tile/qdq_sw125_programme_command_pad_r4.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
