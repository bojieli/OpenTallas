# plain-relay hold-repair probe on the vT3 serdes__t14 post-CTS DB (read-only inputs; writes only under /p/rep)
source /p/hg_head.tcl
set blk [ord::get_db_block]
set lib_h DFFHQNx1_ASAP7_75t_R
set swapped 0; set refs {}
foreach i [$blk getInsts] {
  set n [$i getName]
  if {[string match {*u_rrl_*/q$_DFF_N_} $n]} { lappend refs [[$i getMaster] getName]; lappend sw $n }
}
puts "REL refs [lsort -unique $refs] n [llength $sw]"
proc relay_hold {tag} {
  set w 1e9; set cnt 0
  foreach pe [find_timing_paths -path_delay min -through [get_pins -hierarchical u_bound.u_rrl_*/*] -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] {
    set sp [get_full_name [get_property $pe startpoint]]; set ep [get_full_name [get_property $pe endpoint]]
    if {[string match {*u_rrl_*} $sp] && [string match {*u_rrl_*} $ep]} { incr cnt; set s [get_property $pe slack]; if {$s < $w} {set w $s} }
  }
  puts "REL $tag relay-to-relay hold: neg paths $cnt worst $w"
}
puts "REL design FF hold wns [sta::time_sta_ui [sta::worst_slack_cmd min]] n [sta::endpoint_violation_count min]"
relay_hold nl_before
foreach n $sw {
  set inst [get_cells [string map {[ \\[ ] \\]} $n]]
  replace_cell $inst $lib_h
}
estimate_parasitics -placement
puts "REL swapped [llength $sw] to $lib_h"
puts "REL design FF hold wns [sta::time_sta_ui [sta::worst_slack_cmd min]] n [sta::endpoint_violation_count min]"
relay_hold plain_before_repair
set before [llength [get_cells -quiet -hierarchical *]]
set cells [get_lib_cells -quiet */HB4xp67_ASAP7_75t_R]
if {[llength $cells]} { unset_dont_use $cells }
set t0 [clock seconds]
repair_timing -hold -hold_margin 5 -max_buffer_percent 100
puts "REL repair seconds [expr {[clock seconds]-$t0}]"
set hb 0; foreach i [$blk getInsts] { if {[[$i getMaster] getName] eq "HB4xp67_ASAP7_75t_R"} {incr hb} }
puts "REL HB4 cells $hb ; insts delta [expr {[llength [get_cells -quiet -hierarchical *]]-$before}]"
estimate_parasitics -placement
puts "REL design FF hold wns [sta::time_sta_ui [sta::worst_slack_cmd min]] n [sta::endpoint_violation_count min]"
relay_hold plain_after_repair
write_db /p/rep/relay_plain_repaired.odb
puts "REL done"
