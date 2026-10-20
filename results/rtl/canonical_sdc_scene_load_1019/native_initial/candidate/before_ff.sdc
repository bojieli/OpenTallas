###############################################################################
# Created by write_sdc
###############################################################################
current_design ot_pg_canonical_xor16_1019
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core -period 770.0000 [get_ports {clk}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[0]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[10]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[11]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[12]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[13]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[14]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[15]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[1]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[2]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[3]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[4]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[5]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[6]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[7]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[8]}]
set_input_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {a[9]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[0]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[10]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[11]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[12]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[13]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[14]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[15]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[1]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[2]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[3]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[4]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[5]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[6]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[7]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[8]}]
set_output_delay 100.0000 -clock [get_clocks {core}] -add_delay [get_ports {y[9]}]
set_false_path -hold\
    -from [get_clocks {core}]
set_false_path -setup\
    -from [get_clocks {core}]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 51.0000 [get_ports {y[7]}]
set_load -pin_load 0.0510 [get_ports {y[6]}]
set_load -wire_load 0.0190 [get_ports {y[6]}]
set_load -pin_load 31.0000 [get_ports {y[4]}]
set_load -pin_load 31.0000 [get_ports {y[3]}]
set_load -pin_load 0.0000 [get_ports {y[2]}]
set_load -wire_load 9.0000 [get_ports {y[2]}]
set_load -pin_load 80.0000 [get_ports {y[0]}]
set_port_fanout_number -min 3 [get_ports {y[0]}]
set_port_fanout_number -max 7 [get_ports {y[0]}]
set_load  -min 41.0000 [get_nets {y[5]}]
set_load  -max 43.0000 [get_nets {y[5]}]
###############################################################################
# Design Rules
###############################################################################
