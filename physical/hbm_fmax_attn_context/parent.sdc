# Streaming parent clock/IO budget from Turing current child contract, mapped to tile clk/rst_n.
set_clock_latency -source 0 [get_clocks core_clk]
set_clock_latency -early 90 [get_clocks core_clk]
set_clock_latency -late 100 [get_clocks core_clk]
set ot_inputs [all_inputs -no_clocks]
set_input_delay -clock core_clk -max 166.6666666666667 $ot_inputs
set_input_delay -clock core_clk -min 0 $ot_inputs
set_output_delay -clock core_clk -max 166.6666666666667 [all_outputs]
set_output_delay -clock core_clk -min 0 [all_outputs]
set_load 9.673192 [all_outputs]
