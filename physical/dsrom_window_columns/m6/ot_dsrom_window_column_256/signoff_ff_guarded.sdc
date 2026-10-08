if {[llength [get_libs -quiet *_FF_*]]} {
set_clock_latency 159 [get_clocks vclk]
create_clock -name vclki -period [get_property [get_clocks core_clk] period]
set_clock_latency 171 [get_clocks vclki]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock vclk $ot_in
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2}] -clock vclki $ot_in
set_input_delay -min 0 -clock vclki $ot_in
set_clock_uncertainty -hold 50 -from [get_clocks vclki] -to [get_clocks core_clk]
set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
}
