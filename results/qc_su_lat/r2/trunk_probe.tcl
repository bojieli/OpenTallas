# QC-SU-LAT-R2: arrival/slew at every structure cell output (root, entry, trunk stages, taps, macro leaves) + net wire length, GRT RC. Read-only.
set c $::env(P_CORNER)
set pat [expr {$c eq "TT" ? "*_RVT_TT_*" : "*_RVT_FF_*"}]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] {read_liberty $l}
foreach l $::env(P_LIBS) {read_liberty $l}
read_db $::env(P_ODB)
read_sdc $::env(P_SDC)
source $::env(P_RC)
set_routing_layers -signal M2-M5 -clock M2-M5
global_route -congestion_iterations 30 -allow_congestion
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set blk [ord::get_db_block]
foreach i [lsort [lmap x [$blk getInsts] {expr {[string match ot_ms_* [$x getName]] && ![string match ot_ms_pad* [$x getName]] ? [$x getName] : [continue]}}]] {
  set cell [get_cells $i]; set o [lindex [get_pins -of_objects $cell -filter "direction==output"] 0]; set in [lindex [get_pins -of_objects $cell -filter "direction==input"] 0]
  if {$o eq "" || $in eq ""} continue
  set ai ""; set ao ""; set so ""; catch {set ai [get_property $in arrival_max_rise]; set ao [get_property $o arrival_max_rise]; set so [get_property $o slew_max_rise]}
  if {$ai eq "" || $ao eq ""} { puts "TRUNK $i unconstrained"; continue }
  set inst [$blk findInst $i]; lassign [$inst getLocation] x y
  set n [$inst findITerm Y]; set fo 0; if {$n ne "NULL" && [$n getNet] ne "NULL"} { set fo [llength [[$n getNet] getITerms]] }
  puts [format "TRUNK %-22s %-20s (%6.1f,%6.1f) in %7.1f out %7.1f slew %6.1f fo %d" $i [get_property [get_lib_cells -of_objects $cell] name] [expr {$x/1000.0}] [expr {$y/1000.0}] $ai $ao $so [expr {$fo-1}]]
}
exit
