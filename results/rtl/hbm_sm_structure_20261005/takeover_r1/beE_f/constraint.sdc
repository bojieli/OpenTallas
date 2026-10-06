# block constraints (tools/hbm_accel_smh_physical.py); clock 833 ps, 60 / 25 ps uncertainty
set clk_period 833
create_clock -name core_clk -period $clk_period [get_ports clk]
create_clock -name nbr_clk -period $clk_period
set_clock_latency -source 280 [get_clocks nbr_clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
set nbr_in [get_ports {gin* qin*}]
set nbr_out [all_outputs]
# abutting ports: 300 ps of the neighbour's flop / wire outside, its clock insertion carried by nbr_clk
set_input_delay -max 300 -clock nbr_clk $nbr_in
set_input_delay -min 30 -clock nbr_clk $nbr_in
set_output_delay -max 300 -clock nbr_clk $nbr_out
set_output_delay -min 50 -clock nbr_clk $nbr_out   ;# the neighbour lands it >= 50 ps inside (top STA checks the real pair)
set_load 2.0 [all_outputs]
set_max_fanout 32 [current_design]
