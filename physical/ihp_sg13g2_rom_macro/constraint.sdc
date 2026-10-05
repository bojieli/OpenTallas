# ROM macro periphery timing constraint.
# The period is a deliberately relaxed 10 ns: this flow measures AREA under a
# real router, not maximum frequency, and a tight period would trade area for
# speed and make the area number meaningless.
set clk_period 10.0
create_clock -name clk -period $clk_period [get_ports clk]
set_clock_uncertainty 0.2 [get_clocks clk]
set_input_delay  [expr $clk_period * 0.2] -clock clk [get_ports {req addr[*]}]
set_output_delay [expr $clk_period * 0.2] -clock clk [get_ports {dout[*] valid}]
set_false_path -from [get_ports rst_n]
set_driving_cell -lib_cell sg13g2_inv_2 [get_ports {req addr[*]}]
set_load 0.05 [all_outputs]
