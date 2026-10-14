###############################################################################
# Created by write_sdc
# Wed Oct 14 08:09:52 2026
###############################################################################
current_design pair
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name A -period 833.3330 [get_ports {ca}]
set_clock_transition 0.0000 [get_clocks {A}]
set_clock_uncertainty -setup 210.0000 A
set_clock_uncertainty -hold 100.0000 A
set_propagated_clock [get_clocks {A}]
create_clock -name B -period 833.3330 [get_ports {cb}]
set_clock_transition 0.0000 [get_clocks {B}]
set_clock_uncertainty -setup 210.0000 B
set_clock_uncertainty -hold 100.0000 B
set_propagated_clock [get_clocks {B}]
set_clock_latency -source -266.4025 [get_clocks {A}]
set_clock_latency -source -67.3004 [get_clocks {B}]
###############################################################################
# Environment
###############################################################################
set_input_transition 0.0000 [get_ports {ca}]
set_input_transition 0.0000 [get_ports {cb}]
###############################################################################
# Design Rules
###############################################################################
