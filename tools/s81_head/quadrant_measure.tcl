# Read-only CTS diagnostic at placement RC. Never a sign-off receipt.
set C $::env(OT_CORNER)
set c [string tolower $C]
set lib /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach group {AO INVBUF OA SEQ SIMPLE} {
  set files [lsort [glob $lib/asap7sc7p5t_${group}_RVT_${C}_nldm_*]]
  read_liberty [lindex $files 0]
}
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_db $::env(ODB)
read_sdc /work/constraint_pd.sdc
source /work/setRC_rcx.tcl
if {[info exists ::env(OT_MEASURE_GRT)] && $::env(OT_MEASURE_GRT)} {
  set_routing_layers -signal M2-M5 -clock M2-M5
  global_route -allow_congestion -congestion_iterations 50
  estimate_parasitics -global_routing
  write_db /work/quadrant_grt_${C}.odb
  write_guides /work/quadrant_grt_${C}.guide
  set label quadrant_grt
  set mode GRT_RC_DIAGNOSTIC
} else {
  estimate_parasitics -placement
  set label quadrant
  set mode DIAGNOSTIC_PLACEMENT_RC
}
set_propagated_clock [get_clocks clk]
set b [ord::get_db_block]
set qcache [dict create]
set instances [dict create]
foreach i [$b getInsts] { dict set instances [string map [list [format %c 92] ""] [$i getName]] $i }
proc qroot {net depth} {
  if {$net eq "NULL" || $depth > 30} { return OTHER }
  set n [$net getName]
  if {[regexp {^clk_q(WS|WN|ES|EN)$} $n -> key]} { return $key }
  if {$n eq "clk_m"} { return M }
  if {[dict exists $::qcache $n]} { return [dict get $::qcache $n] }
  foreach it [$net getITerms] {
    if {[$it getIoType] ne "OUTPUT"} continue
    set i [$it getInst]
    foreach inp [$i getITerms] {
      if {[$inp getIoType] ne "INPUT" || [[$inp getMTerm] getSigType] in {POWER GROUND}} continue
      set root [qroot [$inp getNet] [expr {$depth+1}]]
      if {$root ne "OTHER"} { dict set ::qcache $n $root; return $root }
    }
  }
  dict set ::qcache $n OTHER
  return OTHER
}
set samples [dict create]
foreach p [get_pins -hier -filter "name==CLK"] {
  set name [get_full_name $p]
  set iname [get_full_name [get_cells -of_objects $p]]
  if {![dict exists $instances $iname]} continue
  set inst [dict get $instances $iname]
  set it [$inst findITerm CLK]
  if {$it eq "NULL"} continue
  set a [get_property $p arrival_max_rise]
  if {$a eq ""} continue
  dict lappend samples [qroot [$it getNet] 0] $a
}
dict for {key vals} $samples {
  set vals [lsort -real $vals]
  set mean [expr {[tcl::mathop::+ {*}$vals]/double([llength $vals])}]
  puts [format "QMEASURE %s %s n %d min %.2f mean %.2f max %.2f" $C $key [llength $vals] [lindex $vals 0] $mean [lindex $vals end]]
}
puts "QMEASURE $C ALL_HOLD [expr {[sta::worst_slack_cmd min]*1e12}] ALL_SETUP [expr {[sta::worst_slack_cmd max]*1e12}] $mode"
report_checks -path_delay min -group_path_count 8 -format full_clock_expanded > /work/${label}_${C}_min.rpt
