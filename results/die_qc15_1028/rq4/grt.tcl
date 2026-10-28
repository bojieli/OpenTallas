# DIE-QC-15: routed (GRT, calibrated setRC_rcx) recheck of the DIE-QC-14 A0 trunk q4: arrivals rise/fall + slew at every clock pin
source /w/common.tcl
read_db $::env(ODB)
set blk [ord::get_db_block]
set gi [$blk findInst a0t_icg]
if {$gi ne "NULL"} { [$gi findITerm ENA] disconnect; [$gi findITerm SE] disconnect }
read_sdc /p/constraint.sdc
set_propagated_clock [all_clocks]
source /p/setRC_rcx.tcl
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -signal M2-M7 -clock M4-M7
# clock pre-route (METHODOLOGY infra-first: PG -> clock -> reset pre-routed, then signals): GRT on the clock nets
# only; signal nets are flagged special for the GRT step so FastRoute skips them (clock arrivals do not depend on them)
set nsig 0
foreach n [$blk getNets] { set t [$n getSigType]; if {$t ne "CLOCK" && $t ne "POWER" && $t ne "GROUND" && ![$n isSpecial]} { $n setSpecial; incr nsig } }
puts "signal nets skipped for clock GRT: $nsig"
global_route -allow_congestion -verbose
estimate_parasitics -global_routing
set fh [open $::env(OUT) w]
foreach p [get_pins -hier * -filter "is_clock==1"] {
  set inst [get_cells -of_objects $p]; set m [get_property $inst ref_name]
  set n [get_full_name [get_nets -of_objects $p]]
  puts $fh "S [get_full_name $p] $m $n [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_rise] [get_property $p slew_max]"
}
foreach i [get_cells -hier {a0cl*_root a0t_*}] {
  foreach pn {A Y GCLK CLK} {
    set p [get_pins -quiet [get_full_name $i]/$pn]
    if {$p ne ""} { puts $fh "T [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_rise] [get_property $p slew_max]" }
  }
}
set ms 0; set mp ""
foreach p [get_pins -hier */Y] { set s [get_property $p slew_max]; if {$s ne "" && $s > $ms} { set ms $s; set mp [get_full_name $p] } }
puts $fh "MAXSLEW_Y $mp $ms"
close $fh
report_check_types -max_slew -violators > $::env(OUT).slewviol
