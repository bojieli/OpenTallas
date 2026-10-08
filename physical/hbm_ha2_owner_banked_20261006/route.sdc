# HA2 banked: period 770.0 ps, L SS 420.0..480.0, FF min 300.0
create_clock -name clk -period 770.000 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ins [delete_from_list [all_inputs] [get_ports clk]]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ins
set_input_delay -max 930.000 -clock clk $ins
set_input_delay -min 280.000 -clock clk $ins
set_output_delay -max -45.000 -clock clk [all_outputs]
set_output_delay -min -250.000 -clock clk [all_outputs]
set_load 4.0 [all_outputs]
set_false_path -from [get_ports rst_n]
set_max_fanout 32 [current_design]

