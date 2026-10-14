###############################################################################
# Created by write_sdc
###############################################################################
current_design dsfd_rly_2_NW
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 833.3330 [get_ports {ck}]
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
create_clock -name ot_lb_v_core_clk -period 770.0000 
set_clock_uncertainty -setup 60.0000 ot_lb_v_core_clk
set_clock_uncertainty -hold 25.0000 ot_lb_v_core_clk
set_clock_latency 47.6470 [get_clocks {ot_lb_v_core_clk}]
set_clock_latency -source 0.0000 [get_clocks {ot_lb_v_core_clk}]
set_input_delay 45.4263 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[0]}]
set_input_delay 304.3716 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[0]}]
set_input_delay 45.4263 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[1]}]
set_input_delay 304.3716 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[1]}]
set_input_delay 45.4263 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {rs}]
set_input_delay 304.3716 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {rs}]
set_output_delay -95.4263 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[0]}]
set_output_delay 208.9625 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[0]}]
set_output_delay -95.4263 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[1]}]
set_output_delay 208.9625 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[1]}]
set_false_path\
    -from [get_clocks {ot_lb_v_core_clk}]\
    -to [list [get_pins {u.o[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[0]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[1]$_DFF_PN0_/SETN}]]
###############################################################################
# Environment
###############################################################################
set_input_transition 150.0000 [get_ports {rs}]
set_input_transition 150.0000 [get_ports {i[1]}]
set_input_transition 150.0000 [get_ports {i[0]}]
###############################################################################
# Design Rules
###############################################################################
set_max_transition 260.0000 [current_design]
set_max_fanout 32.0000 [current_design]
