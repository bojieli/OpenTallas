source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 5_1_grt.sdc
set_propagated_clock [all_clocks]
help insert_buffer
set block [ord::get_db_block]
foreach n {_000088_ _000080_} {
  set net [$block findNet $n]
  puts "OT_NET $n"
  foreach it [$net getITerms] {puts "OT_TERM [[$it getInst] getName]/[[$it getMTerm] getName] [[$it getInst] getLocation]"}
}
exit
