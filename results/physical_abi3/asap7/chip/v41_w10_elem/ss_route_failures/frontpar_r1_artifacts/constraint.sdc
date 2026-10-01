set clk_period 833
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_input_delay -min 360 -clock core_clk $non_clock_inputs
set_input_delay -max 727 -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_output_delay -min -560 -clock core_clk [all_outputs]
set_output_delay -max -193 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
set_max_transition 320 [current_design]
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]
