###############################################################################
# Created by write_sdc
# Wed Oct 14 10:06:35 2026
###############################################################################
current_design gating
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name OWN_RAW -period 833.3330 [get_ports {clk}]
set_clock_transition 0.0000 [get_clocks {OWN_RAW}]
set_clock_uncertainty -setup 150.0000 OWN_RAW
set_clock_uncertainty -hold 100.0000 OWN_RAW
set_propagated_clock [get_clocks {OWN_RAW}]
create_clock -name OWN_AUX -period 833.3330 [get_ports {clk_aux}]
set_clock_uncertainty -setup 150.0000 OWN_AUX
set_clock_uncertainty -hold 100.0000 OWN_AUX
set_propagated_clock [get_clocks {OWN_AUX}]
create_clock -name RAW_0 -period 833.3330 [get_ports {clk_child_0}]
set_clock_uncertainty -setup 150.0000 RAW_0
set_clock_uncertainty -hold 100.0000 RAW_0
set_propagated_clock [get_clocks {RAW_0}]
create_generated_clock -name G_0 -source [get_ports {clk_child_0}] -master_clock [get_clocks {RAW_0}] -divide_by 1 [get_pins {gate_0/GCLK}]
set_clock_uncertainty -setup 150.0000 G_0
set_clock_uncertainty -hold 100.0000 G_0
set_propagated_clock [get_clocks {G_0}]
create_clock -name RAW_1 -period 833.3330 [get_ports {clk_child_1}]
set_clock_uncertainty -setup 150.0000 RAW_1
set_clock_uncertainty -hold 100.0000 RAW_1
set_propagated_clock [get_clocks {RAW_1}]
create_generated_clock -name G_1 -source [get_ports {clk_child_1}] -master_clock [get_clocks {RAW_1}] -divide_by 1 [get_pins {gate_1/GCLK}]
set_clock_uncertainty -setup 150.0000 G_1
set_clock_uncertainty -hold 100.0000 G_1
set_propagated_clock [get_clocks {G_1}]
create_clock -name RAW_2 -period 833.3330 [get_ports {clk_child_2}]
set_clock_uncertainty -setup 150.0000 RAW_2
set_clock_uncertainty -hold 100.0000 RAW_2
set_propagated_clock [get_clocks {RAW_2}]
create_generated_clock -name G_2 -source [get_ports {clk_child_2}] -master_clock [get_clocks {RAW_2}] -divide_by 1 [get_pins {gate_2/GCLK}]
set_clock_uncertainty -setup 150.0000 G_2
set_clock_uncertainty -hold 100.0000 G_2
set_propagated_clock [get_clocks {G_2}]
create_clock -name RAW_3 -period 833.3330 [get_ports {clk_child_3}]
set_clock_uncertainty -setup 150.0000 RAW_3
set_clock_uncertainty -hold 100.0000 RAW_3
set_propagated_clock [get_clocks {RAW_3}]
create_generated_clock -name G_3 -source [get_ports {clk_child_3}] -master_clock [get_clocks {RAW_3}] -divide_by 1 [get_pins {gate_3/GCLK}]
set_clock_uncertainty -setup 150.0000 G_3
set_clock_uncertainty -hold 100.0000 G_3
set_propagated_clock [get_clocks {G_3}]
create_clock -name RAW_4 -period 833.3330 [get_ports {clk_child_4}]
set_clock_uncertainty -setup 150.0000 RAW_4
set_clock_uncertainty -hold 100.0000 RAW_4
set_propagated_clock [get_clocks {RAW_4}]
create_generated_clock -name G_4 -source [get_ports {clk_child_4}] -master_clock [get_clocks {RAW_4}] -divide_by 1 [get_pins {gate_4/GCLK}]
set_clock_uncertainty -setup 150.0000 G_4
set_clock_uncertainty -hold 100.0000 G_4
set_propagated_clock [get_clocks {G_4}]
create_clock -name RAW_5 -period 833.3330 [get_ports {clk_child_5}]
set_clock_uncertainty -setup 150.0000 RAW_5
set_clock_uncertainty -hold 100.0000 RAW_5
set_propagated_clock [get_clocks {RAW_5}]
create_generated_clock -name G_5 -source [get_ports {clk_child_5}] -master_clock [get_clocks {RAW_5}] -divide_by 1 [get_pins {gate_5/GCLK}]
set_clock_uncertainty -setup 150.0000 G_5
set_clock_uncertainty -hold 100.0000 G_5
set_propagated_clock [get_clocks {G_5}]
create_clock -name RAW_6 -period 833.3330 [get_ports {clk_child_6}]
set_clock_uncertainty -setup 150.0000 RAW_6
set_clock_uncertainty -hold 100.0000 RAW_6
set_propagated_clock [get_clocks {RAW_6}]
create_generated_clock -name G_6 -source [get_ports {clk_child_6}] -master_clock [get_clocks {RAW_6}] -divide_by 1 [get_pins {gate_6/GCLK}]
set_clock_uncertainty -setup 150.0000 G_6
set_clock_uncertainty -hold 100.0000 G_6
set_propagated_clock [get_clocks {G_6}]
create_clock -name RAW_7 -period 833.3330 [get_ports {clk_child_7}]
set_clock_uncertainty -setup 150.0000 RAW_7
set_clock_uncertainty -hold 100.0000 RAW_7
set_propagated_clock [get_clocks {RAW_7}]
create_generated_clock -name G_7 -source [get_ports {clk_child_7}] -master_clock [get_clocks {RAW_7}] -divide_by 1 [get_pins {gate_7/GCLK}]
set_clock_uncertainty -setup 150.0000 G_7
set_clock_uncertainty -hold 100.0000 G_7
set_propagated_clock [get_clocks {G_7}]
create_clock -name RAW_8 -period 833.3330 [get_ports {clk_child_8}]
set_clock_uncertainty -setup 150.0000 RAW_8
set_clock_uncertainty -hold 100.0000 RAW_8
set_propagated_clock [get_clocks {RAW_8}]
create_generated_clock -name G_8 -source [get_ports {clk_child_8}] -master_clock [get_clocks {RAW_8}] -divide_by 1 [get_pins {gate_8/GCLK}]
set_clock_uncertainty -setup 150.0000 G_8
set_clock_uncertainty -hold 100.0000 G_8
set_propagated_clock [get_clocks {G_8}]
create_clock -name RAW_9 -period 833.3330 [get_ports {clk_child_9}]
set_clock_uncertainty -setup 150.0000 RAW_9
set_clock_uncertainty -hold 100.0000 RAW_9
set_propagated_clock [get_clocks {RAW_9}]
create_generated_clock -name G_9 -source [get_ports {clk_child_9}] -master_clock [get_clocks {RAW_9}] -divide_by 1 [get_pins {gate_9/GCLK}]
set_clock_uncertainty -setup 150.0000 G_9
set_clock_uncertainty -hold 100.0000 G_9
set_propagated_clock [get_clocks {G_9}]
create_clock -name RAW_10 -period 833.3330 [get_ports {clk_child_10}]
set_clock_uncertainty -setup 150.0000 RAW_10
set_clock_uncertainty -hold 100.0000 RAW_10
set_propagated_clock [get_clocks {RAW_10}]
create_generated_clock -name G_10 -source [get_ports {clk_child_10}] -master_clock [get_clocks {RAW_10}] -divide_by 1 [get_pins {gate_10/GCLK}]
set_clock_uncertainty -setup 150.0000 G_10
set_clock_uncertainty -hold 100.0000 G_10
set_propagated_clock [get_clocks {G_10}]
create_clock -name RAW_11 -period 833.3330 [get_ports {clk_child_11}]
set_clock_uncertainty -setup 150.0000 RAW_11
set_clock_uncertainty -hold 100.0000 RAW_11
set_propagated_clock [get_clocks {RAW_11}]
create_generated_clock -name G_11 -source [get_ports {clk_child_11}] -master_clock [get_clocks {RAW_11}] -divide_by 1 [get_pins {gate_11/GCLK}]
set_clock_uncertainty -setup 150.0000 G_11
set_clock_uncertainty -hold 100.0000 G_11
set_propagated_clock [get_clocks {G_11}]
set_clock_latency -source -129.2000 [get_clocks {OWN_RAW}]
set_clock_latency -source -69.2000 [get_clocks {OWN_AUX}]
set_clock_latency -source -231.9271 [get_clocks {RAW_0}]
set_clock_latency -source -224.7723 [get_clocks {RAW_1}]
set_clock_latency -source -224.7723 [get_clocks {RAW_2}]
set_clock_latency -source -229.7138 [get_clocks {RAW_3}]
set_clock_latency -source -397.3698 [get_clocks {RAW_4}]
set_clock_latency -source -231.9271 [get_clocks {RAW_5}]
set_clock_latency -source -224.7723 [get_clocks {RAW_6}]
set_clock_latency -source -224.7723 [get_clocks {RAW_7}]
set_clock_latency -source -229.7138 [get_clocks {RAW_8}]
set_clock_latency -source -397.3698 [get_clocks {RAW_9}]
set_clock_latency -source -422.6145 [get_clocks {RAW_10}]
set_clock_latency -source -481.4328 [get_clocks {RAW_11}]
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_11}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_11}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -rise_to [get_clocks {RAW_11}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_RAW}] -fall_to [get_clocks {RAW_11}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_0}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_1}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_2}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_3}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_4}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_5}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_6}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_7}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_8}]  -setup 150.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_9}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_10}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_11}]  -setup 210.0000
set_clock_uncertainty -rise_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_11}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -rise_to [get_clocks {RAW_11}]  -setup 210.0000
set_clock_uncertainty -fall_from [get_clocks {OWN_AUX}] -fall_to [get_clocks {RAW_11}]  -setup 210.0000
###############################################################################
# Environment
###############################################################################
set_input_transition 0.0000 [get_ports {clk}]
set_input_transition 0.0000 [get_ports {clk_aux}]
set_input_transition 0.0000 [get_ports {clk_child_0}]
set_input_transition 0.0000 [get_ports {clk_child_1}]
set_input_transition 0.0000 [get_ports {clk_child_10}]
set_input_transition 0.0000 [get_ports {clk_child_11}]
set_input_transition 0.0000 [get_ports {clk_child_2}]
set_input_transition 0.0000 [get_ports {clk_child_3}]
set_input_transition 0.0000 [get_ports {clk_child_4}]
set_input_transition 0.0000 [get_ports {clk_child_5}]
set_input_transition 0.0000 [get_ports {clk_child_6}]
set_input_transition 0.0000 [get_ports {clk_child_7}]
set_input_transition 0.0000 [get_ports {clk_child_8}]
set_input_transition 0.0000 [get_ports {clk_child_9}]
set_input_transition 0.0000 [get_ports {next_enable}]
###############################################################################
# Design Rules
###############################################################################
