# DIE-HEAD-18: forwarded-clock (fclk_out_o) arrival + chain in the routed DH17 hd_tile (GRT RC SPEF)
set c $::env(CORNER)
set pat [expr {$c eq "TT" ? "*RVT_TT*" : "*RVT_FF*"}]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] { read_liberty $l }
foreach l [glob /work/macros/*_[string tolower $c].lib] { read_liberty $l }
read_db /work/run/results/asap7/dp_hd_tile/base/5_1_grt.odb
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
read_spef /work/meas17g/grt.spef
catch {delete_generated_clock [get_clocks fclk_out_o]}
report_worst_slack -max
foreach pn {clk fclk_in_i fclk_out_o} {
  set p [get_ports $pn]
  set bt [[ord::get_db_block] findBTerm $pn]
  set bb [[lindex [$bt getBPins] 0] getBBox]
  puts "PORT $pn xy [expr [$bb xMin]/1000.0] [expr [$bb yMin]/1000.0]"
}
proc drv {netname} {
  foreach pp [get_pins -of_objects [get_nets $netname]] { if {[get_property $pp direction] eq "output"} { return $pp } }
  return ""
}
set net fclk_out_o
for {set k 0} {$k < 40} {incr k} {
  set d [drv $net]
  if {$d eq ""} { puts "CHAIN end net $net (no driver pin)"; break }
  set cell [get_cells -of_objects $d]
  set ref [get_property $cell ref_name]
  set loc [[ord::get_db_block] findInst [get_full_name $cell]]
  if {$loc eq "NULL" || $loc eq ""} { set xy {-1000 -1000} } else { set bb [$loc getBBox]; set xy [list [$bb xMin] [$bb yMin]] }
  set nl [llength [get_pins -of_objects [get_nets $net]]]
  puts "CHAIN $k [get_full_name $d] $ref xy [expr [lindex $xy 0]/1000.0] [expr [lindex $xy 1]/1000.0] out_max [get_property $d arrival_max_rise] out_min [get_property $d arrival_min_rise] net $net npins $nl"
  set in [lindex [get_pins -of_objects $cell -filter "direction==input"] 0]
  set net [get_full_name [get_nets -of_objects $in]]
}
foreach pp [get_pins -of_objects [get_nets fclk_out_o]] { puts "NETPIN [get_full_name $pp] [get_property $pp direction] amax [get_property $pp arrival_max_rise]" }
