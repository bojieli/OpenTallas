if {[llength [get_libs -quiet *_FF_*]]} {
# RULE H1 (h1-verify 2026-10-08): outputs vs the FF mean leaf + 50 (sender, latest capture); inputs launch at the FF mean, 25 (receiver)
set_clock_latency 203 [get_clocks vclk]
create_clock -name vclki -period [get_property [get_clocks core_clk] period]
set_clock_latency 203 [get_clocks vclki]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock vclk $ot_in
set_input_delay 333.5 -clock vclki $ot_in
set_input_delay -min 32.2 -clock vclki $ot_in
set_clock_uncertainty -hold 25 -from [get_clocks vclki] -to [get_clocks core_clk]
set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
}
