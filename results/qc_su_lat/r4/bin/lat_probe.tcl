# QC-SU-LAT diagnostic: clock-path stage decomposition of a hard core at GRT RC (TT or FF). Read-only.
# env: P_ODB P_SDC P_LIBS (space list) P_CORNER (TT|FF) P_RC (setRC tcl) P_OUT
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
set fo [open $::env(P_OUT) w]
# per-sink latency + clock-cell depth
set n 0
foreach cp [get_pins -hierarchical */CLK] {
  set inst [get_cells -of_objects $cp]
  set arr [get_property $cp arrival_max_rise]
  if {$arr eq "" } continue
  # depth: walk back through buffer/inverter drivers on clock net
  set depth 0; set p $cp; set chain {}
  while {1} {
    set net [get_nets -of_objects $p]
    if {$net eq ""} break
    set drv [get_pins -of_objects $net -filter "direction==output"]
    if {$drv eq ""} break
    set dc [get_cells -of_objects $drv]
    lappend chain [get_property [get_lib_cells -of_objects $dc] name]
    incr depth
    set ip [get_pins -of_objects $dc -filter "direction==input"]
    if {[llength $ip] != 1} break
    set p $ip
    if {$depth > 60} break
  }
  puts $fo "[get_full_name $cp]\t[format %.2f [expr {$arr*1e12 > 1e6 ? $arr : $arr}]]\t$depth\t[join $chain ,]"
  incr n
}
close $fo
puts "LATPROBE done $n sinks"
exit
