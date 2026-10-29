set corner $::env(CORNER)
read_liberty INVBUF_${corner}.lib
read_verilog coupon.v
link_design head_driver_coupon
create_clock -name vclk -period 833
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_input_delay 0 -clock vclk [get_ports a]
set_input_transition 320 [get_ports a]
set_output_delay 0 -clock vclk [all_outputs]
set_load 15 [get_ports inv_y]
set_load 0.852 [get_ports buf_y]
read_spef hop.spef
report_checks -path_delay max -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} -digits 6
foreach cell {inv buf8} {
 set pin [get_pins $cell/Y]
 foreach edge {rise fall} {
   puts "COUPON $corner $cell $edge delay_min_ps=[get_property $pin arrival_min_$edge] delay_max_ps=[get_property $pin arrival_max_$edge] slew_min_ps=[get_property $pin slew_min_$edge] slew_max_ps=[get_property $pin slew_max_$edge]"
 }
}
foreach edge {rise fall} {
 puts "FAR_PI $corner $edge delay_min_ps=[get_property [sta::get_port_pin [get_ports buf_y]] arrival_min_$edge] delay_max_ps=[get_property [sta::get_port_pin [get_ports buf_y]] arrival_max_$edge] slew_min_ps=[get_property [sta::get_port_pin [get_ports buf_y]] slew_min_$edge] slew_max_ps=[get_property [sta::get_port_pin [get_ports buf_y]] slew_max_$edge]"
}
report_check_types -max_slew -max_capacitance -violators
puts "COUPON_DONE $corner"
