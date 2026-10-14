###############################################################################
# Created by write_sdc
###############################################################################
current_design dsfd_rly_15_SN
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
set_clock_latency 31.3752 [get_clocks {ot_lb_v_core_clk}]
set_clock_latency -source 0.0000 [get_clocks {ot_lb_v_core_clk}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[0]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[0]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[10]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[10]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[11]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[11]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[12]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[12]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[13]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[13]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[14]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[14]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[1]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[1]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[2]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[2]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[3]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[3]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[4]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[4]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[5]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[5]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[6]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[6]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[7]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[7]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[8]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[8]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {i[9]}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {i[9]}]
set_input_delay 28.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {rs}]
set_input_delay 287.3398 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {rs}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[0]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[0]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[10]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[10]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[11]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[11]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[12]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[12]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[13]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[13]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[14]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[14]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[1]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[1]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[2]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[2]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[3]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[3]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[4]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[4]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[5]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[5]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[6]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[6]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[7]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[7]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[8]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[8]}]
set_output_delay -78.4336 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {o[9]}]
set_output_delay 225.9942 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {o[9]}]
set_false_path\
    -from [get_clocks {ot_lb_v_core_clk}]\
    -to [list [get_pins {u.o[0]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[0]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[10]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[10]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[11]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[11]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[12]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[12]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[13]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[13]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[14]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[14]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[1]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[1]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[2]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[2]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[3]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[3]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[4]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[4]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[5]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[5]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[6]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[6]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[7]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[7]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[8]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[8]$_DFF_PN0_/SETN}]\
           [get_pins {u.o[9]$_DFF_PN0_/RESETN}]\
           [get_pins {u.o[9]$_DFF_PN0_/SETN}]]
###############################################################################
# Environment
###############################################################################
set_input_transition 150.0000 [get_ports {rs}]
set_input_transition 150.0000 [get_ports {i[14]}]
set_input_transition 150.0000 [get_ports {i[13]}]
set_input_transition 150.0000 [get_ports {i[12]}]
set_input_transition 150.0000 [get_ports {i[11]}]
set_input_transition 150.0000 [get_ports {i[10]}]
set_input_transition 150.0000 [get_ports {i[9]}]
set_input_transition 150.0000 [get_ports {i[8]}]
set_input_transition 150.0000 [get_ports {i[7]}]
set_input_transition 150.0000 [get_ports {i[6]}]
set_input_transition 150.0000 [get_ports {i[5]}]
set_input_transition 150.0000 [get_ports {i[4]}]
set_input_transition 150.0000 [get_ports {i[3]}]
set_input_transition 150.0000 [get_ports {i[2]}]
set_input_transition 150.0000 [get_ports {i[1]}]
set_input_transition 150.0000 [get_ports {i[0]}]
###############################################################################
# Design Rules
###############################################################################
set_max_transition 260.0000 [current_design]
set_max_fanout 32.0000 [current_design]
