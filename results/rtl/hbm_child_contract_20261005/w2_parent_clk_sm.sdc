# Candidate bounded parent clk_sm contract. Time ps; capacitance fF (ASAP7 native).
# SS/FF required. Budget loads are analytical; replace with larger actual extracted loads.
# No IO false paths. Root POR recovery/removal must be checked separately.
create_clock -name clk_sm -period 833.333333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk_sm]
set_clock_uncertainty -hold 25 [get_clocks clk_sm]
set_clock_latency -source 0 [get_clocks clk_sm]
set_clock_latency -early 90 [get_clocks clk_sm]
set_clock_latency -late 100 [get_clocks clk_sm]
set ot_inputs [get_ports {owned installed reserve_v pair_op rows_a rows_b op_a op_b base_a limit_a base_b limit_b provider_tag frame result_v result_op result_row result_data native_done retire_v req_r rsp_v rsp}]
set ot_outputs [get_ports {reserve_r source_permit retained done quiet fault retire_r req_v req rsp_r}]
set_input_delay -clock clk_sm -max 166.666666667 $ot_inputs
set_input_delay -clock clk_sm -min 0 $ot_inputs
set_output_delay -clock clk_sm -max 166.666666667 $ot_outputs
set_output_delay -clock clk_sm -min 0 $ot_outputs
set_load 9.673192000 $ot_outputs
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ot_inputs
# On integrated parent, use propagated clk_sm (remove estimated network latency),
# actual source/receiver arcs and extracted loads; max skew budget10ps is not a waiver.
