# Units are ASAP7 library ps. Core clock already exists at 833.333333ps.
create_clock -name h_clk -period 1024 [get_ports hclk]
set_clock_uncertainty -setup 60 [get_clocks h_clk]
set_clock_uncertainty -hold 25 [get_clocks h_clk]
# Only the coded dual-clock FIFOs and explicit fault synchronizer cross domains.
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks h_clk]
# Replace generic block IO budgets with the actual enclosing context supplied
# by the source-owned parent. No boundary or reset false-path waiver.
remove_input_delay [all_inputs -no_clocks]
remove_output_delay [all_outputs]
