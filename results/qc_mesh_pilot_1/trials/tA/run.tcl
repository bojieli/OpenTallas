
set t0 [clock seconds]
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_def /o/pilot.def
source $P/openRoad/make_tracks.tcl
create_clock -name dck -period 833.0 [get_ports root]
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 $::env(ADJ)
set_global_routing_layer_adjustment M9 $::env(ADJ)
# die clock on M8/M9 only (12.1a: M1-M7 belong to the partition/cores); M2-M7 only for the pin stacks
foreach L {M2 M3 M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.99 }
create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}
foreach n [get_nets n_*] { assign_ndr -ndr CK2W2S -net [get_full_name $n] }
global_route -congestion_iterations 50 -allow_congestion -verbose
write_guides /o/route.guide
proc dump {tag corner} {
  set fh [open /o/tree_${tag}_${corner}.txt w]
  foreach c [get_cells *] {
    set n [get_full_name $c]
    if {[string match L_* $n]} { set pins {A} } else { set pins {A Y} }
    foreach pn $pins {
      set p [get_pins $n/$pn]
      puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
    }
  }
  close $fh
}
proc timing {} {
  create_clock -name vclk -period 833.0
  set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
  set_input_delay 0 -clock vclk [get_ports root]
  foreach c [get_cells M*] { set_disable_timing $c }
}
source $P/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
timing
dump grt TT
puts "OT_T grt [expr {[clock seconds]-$t0}]"
detailed_route -output_drc /o/drc.rpt -verbose 0
puts "OT_T drt [expr {[clock seconds]-$t0}]"
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef /o/drt.spef
dump drt TT
write_db /o/drt.odb
write_def /o/drt.def
puts "OT_DONE [expr {[clock seconds]-$t0}]"
