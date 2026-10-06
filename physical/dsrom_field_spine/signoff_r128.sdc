# DS-ROM field spine v13 (margin-first) SIGN-OFF constraints, read by tools/w18/corner_sta.py --post-sdc after the routed
# 6_final.sdc (routed over-constrained at 770 ps) with the clock propagated, one corner per run (units ps): the clock
# back at 833.333 ps with 60 / 25 ps uncertainty, and the die-integration IO budget against THIS corner's propagated
# clock arrival at the boundary registers (input side q_go, output side o_ready; screen wrapper flops), as virtual
# neighbour clocks with that source latency:
#   setup: neighbour +/- 150 ps across clock regions + 100 ps wire  -> input / output max 250
#   hold:  50 ps hold IO uncertainty (owner clarification)          -> input / output min -50
# Every port is registered at the boundary; fixture ROM write ports and rst_n false-pathed as in the routing SDC.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [get_clocks core_clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
sta::worst_slack_cmd max
set fs_ai [get_property [get_pins {q_go$_DFF_P_/CLK}] arrival_max_rise]
set fs_ao [get_property [get_pins {o_ready$_DFF_P_/CLK}] arrival_max_rise]
puts "FS boundary clock arrival: in $fs_ai out $fs_ao"
create_clock -name io_ci -period 833.333
create_clock -name io_co -period 833.333
set_clock_latency -source $fs_ai [get_clocks io_ci]
set_clock_latency -source $fs_ao [get_clocks io_co]
set_clock_uncertainty -setup 60 [get_clocks {io_ci io_co}]
set_clock_uncertainty -hold 25 [get_clocks {io_ci io_co}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
set_input_delay  250 -max -clock io_ci $fs_in
set_input_delay  -50 -min -clock io_ci $fs_in
set_output_delay 250 -max -clock io_co [all_outputs]
set_output_delay -50 -min -clock io_co [all_outputs]
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]
set_load 3.898 [all_outputs]
