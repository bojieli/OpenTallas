set clk_period 833.333
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_input_delay -min 0 -clock core_clk $non_clock_inputs
set_input_delay -max 166.667 -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_output_delay -max 166.667 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
set_max_transition 320 [current_design]
create_clock -name core_clk -period 833.333333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_clock_latency -source 0 [get_clocks core_clk]
set_clock_latency -early 90 [get_clocks core_clk]
set_clock_latency -late 100 [get_clocks core_clk]
set ot_inputs [get_ports {launch_v launch_pc cp_job cp_gen launch_token launch_pos lease_granted release_r exec_done exec_fault retired_original_ops shared_fault}]
set ot_outputs [get_ports {native_launch lease_v release_v owned pending quiet selected done fault selected_pc held_job held_gen held_token held_pos}]
set_input_delay -clock core_clk -max 166.666666667 $ot_inputs
set_input_delay -clock core_clk -min 0 $ot_inputs
set_output_delay -clock core_clk -max 166.666666667 $ot_outputs
set_output_delay -clock core_clk -min 0 $ot_outputs
set_load 9.673192000 $ot_outputs
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ot_inputs
set ot_association_outputs [get_ports {exec_owned new_request_permit association_fault}]
set_output_delay -clock core_clk -max 166.666666667 $ot_association_outputs
set_output_delay -clock core_clk -min 0 $ot_association_outputs
set_load 9.673192000 $ot_association_outputs
set_input_delay -clock core_clk -max 166.666666667 [get_ports por_n]
set_input_delay -clock core_clk -min 0 [get_ports por_n]
