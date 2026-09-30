# W18 spine channel: only the station-to-station segments are the object of the check; the chain ends are
# ports of this strip, fed/consumed by registers outside it, so they carry no timing requirement here.
create_clock -name core_clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [delete_from_list [all_inputs] [get_ports clk]]
set_false_path -to [all_outputs]
set_max_fanout 32 [current_design]
