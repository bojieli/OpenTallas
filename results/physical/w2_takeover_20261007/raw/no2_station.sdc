# W2 rb station receiver clock-root contract: period 730.0 ps, L SS 531.0..570.0 FFmin 341.0 ps, setup skew 150.0 ps, hold skew 50.0 ps, IO windows at 833.333 ps
create_clock -name clk_sm -period 730.000 [get_ports clk_sm]
set prev [get_ports clk_sm]
set master clk_sm
for {set i 0} {$i<4} {incr i} {
 set roots {}
 foreach p [get_pins -hierarchical *] {
  if {[regexp "u_clk${i}.*/Y$" [get_full_name $p]]} {lappend roots $p}
 }
 if {[llength $roots]!=1} {error "missing kept station forwarding inverter $i"}
 create_generated_clock -name forwarded$i -source $prev -master_clock $master -divide_by 1 -invert [lindex $roots 0]
 set prev [lindex $roots 0];set master forwarded$i
}
create_generated_clock -name forwarded_port -source $prev -master_clock $master -divide_by 1 [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 50 [all_clocks]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [delete_from_list [all_inputs] [get_ports clk_sm]]
foreach p [all_inputs] {
 if {[get_full_name $p] eq "clk_sm"} {continue}
 set_input_delay -max 976.667 -clock clk_sm $p
 set_input_delay -min 405.200 -clock clk_sm $p
}
foreach p [all_outputs] {
 if {[get_full_name $p] eq "fclk_o"} {continue}
 set_output_delay -max -199.333 -clock clk_sm $p
 set_output_delay -min -281.000 -clock clk_sm $p
 set_load 4.0 $p
}
set_max_fanout 32 [current_design]
