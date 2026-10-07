# HA2 banked: period 730.0 ps, L SS 791.65..968.71, FF min 484.57
create_clock -name clk -period 730.000 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ins [delete_from_list [all_inputs] [get_ports clk]]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ins
set_input_delay -max 1315.377 -clock clk $ins
set_input_delay -min 771.650 -clock clk $ins
set_output_delay -max -519.983 -clock clk [all_outputs]
set_output_delay -min -741.650 -clock clk [all_outputs]
set_load 4.0 [all_outputs]
set_false_path -from [get_ports rst_n]
set_max_fanout 32 [current_design]

