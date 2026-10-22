###############################################################################
# Created by write_sdc
# Tue Oct 20 11:44:21 2026
###############################################################################
current_design fc_coupon
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name input_clk -period 900.0000 -waveform {23.0000 377.0000} [get_ports {ck}]
set_clock_uncertainty -setup 60.0000 input_clk
set_clock_uncertainty -hold 25.0000 input_clk
set_propagated_clock [get_clocks {input_clk}]
create_generated_clock -name ck_o_fwd -source [get_ports {ck}] -divide_by 1 -invert [get_ports {ck_o}]
set_clock_uncertainty -setup 60.0000 ck_o_fwd
set_clock_uncertainty -hold 25.0000 ck_o_fwd
set_propagated_clock [get_clocks {ck_o_fwd}]
set_clock_latency -source 17.0000 [get_clocks {input_clk}]
set_input_delay 70.0000 -clock [get_clocks {input_clk}] -add_delay [get_ports {d}]
set_output_delay 50.0000 -clock [get_clocks {input_clk}] -add_delay [get_ports {q}]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 37.0000 [get_ports {ck_o}]
set_load -pin_load 20.0000 [get_ports {q}]
set_input_transition 20.0000 [get_ports {ck}]
set_input_transition 15.0000 [get_ports {d}]
###############################################################################
# Design Rules
###############################################################################
