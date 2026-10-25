# CORE-HBM: post-route corner STA of a core kit (read-only).  make ... CORNER=TC|BC RUN_SCRIPT=core_sta.tcl run
# Prints CORE_STA <corner> setup_wns tns hold_wns hold_tns + clock insertion (min/mean/max to the flop CK pins) + skew.
source $::env(SCRIPTS_DIR)/load.tcl
set odb 5_route.odb
if {[file exists $::env(RESULTS_DIR)/6_final.odb]} { set odb 6_final.odb }
load_design $odb 4_cts.sdc
set_propagated_clock [all_clocks]
set c $::env(CORNER)
if {[env_var_exists_and_non_empty RCX_RULES] && [file exists $::env(RCX_RULES)]} {
  define_process_corner -ext_model_index 0 X
  extract_parasitics -ext_model_file $::env(RCX_RULES)
  set par rcx
} else { estimate_parasitics -placement; set par placement }
set ws [sta::worst_slack -max]; set wh [sta::worst_slack -min]
set ts [sta::total_negative_slack -max]; set th [sta::total_negative_slack -min]
set lat {}
foreach p [get_pins -hierarchical */CLK] {
  set a [get_property $p arrival_max_rise]
  if {$a ne "" && $a ne "INF"} { lappend lat $a }
}
set n [llength $lat]
if {$n} { set s [lsort -real $lat]; set mn [lindex $s 0]; set mx [lindex $s end]; set sum 0; foreach v $s { set sum [expr {$sum+$v}] } ; set me [expr {$sum/$n}] } else { set mn -; set mx -; set me - }
puts [format "CORE_STA %s par=%s setup_wns %.1f tns %.1f hold_wns %.1f hold_tns %.1f ck_pins %d insertion_min %s mean %s max %s" $c $par $ws $ts $wh $th $n $mn $me $mx]
report_clock_skew
if {[catch {report_clock_latency} e]} { puts "no report_clock_latency: $e" }
report_checks -path_delay max -group_path_count 3 -format end
report_checks -path_delay min -group_path_count 3 -format end
puts "DONE $c"
