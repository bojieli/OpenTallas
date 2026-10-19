###############################################################################
# Created by write_sdc
###############################################################################
current_design ot_pg_canonical_xor16_1019
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 770.0000 [get_ports {clk}]
set_clock_uncertainty -setup 60.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
create_clock -name ot_lb_v_core_clk -period 770.0000 
set_clock_uncertainty -setup 60.0000 ot_lb_v_core_clk
set_clock_latency 52.9600 [get_clocks {ot_lb_v_core_clk}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[0]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[10]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[11]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[12]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[13]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[14]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[15]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[1]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[2]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[3]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[4]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[5]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[6]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[7]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[8]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {a[9]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[0]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[10]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[11]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[12]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[13]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[14]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[15]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[1]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[2]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[3]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[4]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[5]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[6]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[7]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[8]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {b[9]}]
set_input_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {rst_n}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[0]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[10]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[11]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[12]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[13]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[14]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[15]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[1]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[2]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[3]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[4]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[5]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[6]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[7]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[8]}]
set_output_delay 100.0000 -clock [get_clocks {core_clk}] -add_delay [get_ports {y[9]}]
set_false_path\
    -from [get_clocks {ot_lb_v_core_clk}]\
    -to [list [get_pins {a_q[0]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[0]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[10]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[10]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[11]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[11]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[12]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[12]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[13]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[13]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[14]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[14]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[15]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[15]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[1]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[1]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[2]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[2]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[3]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[3]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[4]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[4]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[5]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[5]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[6]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[6]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[7]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[7]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[8]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[8]$_DFF_PN0_/SETN}]\
           [get_pins {a_q[9]$_DFF_PN0_/RESETN}]\
           [get_pins {a_q[9]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[0]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[0]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[10]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[10]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[11]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[11]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[12]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[12]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[13]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[13]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[14]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[14]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[15]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[15]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[1]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[1]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[2]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[2]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[3]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[3]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[4]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[4]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[5]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[5]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[6]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[6]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[7]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[7]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[8]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[8]$_DFF_PN0_/SETN}]\
           [get_pins {b_q[9]$_DFF_PN0_/RESETN}]\
           [get_pins {b_q[9]$_DFF_PN0_/SETN}]\
           [get_pins {reset_first$_DFF_PN0_/RESETN}]\
           [get_pins {reset_first$_DFF_PN0_/SETN}]\
           [get_pins {u_reset_a/q$_DFF_PN0_/RESETN}]\
           [get_pins {u_reset_a/q$_DFF_PN0_/SETN}]\
           [get_pins {u_reset_b/q$_DFF_PN0_/RESETN}]\
           [get_pins {u_reset_b/q$_DFF_PN0_/SETN}]\
           [get_pins {y[0]$_DFF_PN0_/RESETN}]\
           [get_pins {y[0]$_DFF_PN0_/SETN}]\
           [get_pins {y[10]$_DFF_PN0_/RESETN}]\
           [get_pins {y[10]$_DFF_PN0_/SETN}]\
           [get_pins {y[11]$_DFF_PN0_/RESETN}]\
           [get_pins {y[11]$_DFF_PN0_/SETN}]\
           [get_pins {y[12]$_DFF_PN0_/RESETN}]\
           [get_pins {y[12]$_DFF_PN0_/SETN}]\
           [get_pins {y[13]$_DFF_PN0_/RESETN}]\
           [get_pins {y[13]$_DFF_PN0_/SETN}]\
           [get_pins {y[14]$_DFF_PN0_/RESETN}]\
           [get_pins {y[14]$_DFF_PN0_/SETN}]\
           [get_pins {y[15]$_DFF_PN0_/RESETN}]\
           [get_pins {y[15]$_DFF_PN0_/SETN}]\
           [get_pins {y[1]$_DFF_PN0_/RESETN}]\
           [get_pins {y[1]$_DFF_PN0_/SETN}]\
           [get_pins {y[2]$_DFF_PN0_/RESETN}]\
           [get_pins {y[2]$_DFF_PN0_/SETN}]\
           [get_pins {y[3]$_DFF_PN0_/RESETN}]\
           [get_pins {y[3]$_DFF_PN0_/SETN}]\
           [get_pins {y[4]$_DFF_PN0_/RESETN}]\
           [get_pins {y[4]$_DFF_PN0_/SETN}]\
           [get_pins {y[5]$_DFF_PN0_/RESETN}]\
           [get_pins {y[5]$_DFF_PN0_/SETN}]\
           [get_pins {y[6]$_DFF_PN0_/RESETN}]\
           [get_pins {y[6]$_DFF_PN0_/SETN}]\
           [get_pins {y[7]$_DFF_PN0_/RESETN}]\
           [get_pins {y[7]$_DFF_PN0_/SETN}]\
           [get_pins {y[8]$_DFF_PN0_/RESETN}]\
           [get_pins {y[8]$_DFF_PN0_/SETN}]\
           [get_pins {y[9]$_DFF_PN0_/RESETN}]\
           [get_pins {y[9]$_DFF_PN0_/SETN}]]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 80.0000 [get_ports {y[15]}]
set_load -pin_load 80.0000 [get_ports {y[14]}]
set_load -pin_load 80.0000 [get_ports {y[13]}]
set_load -pin_load 80.0000 [get_ports {y[12]}]
set_load -pin_load 80.0000 [get_ports {y[11]}]
set_load -pin_load 80.0000 [get_ports {y[10]}]
set_load -pin_load 80.0000 [get_ports {y[9]}]
set_load -pin_load 80.0000 [get_ports {y[8]}]
set_load -pin_load 80.0000 [get_ports {y[7]}]
set_load -pin_load 80.0000 [get_ports {y[6]}]
set_load -pin_load 80.0000 [get_ports {y[5]}]
set_load -pin_load 80.0000 [get_ports {y[4]}]
set_load -pin_load 80.0000 [get_ports {y[3]}]
set_load -pin_load 80.0000 [get_ports {y[2]}]
set_load -pin_load 80.0000 [get_ports {y[1]}]
set_load -pin_load 80.0000 [get_ports {y[0]}]
###############################################################################
# Design Rules
###############################################################################
set_max_fanout 32.0000 [current_design]
