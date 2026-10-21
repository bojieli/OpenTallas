# Database-only composition harness: canonical final scripts remain unchanged.
proc erase_non_stage_variables {args} {}
proc load_design {args} {read_db $::env(TEST_ODB)}
proc source_step_tcl {pre step} {source $::env(TEST_BOOTSTRAP)}
proc set_propagated_clock {args} {}
proc all_clocks {} {return {}}
proc orfs_write_db {path} {write_db $path}
proc orfs_write_sdc {path} {puts "TEST_NO_SDC_WRITE $path"}
