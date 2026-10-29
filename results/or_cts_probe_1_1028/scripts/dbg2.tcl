foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_db $::env(D)/tree.odb
create_clock -name clk -period 833.333 [get_ports clk]
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports clk]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_propagated_clock [all_clocks]
proc walk {tag} {
  set b [ord::get_db_block]; set i [$b findInst g14]; set pin CLK
  while {1} {
    set p [get_pins [$i getName]/$pin]
    set l [$i getLocation]
    puts "$tag [$i getName]/$pin [expr {[lindex $l 0]/1000.}] [expr {[lindex $l 1]/1000.}] arr [get_property $p arrival_max_rise] slew [get_property $p slew_max_rise]"
    set n [[$i findITerm $pin] getNet]; set d ""
    foreach t [$n getITerms] { if {[$t isOutputSignal]} { set d [$t getInst] } }
    if {$d eq ""} break
    set q [get_pins [$d getName]/Y]; puts "$tag   drv [$d getName] Y arr [get_property $q arrival_max_rise] slew [get_property $q slew_max_rise] fo [llength [$n getITerms]]"
    set i $d; set pin A
  }
}
estimate_parasitics -placement
walk PL
set_routing_layers -signal M2-M9 -clock M8-M9
global_route -allow_congestion
estimate_parasitics -global_routing
walk GR
