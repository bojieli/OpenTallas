# Existing typed PHY export: preserve the logical clock and every timing policy,
# but bind its source to the actually connected port after physical tap splitting.
# Only the generator-owned pma_tck-from-clk contract calls this helper.
proc ot_phy_json_string {s} {
 return "\"[string map [list "\\" "\\\\" "\"" "\\\"" "\n" "\\n" "\r" "\\r"] $s]\""
}
proc ot_phy_export_rebind {cfg} {
 if {![llength [info commands ord::get_db_block]]} {return}
 set block [ord::get_db_block]
 set target [dict get $cfg target]
 set declared [dict get $cfg declared_source]
 set clock [dict get $cfg clock]
 set master [dict get $cfg master]
 set bt [$block findBTerm $target]
 if {$bt eq "NULL" || $bt eq ""} {return}
 set clocks [get_clocks -quiet [list $clock]]
 set masters [get_clocks -quiet [list $master]]
 if {[llength $clocks]!=1 || [llength $masters]!=1 || ![get_property $clocks is_generated]} {return}
 if {abs([get_property $masters period]-[dict get $cfg period])>0.000001} {return}
 set roots {};set chain {};set todo [list [$bt getNet]];set seen [dict create];set inv 0;set valid 1
 for {set at 0} {$at<[llength $todo]} {incr at} {
  set net [lindex $todo $at]
  if {$net eq "NULL" || $net eq "" || [dict exists $seen $net]} {set valid 0;break}
  dict set seen $net 1
  foreach p [$net getBTerms] {if {[$p getIoType] eq "INPUT"} {lappend roots [$p getName]}}
  set drivers {};foreach p [$net getITerms] {if {[$p getIoType] eq "OUTPUT"} {lappend drivers $p}}
  if {![llength $drivers]} {continue}
  if {[llength $drivers]!=1} {set valid 0;break}
  set drv [lindex $drivers 0];set inst [$drv getInst];set name [[$inst getMaster] getName]
  if {![regexp {^(BUF|INV)} $name]} {set valid 0;break}
  if {[string match INV* $name]} {incr inv}
  lappend chain [$inst getName]
  set inputs {};foreach p [$inst getITerms] {
   if {[$p getIoType] eq "INPUT" && [$p getSigType] ni {POWER GROUND}} {lappend inputs $p}
  }
  if {[llength $inputs]!=1} {set valid 0;break}
  lappend todo [[lindex $inputs 0] getNet]
 }
 set master_ports {};foreach p [get_property $masters sources] {lappend master_ports [get_full_name $p]}
 set roots [lsort -unique $roots];set actual ""
 # A direct raw-root alias is still a valid path; never rebase it blindly.
 if {$declared in $roots} {set actual $declared
 } elseif {[llength $roots]==1 && [lindex $roots 0] in $master_ports} {set actual [lindex $roots 0]}
 if {!$valid || $inv%2 || $actual eq ""} {
  puts "OT_PHY_CLOCK_EXPORT unresolved target=$target roots=$roots buffer_only=$valid inversion=$inv"
  return
 }
 set state UNCHANGED
 if {$actual ne $declared} {
  set propagated [get_property $clocks is_propagated]
  # Exact embedded OpenSTA Sdc::makeGeneratedClock reuses this same Clock;
  # do not remove_clock: its uncertainty, IO latency and CDC exceptions survive.
  create_generated_clock -name $clock -master_clock $master -source [get_ports [list $actual]] -divide_by 1 [get_ports [list $target]]
  if {$propagated} {set_propagated_clock [get_clocks [list $clock]]
  } else {unset_propagated_clock [get_clocks [list $clock]]}
  set state REBOUND
 }
 set out [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : [file dirname [info script]]}]
 set f [open [file join $out phy_clock_export_binding.json] w]
 puts $f [format {{"schema":"opentallas.phy_clock_export_binding.v1","target":%s,"clock":%s,"master":%s,"declared_source":%s,"realized_source":%s,"period_ps":%s,"status":%s,"buffer_instances":%d,"only_source_identity_changed":true}} [ot_phy_json_string $target] [ot_phy_json_string $clock] [ot_phy_json_string $master] [ot_phy_json_string $declared] [ot_phy_json_string $actual] [dict get $cfg period_ps] [ot_phy_json_string $state] [llength $chain]]
 close $f
 puts "OT_PHY_CLOCK_EXPORT $state target=$target declared=$declared realized=$actual master=$master period=[get_property $masters period] buffer_instances=[llength $chain]"
}
