create_clock -name clk -period 833 [get_ports clk]
set_false_path -from [all_inputs]
set_false_path -to [all_outputs]
