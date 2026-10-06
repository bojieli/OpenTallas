# hfd_attn_tile IO budget (CLAUDE HBM-ABSTRACTS attn): the die clock tree balances this tile's insertion delay (its ck
# pin is a CTS sink with a 1500 ps insertion delay, the latency every face register is built to), so the 0.2 T IO budget
# is taken against a virtual clock carrying that latency: an IO path then sees only its register's skew from 1500 ps.
# Pre-CTS (ideal clocks) core_clk carries the same network latency, so placement weighs IO paths as signoff will.
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency 1500 [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
