# DIE-QC-45: re-run of DIE-QC-44 TRIAL1 G2 (grt_leaf.tcl, -clock M4-M7, same source/settings) + a FULL edge readout
# for main trial_tap_arrivals.py: every die clock cell (ck_*) Y rise/fall max/min + master, every core tap pin
# rise/fall max/min + rise slew.  Polarity is resolved offline (parity walk over tree parent_of).
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set O $::env(OUT)
set C $::env(CORNER)
foreach f [glob $P/lib/NLDM/*RVT_${C}_nldm*.lib*] { read_liberty $f }
read_db /s/codex-qc-2249/complete_pg/provider.odb
create_clock -name dck -period 833.000 [get_ports root]
set_propagated_clock [all_clocks]
source $P/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M7
foreach L {M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.75 }
set_global_routing_layer_adjustment M8 0
set_global_routing_layer_adjustment M9 0
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file $O/congestion.rpt
puts QC45_GRT_DONE
estimate_parasitics -global_routing
read_spef /s/die-qc-44/grt/clock.spef
puts QC45_SPEF_READ
set fh [open $O/edges_raw.txt w]
set n 0
foreach inst [[ord::get_db_block] getInsts] {
  set nm [$inst getName]
  if {[string range $nm 0 2] ne "ck_"} continue
  set p [get_pins -quiet $nm/Y]
  if {![llength $p]} { puts $fh "C $nm [[$inst getMaster] getName] NA"; continue }
  puts $fh "C $nm [[$inst getMaster] getName] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall]"
  incr n
}
puts "QC45_CELLS $n"
set tf [open /s/die-qc-44/grt/taps.txt]
while {[gets $tf l] >= 0} {
  lassign $l t inst pin x y
  set p [get_pins -quiet $inst/$pin]
  if {[llength $p]} {
    set drv ""
    set net [get_nets -quiet -of_objects $p]
    if {[llength $net]} { foreach dp [get_pins -quiet -of_objects $net -filter "direction==output"] { set drv [get_full_name $dp] } }
    puts $fh "T $t [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_rise] $drv"
  } else { puts $fh "T $t NA" }
}
close $tf
close $fh
puts QC45_ARR_DONE
