# Diagnostic only: one real ASAP7 input receiver, same FF IO references as HEAD A.
# Probes whether incremental-GRT hold repair sees the inserted input delays.
# The large production jobs remain untouched. This is not sign-off evidence.
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
set f [open /work/coupon.v w]
set ffname u_ff
set pinname v
set pinset v
if {[info exists ::env(OT_COUPON_BUS)]} {
  set ffname {u_m.g_pin.x_q[137]$_DFF_P_}
  set pinname {x[137]}
  set pinset x
  puts $f {module coupon(input clk, input [255:0] x, output y); DFFHQNx1_ASAP7_75t_R \u_m.g_pin.x_q[137]$_DFF_P_ (.CLK(clk),.D(x[137]),.QN(y)); endmodule}
} else {
  puts $f {module coupon(input clk, input v, output y); DFFHQNx1_ASAP7_75t_R u_ff(.CLK(clk),.D(v),.QN(y)); endmodule}
}
close $f
read_verilog /work/coupon.v
link_design coupon
if {[info exists ::env(OT_COUPON_NATIVE_DONTUSE)]} {
  set_dont_use "*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*"
  puts "COUPON_NATIVE_DONTUSE fractional masters excluded as in native ASAP7 flow"
}
initialize_floorplan -die_area {0 0 21.6 21.6} -core_area {2.16 2.16 19.44 19.44} -site asap7sc7p5t
source /work/make_tracks.tcl
set i [lindex [[ord::get_db_block] getInsts] 0]
puts "COUPON_RECEIVER [$i getName]"
$i setLocation 8640 8640
$i setPlacementStatus PLACED
place_pin -pin_name clk -layer M5 -location {10.8 0.042} -pin_size {0.024 0.084}
place_pin -pin_name $pinname -layer M4 -location {0.042 8.64} -pin_size {0.084 0.024}
place_pin -pin_name y -layer M4 -location {21.558 8.64} -pin_size {0.084 0.024}
create_clock -name clk -period 833 [get_ports clk]
create_clock -name vclk -period 833
set_clock_latency -source 190.78 [get_clocks clk]
set_clock_latency -source 202.5 [get_clocks vclk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_clock_uncertainty -hold 12.5 -from [get_clocks vclk] -to [get_clocks clk]
set_input_delay -clock vclk -min -40 [get_ports $pinset]
set_input_delay -clock vclk -max 166.6 [get_ports $pinset]
set_output_delay -clock vclk -min 0 [get_ports y]
set_output_delay -clock vclk -max 166.6 [get_ports y]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [get_ports $pinset]
set_load 2 [get_ports y]
set_propagated_clock [get_clocks clk]
set ::env(OT_RC_CAL) 0.8,0.9
source /work/rc_cal.tcl
set_routing_layers -signal M2-M5 -clock M4-M5
global_route -resistance_aware
estimate_parasitics -global_routing
proc metric {stage} {
  set w [sta::time_sta_ui [sta::worst_slack_cmd min]]
  puts "COUPON $stage hold_ps $w instances [llength [[ord::get_db_block] getInsts]]"
  report_checks -path_delay min -group_path_count 2 -format full_clock_expanded
}
metric BEFORE
write_db /work/before.odb
global_route -start_incremental
# Use the normal100% repair budget on this one-receiver experiment. The observed
# outcomes are one HB4 cell or four ordinary buffers; this is not core sign-off.
set rc [catch {repair_timing -hold -hold_margin 0 -max_buffer_percent 100} msg]
puts "COUPON repair_return $rc $msg"
metric IN_REPAIR
detailed_placement
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
metric AFTER_REROUTE
write_db /work/after.odb
write_sdc /work/after.sdc
exit
