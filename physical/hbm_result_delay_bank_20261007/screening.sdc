# Explicit screening envelope, NOT actual die-context budgets.
# ASAP7 native units: ps and fF. Clock and uncertainties supplied by driver.
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_input_delay -max 166.6666 -clock core_clk [all_inputs -no_clocks]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_output_delay -max 166.6666 -clock core_clk [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_load 80 [all_outputs]
