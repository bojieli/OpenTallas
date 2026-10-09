# Fixed planning IO against calibrated root insertion; parent skew bound90ps and max wire100um.
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency 393 [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay 333.5 -clock vclk $ot_in
set_output_delay 274.5 -clock vclk [all_outputs]
set_input_delay -min [expr {203 - 393 + 32.2}] -clock vclk $ot_in
# CLAUDE s81-blocks: sign fixed (was FMIN - L + 65: required = L + 25 - min must equal the sign-off FMIN + 50 - 15)
# RULE H1 (h1-verify 2026-10-08): capture at the FF mean leaf FMID + 50 - 15
set_output_delay -min [expr {393 - 203 - 10}] -clock vclk [all_outputs]
