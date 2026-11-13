# HOLD-TAP-1: every FF hold violating endpoint by class (port-in / reg-reg / port-out), per launch clock
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
if {[info exists ::env(LAYER_PARASITICS_FILE)] && $::env(LAYER_PARASITICS_FILE) ne ""} { source $::env(LAYER_PARASITICS_FILE) } else { source $::env(PLATFORM_DIR)/setRC.tcl }
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF) } else { estimate_parasitics -placement }
if {[info exists ::env(OT_VCLK_FF)] && $::env(OT_VCLK_FF) ne ""} { set_clock_latency -source $::env(OT_VCLK_FF) [get_clocks vclk] }
set ps [find_timing_paths -path_delay min -group_path_count 3000000 -endpoint_path_count 1 -slack_max 0]
set f [open $::env(OUT) w]
puts $f "slack\tclass\tsclk\teclk\tstart\tend\tdata_arr\trequired\ttgt_clk_delay"
array set cnt {}; array set ws {}
foreach pe $ps {
  set s [sta::time_sta_ui [$pe slack]]
  set p0 [get_property $pe startpoint]; set pN [get_property $pe endpoint]
  set a [expr {[sta::sta_to_db_pin $p0] eq "NULL" ? "port" : "reg"}]
  set b [expr {[sta::sta_to_db_pin $pN] eq "NULL" ? "port" : "reg"}]
  set sc ""; set ec ""
  catch {set sc [get_full_name [get_property $pe startpoint_clock]]}
  catch {set ec [get_full_name [get_property $pe endpoint_clock]]}
  set k "$a>$b"
  if {![info exists cnt($k)]} { set cnt($k) 0; set ws($k) 0 }
  incr cnt($k); if {$s < $ws($k)} { set ws($k) $s }
  puts $f [format "%.2f\t%s\t%s\t%s\t%s\t%s\t%.2f\t%.2f\t%.2f" $s $k $sc $ec [get_full_name $p0] [get_full_name $pN] [sta::time_sta_ui [$pe data_arrival_time]] [sta::time_sta_ui [$pe data_required_time]] [sta::time_sta_ui [$pe target_clk_delay]]]
}
close $f
foreach k [lsort [array names cnt]] { puts "ALL_DIAG $k n $cnt($k) ws $ws($k)" }
puts "ALL_DIAG total [llength $ps] ws [sta::time_sta_ui [sta::worst_slack_cmd min]]"
