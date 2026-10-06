# DS-ROM field spine v13 (margin-first) SIGN-OFF constraints, read by tools/w18/corner_sta.py --post-sdc after the routed
# 6_final.sdc (routed over-constrained at 770 ps) with the clock propagated, one corner per run (units ps):
# the clock back at 833.333 ps with 60 / 25 ps uncertainty, and the die-integration IO budget referenced to THIS
# corner's propagated clock arrival at the boundary registers (input: q_go, output: o_ready; screen wrapper flops):
#   inputs:  max = arr(q_go) + 150 + 100, min = arr(q_go) - 150      (neighbour launch +/- 150 ps, 100 ps wire)
#   outputs: max = 100 - (arr(o_ready) - 150), min = -(arr(o_ready) + 150)
# Every port is registered at the boundary (pin-to-flop / flop-to-pin wire only); fixture ROM write ports and rst_n
# false-pathed as in the routing SDC.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
sta::worst_slack_cmd max
set fs_ai [get_property [get_pins {q_go$_DFF_P_/CLK}] arrival_max_rise]
set fs_ao [get_property [get_pins {o_ready$_DFF_P_/CLK}] arrival_max_rise]
puts "FS boundary clock arrival: in $fs_ai out $fs_ao"
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
set_input_delay  [expr {$fs_ai + 250}] -max -clock core_clk $fs_in
set_input_delay  [expr {$fs_ai - 150}] -min -clock core_clk $fs_in
set_output_delay [expr {250 - $fs_ao}] -max -clock core_clk [all_outputs]
set_output_delay [expr {-$fs_ao - 150}] -min -clock core_clk [all_outputs]
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]
set_load 3.898 [all_outputs]
