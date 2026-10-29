# ot-clk bench_cts (from OR-CTS-PROBE-1 @76e78b8c01): TritonCTS on one extracted region. env: CORNER (TT builds the tree; FF re-times the TT tree), D (case dir), V (variant), OPTS
set t0 [clock milliseconds]
set D $::env(D); set V $::env(V); set C $::env(CORNER)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
proc ot_fix {n x y} { set b [ord::get_db_block]; set i [$b findInst $n]; set d [[$b getTech] getDbUnitsPerMicron]; $i setLocation [expr {round($x*$d)}] [expr {round($y*$d)}]; $i setPlacementStatus FIRM }
foreach f [glob $P/lib/NLDM/*RVT_${C}_nldm*.lib*] { read_liberty $f }
if {[file exists $D/sink_$C.lib]} { read_liberty $D/sink_$C.lib }
if {$C eq "TT"} {
  read_lef $P/lef/asap7_tech_1x_201209.lef
  read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
  if {[file exists $D/sink.lef]} { read_lef $D/sink.lef }
  read_verilog $D/region.v
  link_design region
  source $D/place.tcl
  initialize_floorplan -die_area $DIE -core_area $DIE -site asap7sc7p5t
  source $::env(TRACKS)
  source $D/place.tcl
  place_pin -pin_name clk -layer M8 -location $ROOT -pin_size {0.32 0.32}
} else {
  read_db $D/$V/tree.odb
}
create_clock -name clk -period 833.333 [get_ports clk]
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports clk]
source $P/setRC.tcl
set_wire_rc -clock -layer M8
if {$C eq "TT"} {
  set tc [clock milliseconds]
  eval clock_tree_synthesis -root_buf BUFx24_ASAP7_75t_R -buf_list {{BUFx24_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx12f_ASAP7_75t_R}} $::env(OPTS)
  puts "OT_CTS_MS [expr {[clock milliseconds]-$tc}]"
  set_placement_padding -global -left 0 -right 0
  if {[catch {detailed_placement} e]} { puts "OT_DPL_ERR $e" }
  if {[catch {check_placement -verbose} e]} { puts "OT_CHECK_PLACEMENT_FAIL $e" }
  create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}
  foreach n [get_nets *] { if {[get_full_name $n] ne "clk" || 1} { } }
}
set_propagated_clock [all_clocks]
set_routing_layers -signal M2-M9 -clock M8-M9
if {$C eq "TT"} { assign_ndr -ndr CK2W2S -all_clocks }
global_route -allow_congestion -verbose
estimate_parasitics -global_routing
if {[catch {grt::report_layer_wire_lengths} e]} { puts "OT_NO_LAYER_WL $e" }
report_wire_length -net * -global_route -summary
set fh [open $D/$V/arr_$C.txt w]
foreach p [get_pins -hierarchical */CLK] { puts $fh "S [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall]" }
foreach p [get_pins -hierarchical */clk*] { puts $fh "S [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise] [get_property $p arrival_max_fall]" }
set nb 0; foreach i [get_cells *] { set m [get_property $i ref_name]; if {[string match BUF* $m]} { incr nb; set l [[[ord::get_db_block] findInst [get_full_name $i]] getLocation]; puts $fh "B [get_full_name $i] $m [expr {[lindex $l 0]/double([[ord::get_db_tech] getDbUnitsPerMicron])}] [expr {[lindex $l 1]/double([[ord::get_db_tech] getDbUnitsPerMicron])}]" } }
close $fh
puts "OT_NBUF $nb"
report_clock_skew
report_clock_latency
report_check_types -max_slew -max_capacitance -violators
set_power_activity -global -activity 0.1
report_power
if {$C eq "TT"} { write_db $D/$V/tree.odb; write_def $D/$V/tree.def }
puts "OT_TOTAL_MS [expr {[clock milliseconds]-$t0}]"
puts OT_DONE
