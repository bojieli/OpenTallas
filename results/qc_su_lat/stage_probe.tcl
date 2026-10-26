# QC-SU-LAT: per-stage clock arrival along the chain to a few sinks (TT, GRT RC). env as lat_probe + P_SINKS
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
set ck [get_ports ck]
puts "PORT ck xy [ord::dbu_to_microns [[[[ord::get_db_block] findBTerm ck] getBBox] xMin]] [ord::dbu_to_microns [[[[ord::get_db_block] findBTerm ck] getBBox] yMin]]"
set fh [open $::env(P_SINKS)]; set sl [split [string trim [read $fh]] "\n"]; close $fh
foreach s $sl {
  set cp [get_pins -quiet [string map {"\[" "\\\[" "\]" "\\\]"} $s]]; if {$cp eq ""} {puts "NOSINK $s"; continue}
  set p $cp; set out {}
  while {1} {
    set net [get_nets -of_objects $p]
    if {$net eq ""} break
    set drv [get_pins -of_objects $net -filter "direction==output"]
    if {$drv eq ""} { lappend out "PORT"; break }
    set dc [get_cells -of_objects $drv]
    set inst [[ord::get_db_block] findInst [get_full_name $dc]]
    lassign [$inst getLocation] x y
    set ip [get_pins -of_objects $dc -filter "direction==input"]
    lappend out "[get_property [get_lib_cells -of_objects $dc] name]([format %.0f [ord::dbu_to_microns $x]],[format %.0f [ord::dbu_to_microns $y]]) in=[get_property [lindex $ip 0] arrival_max_rise] out=[get_property $drv arrival_max_rise] slew=[get_property $drv slew_max_rise] fo=[llength [get_pins -of_objects $net -filter direction==input]]"
    if {[llength $ip] != 1} break
    set p $ip
  }
  puts "SINK $s arr=[get_property $cp arrival_max_rise]"
  foreach o [lreverse $out] { puts "   $o" }
}
exit
