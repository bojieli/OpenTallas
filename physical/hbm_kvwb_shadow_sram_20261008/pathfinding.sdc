# PATHFINDING: actual die slot and neighbor insertion/budgets are pending.
# Provisional 300 ps external max and 30 ps input min; no headline/abutment claim.
create_clock -name core_clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set data_inputs {}
foreach port [all_inputs] {
  if {[get_full_name $port] ni {clk rst_n}} {lappend data_inputs $port}
}
set_input_delay -max 300 -clock core_clk $data_inputs
set_input_delay -min 30 -clock core_clk $data_inputs
set_output_delay -max 300 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_false_path -from [get_ports rst_n]
set_load 2.0 [all_outputs]
set_max_fanout 32 [current_design]
