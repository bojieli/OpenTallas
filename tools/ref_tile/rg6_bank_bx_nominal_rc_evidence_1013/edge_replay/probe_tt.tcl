set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /probe/bank_Q/ot_qfd_vm_bank_t.lef
read_liberty /probe/bank_Q/ot_qfd_vm_bank_t_tt.lib
read_lef /probe/existing_BX_D/ot_qwen_tree_delay1_t.lef
read_liberty /probe/existing_BX_D/ot_qwen_tree_delay1_t_tt.lib
read_verilog /probe/pair.v
link_design pair
set sites {}
foreach lib [[ord::get_db] getLibs] {foreach site [$lib getSites] {lappend sites [$site getName]}}
set sites [lsort -unique $sites]
if {[llength $sites]!=1} {error "ambiguous actual placement site"}
initialize_floorplan -site [lindex $sites 0] -die_area {0 0 345.6 211.68} -core_area {0 0 345.6 211.68}
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set i [$block findInst bank]
$i setLocation [expr {round(90.72*$dbu)}] [expr {round(10.8*$dbu)}]
$i setOrient R0
$i setPlacementStatus FIRM
set bt [$block findBTerm ca]
set bp [odb::dbBPin_create $bt]
$bp setPlacementStatus FIRM
set layer [[ord::get_db_tech] findLayer M5]
odb::dbBox_create $bp $layer [expr {round(194.736*$dbu)}] [expr {round(10.8*$dbu)}] [expr {round(194.76*$dbu)}] [expr {round(12.937000000000001*$dbu)}]
set actual [[$i findITerm clk] getBBox]
set source [$bt getBBox]
foreach axis {xMin yMin xMax yMax} {
  if {[$actual $axis] != [$source $axis]} {error "clock entry coincidence mismatch bank $axis"}
}
puts "PAIR_CLOCK_GEOMETRY tt bank coincidence=exact layer=M5"
set i [$block findInst bx]
$i setLocation [expr {round(313.2*$dbu)}] [expr {round(71.28*$dbu)}]
$i setOrient R0
$i setPlacementStatus FIRM
set bt [$block findBTerm cb]
set bp [odb::dbBPin_create $bt]
$bp setPlacementStatus FIRM
set layer [[ord::get_db_tech] findLayer M5]
odb::dbBox_create $bp $layer [expr {round(315.55199999999996*$dbu)}] [expr {round(71.28*$dbu)}] [expr {round(315.57599999999996*$dbu)}] [expr {round(71.365*$dbu)}]
set actual [[$i findITerm clk] getBBox]
set source [$bt getBBox]
foreach axis {xMin yMin xMax yMax} {
  if {[$actual $axis] != [$source $axis]} {error "clock entry coincidence mismatch bx $axis"}
}
puts "PAIR_CLOCK_GEOMETRY tt bx coincidence=exact layer=M5"
create_clock -name A -period 833.333 -waveform {0 416.6665} [get_ports ca]
create_clock -name B -period 833.333 -waveform {0 416.6665} [get_ports cb]
set_input_transition 0 [get_ports {ca cb}]
set_clock_transition 0 [all_clocks]
set_clock_uncertainty -setup 210 [all_clocks]
set_clock_uncertainty -hold 100 [all_clocks]
set_propagated_clock [all_clocks]
proc sample {tag} {
  foreach kind {max min} {
    set paths [find_timing_paths -from [get_pins {bank/q[286]}] -to [get_pins {bx/d[219]}] -path_delay $kind -group_path_count 1]
    if {[llength $paths]!=1} {error "missing selected actual macro path $kind"}
    set p [lindex $paths 0]
    puts "PAIR_PATH $tag $kind slack=[get_property $p slack]"
  }
  foreach edge {rise fall} {
    foreach kind {max min} {
      set command [list find_timing_paths -from [get_pins {bank/q[286]}] -${edge}_to [get_pins {bx/d[219]}] -path_delay $kind -group_path_count 1]
      set paths [{*}$command]
      if {[llength $paths]!=1} {error "missing selected $edge $kind actual macro path"}
      puts "PAIR_EDGE $tag $edge $kind slack=[get_property [lindex $paths 0] slack]"
    }
  }
  report_checks -from [get_pins {bank/q[286]}] -to [get_pins {bx/d[219]}] -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -digits 6
  report_checks -from [get_pins {bank/q[286]}] -to [get_pins {bx/d[219]}] -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -digits 6
}
set_clock_latency -source -319.3 [get_clocks A]
set_clock_latency -source -84.1 [get_clocks B]
sample "tt_pin_cap_only"
source $plat/setRC.tcl
# This specific estimate treats all Manhattan wire as nominal M5; it is not
# extracted M4-access/via/M5 topology or SS RC qualification.
set_wire_rc -signal -layer M5
set_wire_rc -clock -layer M5
estimate_parasitics -placement
set_clock_latency -source 0 [get_clocks A]
set wire [get_property [get_pins bank/clk] arrival_max_rise]
puts "PAIR_ENTRY tt bank lambda0_wire=$wire childR=319.3"
set_clock_latency -source [expr {-$wire-319.3}] [get_clocks A]
set now [get_property [get_pins bank/clk] arrival_max_rise]
if {abs($now+319.3)>0.01} {error "entry compensation failure bank"}
puts "PAIR_COMP tt bank phi=[expr {$now+319.3}]"
set_clock_latency -source 0 [get_clocks B]
set wire [get_property [get_pins bx/clk] arrival_max_rise]
puts "PAIR_ENTRY tt bx lambda0_wire=$wire childR=84.1"
set_clock_latency -source [expr {-$wire-84.1}] [get_clocks B]
set now [get_property [get_pins bx/clk] arrival_max_rise]
if {abs($now+84.1)>0.01} {error "entry compensation failure bx"}
puts "PAIR_COMP tt bx phi=[expr {$now+84.1}]"
sample "tt_nominal_M5"
report_arrival -digits 6 [get_pins {bank/q[286]}]
report_arrival -digits 6 [get_pins {bx/d[219]}]
report_clock_properties [all_clocks]
write_sdc /probe/executed_tt.sdc
write_db /probe/pair_tt.odb
puts "PAIR_PASS tt nominal_M5_placementRC_diagnostic"
exit
