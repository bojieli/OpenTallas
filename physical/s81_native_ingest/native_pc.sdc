# Native per-PC endpoint pathfinding: explicit shared stream clock budgets.
# Adjacent relay endpoints launch/capture these buses. Allocation is 20%T
# plus150ps wire/clock-arrival margin; actual extracted diebudget remains a gate.
set ot_data_inputs [remove_from_collection [all_inputs] [get_ports {ck rst_n}]]
set_input_delay -max 0.316667 -clock core_clk $ot_data_inputs
set_input_delay -min 0.050000 -clock core_clk $ot_data_inputs
set_output_delay -max 0.316667 -clock core_clk [all_outputs]
set_output_delay -min 0.050000 -clock core_clk [all_outputs]
set_false_path -from [get_ports rst_n]
