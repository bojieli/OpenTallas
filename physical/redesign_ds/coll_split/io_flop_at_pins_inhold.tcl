# ds-coll 2026-10-12: PRE_GLOBAL_PLACE chain for the old-flow ceh tiles = pin flops at the face (io_flop_at_pins.tcl)
# THEN one input-hold pad per data input (leaf_inhold.tcl, VM8 181753c60: dont_touch HB4 hold cell + OT_INHOLD_DRV
# strong driver, both FIRM at the pin).  ces0 f9453c0d4 closed TT +41.06 but missed FF hold by -0.5 ps on 5
# input -> capture paths (hold repair stalled): deterministic delay stage at the inputs (owner 10-10), constraints unchanged.
set ot_ioih_dir [file dirname [file normalize [info script]]]
source [file join $ot_ioih_dir ../../qwen_die_masters/io_flop_at_pins.tcl]
source [file join $ot_ioih_dir ../../dsrom_window_source/leaf_inhold.tcl]
